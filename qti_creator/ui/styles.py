"""Shared styles and CSS for QTI-Creator multipage application."""

from src.ui_icons import button_icon_css

SHARED_CSS = """
/* ── Multipage Navigation Bar: align to left ── */
.nav-holder nav,
nav.svelte-99kmwu {
  justify-content: flex-start !important;
}

/* ── Reset and layout limits ── */
.docs-content {
  max-width: 960px;
  margin-inline: auto;
  padding: 1rem 1.5rem;
}

.home-container {
  max-width: 960px;
  margin-inline: auto;
  padding: 1.5rem 1.5rem;
}

/* Empty diagnostics should not reserve a row between status and workspace. */
.editor-diagnostics.block:has(.prose:empty) { display: none !important; }
.quiz-editor-page-container { gap: 12px !important; }
.quiz-editor-page-container > .quiz-command-bar { margin-bottom: 0 !important; }

/* Gradio rotates a downward triangle left when closed; use right/down chevrons. */
.docs-content button.label-wrap > .icon,
.home-container button.label-wrap > .icon,
.media-page-container button.label-wrap > .icon {
  font-size: 0 !important;
  transform: rotate(0deg) !important;
}
.docs-content button.label-wrap > .icon::after,
.home-container button.label-wrap > .icon::after,
.media-page-container button.label-wrap > .icon::after {
  content: "";
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(-45deg);
}
.docs-content button.label-wrap.open > .icon::after,
.home-container button.label-wrap.open > .icon::after,
.media-page-container button.label-wrap.open > .icon::after { transform: rotate(45deg); }

/* Shared page titles, primary actions, and reference table layout. */
.docs-content h2, .editor-header-row h2, .media-header-bar h2 {
  font-size: 1.4rem !important;
  font-weight: 700 !important;
  line-height: 1.3 !important;
  margin: 0 0 0.75rem !important;
}
#btn_open_editor, #btn_generate_package, #btn_download_package,
#btn_upload_media_zip, #btn_upload_media_zip button {
  min-height: 40px !important;
  padding: 8px 16px !important;
  font-size: 0.95rem !important;
  border-radius: 6px !important;
}
.syntax-content table {
  width: 100%;
  table-layout: auto;
}
.syntax-content th, .syntax-content td {
  word-break: normal !important;
  overflow-wrap: normal !important;
}
.syntax-content th:first-child, .syntax-content td:first-child {
  min-width: 9rem;
  width: 18%;
}
.syntax-content .prose { overflow-x: auto; }
.bias-details { width: 100%; font-weight: 400; color: #92400e; }
.bias-details summary { cursor: pointer; font-size: 0.85rem; }

/* ── No-scroll overrides for static markdown blocks ── */
.no-scroll-block,
.no-scroll-block > div,
.no-scroll-block .prose {
  overflow: visible !important;
  overflow-y: visible !important;
}

.no-scroll-block h1, .no-scroll-block h2, .no-scroll-block h3,
.no-scroll-block h4, .no-scroll-block h5, .no-scroll-block h6 {
  overflow: visible !important;
  margin-top: 0.25rem !important;
  margin-bottom: 0.25rem !important;
}

/* ── Markdown tables ── */
table.table, table.b_default {
  width: 100% !important;
  border-collapse: collapse !important;
  margin: 12px 0 !important;
  font-size: 0.92em !important;
}
table.table th, table.table td,
table.b_default th, table.b_default td {
  border: 1px solid #cbd5e1 !important;
  padding: 8px 12px !important;
  line-height: 1.4 !important;
}
table.table th {
  background-color: #f1f5f9 !important;
  font-weight: 600 !important;
  color: #1e293b !important;
}
table.table tbody tr:nth-child(even) {
  background-color: #f8fafc !important;
}

/* ── Hidden Bridge Element for Visual Editor Events ── */
#hotspot_action_input {
  display: none !important;
  visibility: hidden !important;
  position: absolute !important;
  pointer-events: none !important;
  opacity: 0 !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
}
.quiz-command-bar {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  background-color: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  padding: 8px 14px !important;
  margin-bottom: 12px !important;
}

.quiz-status-pill {
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
}

/* ── Workspace Panes & Horizon Alignment ── */
.quiz-workspace-container {
  gap: 16px !important;
  align-items: stretch !important;
}

.quiz-pane {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 8px !important;
  padding: 12px 14px !important;
  display: flex !important;
  flex-direction: column !important;
  box-sizing: border-box !important;
}

/* ── Monospace editor with stable height & internal scrolling ── */
.quiz-source-editor textarea,
.quiz-source-editor textarea:focus {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
  font-feature-settings: "liga" 0, "calt" 0;
  font-size: 0.92rem !important;
  line-height: 1.55 !important;
  tab-size: 2 !important;
  height: clamp(34rem, 65vh, 52rem) !important;
  min-height: 34rem !important;
  max-height: 52rem !important;
  overflow-y: auto !important;
  resize: none !important;
}

#quiz_preview_display {
  height: clamp(34rem, 65vh, 52rem) !important;
  min-height: 34rem !important;
  max-height: 52rem !important;
  overflow-y: auto !important;
  padding-right: 6px !important;
}

/* ── Header toolbar rows ── */
.quiz-fullscreen-header {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  margin-bottom: 8px !important;
  flex-shrink: 0 !important;
  flex-wrap: nowrap !important;
}

.quiz-fullscreen-header > *:first-child {
  flex: 1 1 auto !important;
}

/* Small toolbar buttons (fullscreen toggle, refresh, upload, expand-all, edit jump) */
.quiz-fullscreen-btn,
.quiz-upload-btn,
.quiz-upload-btn button,
.quiz-upload-btn label,
.quiz-fullscreen-header button,
.quiz-fullscreen-header .upload-button,
.quiz-fullscreen-header .upload-button button,
.quiz-fullscreen-header .upload-button label,
.quiz-expand-btn,
.quiz-edit-jump-btn,
.hotspot-editor-btn,
.hotspot-mode-btn {
  font-family: var(--font, "Source Sans 3", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  line-height: 1 !important;
  height: 24px !important;
  min-height: 24px !important;
  max-height: 24px !important;
  padding: 2px 8px !important;
  border-radius: 4px !important;
  border: 1px solid #cbd5e1 !important;
  color: #334155 !important;
  background: #ffffff !important;
  cursor: pointer !important;
  min-width: 24px !important;
  width: auto !important;
  flex: 0 0 auto !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
  margin: 0 !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
  white-space: nowrap !important;
  transition: all 0.15s ease !important;
}

.quiz-fullscreen-btn:hover,
.quiz-upload-btn:hover,
.quiz-upload-btn button:hover,
.quiz-upload-btn label:hover,
.quiz-fullscreen-header button:hover,
.quiz-fullscreen-header .upload-button:hover,
.quiz-fullscreen-header .upload-button button:hover,
.quiz-fullscreen-header .upload-button label:hover,
.quiz-expand-btn:hover,
.quiz-edit-jump-btn:hover,
.hotspot-editor-btn:hover,
.hotspot-mode-btn:hover {
  background: #f1f5f9 !important;
  color: #0f172a !important;
  border-color: #94a3b8 !important;
}

.quiz-upload-btn input[type="file"] {
  display: none !important;
}

/* Compact checkbox in header toolbars */
.quiz-header-checkbox {
  flex: 0 0 auto !important;
  min-width: 0 !important;
  max-width: fit-content !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

.quiz-header-checkbox label,
.quiz-header-checkbox .checkbox-container {
  gap: 5px !important;
  padding: 2px 4px !important;
  margin: 0 !important;
  white-space: nowrap !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  color: #64748b !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  line-height: 1 !important;
}

.quiz-header-checkbox label:hover,
.quiz-header-checkbox .checkbox-container:hover {
  color: #0f172a !important;
}

/* ── Fullscreen styling ── */
.quiz-fs-active,
#quiz_source_container.quiz-fs-active,
#quiz_preview_container.quiz-fs-active {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 99999 !important;
  background: #ffffff !important;
  padding: 16px 24px !important;
  box-sizing: border-box !important;
  display: flex !important;
  flex-direction: column !important;
  flex-wrap: nowrap !important;
  overflow: hidden !important;
}

/* Header: Restrict to content height and prevent growing */
.quiz-fs-active .quiz-fullscreen-header,
.quiz-fs-active .row.quiz-fullscreen-header {
  height: auto !important;
  min-height: auto !important;
  max-height: 48px !important;
  flex: 0 0 auto !important;
  margin-bottom: 8px !important;
}

/* Form / inner wrapper: Enable shrinking and growing to fill remaining vertical space */
.quiz-fs-active .form,
.quiz-fs-active .quiz-source-editor,
.quiz-fs-active #quiz_preview_display {
  flex: 1 1 auto !important;
  height: calc(100vh - 75px) !important;
  min-height: calc(100vh - 75px) !important;
  max-height: calc(100vh - 75px) !important;
  display: flex !important;
  flex-direction: column !important;
}

.quiz-fs-active .quiz-source-editor textarea {
  height: 100% !important;
  min-height: calc(100vh - 105px) !important;
  max-height: none !important;
  flex: 1 1 auto !important;
}

/* ── Media Page Specific Styling ── */
.media-header-bar {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 12px !important;
  margin-bottom: 12px !important;
}

.media-summary-banner {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 12px;
  font-size: 0.95rem;
  font-weight: 500;
  color: #1e293b;
}

.media-detail-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  min-height: 380px;
}

/* ── Jump to Line button in Diagnostics ── */
.quiz-diag-jump-btn {
  background: #ffffff !important;
  border: 1px solid #cbd5e1 !important;
  color: #0284c7 !important;
  border-radius: 4px !important;
  padding: 1px 6px !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  display: inline-flex !important;
  align-items: center !important;
  margin-left: 4px !important;
  vertical-align: middle !important;
  line-height: 1.2 !important;
  text-decoration: none !important;
  transition: all 0.15s ease !important;
}

.quiz-diag-jump-btn:hover {
  background: #e0f2fe !important;
  border-color: #38bdf8 !important;
  color: #0369a1 !important;
}
/* Restrained application hierarchy. Main panes define the workspace boundary. */
.gradio-container { color: #1e293b; }
.gradio-container button { box-shadow: none !important; }
.gradio-container button:focus-visible, .gradio-container summary:focus-visible,
.gradio-container a:focus-visible { outline: 2px solid #334155 !important; outline-offset: 3px; }
.gradio-container button.primary { background: #334155 !important; border-color: #334155 !important; color: #fff !important; }
.gradio-container button.primary:hover { background: #1e293b !important; }
.gradio-container button.secondary { background: #fff !important; color: #334155 !important; border: 1px solid #cbd5e1 !important; }
.home-heading { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.home-heading h1 { margin: 0; font-size: 1.8rem; font-weight: 650; color: #0f172a; }
.release-version { font-size: 0.78rem; color: #64748b; }
.home-intro { font-size: 1.05rem; line-height: 1.6; color: #475569; max-width: 44rem; }
.home-container { gap: 16px !important; }
.home-actions { flex-grow: 0 !important; justify-content: flex-start !important; gap: 8px !important; }
.home-actions > button { flex: 0 0 auto !important; width: auto !important; }
.example-note { font-size: 0.9rem !important; color: #64748b !important; }
.example-source textarea { font-family: ui-monospace, monospace !important; font-size: 0.88rem !important; max-height: 22rem; }
#btn_open_editor, #btn_generate_package, #btn_download_package, #btn_upload_media_zip {
  flex: 0 0 auto !important; width: auto !important; min-height: 36px !important;
  font-size: 0.92rem !important; font-weight: 500 !important; border-radius: 5px !important;
  display: inline-flex !important; align-items: center; justify-content: center; gap: 7px;
}
.export-actions > button { min-width: 0 !important; width: max-content !important; }
.export-actions { flex: 0 0 auto !important; width: max-content !important; min-width: 0 !important; flex-wrap: nowrap !important; gap: 8px !important; }
.quiz-command-bar { display: grid !important; grid-template-columns: minmax(0, 1fr) max-content; background: #fff !important; border: 0 !important; border-bottom: 1px solid #e2e8f0 !important; border-radius: 0 !important; padding: 8px 0 14px !important; align-items: flex-start !important; }
.quiz-command-bar > .quiz-status-pill { flex: 1 1 280px !important; width: auto !important; min-width: 0 !important; }
.editor-header-row .block, .editor-header-row .html-container, .quiz-command-bar > .quiz-status-pill { padding: 0 !important; }
.editor-header-row h2 { margin: 0 !important; }
.editor-status { display: flex; align-items: baseline; gap: 8px 12px; flex-wrap: wrap; font-size: 0.9rem; }
.answer-quality-checks { flex-basis: 100%; font-weight: 400; color: #475569; font-size: 0.85rem; }
.answer-quality-checks summary { cursor: pointer; padding: 3px 0; }
.answer-quality-checks ul { padding-left: 20px; margin: 8px 0; color: #92400e; }
.quality-metrics { padding: 8px 0 0; line-height: 1.7; }
.package-ready { color: #166534; font-weight: 400; }
.quiz-pane { border-color: #e2e8f0 !important; border-radius: 5px !important; box-shadow: none !important; padding: 12px !important; }
.quiz-source-editor, .quiz-source-editor label, .quiz-source-editor textarea { border: 0 !important; box-shadow: none !important; background: #fff !important; }
.quiz-source-editor textarea:focus-visible { outline: 2px solid #94a3b8 !important; outline-offset: 2px; }
.quiz-fullscreen-header { margin-bottom: 12px !important; }
.preview-expand-control { flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; padding: 0 !important; }
.preview-expand-control .html-container { padding: 0 !important; }
.quiz-fullscreen-header button, .quiz-expand-btn, .quiz-edit-jump-btn { box-shadow: none !important; font-weight: 500 !important; border-color: #e2e8f0 !important; }
#btn_editor_fs, #btn_preview_fs { font-size: 0 !important; gap: 0 !important; }
#btn_editor_fs::before, #btn_preview_fs::before { width: 14px; height: 14px; }
#btn_upload_file, #btn_refresh, #btn_copy_prompt, #btn_download_example_media { display: inline-flex !important; align-items: center; justify-content: center; gap: 6px; }
.docs-content { line-height: 1.65; }
.docs-content h3, .home-container h3 { font-size: 1.08rem !important; font-weight: 600 !important; }
.docs-content table { width: 100%; border: 0 !important; border-collapse: collapse; }
.docs-content table tr { border: 0 !important; }
.docs-content table th, .docs-content table td { border: 0 !important; border-bottom: 1px solid #e2e8f0 !important; padding: 10px 12px !important; vertical-align: top; line-height: 1.5; }
.docs-content table th { background: #f8fafc !important; color: #334155 !important; font-weight: 600; }
.docs-content .prose pre { border: 0 !important; background: #f8fafc !important; border-radius: 4px !important; }
.media-page-container { gap: 12px !important; }
.media-header-bar { margin-bottom: 0 !important; align-items: flex-start !important; }
.media-summary-banner { border: 0 !important; border-radius: 4px; margin: 0 !important; font-size: 0.9rem; font-weight: 400; }
.media-page-container > .quiz-media-settings-bar { padding-top: 4px !important; }
@media(max-width: 760px) {
  .quiz-command-bar { grid-template-columns: minmax(0, 1fr); }
  .quiz-fullscreen-header { flex-wrap: wrap !important; }
  .quiz-fullscreen-header > :first-child { flex: 1 0 100% !important; }
  .hotspot-mode-toggle { flex-wrap: wrap; }
  .export-actions { width: 100% !important; }
  .export-actions > button { min-width: 0 !important; flex: 1 1 0 !important; }
  .home-container, .docs-content { padding-inline: 1rem; }
}


"""

SHARED_CSS += "\n" + button_icon_css()


MATHJAX_HEAD = """
<script>
(function() {
  try {
    var key = 'qti_creator_sid';
    var sid = window.sessionStorage.getItem(key) || window.localStorage.getItem(key);
    if (!sid) {
      sid = 'qti_' + Math.random().toString(36).substring(2) + '_' + Date.now().toString(36);
    }
    window.sessionStorage.setItem(key, sid);
    window.localStorage.setItem(key, sid);
    document.cookie = key + '=' + encodeURIComponent(sid) + '; path=/; SameSite=Lax; max-age=86400';
  } catch (e) {}
})();

window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
  },
  svg: { fontCache: 'global' }
};

// Generic toggle fullscreen helper
window.toggleFullscreen = function(targetId, btnId) {
  const container = document.getElementById(targetId);
  const btn = document.getElementById(btnId);
  if (!container) return;

  const isFs = container.classList.toggle('quiz-fs-active');
  if (isFs) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }

  if (btn) {
    btn.innerHTML = isFs ? '✕' : '⛶';
    btn.title = isFs ? 'Exit Fullscreen (Esc)' : 'Fullscreen';
  }

  if (!window._quiz_fs_bound) {
    window._quiz_fs_bound = true;
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.quiz-fs-active').forEach(c => {
          c.classList.remove('quiz-fs-active');
        });
        document.body.style.overflow = '';
        const b1 = document.getElementById('btn_editor_fs');
        if (b1) { b1.innerHTML = '⛶'; b1.title = 'Fullscreen'; }
        const b2 = document.getElementById('btn_preview_fs');
        if (b2) { b2.innerHTML = '⛶'; b2.title = 'Fullscreen'; }
      }
    });
  }
};

window.quizJumpToLine = function(lineNo, title) {
  const prevContainer = document.getElementById('quiz_preview_container');
  const prevBtn = document.getElementById('btn_preview_fs');
  if (prevContainer && prevContainer.classList.contains('quiz-fs-active')) {
    prevContainer.classList.remove('quiz-fs-active');
    document.body.style.overflow = '';
    if (prevBtn) {
      prevBtn.innerHTML = '⛶';
      prevBtn.title = 'Fullscreen';
    }
  }

  const editor = document.querySelector('.quiz-source-editor textarea');
  if (!editor) return;

  const text = editor.value;
  let targetIndex = -1;
  let targetEnd = -1;

  if (title) {
    const cleanTitle = title.trim();
    const headingPattern = new RegExp('^##\\\\s+' + cleanTitle.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'm');
    const match = text.match(headingPattern);
    if (match && typeof match.index === 'number') {
      targetIndex = match.index;
      const lineEnd = text.indexOf('\\n', targetIndex);
      targetEnd = lineEnd !== -1 ? lineEnd : targetIndex + match[0].length;
    }
  }

  if (targetIndex === -1) {
    const lines = text.split('\\n');
    const targetLine = Math.max(1, Math.min(lineNo, lines.length));
    targetIndex = 0;
    for (let i = 0; i < targetLine - 1; i++) {
      targetIndex += lines[i].length + 1;
    }
    const lineLen = lines[targetLine - 1] ? lines[targetLine - 1].length : 0;
    targetEnd = targetIndex + lineLen;
  }

  editor.focus();
  editor.setSelectionRange(targetIndex, targetEnd);

  const computedLineHeight = parseFloat(window.getComputedStyle(editor).lineHeight) || 20;
  const linesBefore = text.substring(0, targetIndex).split('\\n').length - 1;
  const scrollPos = Math.max(0, (linesBefore - 2) * computedLineHeight);
  editor.scrollTop = scrollPos;
  editor.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  if (typeof window.syncActiveQuestionToPreview === 'function') {
    window.syncActiveQuestionToPreview(true);
  }
};

window.addEventListener('message', function(event) {
  if (event.data && event.data.action === 'quiz-jump') {
    if (typeof window.quizJumpToLine === 'function') {
      window.quizJumpToLine(event.data.line, event.data.title);
    }
  }
});

// ── Active Question Auto-Expand and Tracking ──
window.getActiveQuizQuestionIdx = function(editor) {
  if (!editor || typeof editor.selectionStart !== 'number') return 0;
  var text = editor.value || '';
  var pos = editor.selectionStart;
  var textBefore = text.substring(0, pos);
  var lines = textBefore.split('\\n');
  var qIdx = 0;
  var inCode = false;
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim();
    if (line.startsWith('```')) {
      inCode = !inCode;
      continue;
    }
    if (!inCode && /^##(?:\\s+|$)/.test(line)) {
      qIdx++;
    }
  }
  return qIdx;
};

window.syncActiveQuestionToPreview = function(scrollIntoView) {
  var editor = document.querySelector('.quiz-source-editor textarea');
  if (!editor) return;
  var qIdx = window.getActiveQuizQuestionIdx(editor);
  if (qIdx <= 0) return;

  var cardId = 'qcard_' + qIdx;
  if (!window._openQuestionCards) {
    window._openQuestionCards = new Set();
    try {
      var raw = sessionStorage.getItem('qti_open_quiz_cards');
      if (raw) window._openQuestionCards = new Set(JSON.parse(raw));
    } catch(e) {}
  }
  window._openQuestionCards.add(cardId);
  try {
    sessionStorage.setItem('qti_open_quiz_cards', JSON.stringify(Array.from(window._openQuestionCards)));
  } catch(e) {}

  var card = document.querySelector('.quiz-question-card[data-question-idx="' + qIdx + '"]');
  if (card) {
    if (!card.open) {
      card.open = true;
    }
    window._lastActiveQuestionIdx = qIdx;

    // Scroll only the preview pane, never the page or focused source editor.
    var pane = document.getElementById('quiz_preview_display');
    if (scrollIntoView && pane && pane.clientHeight > 0) {
      var bounds = pane.getBoundingClientRect();
      var target = card.getBoundingClientRect();
      var visibleContext = Math.min(target.height, pane.clientHeight - 24, 160);
      if (target.top < bounds.top + 8 || target.top + visibleContext > bounds.bottom - 8) {
        pane.scrollTo({
          top: Math.max(0, pane.scrollTop + target.top - bounds.top - 12),
          behavior: 'smooth'
        });
      }
    }
  }
};

window.cancelDelayedPreviewSync = function() {
  clearTimeout(window._previewSyncTimer);
  window._previewSyncTimer = null;
  window._previewSyncReady = false;
  window._previewSyncToken = (window._previewSyncToken || 0) + 1;
};

window.flushDelayedPreviewSync = async function() {
  if (!window._previewSyncReady || window._previewSyncTimer) return;
  var editor = document.querySelector('.quiz-source-editor textarea');
  if (!editor || document.activeElement !== editor || editor._quizComposing) return;
  var token = window._previewSyncToken;
  var source = editor.value;
  var root = document.querySelector('#quiz_preview_display .quiz-preview-root');
  if (!root) return;

  // A slow response must not navigate an older preview after headings change.
  var expectedHash = root.getAttribute('data-source-hash');
  if (expectedHash && window.crypto && window.crypto.subtle) {
    var digest = await window.crypto.subtle.digest('SHA-256', new TextEncoder().encode(source));
    var currentHash = Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
    if (currentHash !== expectedHash) return; // Retry when the matching preview arrives.
  }
  if (!window._previewSyncReady || token !== window._previewSyncToken || editor.value !== source || document.activeElement !== editor) return;
  window._previewSyncReady = false;
  window.syncActiveQuestionToPreview(true);
};

window.scheduleDelayedPreviewSync = function() {
  window.cancelDelayedPreviewSync();
  window._previewSyncTimer = setTimeout(function() {
    window._previewSyncTimer = null;
    window._previewSyncReady = true;
    window.flushDelayedPreviewSync();
  }, 1000);
};

window.initEditorQuestionTracker = function() {
  var editor = document.querySelector('.quiz-source-editor textarea');
  if (!editor || editor._hasQuestionTracker) return;
  editor._hasQuestionTracker = true;

  editor.addEventListener('click', function() {
    window.cancelDelayedPreviewSync();
    window.syncActiveQuestionToPreview(true);
  });
  editor.addEventListener('keyup', function(e) {
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageUp', 'PageDown', 'Home', 'End'].indexOf(e.key) !== -1) {
      window.cancelDelayedPreviewSync();
      window.syncActiveQuestionToPreview(true);
    }
  });
  editor.addEventListener('input', function() {
    if (!editor._quizComposing) window.scheduleDelayedPreviewSync();
  });
  editor.addEventListener('compositionstart', function() {
    editor._quizComposing = true;
    window.cancelDelayedPreviewSync();
  });
  editor.addEventListener('compositionend', function() {
    editor._quizComposing = false;
    window.scheduleDelayedPreviewSync();
  });
  editor.addEventListener('blur', function() {
    window.cancelDelayedPreviewSync();
  });
};

document.addEventListener('DOMContentLoaded', function() {
  if (window.initEditorQuestionTracker) window.initEditorQuestionTracker();
  if (window.initAllTooltips) window.initAllTooltips();
});
var _trackerInitTimer = setInterval(function() {
  var editor = document.querySelector('.quiz-source-editor textarea');
  if (editor) {
    if (window.initEditorQuestionTracker) window.initEditorQuestionTracker();
    if (window.initAllTooltips) window.initAllTooltips();
    clearInterval(_trackerInitTimer);
  }
}, 300);

// ── Tooltip Initialization for All Buttons and Pills ──
window.initAllTooltips = function() {
  var tooltips = {
    '#btn_refresh': 'Re-parse QuizMD source and refresh the preview',
    '#btn_editor_fs': 'Toggle fullscreen for the QuizMD editor (Esc to exit)',
    '#btn_preview_fs': 'Toggle fullscreen for the preview pane (Esc to exit)',
    '#btn_generate_package': 'Generate QTI 2.1 zip package from the valid quiz',
    '#btn_download_package': 'Download the generated QTI 2.1 zip package',
    '#btn_upload_file': 'Upload a local .md or .txt QuizMD file into the editor',
    '#btn_upload_file button': 'Upload a local .md or .txt QuizMD file into the editor',
    '.quiz-upload-btn': 'Upload a local .md or .txt QuizMD file into the editor',
    '.quiz-upload-btn button': 'Upload a local .md or .txt QuizMD file into the editor',
    '#cb_render_math': 'Toggle LaTeX math rendering in the preview pane',
    '.quiz-header-checkbox': 'Toggle LaTeX math rendering in the preview pane',
    '.quiz-header-checkbox label': 'Toggle LaTeX math rendering in the preview pane',
    '.quiz-header-checkbox input': 'Toggle LaTeX math rendering in the preview pane',
    '#btn_upload_media_zip': 'Upload a ZIP archive containing images and media assets for this quiz',
    '#btn_upload_media_zip button': 'Upload a ZIP archive containing images and media assets for this quiz',
    '#btn_copy_prompt': 'Copy AI prompt template to clipboard',
    '#btn_open_editor': 'Switch to the Quiz Editor tab to compose and test quizzes',
  };
  for (var sel in tooltips) {
    document.querySelectorAll(sel).forEach(function(el) {
      if (!el.getAttribute('title')) {
        el.setAttribute('title', tooltips[sel]);
      }
    });
  }

  var genBtn = document.getElementById('btn_generate_package');
  if (genBtn) {
    var txt = genBtn.textContent || '';
    if (document.querySelector('.package-ready')) {
      genBtn.setAttribute('title', 'Generate a fresh copy of the current QTI package');
    } else if (txt.indexOf('Regenerate') !== -1) {
      genBtn.setAttribute('title', 'Quiz source or media has changed; click to regenerate the QTI 2.1 package');
    } else {
      genBtn.setAttribute('title', 'Generate QTI 2.1 zip package from the valid quiz');
    }
  }

  var edFs = document.getElementById('btn_editor_fs');
  if (edFs) {
    var edContainer = document.getElementById('quiz_source_container');
    var isEdFs = edContainer && edContainer.classList.contains('quiz-fs-active');
    edFs.setAttribute('title', isEdFs ? 'Exit fullscreen (Esc)' : 'Toggle fullscreen for QuizMD editor');
  }
  var prevFs = document.getElementById('btn_preview_fs');
  if (prevFs) {
    var prContainer = document.getElementById('quiz_preview_container');
    var isPrFs = prContainer && prContainer.classList.contains('quiz-fs-active');
    prevFs.setAttribute('title', isPrFs ? 'Exit fullscreen (Esc)' : 'Toggle fullscreen for preview pane');
  }
};

// ── Question Card Collapse State Persistence in Session ──
window.onQuizCardToggle = function(card) {
  if (!card) return;
  const id = card.getAttribute('data-card-id');
  if (!id) return;
  if (!window._openQuestionCards) {
    window._openQuestionCards = new Set();
    try {
      const raw = sessionStorage.getItem('qti_open_quiz_cards');
      if (raw) window._openQuestionCards = new Set(JSON.parse(raw));
    } catch(e) {}
  }
  if (card.open) {
    window._openQuestionCards.add(id);
  } else {
    window._openQuestionCards.delete(id);
  }
  try {
    sessionStorage.setItem('qti_open_quiz_cards', JSON.stringify(Array.from(window._openQuestionCards)));
  } catch(e) {}
};

window.syncExpandAllControl = function() {
  const btn = document.querySelector('.preview-expand-control .quiz-expand-btn');
  if (!btn) return;
  const items = document.querySelectorAll('#quiz_preview_display .quiz-question-card, #quiz_preview_display .quiz-section-desc-details');
  const allOpen = items.length > 0 && Array.from(items).every(c => c.open);
  btn.textContent = allOpen ? '▼ Collapse All' : '▶ Expand All';
  btn.title = allOpen ? 'Collapse all question cards' : 'Expand all question cards';
  btn.disabled = items.length === 0;
};

window.onQuizExpandAllToggle = function(allOpen) {
  if (!window._openQuestionCards) window._openQuestionCards = new Set();
  document.querySelectorAll('.quiz-question-card').forEach(function(c) {
    const id = c.getAttribute('data-card-id');
    if (id) {
      if (allOpen) window._openQuestionCards.add(id);
      else window._openQuestionCards.delete(id);
    }
  });
  try {
    sessionStorage.setItem('qti_open_quiz_cards', JSON.stringify(Array.from(window._openQuestionCards)));
  } catch(e) {}
};

document.addEventListener('toggle', function(e) {
  if (e.target && e.target.classList && e.target.classList.contains('quiz-question-card')) {
    window.onQuizCardToggle(e.target);
    if (window.syncExpandAllControl) window.syncExpandAllControl();
  }
}, true);

// ── Milestone 3: Hotspot Visual Editor Client Bridge & Interactions ──
window.dispatchHotspotAction = function(payload) {
  const container = document.getElementById('hotspot_action_input');
  if (!container) return;
  const inputEl = container.querySelector('textarea') || container.querySelector('input');
  if (!inputEl) return;

  // Track card and active hotspot state so it persists across preview re-renders
  const cardId = 'qcard_' + (payload.question_idx || 1);
  if (!window._openQuestionCards) window._openQuestionCards = new Set();
  window._openQuestionCards.add(cardId);
  try {
    sessionStorage.setItem('qti_open_quiz_cards', JSON.stringify(Array.from(window._openQuestionCards)));
  } catch(e) {}

  window._lastHotspotAction = {
    question_idx: payload.question_idx || 1,
    region_idx: payload.region_idx || 1,
    action: payload.action,
    time: Date.now()
  };

  // Set value across both direct and prototype setter to trigger Svelte/React bindings
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
    'value'
  ) || Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');

  const strVal = JSON.stringify(payload);
  if (nativeSetter && nativeSetter.set) {
    nativeSetter.set.call(inputEl, strVal);
  } else {
    inputEl.value = strVal;
  }

  inputEl.dispatchEvent(new Event('input', { bubbles: true }));
  inputEl.dispatchEvent(new Event('change', { bubbles: true }));

  // Flash immediate visual feedback in the hotspot toolbar
  const widget = document.querySelector('.hotspot-preview-widget[data-question-idx="' + (payload.question_idx || 1) + '"]');
  if (widget) {
    let toast = widget.querySelector('.hotspot-save-toast');
    if (!toast) {
      toast = document.createElement('span');
      toast.className = 'hotspot-save-toast';
      toast.style.cssText = 'background: #dcfce7; color: #166534; border: 1px solid #86efac; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; margin-left: 8px; transition: opacity 0.3s;';
      const tb = widget.querySelector('.hotspot-toolbar > div');
      if (tb) tb.appendChild(toast);
    }
    toast.textContent = '✓ Saved to source';
    toast.style.opacity = '1';
    clearTimeout(widget._toastTimer);
    widget._toastTimer = setTimeout(function() {
      toast.style.opacity = '0';
    }, 2500);
  }
};

window.initHotspotEditor = function(widget) {
  if (!widget) return;
  let targetGroup = widget.querySelector('.hotspot-region-group[data-selected="1"]');
  if (!targetGroup) {
    targetGroup = widget.querySelector('.hotspot-region-group');
  }
  if (targetGroup) {
    const rIdx = parseInt(targetGroup.getAttribute('data-region-idx'), 10);
    window.selectHotspotRegion(widget, rIdx);
  }
};

window.selectHotspotRegion = function(widget, regionIdx) {
  if (!widget) return;
  widget.querySelectorAll('.hotspot-region-group').forEach(function(g) {
    g.setAttribute('data-selected', '0');
  });
  // Clear any existing transform handles
  widget.querySelectorAll('.hotspot-transform-handle').forEach(function(h) { h.remove(); });

  const targetGroup = widget.querySelector('.hotspot-region-group[data-region-idx="' + regionIdx + '"]');
  if (!targetGroup) return;
  targetGroup.setAttribute('data-selected', '1');

  // Update region selector pills
  widget.querySelectorAll('.hotspot-region-pill').forEach(function(p) {
    if (parseInt(p.getAttribute('data-region-idx'), 10) === regionIdx) {
      p.setAttribute('data-selected', '1');
    } else {
      p.removeAttribute('data-selected');
    }
  });

  // Update legend items
  widget.querySelectorAll('.hotspot-legend-item').forEach(function(li) {
    if (parseInt(li.getAttribute('data-region-idx'), 10) === regionIdx) {
      li.setAttribute('data-selected', '1');
    } else {
      li.removeAttribute('data-selected');
    }
  });

  // Update controls bar
  const selInfo = widget.querySelector('.hotspot-editor-sel-info');
  const btnCorrect = widget.querySelector('.hotspot-editor-btn-correct');
  const btnDelete = widget.querySelector('.hotspot-editor-btn-danger');

  const shape = targetGroup.getAttribute('data-shape');
  const isCorrect = targetGroup.getAttribute('data-correct') === '1';
  const rId = targetGroup.getAttribute('data-region-id') || ('hc_' + regionIdx);

  if (selInfo) {
    const badgeColor = isCorrect ? '#16a34a' : '#dc2626';
    const typeLabel = isCorrect ? 'Correct' : 'Distractor';
    selInfo.innerHTML = 'Selected: <strong>#' + regionIdx + ' (' + rId + ')</strong> [<span style="color:' + badgeColor + '; font-weight:600;">' + typeLabel + '</span>]';
  }
  if (btnCorrect) {
    btnCorrect.style.display = 'inline-block';
    btnCorrect.textContent = isCorrect ? 'Mark as Distractor' : 'Mark as Correct';
    btnCorrect.title = isCorrect ? 'Change this hotspot into an incorrect distractor (0 pts)' : 'Change this hotspot into a correct answer';
  }
  if (btnDelete) {
    btnDelete.style.display = 'inline-block';
    btnDelete.title = 'Delete hotspot #' + regionIdx + ' (' + rId + ') from question';
  }

  // Render SVG interactive handles for move/resize
  window.attachHotspotHandles(widget, targetGroup);
};

window.attachHotspotHandles = function(widget, group) {
  const svg = widget.querySelector('.hotspot-overlay-svg');
  if (!svg) return;
  const shape = group.getAttribute('data-shape');
  const coordsStr = group.getAttribute('data-px-coords');
  if (!coordsStr) return;
  const coords = coordsStr.split(',').map(Number);
  const qIdx = parseInt(widget.getAttribute('data-question-idx') || '1', 10);
  const rIdx = parseInt(group.getAttribute('data-region-idx'), 10);
  const unit = group.getAttribute('data-unit') || 'pct';
  const imgW = parseFloat(widget.getAttribute('data-img-w') || '800');
  const imgH = parseFloat(widget.getAttribute('data-img-h') || '600');
  const srcHash = widget.getAttribute('data-source-hash') || '';

  const handleGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  handleGroup.setAttribute('class', 'hotspot-transform-handle');

  function getSvgPoint(evt) {
    const pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
  }

  function commitCoords(newPxCoords) {
    let finalCoords = newPxCoords;
    if (unit === 'pct') {
      if (shape === 'rect') {
        finalCoords = [
          Math.round((newPxCoords[0] / imgW) * 1000) / 10,
          Math.round((newPxCoords[1] / imgH) * 1000) / 10,
          Math.round((newPxCoords[2] / imgW) * 1000) / 10,
          Math.round((newPxCoords[3] / imgH) * 1000) / 10
        ];
      } else if (shape === 'circle') {
        const minDim = Math.min(imgW, imgH);
        finalCoords = [
          Math.round((newPxCoords[0] / imgW) * 1000) / 10,
          Math.round((newPxCoords[1] / imgH) * 1000) / 10,
          Math.round((newPxCoords[2] / minDim) * 1000) / 10
        ];
      }
    }
    window.dispatchHotspotAction({
      action: 'update_coords',
      question_idx: qIdx,
      region_idx: rIdx,
      shape: shape,
      coords: finalCoords,
      unit: unit,
      source_hash: srcHash
    });
  }

  if (shape === 'rect') {
    let [x1, y1, x2, y2] = coords;
    const shapeEl = group.querySelector('.hotspot-shape');

    // Drag body to move
    let isDragging = false;
    let startPt = null;
    let initialRect = null;

    function onBodyMouseDown(e) {
      if (widget.getAttribute('data-view-mode') !== 'editor') return;
      e.stopPropagation();
      isDragging = true;
      startPt = getSvgPoint(e);
      initialRect = [x1, y1, x2, y2];

      function onMouseMove(moveEvt) {
        if (!isDragging) return;
        const curPt = getSvgPoint(moveEvt);
        const dx = curPt.x - startPt.x;
        const dy = curPt.y - startPt.y;
        const rw = initialRect[2] - initialRect[0];
        const rh = initialRect[3] - initialRect[1];

        let nx1 = Math.max(0, Math.min(imgW - rw, initialRect[0] + dx));
        let ny1 = Math.max(0, Math.min(imgH - rh, initialRect[1] + dy));
        let nx2 = nx1 + rw;
        let ny2 = ny1 + rh;

        shapeEl.setAttribute('x', Math.round(nx1));
        shapeEl.setAttribute('y', Math.round(ny1));
        updateHandles(nx1, ny1, nx2, ny2);
      }

      function onMouseUp(upEvt) {
        if (!isDragging) return;
        isDragging = false;
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        const curPt = getSvgPoint(upEvt);
        const dx = curPt.x - startPt.x;
        const dy = curPt.y - startPt.y;
        const rw = initialRect[2] - initialRect[0];
        const rh = initialRect[3] - initialRect[1];
        let nx1 = Math.round(Math.max(0, Math.min(imgW - rw, initialRect[0] + dx)));
        let ny1 = Math.round(Math.max(0, Math.min(imgH - rh, initialRect[1] + dy)));
        let nx2 = nx1 + rw;
        let ny2 = ny1 + rh;
        commitCoords([nx1, ny1, nx2, ny2]);
      }

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    }

    shapeEl.setAttribute('title', 'Drag to move rectangle');
    shapeEl.addEventListener('mousedown', onBodyMouseDown);

    // 4 Corner handles for resize
    const corners = [
      { id: 'tl', cursor: 'nwse-resize' },
      { id: 'tr', cursor: 'nesw-resize' },
      { id: 'br', cursor: 'nwse-resize' },
      { id: 'bl', cursor: 'nesw-resize' }
    ];

    const hEls = {};
    const hSize = Math.max(8, Math.round(Math.min(imgW, imgH) * 0.016));

    corners.forEach(function(c) {
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('class', 'hotspot-handle');
      rect.setAttribute('width', hSize);
      rect.setAttribute('height', hSize);
      rect.setAttribute('title', 'Drag corner to resize rectangle');
      rect.style.cursor = c.cursor;
      handleGroup.appendChild(rect);
      hEls[c.id] = rect;

      rect.addEventListener('mousedown', function(e) {
        e.stopPropagation();
        const startPt = getSvgPoint(e);
        const orig = [x1, y1, x2, y2];

        function onCornerMove(me) {
          const pt = getSvgPoint(me);
          let curX1 = orig[0], curY1 = orig[1], curX2 = orig[2], curY2 = orig[3];
          if (c.id === 'tl') {
            curX1 = Math.max(0, Math.min(orig[2] - 10, pt.x));
            curY1 = Math.max(0, Math.min(orig[3] - 10, pt.y));
          } else if (c.id === 'tr') {
            curX2 = Math.min(imgW, Math.max(orig[0] + 10, pt.x));
            curY1 = Math.max(0, Math.min(orig[3] - 10, pt.y));
          } else if (c.id === 'br') {
            curX2 = Math.min(imgW, Math.max(orig[0] + 10, pt.x));
            curY2 = Math.min(imgH, Math.max(orig[1] + 10, pt.y));
          } else if (c.id === 'bl') {
            curX1 = Math.max(0, Math.min(orig[2] - 10, pt.x));
            curY2 = Math.min(imgH, Math.max(orig[1] + 10, pt.y));
          }
          shapeEl.setAttribute('x', Math.round(curX1));
          shapeEl.setAttribute('y', Math.round(curY1));
          shapeEl.setAttribute('width', Math.round(curX2 - curX1));
          shapeEl.setAttribute('height', Math.round(curY2 - curY1));
          updateHandles(curX1, curY1, curX2, curY2);
        }

        function onCornerUp(ue) {
          window.removeEventListener('mousemove', onCornerMove);
          window.removeEventListener('mouseup', onCornerUp);
          const finalX1 = Math.round(parseFloat(shapeEl.getAttribute('x')));
          const finalY1 = Math.round(parseFloat(shapeEl.getAttribute('y')));
          const finalW = Math.round(parseFloat(shapeEl.getAttribute('width')));
          const finalH = Math.round(parseFloat(shapeEl.getAttribute('height')));
          commitCoords([finalX1, finalY1, finalX1 + finalW, finalY1 + finalH]);
        }

        window.addEventListener('mousemove', onCornerMove);
        window.addEventListener('mouseup', onCornerUp);
      });
    });

    function updateHandles(rx1, ry1, rx2, ry2) {
      const half = hSize / 2;
      hEls['tl'].setAttribute('x', rx1 - half);
      hEls['tl'].setAttribute('y', ry1 - half);
      hEls['tr'].setAttribute('x', rx2 - half);
      hEls['tr'].setAttribute('y', ry1 - half);
      hEls['br'].setAttribute('x', rx2 - half);
      hEls['br'].setAttribute('y', ry2 - half);
      hEls['bl'].setAttribute('x', rx1 - half);
      hEls['bl'].setAttribute('y', ry2 - half);
    }

    updateHandles(x1, y1, x2, y2);
    svg.appendChild(handleGroup);

  } else if (shape === 'circle') {
    let [cx, cy, r] = coords;
    const shapeEl = group.querySelector('.hotspot-shape');
    shapeEl.setAttribute('title', 'Drag to move circle');
    const hSize = Math.max(8, Math.round(Math.min(imgW, imgH) * 0.016));
    const half = hSize / 2;

    // Center handle for moving circle
    const centerHandle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    centerHandle.setAttribute('class', 'hotspot-handle');
    centerHandle.setAttribute('cx', cx);
    centerHandle.setAttribute('cy', cy);
    centerHandle.setAttribute('r', half);
    centerHandle.setAttribute('title', 'Drag center handle to move circle');
    centerHandle.style.cursor = 'move';
    handleGroup.appendChild(centerHandle);

    // Perimeter handle for radius resize
    const edgeHandle = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    edgeHandle.setAttribute('class', 'hotspot-handle');
    edgeHandle.setAttribute('width', hSize);
    edgeHandle.setAttribute('height', hSize);
    edgeHandle.setAttribute('x', cx + r - half);
    edgeHandle.setAttribute('y', cy - half);
    edgeHandle.setAttribute('title', 'Drag handle to resize circle radius');
    edgeHandle.style.cursor = 'ew-resize';
    handleGroup.appendChild(edgeHandle);

    // Drag shape or center handle to move
    function onCircleMoveStart(e) {
      if (widget.getAttribute('data-view-mode') !== 'editor') return;
      e.stopPropagation();
      const startPt = getSvgPoint(e);
      const initCx = cx, initCy = cy;

      function onMove(me) {
        const pt = getSvgPoint(me);
        const dx = pt.x - startPt.x;
        const dy = pt.y - startPt.y;
        const ncx = Math.max(r, Math.min(imgW - r, initCx + dx));
        const ncy = Math.max(r, Math.min(imgH - r, initCy + dy));
        shapeEl.setAttribute('cx', Math.round(ncx));
        shapeEl.setAttribute('cy', Math.round(ncy));
        centerHandle.setAttribute('cx', Math.round(ncx));
        centerHandle.setAttribute('cy', Math.round(ncy));
        edgeHandle.setAttribute('x', Math.round(ncx + r - half));
        edgeHandle.setAttribute('y', Math.round(ncy - half));
      }

      function onUp(ue) {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
        const finalCx = Math.round(parseFloat(shapeEl.getAttribute('cx')));
        const finalCy = Math.round(parseFloat(shapeEl.getAttribute('cy')));
        commitCoords([finalCx, finalCy, r]);
      }

      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    }

    shapeEl.addEventListener('mousedown', onCircleMoveStart);
    centerHandle.addEventListener('mousedown', onCircleMoveStart);

    // Drag edge handle to resize radius
    edgeHandle.addEventListener('mousedown', function(e) {
      e.stopPropagation();
      const startPt = getSvgPoint(e);
      const initR = r;

      function onRadiusMove(me) {
        const pt = getSvgPoint(me);
        const dist = Math.hypot(pt.x - cx, pt.y - cy);
        const maxR = Math.min(cx, cy, imgW - cx, imgH - cy);
        const nr = Math.max(5, Math.min(maxR, dist));
        shapeEl.setAttribute('r', Math.round(nr));
        edgeHandle.setAttribute('x', Math.round(cx + nr - half));
      }

      function onRadiusUp() {
        window.removeEventListener('mousemove', onRadiusMove);
        window.removeEventListener('mouseup', onRadiusUp);
        const finalR = Math.round(parseFloat(shapeEl.getAttribute('r')));
        commitCoords([cx, cy, finalR]);
      }

      window.addEventListener('mousemove', onRadiusMove);
      window.addEventListener('mouseup', onRadiusUp);
    });

    svg.appendChild(handleGroup);
  }
};

window.toggleSelectedCorrectness = function(widget) {
  if (!widget) return;
  const selGroup = widget.querySelector('.hotspot-region-group[data-selected="1"]');
  if (!selGroup) return;
  const qIdx = parseInt(widget.getAttribute('data-question-idx') || '1', 10);
  const rIdx = parseInt(selGroup.getAttribute('data-region-idx'), 10);
  const srcHash = widget.getAttribute('data-source-hash') || '';

  window.dispatchHotspotAction({
    action: 'toggle_correct',
    question_idx: qIdx,
    region_idx: rIdx,
    source_hash: srcHash
  });
};

window.deleteSelectedRegion = function(widget) {
  if (!widget) return;
  const selGroup = widget.querySelector('.hotspot-region-group[data-selected="1"]');
  if (!selGroup) return;
  const qIdx = parseInt(widget.getAttribute('data-question-idx') || '1', 10);
  const rIdx = parseInt(selGroup.getAttribute('data-region-idx'), 10);
  const srcHash = widget.getAttribute('data-source-hash') || '';

  window.dispatchHotspotAction({
    action: 'delete_region',
    question_idx: qIdx,
    region_idx: rIdx,
    source_hash: srcHash
  });
};

window.addHotspotShape = function(widget, shape) {
  if (!widget) return;
  const qIdx = parseInt(widget.getAttribute('data-question-idx') || '1', 10);
  const srcHash = widget.getAttribute('data-source-hash') || '';

  // Default coordinate placement: centered 20% box or 10% circle
  let coords = shape === 'circle' ? [50, 50, 10] : [40, 40, 60, 60];

  window.dispatchHotspotAction({
    action: 'add_region',
    question_idx: qIdx,
    shape: shape,
    coords: coords,
    unit: 'pct',
    correct: false,
    author_label: 'New ' + (shape === 'circle' ? 'circle' : 'rectangle'),
    source_hash: srcHash
  });
};

</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""

MATHJAX_TYPESET_JS = """() => {
  if (window.syncExpandAllControl) window.syncExpandAllControl();
  // 1. Ensure question tracker is initialized on the editor textarea
  if (typeof window.initEditorQuestionTracker === 'function') {
    window.initEditorQuestionTracker();
  }

  // 2. Restore question card collapse/expand state
  try {
    let openCards = window._openQuestionCards;
    if (!openCards && window.sessionStorage) {
      const saved = sessionStorage.getItem('qti_open_quiz_cards');
      if (saved) openCards = new Set(JSON.parse(saved));
    }
    if (openCards && openCards.size > 0) {
      document.querySelectorAll('.quiz-question-card').forEach(function(c) {
        const id = c.getAttribute('data-card-id');
        if (id && openCards.has(id)) c.open = true;
      });
    }
  } catch(e) {}

  // 3. Navigate only after typing pauses and the rendered source is current.
  if (window._previewSyncReady && typeof window.flushDelayedPreviewSync === 'function') {
    window.flushDelayedPreviewSync();
  } else if (!window._previewSyncTimer && typeof window.syncActiveQuestionToPreview === 'function') {
    const editor = document.querySelector('.quiz-source-editor textarea');
    if (editor && document.activeElement === editor && !editor._quizComposing) window.syncActiveQuestionToPreview(false);
  }

  // 4. Restore active hotspot editor state if a recent edit occurred
  if (window._lastHotspotAction && (Date.now() - window._lastHotspotAction.time < 30000)) {
    const last = window._lastHotspotAction;
    const qCard = document.querySelector('.quiz-question-card[data-card-id="qcard_' + last.question_idx + '"]');
    if (qCard) {
      qCard.open = true;
      const widget = qCard.querySelector('.hotspot-preview-widget');
      if (widget) {
        widget.setAttribute('data-view-mode', 'editor');
        const groups = widget.querySelectorAll('.hotspot-region-group');
        let targetRegion = last.region_idx;
        if (last.action === 'add_region') {
          targetRegion = groups.length;
        } else if (last.action === 'delete_region') {
          targetRegion = Math.max(1, Math.min(last.region_idx, groups.length));
        }
        if (window.selectHotspotRegion) {
          window.selectHotspotRegion(widget, targetRegion);
        }
        // Flash the 'Saved to MD' toast
        let toast = widget.querySelector('.hotspot-save-toast');
        if (!toast) {
          toast = document.createElement('span');
          toast.className = 'hotspot-save-toast';
          toast.style.cssText = 'background: #dcfce7; color: #166534; border: 1px solid #86efac; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; margin-left: 8px; transition: opacity 0.3s;';
          const tb = widget.querySelector('.hotspot-toolbar > div');
          if (tb) tb.appendChild(toast);
        }
        toast.textContent = '✓ Saved to source';
        toast.style.opacity = '1';
        clearTimeout(widget._toastTimer);
        widget._toastTimer = setTimeout(function() {
          toast.style.opacity = '0';
        }, 2500);
      }
    }
    window._lastHotspotAction = null;
  }

  // 5. Tooltip initialization
  if (typeof window.initAllTooltips === 'function') {
    window.initAllTooltips();
  }

  // 6. MathJax Typesetting
  if (!window.MathJax) return;
  const mathSpans = document.querySelectorAll('span.math:not([data-mathjax-typeset])');
  mathSpans.forEach(span => {
    span.setAttribute('data-mathjax-typeset', 'true');
    // Detect interactive form widgets (e.g. gaps) inside math spans
    const hasWidget = span.querySelector('input, select, textarea');
    if (hasWidget) {
      span.setAttribute('data-mathjax-error', 'widget-in-math');
      span.style.border = '1.5px solid #ef4444';
      span.style.background = '#fef2f2';
      span.style.padding = '2px 6px';
      span.style.borderRadius = '4px';
      span.style.display = 'inline-flex';
      span.style.alignItems = 'center';
      span.style.gap = '6px';

      const flag = document.createElement('span');
      flag.style.color = '#b91c1c';
      flag.style.fontWeight = '700';
      flag.style.fontSize = '0.82em';
      flag.style.cursor = 'help';
      flag.style.background = '#fee2e2';
      flag.style.padding = '1px 5px';
      flag.style.borderRadius = '3px';
      flag.style.border = '1px solid #fca5a5';
      flag.title = 'Syntax Error: Form widget / gap placed inside LaTeX math ($...$). OpenOLAT MathJax cannot render widgets inside math.';
      flag.textContent = '⚠️ [MathJax Gap Conflict]';
      span.prepend(flag);
      return;
    }

    const isDisplay = span.closest('p') && span.closest('p').style.textAlign === 'center';
    const rawLatex = span.getAttribute('title') ? decodeURIComponent(span.getAttribute('title')) : span.textContent;
    if (isDisplay) {
      span.textContent = '$$' + rawLatex + '$$';
    } else {
      span.textContent = '\\\\(' + rawLatex + '\\\\)';
    }
  });
  if (window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise().catch(err => {
      console.warn('MathJax typesetting error:', err);
    });
  }
}"""
