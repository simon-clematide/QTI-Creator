"""Shared styles and CSS for QTI-Creator multipage application."""

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

/* ── Editor Command / Status Bar ── */
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

/* Small toolbar buttons (fullscreen toggle, refresh) */
.quiz-fullscreen-btn {
  background: transparent !important;
  border: 1px solid #e2e8f0 !important;
  color: #64748b !important;
  border-radius: 4px !important;
  padding: 2px 6px !important;
  font-size: 0.85rem !important;
  line-height: 1 !important;
  cursor: pointer !important;
  min-width: 24px !important;
  height: 24px !important;
  flex: 0 0 auto !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.quiz-fullscreen-btn:hover {
  background: #f1f5f9 !important;
  color: #0f172a !important;
  border-color: #94a3b8 !important;
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
.quiz-fs-active {
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
  overflow: hidden !important;
}

.quiz-fs-active .quiz-source-editor,
.quiz-fs-active #quiz_preview_display {
  flex: 1 1 auto !important;
  height: calc(100vh - 75px) !important;
  min-height: calc(100vh - 75px) !important;
  max-height: calc(100vh - 75px) !important;
}

.quiz-fs-active .quiz-source-editor textarea {
  height: 100% !important;
  min-height: calc(100vh - 105px) !important;
  max-height: none !important;
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
"""

MATHJAX_HEAD = """
<script>
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
};

window.addEventListener('message', function(event) {
  if (event.data && event.data.action === 'quiz-jump') {
    if (typeof window.quizJumpToLine === 'function') {
      window.quizJumpToLine(event.data.line, event.data.title);
    }
  }
});
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""

MATHJAX_TYPESET_JS = """() => {
  if (!window.MathJax) return;
  const mathSpans = document.querySelectorAll('span.math:not([data-mathjax-typeset])');
  mathSpans.forEach(span => {
    span.setAttribute('data-mathjax-typeset', 'true');
    const isDisplay = span.closest('p') && span.closest('p').style.textAlign === 'center';
    const rawLatex = span.getAttribute('title') ? decodeURIComponent(span.getAttribute('title')) : span.textContent;
    if (isDisplay) {
      span.innerHTML = '$$' + rawLatex + '$$';
    } else {
      span.innerHTML = '\\\\(' + rawLatex + '\\\\)';
    }
  });
  if (window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise();
  }
}"""
