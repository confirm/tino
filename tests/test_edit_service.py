'''Tests for the exact-string replacement logic behind the MCP ``edit_file`` tool.'''

import pytest

from tino.models import FileEdit
from tino.services.edit import EditError, Splice, apply_edits


def _edit(old, new, replace_all=False):
    return FileEdit(old_string=old, new_string=new, replace_all=replace_all)


def _replay(text, splices):
    for splice in splices:
        text = text[:splice.start] + splice.insert + text[splice.end:]
    return text


def test_single_replacement():
    text, splices = apply_edits('hello world', [_edit('world', 'TINO')])
    assert text == 'hello TINO'
    assert splices == [Splice(6, 11, 'TINO')]


def test_edits_apply_sequentially():
    text, _ = apply_edits('a b c', [_edit('a', 'x'), _edit('x b', 'y')])
    assert text == 'y c'


def test_replace_all():
    text, splices = apply_edits('foo bar foo baz foo', [_edit('foo', 'quux', replace_all=True)])
    assert text == 'quux bar quux baz quux'
    assert len(splices) == 3


def test_replace_all_with_unique_match():
    assert apply_edits('one', [_edit('one', 'two', replace_all=True)])[0] == 'two'


def test_deletion_and_multiline():
    source = '= Title\n\nold para\nkeep\n'
    text, _ = apply_edits(source, [_edit('old para\n', '')])
    assert text == '= Title\n\nkeep\n'


@pytest.mark.parametrize('source, edits', [
    ('abc abc', [_edit('abc', 'x', replace_all=True)]),
    ('ä🦄 ä🦄 b', [_edit('🦄', '🐉🐉', replace_all=True), _edit('b', 'ÄÖÜ')]),
    ('aaaa', [_edit('aa', 'a', replace_all=True)]),
    ('x\ny\nz', [_edit('y', 'Y'), _edit('x\nY', 'XY'), _edit('z', '')]),
])
def test_splices_replay_to_result(source, edits):
    text, splices = apply_edits(source, edits)
    assert _replay(source, splices) == text


@pytest.mark.parametrize('edit, message', [
    (_edit('', 'x'), 'must not be empty'),
    (_edit('same', 'same'), 'identical'),
    (_edit('missing', 'x'), 'not found'),
    (_edit('dup', 'x'), 'matches 2 times'),
])
def test_invalid_edits(edit, message):
    with pytest.raises(EditError, match=message):
        apply_edits('dup dup same', [edit])


def test_error_names_the_failing_edit():
    with pytest.raises(EditError, match='^Edit 2: old_string not found'):
        apply_edits('abc', [_edit('a', 'x'), _edit('a', 'y')])


def test_edit_error_is_a_value_error():
    assert issubclass(EditError, ValueError)


def test_no_edits_is_identity():
    assert apply_edits('abc', []) == ('abc', [])
