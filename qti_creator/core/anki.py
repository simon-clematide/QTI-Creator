"""Deterministic QuizMD-to-Anki conversion and portable deck packaging."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import html
from html.parser import HTMLParser
from pathlib import Path
import random
import re
import tempfile

import genanki

from qti_creator.core.markdown import RE_GAP, RE_DROPDOWN_GAP, extract_hottexts, markdown_to_qti_xhtml
from qti_creator.core.media import preflight_media
from qti_creator.core.model import (
    AssociationQuestion, EssayQuestion, FillBlankQuestion, HotspotQuestion,
    HottextQuestion, InlineChoiceQuestion, InvalidQuestion, KprimQuestion,
    MultipleChoiceQuestion, NumericalQuestion, OrderQuestion, Quiz,
    SingleChoiceQuestion, TrueFalseQuestion,
)
from qti_creator.core.parser import parse_quizmd
from qti_creator.core.validation import Severity

CSS = """.card { font-family: sans-serif; font-size: 20px; text-align: left;
line-height: 1.5; padding: 20px; } img { max-width: 100%; height: auto; }
pre { white-space: pre-wrap; } .cloze { font-weight: bold; color: #2563eb; }
.extra { margin-top: 1em; } table { border-collapse: collapse; }
td, th { border: 1px solid #888; padding: .3em; }"""


@dataclass
class AnkiNote:
    key: str
    kind: str
    front: str
    back: str
    extra: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class AnkiExport:
    deck_name: str
    identity: str
    notes: list[AnkiNote] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    media: dict[str, bytes] = field(default_factory=dict)

    @property
    def card_count(self) -> int:
        return sum(len(set(re.findall(r"{{c(\d+)::", n.front))) if n.kind == "cloze" else 1
                   for n in self.notes)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _render(text: str, assets: dict[str, str]) -> str:
    rendered = markdown_to_qti_xhtml(text, asset_map=assets)
    # The shared renderer protects math in spans; Anki needs native delimiters.
    def math_span(match):
        formula = match.group(1)
        display = '\\[' if '\n' in formula else '\\('
        return display + formula + ('\\]' if display == '\\[' else '\\)')
    rendered = re.sub(r'<p class="text-center"><span class="math" title="[^"]*">(.*?)</span></p>',
                      lambda m: '<p>\\[' + m[1] + '\\]</p>', rendered, flags=re.S)
    rendered = re.sub(r'<span class="math" title="[^"]*">(.*?)</span>',
                      math_span, rendered, flags=re.S)
    # Literal QuizMD/Anki-like syntax in code must never create extra clozes.
    return rendered.replace('{{', '&#123;&#123;').replace('}}', '&#125;&#125;')


def convert_quiz(quiz: Quiz, *, deck_name: str = "", separate_gaps: bool = True,
                 assets: dict[str, str] | None = None) -> AnkiExport:
    """Build previewable notes without performing I/O or inventing answers.

    Explicit question Identifier metadata is preferred; otherwise section/title
    pairs provide stable identities across reorderings and answer edits.
    """
    assets = assets or {}
    result = AnkiExport(deck_name.strip() or quiz.title, quiz.title)
    seen = set()
    render = lambda text: _render(text or '', assets)
    for section in quiz.sections:
        for q in section.questions:
            if isinstance(q, InvalidQuestion):
                raise ValueError(f'Invalid question: {q.title}')
            if isinstance(q, (EssayQuestion, HotspotQuestion)):
                result.warnings.append(f'{q.title}: skipped ({"no model answer" if isinstance(q, EssayQuestion) else "hotspot conversion is not supported yet"}).')
                continue
            explicit = re.search(r'^Identifier:\s*(.+)$', q.raw_markdown, re.M | re.I)
            key = ('id:' + explicit.group(1).strip()) if explicit else 'title:' + section.title + '\x1f' + q.title
            if key in seen:
                raise ValueError(f'Duplicate Anki identity for "{q.title}". Add unique Identifier: metadata.')
            seen.add(key)
            tags = sorted({re.sub(r'\s+', '_', t.strip()) for t in
                           [section.title, quiz.topic or '', q.topic or '', *quiz.keywords, *q.keywords] if t.strip()})
            prompt = render(q.prompt)
            extra = render(q.feedback)
            hint = ('<details><summary>Hint</summary>' + render(q.hint) + '</details>') if q.hint else ''

            def add(front, back, child='main', kind='basic', extra_html=extra):
                result.notes.append(AnkiNote(key + '\x1f' + child, kind, front + hint, back, extra_html, tags))

            if isinstance(q, (SingleChoiceQuestion, MultipleChoiceQuestion, TrueFalseQuestion)):
                choices = '<ul>' + ''.join('<li>' + render(c.text) + '</li>' for c in q.choices) + '</ul>'
                answer = ''.join(render(c.text) + (render(c.feedback) if c.feedback else '')
                                 for c in q.choices if c.is_correct)
                add(prompt + choices, answer)
            elif isinstance(q, (FillBlankQuestion, InlineChoiceQuestion)):
                pattern = RE_GAP if isinstance(q, FillBlankQuestion) else RE_DROPDOWN_GAP
                tokens = list(pattern.finditer(q.prompt))
                if len(tokens) != len(q.gaps):
                    raise ValueError(f'Cannot reliably locate gaps in {q.title}.')
                text = q.prompt
                replacements = []
                alternatives = []
                for i, gap in enumerate(q.gaps):
                    if isinstance(q, FillBlankQuestion):
                        answer = gap.expected_value
                        if gap.alternatives:
                            alternatives.append(f'Gap {i + 1}: ' + ' / '.join([answer, *gap.alternatives]))
                    else:
                        answer = next(c.text for c in gap.choices if c.is_correct)
                    # Keep cloze syntax out of Markdown rendering and HTML escaping.
                    answer_html = render(answer)
                    answer_html = re.sub(r'^<p>(.*?)</p>$', r'\1', answer_html, flags=re.S)
                    answer_html = answer_html.replace('{', '&#123;').replace('}', '&#125;').replace(':', '&#58;')
                    replacements.append('{{c' + str(i + 1 if separate_gaps else 1) + '::' + answer_html + '}}')
                for i, token in reversed(list(enumerate(tokens))):
                    text = text[:token.start()] + f'ANKIGAPPLACEHOLDER{i}END' + text[token.end():]
                text = render(text)
                for i, replacement in enumerate(replacements):
                    text = text.replace(f'ANKIGAPPLACEHOLDER{i}END', replacement)
                add(text, '', kind='cloze', extra_html=extra + ''.join(render(a) for a in alternatives))
            elif isinstance(q, KprimQuestion):
                for s in q.statements:
                    add(prompt + render(s.text), 'True' if s.is_correct else 'False', 'statement:' + s.text)
            elif isinstance(q, AssociationQuestion):
                targets = {t.identifier: t.text for t in q.targets}
                for item in q.items:
                    add(prompt + render(item.text), ''.join(render(targets[t]) for t in item.target_ids), 'item:' + item.text)
            elif isinstance(q, OrderQuestion):
                items = list(q.items)
                random.Random(_digest(key)).shuffle(items)
                if items == q.items:
                    items = items[1:] + items[:1]
                add(prompt + '<ul>' + ''.join('<li>' + render(i.text) + '</li>' for i in items) + '</ul>',
                    '<ol>' + ''.join('<li>' + render(i.text) + '</li>' for i in q.items) + '</ol>')
            elif isinstance(q, NumericalQuestion):
                add(prompt, html.escape(f'{q.answer:g}' + (f' ± {q.tolerance:g}' if q.tolerance else '')))
            elif isinstance(q, HottextQuestion):
                front, back = q.prompt, q.prompt
                for start, end, _, inner, correct in reversed(extract_hottexts(q.prompt)):
                    front = front[:start] + inner + front[end:]
                    back = back[:start] + ('**' + inner + '**' if correct else inner) + back[end:]
                add(render(front), render(back))
            else:
                raise ValueError(f'Unsupported question type: {type(q).__name__}')
    keys = [n.key for n in result.notes]
    if len(keys) != len(set(keys)):
        raise ValueError('Repeated statements or matching items would create duplicate cards. Give them distinct wording.')
    return result


def prepare_anki_export(source: str, *, deck_name: str = '', separate_gaps: bool = True,
                        media_zip_bytes: bytes | None = None) -> AnkiExport:
    """Validate source, resolve media used by exported notes, and convert."""
    if not source.strip():
        raise ValueError('Cannot export an empty quiz.')
    quiz, diagnostics = parse_quizmd(source)
    errors = [d.message for d in diagnostics if d.severity == Severity.ERROR]
    if errors:
        raise ValueError('Validation failed: ' + '; '.join(errors))
    result = convert_quiz(quiz, deck_name=deck_name, separate_gaps=separate_gaps)
    if not result.notes:
        raise ValueError('No exportable cards. ' + ' '.join(result.warnings))
    # The media scanner accepts Markdown images, so extract actual HTML img tags
    # from converted cards (not escaped examples in code blocks).
    class Images(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sources = set()

        def handle_starttag(self, tag, attrs):
            if tag == 'img':
                self.sources.update(value for name, value in attrs if name == 'src' and value)

    images = Images()
    for note in result.notes:
        images.feed(note.front + note.back + note.extra)
    media_quiz = Quiz(questions=[EssayQuestion(prompt='\n'.join(
        '![](' + src + ')' for src in sorted(images.sources)))])
    media = preflight_media(media_quiz, include_media=True, media_zip_bytes=media_zip_bytes)
    if media.has_errors:
        raise ValueError('Media resolution failed: ' + '; '.join(d.message for d in media.diagnostics if d.severity == Severity.ERROR))
    mapping = {}
    for source_ref, asset in media.resolved_assets.items():
        name = 'anki_' + asset.content_hash + Path(asset.filename).suffix.lower()
        result.media[name] = asset.data
        mapping[source_ref] = name
    # Re-render from Markdown so URL rewriting follows the shared renderer rules.
    converted = convert_quiz(quiz, deck_name=deck_name, separate_gaps=separate_gaps, assets=mapping)
    converted.media = result.media
    converted.warnings.extend(d.message for d in diagnostics if d.severity == Severity.WARNING)
    converted.warnings.extend(d.message for d in media.diagnostics if d.severity == Severity.WARNING)
    return converted


def write_anki_package(export: AnkiExport, path: str) -> None:
    """Write custom Basic/Cloze note types and bundled media to an .apkg."""
    basic = genanki.Model(1874500101, 'QTI Creator Basic v1',
        fields=[{'name': n} for n in ['Front', 'Back', 'Extra']],
        templates=[{'name': 'Recall', 'qfmt': '{{Front}}',
                    'afmt': '{{FrontSide}}<hr id="answer">{{Back}}<div class="extra">{{Extra}}</div>'}], css=CSS)
    cloze = genanki.Model(1874500102, 'QTI Creator Cloze v1',
        fields=[{'name': n} for n in ['Text', 'Extra']], model_type=genanki.Model.CLOZE,
        templates=[{'name': 'Cloze', 'qfmt': '{{cloze:Text}}',
                    'afmt': '{{cloze:Text}}<div class="extra">{{Extra}}</div>'}], css=CSS)
    deck = genanki.Deck(int(_digest('qti-anki:' + export.identity)[:15], 16), export.deck_name)
    for note in export.notes:
        fields = [note.front, note.extra] if note.kind == 'cloze' else [note.front, note.back, note.extra]
        deck.add_note(genanki.Note(model=cloze if note.kind == 'cloze' else basic,
                      fields=fields, tags=note.tags, guid=genanki.guid_for(export.identity, note.key)))
    with tempfile.TemporaryDirectory(prefix='anki_media_') as tmp:
        paths = []
        for name, data in export.media.items():
            target = Path(tmp) / name
            target.write_bytes(data)
            paths.append(str(target))
        genanki.Package(deck, media_files=paths).write_to_file(path)


def render_anki_preview(export: AnkiExport) -> str:
    """Render each generated card, including distinct cloze masks."""
    parts = [f'<p>{len(export.notes)} notes · {export.card_count} cards</p>']
    for warning in export.warnings:
        parts.append('<p>⚠ ' + html.escape(warning) + '</p>')
    card_index = 0
    for note in export.notes:
        masks = sorted(set(re.findall(r'{{c(\d+)::', note.front))) if note.kind == 'cloze' else [None]
        for mask in masks:
            front, back = note.front, note.back
            if mask:
                back = re.sub(r'{{c(\d+)::(.*?)}}', lambda m: '<strong>' + m[2] + '</strong>' if m[1] == mask else m[2], note.front, flags=re.S)
                front = re.sub(r'{{c(\d+)::(.*?)}}', lambda m: '[…]' if m[1] == mask else m[2], note.front, flags=re.S)
            card_index += 1
            parts.append('<details style="border:1px solid #94a3b8;border-radius:6px;padding:10px;margin:8px 0"><summary>Card ' + str(card_index) +
                         '</summary><div style="margin-top:12px"><b>Front</b>' + front + '<hr style="margin:12px 0"><b>Back</b>' + back + note.extra + '</div></details>')
    return ''.join(parts)
