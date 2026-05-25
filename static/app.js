const state = {
  articles: [],
  selectedId: null,
  pendingHtml: "",
  articleCollapsed: false,
  bookmarklet: "",
  searchTimer: null,
};

const els = {
  articleList: document.querySelector("#articleList"),
  articleBody: document.querySelector("#articleBody"),
  bookmarkletLink: document.querySelector("#bookmarkletLink"),
  bookmarkletStatus: document.querySelector("#bookmarkletStatus"),
  collapseAllButton: document.querySelector("#collapseAllButton"),
  copyBookmarkletButton: document.querySelector("#copyBookmarkletButton"),
  deleteButton: document.querySelector("#deleteButton"),
  editorPane: document.querySelector("#editorPane"),
  expandAllButton: document.querySelector("#expandAllButton"),
  newButton: document.querySelector("#newButton"),
  outline: document.querySelector("#outline"),
  pasteSurface: document.querySelector("#pasteSurface"),
  readerPane: document.querySelector("#readerPane"),
  readerSource: document.querySelector("#readerSource"),
  readerTitle: document.querySelector("#readerTitle"),
  refreshButton: document.querySelector("#refreshButton"),
  saveButton: document.querySelector("#saveButton"),
  saveStatus: document.querySelector("#saveStatus"),
  searchInput: document.querySelector("#searchInput"),
  searchMeta: document.querySelector("#searchMeta"),
  titleInput: document.querySelector("#titleInput"),
  toggleArticleButton: document.querySelector("#toggleArticleButton"),
  urlInput: document.querySelector("#urlInput"),
  webCollectButton: document.querySelector("#webCollectButton"),
  webCollectResults: document.querySelector("#webCollectResults"),
  webCollectStatus: document.querySelector("#webCollectStatus"),
  webCountInput: document.querySelector("#webCountInput"),
  webKeywordInput: document.querySelector("#webKeywordInput"),
  webModeSelect: document.querySelector("#webModeSelect"),
};

function setStatus(message, isError = false) {
  els.saveStatus.textContent = message;
  els.saveStatus.className = isError ? "error" : "toast";
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload;
}

async function loadArticles() {
  const query = els.searchInput.value.trim();
  const path = query ? `/api/articles?q=${encodeURIComponent(query)}` : "/api/articles";
  const payload = await api(path);
  state.articles = payload.articles || [];
  renderArticleList();
}

async function loadBookmarklet() {
  try {
    const payload = await api("/api/bookmarklet");
    state.bookmarklet = payload.bookmarklet || "";
    els.bookmarkletLink.href = state.bookmarklet;
    els.bookmarkletLink.textContent = payload.label || "Save to Article Outliner";
    els.bookmarkletStatus.textContent = "Ready";
    els.bookmarkletStatus.className = "toast";
    els.copyBookmarkletButton.disabled = !state.bookmarklet;
  } catch (error) {
    els.bookmarkletStatus.textContent = error.message;
    els.bookmarkletStatus.className = "error";
    els.copyBookmarkletButton.disabled = true;
  }
}

function renderArticleList() {
  const query = els.searchInput.value.trim();
  const matches = state.articles;
  els.searchMeta.textContent = query
    ? `${matches.length} match${matches.length === 1 ? "" : "es"} in saved articles`
    : "All saved articles";

  els.articleList.innerHTML = "";
  if (!matches.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No articles";
    els.articleList.append(empty);
    return;
  }

  for (const article of matches) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `article-item${article.id === state.selectedId ? " active" : ""}`;
    const matchLabel = article.match_field ? `<span class="match-label">${escapeHtml(matchLabelText(article.match_field))}</span>` : "";
    button.innerHTML = `
      <strong>${escapeHtml(article.title)}</strong>
      <span>${escapeHtml(article.source_url || "Saved article")}</span>
      <span class="snippet">${matchLabel}${escapeHtml(article.summary || "")}</span>
      <span>${formatDate(article.updated_at)}</span>
    `;
    button.addEventListener("click", () => openArticle(article.id));
    els.articleList.append(button);
  }
}

function matchLabelText(field) {
  if (field === "title") {
    return "Title";
  }
  if (field === "source_url") {
    return "URL";
  }
  if (field === "body") {
    return "Body";
  }
  return "";
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function startNewClip() {
  state.selectedId = null;
  state.pendingHtml = "";
  els.titleInput.value = "";
  els.urlInput.value = "";
  els.pasteSurface.innerHTML = "";
  els.editorPane.hidden = false;
  els.readerPane.hidden = true;
  setStatus("Ready");
  renderArticleList();
  els.titleInput.focus();
}

function deriveTitleFromHtml(rawHtml) {
  const doc = new DOMParser().parseFromString(rawHtml, "text/html");
  const titleNode = doc.querySelector("h1, h2, h3, title");
  return titleNode ? titleNode.textContent.trim().replace(/\s+/g, " ").slice(0, 180) : "";
}

function normalizePaste(event) {
  const clipboard = event.clipboardData;
  if (!clipboard) {
    return;
  }
  const richHtml = clipboard.getData("text/html");
  const plainText = clipboard.getData("text/plain");
  if (!richHtml && !plainText) {
    return;
  }

  event.preventDefault();
  const html = richHtml || `<p>${escapeHtml(plainText).replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>")}</p>`;
  state.pendingHtml = html;
  els.pasteSurface.innerHTML = html;

  if (!els.titleInput.value.trim()) {
    els.titleInput.value = deriveTitleFromHtml(html);
  }
  if (!els.urlInput.value.trim() && /^https?:\/\//i.test(plainText.trim())) {
    els.urlInput.value = plainText.trim();
  }
  setStatus("Ready");
}

async function saveClip() {
  const html = els.pasteSurface.innerHTML;
  const payload = {
    title: els.titleInput.value.trim(),
    source_url: els.urlInput.value.trim(),
    html,
  };

  if (!payload.html.trim()) {
    setStatus("Paste required", true);
    return;
  }

  els.saveButton.disabled = true;
  setStatus("Saving");
  try {
    const result = await api("/api/articles", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadArticles();
    await openArticle(result.article.id);
    setStatus("Saved");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    els.saveButton.disabled = false;
  }
}

async function openArticle(id) {
  const payload = await api(`/api/articles/${id}`);
  const article = payload.article;
  state.selectedId = article.id;
  state.articleCollapsed = false;
  els.editorPane.hidden = true;
  els.readerPane.hidden = false;
  els.readerTitle.textContent = article.title;
  if (article.source_url) {
    els.readerSource.hidden = false;
    els.readerSource.href = article.source_url;
    els.readerSource.textContent = article.source_url;
  } else {
    els.readerSource.hidden = true;
    els.readerSource.removeAttribute("href");
    els.readerSource.textContent = "";
  }
  els.articleBody.classList.remove("is-hidden");
  els.toggleArticleButton.textContent = "Article";
  renderArticle(article.html);
  renderArticleList();
}

function renderArticle(html) {
  els.articleBody.innerHTML = html;
  buildSections();
  highlightOpenArticle();
  buildOutline();
}

function clearHighlights() {
  els.articleBody.querySelectorAll("mark.search-hit").forEach((mark) => {
    mark.replaceWith(document.createTextNode(mark.textContent));
  });
  els.articleBody.normalize();
}

function highlightOpenArticle() {
  clearHighlights();
  const query = els.searchInput.value.trim();
  if (!query) {
    return;
  }

  const pattern = new RegExp(escapeRegExp(query), "gi");
  const walker = document.createTreeWalker(els.articleBody, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || parent.closest("button, mark.search-hit")) {
        return NodeFilter.FILTER_REJECT;
      }
      pattern.lastIndex = 0;
      return pattern.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });

  const matches = [];
  while (walker.nextNode()) {
    matches.push(walker.currentNode);
  }

  for (const node of matches) {
    pattern.lastIndex = 0;
    const fragment = document.createDocumentFragment();
    let lastIndex = 0;
    for (const match of node.nodeValue.matchAll(pattern)) {
      if (match.index > lastIndex) {
        fragment.append(document.createTextNode(node.nodeValue.slice(lastIndex, match.index)));
      }
      const mark = document.createElement("mark");
      mark.className = "search-hit";
      mark.textContent = match[0];
      fragment.append(mark);
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < node.nodeValue.length) {
      fragment.append(document.createTextNode(node.nodeValue.slice(lastIndex)));
    }
    node.replaceWith(fragment);
  }

  els.articleBody.querySelectorAll("mark.search-hit").forEach((mark) => {
    const section = mark.closest(".clip-section");
    if (section) {
      toggleSection(section, false);
    }
  });
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildSections() {
  const headings = Array.from(els.articleBody.querySelectorAll("h1, h2, h3, h4, h5, h6"));
  let index = 0;

  for (const heading of headings) {
    if (heading.closest(".clip-section")?.firstElementChild === heading) {
      continue;
    }

    const level = Number(heading.tagName.slice(1));
    const parent = heading.parentNode;
    const wrapper = document.createElement("section");
    wrapper.className = "clip-section";
    wrapper.dataset.sectionId = `section-${++index}`;
    wrapper.dataset.level = String(level);

    parent.insertBefore(wrapper, heading);
    wrapper.appendChild(heading);
    heading.classList.add("section-heading");
    heading.id = heading.id || wrapper.dataset.sectionId;

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "section-toggle";
    toggle.setAttribute("aria-label", "折りたたみ");
    toggle.textContent = "-";
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleSection(wrapper);
    });
    heading.insertBefore(toggle, heading.firstChild);

    while (wrapper.nextSibling) {
      const next = wrapper.nextSibling;
      if (next.nodeType === Node.ELEMENT_NODE && /^H[1-6]$/.test(next.tagName)) {
        const nextLevel = Number(next.tagName.slice(1));
        if (nextLevel <= level) {
          break;
        }
      }
      wrapper.appendChild(next);
    }
  }
}

function toggleSection(section, collapsed = undefined) {
  const shouldCollapse = collapsed ?? !section.classList.contains("is-collapsed");
  section.classList.toggle("is-collapsed", shouldCollapse);
  const button = section.querySelector(":scope > .section-heading > .section-toggle");
  if (button) {
    button.textContent = shouldCollapse ? "+" : "-";
  }
}

function setAllSections(collapsed) {
  els.articleBody.querySelectorAll(".clip-section").forEach((section) => {
    toggleSection(section, collapsed);
  });
}

function buildOutline() {
  els.outline.innerHTML = "";
  const headings = Array.from(els.articleBody.querySelectorAll(".section-heading"));
  if (!headings.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No headings";
    els.outline.append(empty);
    return;
  }

  for (const heading of headings) {
    const level = Number(heading.tagName.slice(1));
    const button = document.createElement("button");
    button.type = "button";
    button.style.paddingLeft = `${Math.max(0, level - 1) * 12 + 7}px`;
    button.textContent = heading.textContent.replace(/^[+-]\s*/, "").trim() || heading.tagName;
    button.addEventListener("click", () => heading.scrollIntoView({ behavior: "smooth", block: "start" }));
    els.outline.append(button);
  }
}

async function deleteCurrentArticle() {
  if (!state.selectedId) {
    return;
  }
  await api(`/api/articles/${state.selectedId}`, { method: "DELETE" });
  await loadArticles();
  startNewClip();
}

function toggleWholeArticle() {
  state.articleCollapsed = !state.articleCollapsed;
  els.articleBody.classList.toggle("is-hidden", state.articleCollapsed);
  els.toggleArticleButton.textContent = state.articleCollapsed ? "Show" : "Article";
}

async function copyBookmarklet() {
  if (!state.bookmarklet) {
    return;
  }
  try {
    await navigator.clipboard.writeText(state.bookmarklet);
    els.bookmarkletStatus.textContent = "Copied";
    els.bookmarkletStatus.className = "toast";
  } catch (error) {
    els.bookmarkletStatus.textContent = "Copy failed";
    els.bookmarkletStatus.className = "error";
  }
}

function setWebCollectStatus(message, isError = false) {
  els.webCollectStatus.textContent = message;
  els.webCollectStatus.className = isError ? "error" : "toast";
}

function renderWebCollectResults(payload) {
  const imported = payload.imported || [];
  const skipped = payload.skipped || [];
  const failed = payload.failed || [];
  const rows = [];

  for (const item of imported) {
    rows.push(`<li><strong>Saved</strong><span>${escapeHtml(item.title || item.source_url)}</span></li>`);
  }
  for (const item of skipped) {
    rows.push(`<li><strong>Skipped</strong><span>${escapeHtml(item.title || item.url)} (${escapeHtml(item.reason || "")})</span></li>`);
  }
  for (const item of failed) {
    rows.push(`<li><strong>Failed</strong><span>${escapeHtml(item.title || item.url)}: ${escapeHtml(item.error || "")}</span></li>`);
  }

  els.webCollectResults.innerHTML = rows.length ? `<ul>${rows.join("")}</ul>` : "";
}

async function collectFromWeb() {
  const keyword = els.webKeywordInput.value.trim();
  const count = Math.max(1, Math.min(10, Number.parseInt(els.webCountInput.value, 10) || 3));
  const mode = els.webModeSelect.value === "fuzzy" ? "fuzzy" : "exact";

  if (!keyword) {
    setWebCollectStatus("Keyword required", true);
    els.webKeywordInput.focus();
    return;
  }

  els.webCollectButton.disabled = true;
  setWebCollectStatus("Collecting");
  els.webCollectResults.innerHTML = "";
  try {
    const payload = await api("/api/web-collect", {
      method: "POST",
      body: JSON.stringify({ keyword, count, mode }),
    });
    renderWebCollectResults(payload);
    await loadArticles();
    const importedCount = (payload.imported || []).length;
    const skippedCount = (payload.skipped || []).length;
    const failedCount = (payload.failed || []).length;
    setWebCollectStatus(`Saved ${importedCount}, skipped ${skippedCount}, failed ${failedCount}`, failedCount > 0 && importedCount === 0);
  } catch (error) {
    setWebCollectStatus(error.message, true);
  } finally {
    els.webCollectButton.disabled = false;
  }
}

els.pasteSurface.addEventListener("paste", normalizePaste);
els.saveButton.addEventListener("click", saveClip);
els.newButton.addEventListener("click", startNewClip);
els.refreshButton.addEventListener("click", loadArticles);
els.copyBookmarkletButton.addEventListener("click", copyBookmarklet);
els.webCollectButton.addEventListener("click", collectFromWeb);
els.webKeywordInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    collectFromWeb();
  }
});
els.searchInput.addEventListener("input", () => {
  window.clearTimeout(state.searchTimer);
  state.searchTimer = window.setTimeout(() => {
    loadArticles().catch((error) => setStatus(error.message, true));
    if (!els.readerPane.hidden) {
      highlightOpenArticle();
    }
  }, 180);
});
els.collapseAllButton.addEventListener("click", () => setAllSections(true));
els.expandAllButton.addEventListener("click", () => setAllSections(false));
els.deleteButton.addEventListener("click", deleteCurrentArticle);
els.toggleArticleButton.addEventListener("click", toggleWholeArticle);

loadArticles().catch((error) => setStatus(error.message, true));
loadBookmarklet();
