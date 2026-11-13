"""Check learning content, stable identities, and actual Anki package contents."""
import base64
import io
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

from qti_creator.core.anki import convert_quiz, prepare_anki_export, render_anki_preview, write_anki_package
from qti_creator.core.examples import SAMPLE_ALL_TYPES
from qti_creator.core.model import (
    AssociationItem, AssociationQuestion, AssociationTarget, Choice, EssayQuestion,
    HottextItem, HottextQuestion, KprimQuestion, KprimStatement, NumericalQuestion,
    OrderItem, OrderQuestion, Quiz, SingleChoiceQuestion, TrueFalseQuestion,
)


def package_db(export, tmp_path):
    path = tmp_path / 'deck.apkg'
    write_anki_package(export, str(path))
    with zipfile.ZipFile(path) as archive:
        db_path = tmp_path / 'collection.anki2'
        db_path.write_bytes(archive.read('collection.anki2'))
    return sqlite3.connect(db_path), path


def test_cloze_masks_alternatives_feedback_and_hint(tmp_path):
    export = prepare_anki_export('''# Linguistics
## Tokens
The units are {{tokens | token units}} and {{words}}.
Feedback: **Review** the distinction.
Hint: Think of segmentation.
''')
    assert export.card_count == 2
    note = export.notes[0]
    assert '{{c1::tokens}}' in note.front and '{{c2::words}}' in note.front
    assert 'token units' in note.extra and '<strong>Review</strong>' in note.extra
    assert '<details><summary>Hint</summary>' in note.front
    db, _ = package_db(export, tmp_path)
    assert db.execute('select count(*) from cards').fetchone()[0] == 2
    models = json.loads(db.execute('select models from col').fetchone()[0])
    assert next(iter(models.values()))['type'] == 1
    preview = render_anki_preview(export)
    assert '{{c' not in preview and preview.count('<b>Front</b>') == 2
    together = prepare_anki_export('## Gaps\n{{one}} and {{two}}', separate_gaps=False)
    assert together.card_count == 1
    assert together.notes[0].front.count('{{c1::') == 2
    db.close()


def test_dropdown_uses_correct_choice():
    note = prepare_anki_export('## City\nCapital: {[Paris|**Bern**|Berlin]}.').notes[0]
    assert '{{c1::Bern}}' in note.front
    assert 'Paris' not in note.front and 'Berlin' not in note.front


def test_choices_do_not_reveal_answer_on_front():
    export = prepare_anki_export('''# Test
## Choose
Which one?
- [ ] Distractor
- [X] **Correct**
Feedback: Explanation.
Keywords: term with spaces
''')
    note = export.notes[0]
    assert 'Distractor' in note.front and 'Correct' in note.front
    assert '[X]' not in note.front
    assert 'Correct' in note.back and 'Distractor' not in note.back
    assert 'Explanation' in note.extra
    assert 'term_with_spaces' in note.tags


def test_conversion_for_other_types():
    target = AssociationTarget('Noun')
    quiz = Quiz(title='Course', questions=[
        TrueFalseQuestion(prompt='A statement', choices=[Choice('True', False), Choice('False', True)]),
        KprimQuestion(prompt='Judge each', statements=[KprimStatement('Statement ' + str(i), i % 2 == 0) for i in range(4)]),
        AssociationQuestion(prompt='Classify', targets=[target], items=[AssociationItem('dog', [target.identifier])]),
        NumericalQuestion(prompt='Calculate', answer=4, tolerance=.1),
        OrderQuestion(prompt='Order these', items=[OrderItem('First'), OrderItem('Second'), OrderItem('Third')]),
        HottextQuestion(prompt='Select {+ cat } and {- runs }.', items=[HottextItem('cat', True), HottextItem('runs', False)]),
        EssayQuestion(prompt='Discuss'),
    ])
    export = convert_quiz(quiz)
    assert export.card_count == 9
    assert export.notes[0].back == '<p>False</p>'
    assert [n.back for n in export.notes[1:5]] == ['True', 'False', 'True', 'False']
    assert 'dog' in export.notes[5].front and 'Noun' in export.notes[5].back
    assert export.notes[6].back == '4 ± 0.1'
    assert export.notes[7].front.index('First') != export.notes[7].back.index('First')
    assert '<strong>cat</strong>' in export.notes[8].back
    assert '{+' not in export.notes[8].front and '{-' not in export.notes[8].front
    assert any('no model answer' in w for w in export.warnings)


def test_media_packaged_and_rewritten(tmp_path):
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aGZkAAAAASUVORK5CYII=')
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('fig/pixel.png', png)
    source = '''## Picture
What is this?
- [X] ![pixel](fig/pixel.png)
- [ ] Empty
Hint: ![pixel](fig/pixel.png)
'''
    with pytest.raises(ValueError, match='Media resolution failed'):
        prepare_anki_export(source)
    export = prepare_anki_export(source, media_zip_bytes=data.getvalue())
    assert len(export.media) == 1
    filename = next(iter(export.media))
    assert filename in export.notes[0].front and filename in export.notes[0].back
    assert 'fig/pixel.png' not in export.notes[0].front
    db, path = package_db(export, tmp_path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read('media'))
        assert list(manifest.values()) == [filename]
        assert archive.read(next(iter(manifest))) == png
    db.close()


def test_stable_guids_across_parse_edit_and_reorder(tmp_path):
    one = '# Course\n## One\nIdentifier: persistent\n{{answer}}\n## Two\n{{second}}'
    two = '# Course\n## Two\n{{second}}\n## Renamed\nIdentifier: persistent\n{{updated}}'
    a = prepare_anki_export(one)
    b = prepare_anki_export(two, deck_name='Custom display name')
    db, _ = package_db(a, tmp_path)
    before = set(row[0] for row in db.execute('select guid from notes'))
    db.close()
    (tmp_path / 'collection.anki2').unlink()
    db, _ = package_db(b, tmp_path)
    after = set(row[0] for row in db.execute('select guid from notes'))
    assert before == after
    db.close()


@pytest.mark.parametrize('source, message', [
    ('', 'empty'),
    ('## Broken\n- [X] Yes\n- [X] Also', 'Validation failed'),
    ('## Essay\nDiscuss something', 'No exportable cards'),
    ('# Course\n## Same\n{{one}}\n## Same\n{{two}}', 'Duplicate Anki identity'),
])
def test_export_rejects_unusable_input(source, message):
    with pytest.raises(ValueError, match=message):
        prepare_anki_export(source)


def test_math_code_and_literal_cloze_are_safe():
    note = prepare_anki_export(r'''## Formula
Recall $x^2$ and {{value}}. Literal `{{c7::example}}`.
''').notes[0]
    # Parser treats the code example as a second QuizMD gap; literal braces in
    # its answer must not create a third Anki card.
    assert '\\(x^2\\)' in note.front
    assert '{{c7::' not in note.front


def test_sample_all_types_builds(tmp_path):
    # Bundled sample includes remote imagery; don't fetch it in this unit test.
    from qti_creator.core.parser import parse_quizmd
    quiz, _ = parse_quizmd(SAMPLE_ALL_TYPES)
    export = convert_quiz(quiz)
    assert export.notes
    db, _ = package_db(export, tmp_path)
    assert db.execute('select count(*) from cards').fetchone()[0] == export.card_count
    db.close()


def test_headless_api(tmp_path):
    import gradio as gr
    from qti_creator.api import export_anki_api
    with pytest.raises(gr.Error):
        export_anki_api('')
    path = Path(export_anki_api('## Test\nA {{card}}.'))
    try:
        assert path.suffix == '.apkg' and zipfile.is_zipfile(path)
    finally:
        path.unlink()
