'''Tests for SearchService: name/content matching, snippets and limits.'''

import pytest

from tino.services import search as search_module
from tino.services.search import SearchService


@pytest.fixture
def search(files):
    return SearchService(files)


def test_name_match(search, files, bucket):
    files.write(bucket, 'Report.typ', 'nothing here')
    [result] = search.search_bucket(bucket, 'report', limit=10)
    assert result.path == 'Report.typ'
    assert result.name_match is True
    assert result.snippets == []


def test_content_match_is_case_insensitive_with_line_numbers(search, files, bucket):
    files.write(bucket, 'a.typ', 'first\n  Hello WORLD  \nthird\nworld again')
    [result] = search.search_bucket(bucket, 'world', limit=10)
    assert result.name_match is False
    assert [(s.line, s.text) for s in result.snippets] == [
        (2, 'Hello WORLD'), (4, 'world again'),
    ]


def test_no_match(search, files, bucket):
    files.write(bucket, 'a.typ', 'abc')
    assert search.search_bucket(bucket, 'xyz', limit=10) == []


def test_directories_are_not_results(search, files, bucket):
    files.write(bucket, 'needle/a.typ', 'x')
    assert [r.path for r in search.search_bucket(bucket, 'needle', limit=10)] == ['needle/a.typ']


def test_snippets_capped_per_file(search, files, bucket):
    files.write(bucket, 'a.typ', '\n'.join(['hit'] * 20))
    [result] = search.search_bucket(bucket, 'hit', limit=10)
    assert len(result.snippets) == search_module.MAX_SNIPPETS_PER_FILE


def test_snippet_text_is_trimmed(search, files, bucket):
    files.write(bucket, 'a.typ', 'hit' + 'x' * 500)
    [result] = search.search_bucket(bucket, 'hit', limit=10)
    assert len(result.snippets[0].text) == search_module.SNIPPET_MAX_LEN


def test_limit_caps_results(search, files, bucket):
    for i in range(5):
        files.write(bucket, f'doc{i}.typ', 'x')
    assert len(search.search_bucket(bucket, 'doc', limit=3)) == 3


def test_binary_files_only_match_by_name(search, files, bucket):
    files.upload(bucket, 'needle.bin', b'\xff\xfeneedle')
    [result] = search.search_bucket(bucket, 'needle', limit=10)
    assert result.name_match is True
    assert result.snippets == []


def test_large_files_skip_content(search, files, bucket, monkeypatch):
    monkeypatch.setattr(search_module, 'MAX_FILE_BYTES', 10)
    files.write(bucket, 'big.typ', 'needle' * 10)
    assert search.search_bucket(bucket, 'needle', limit=10) == []


def test_hidden_files_are_not_searched(search, files, bucket, data_dir):
    (data_dir / bucket / '.secret').write_text('needle')
    assert search.search_bucket(bucket, 'needle', limit=10) == []
