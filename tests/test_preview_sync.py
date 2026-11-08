"""Exercise the shipped tracker with deterministic timers and a minimal DOM."""
import json
import shutil
import subprocess

import pytest

from qti_creator.ui.styles import MATHJAX_HEAD


def test_delayed_preview_navigation():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the client-side timer test")
    start = MATHJAX_HEAD.index("window.getActiveQuizQuestionIdx =")
    end = MATHJAX_HEAD.index("document.addEventListener('DOMContentLoaded'", start)
    tracker = MATHJAX_HEAD[start:end]
    script = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const {createHash} = require('node:crypto');
const tracker = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
let now = 0, seq = 0, scrolls = [], timers = new Map();
const editor = {value: '## First\nFirst prompt\n## Second\nSecond prompt', selectionStart: 0,
  listeners: {}, addEventListener(name, fn) { this.listeners[name] = fn; }};
const pane = {scrollTop: 0, clientHeight: 300,
  getBoundingClientRect() { return {top: 0, bottom: 300}; },
  scrollTo(options) { scrolls.push(options); this.scrollTop = options.top; }};
const cards = [1, 2, 3].map((n) => ({open: false,
  getBoundingClientRect() { return {top: (n === 1 ? 20 : 900) - pane.scrollTop, height: 400}; }}));
const hash = s => createHash('sha256').update(s).digest('hex');
let renderedHash = hash(editor.value);
const root = {getAttribute() { return renderedHash; }};
const document = {activeElement: editor,
  getElementById(id) { return id === 'quiz_preview_display' ? pane : null; },
  querySelector(selector) {
    if (selector === '.quiz-source-editor textarea') return editor;
    if (selector.includes('quiz-preview-root')) return root;
    const m = selector.match(/data-question-idx="(\d+)"/);
    return m ? cards[Number(m[1]) - 1] : null;
  }};
const window = {crypto: {subtle: {digest: async (_, data) => createHash('sha256').update(data).digest()} }};
const sessionStorage = {getItem() { return null; }, setItem() {}};
const context = {window, document, sessionStorage, TextEncoder, Uint8Array,
  setTimeout(fn, ms) { const id = ++seq; timers.set(id, {at: now + ms, fn}); return id; },
  clearTimeout(id) { timers.delete(id); }};
vm.runInNewContext(tracker, context);
window.initEditorQuestionTracker();
const tick = async ms => {
  now += ms;
  for (const [id, timer] of [...timers]) if (timer.at <= now) { timers.delete(id); timer.fn(); }
  await new Promise(setImmediate);
};
(async () => {
  editor.selectionStart = editor.value.length;
  editor.listeners.input();
  await tick(600);
  assert.equal(scrolls.length, 0);
  editor.listeners.input(); // Another key restarts the full idle interval.
  await tick(999);
  assert.equal(scrolls.length, 0);
  await tick(1);
  assert.equal(scrolls.length, 1);
  assert.equal(cards[1].open, true);
  assert.equal(document.activeElement, editor);
  assert.equal(editor.selectionStart, editor.value.length);
  assert.equal(scrolls[0].behavior, 'smooth');

  editor.listeners.input(); // The same visible question should not jump again.
  await tick(1000);
  assert.equal(scrolls.length, 1);

  pane.scrollTop = 0;
  editor.value += '\n## Third\nNew question';
  editor.selectionStart = editor.value.length;
  editor.listeners.input();
  await tick(1000); // Old preview must not navigate to a mismatched heading index.
  assert.equal(scrolls.length, 1);
  renderedHash = hash(editor.value);
  await window.flushDelayedPreviewSync(); // Matching server response has arrived.
  assert.equal(scrolls.length, 2);
  assert.equal(cards[2].open, true);

  pane.scrollTop = 0;
  editor.listeners.input();
  editor.listeners.blur();
  document.activeElement = {};
  await tick(1000);
  assert.equal(scrolls.length, 2); // No late movement after leaving the editor.

  document.activeElement = editor;
  editor.listeners.compositionstart();
  editor.listeners.input();
  await tick(1000);
  assert.equal(scrolls.length, 2);
  editor.listeners.compositionend();
  await tick(999);
  assert.equal(scrolls.length, 2);
  await tick(1);
  assert.equal(scrolls.length, 3);

  pane.scrollTop = 0;
  editor.listeners.keyup({key: 'ArrowUp'});
  assert.equal(scrolls.length, 4); // Explicit cursor navigation stays immediate.
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run([node, "-e", script], input=json.dumps(tracker), text=True,
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
