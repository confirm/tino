'''Tests for FontService: listing, upload validation and deletion.'''

import pytest

from tino.services.font import FontService


@pytest.fixture
def fonts(tmp_path):
    return FontService(tmp_path)


def test_list_missing_dir_is_empty(tmp_path):
    assert FontService(tmp_path / 'nope').list() == []


def test_upload_and_list_sorted_case_insensitive(fonts):
    assert fonts.upload('b.TTF', b'12') is True
    assert fonts.upload('A.otf', b'1') is True
    assert fonts.list() == [
        {'filename': 'A.otf', 'size': 1},
        {'filename': 'b.TTF', 'size': 2},
    ]


def test_list_ignores_non_fonts(fonts, tmp_path):
    (tmp_path / 'readme.txt').write_text('x')
    (tmp_path / 'sub.ttf').mkdir()
    assert fonts.list() == []


@pytest.mark.parametrize('name', [
    'evil.exe',
    'noext',
    '.hidden.ttf',
    '../escape.ttf',
    'sub/font.ttf',
    'sub\\font.ttf',
])
def test_upload_rejects_invalid_names(fonts, tmp_path, name):
    assert fonts.upload(name, b'x') is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('ext', ['.ttf', '.otf', '.woff', '.woff2'])
def test_upload_accepts_all_font_types(fonts, ext):
    assert fonts.upload(f'font{ext}', b'x') is True


def test_delete(fonts):
    fonts.upload('a.ttf', b'x')
    assert fonts.delete('a.ttf') is True
    assert fonts.delete('a.ttf') is False


def test_delete_rejects_invalid_names(fonts, tmp_path):
    (tmp_path.parent / 'outside.ttf').write_bytes(b'x')
    assert fonts.delete('../outside.ttf') is False
    assert (tmp_path.parent / 'outside.ttf').exists()
