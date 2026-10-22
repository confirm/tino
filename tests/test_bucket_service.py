'''Tests for BucketService: CRUD and .meta.yml round-trips.'''

import pytest

from tino.models import AccessEntry


def test_create_returns_info(buckets):
    info = buckets.create('proj', description='My project')
    assert info.slug == 'proj'
    assert info.description == 'My project'
    assert info.access == []


def test_create_persists(buckets):
    buckets.create('proj', description='desc')
    got = buckets.get('proj')
    assert got is not None
    assert got.description == 'desc'


def test_create_with_access(buckets):
    access = [AccessEntry(group='team', role='editor')]
    buckets.create('proj', access=access)
    assert buckets.get('proj').access == access


def test_create_with_mcp_instructions(buckets):
    buckets.create('proj', mcp_instructions='Write in German')
    assert buckets.get('proj').mcp_instructions == 'Write in German'


def test_duplicate_create_raises(buckets):
    buckets.create('proj')
    with pytest.raises(FileExistsError):
        buckets.create('proj')


def test_get_missing_returns_none(buckets):
    assert buckets.get('ghost') is None


def test_list_is_sorted(buckets):
    buckets.create('beta')
    buckets.create('alpha')
    assert [b.slug for b in buckets.list()] == ['alpha', 'beta']


def test_update_description(buckets):
    buckets.create('proj', description='old')
    buckets.update('proj', description='new')
    assert buckets.get('proj').description == 'new'


def test_update_access(buckets):
    buckets.create('proj')
    access = [AccessEntry(group='g', role='committer')]
    buckets.update('proj', access=access)
    assert buckets.get('proj').access == access


def test_update_only_touches_given_fields(buckets):
    buckets.create('proj', description='keep')
    buckets.update('proj', mcp_instructions='hi')
    got = buckets.get('proj')
    assert got.description == 'keep'
    assert got.mcp_instructions == 'hi'


def test_update_clears_mcp_instructions(buckets):
    buckets.create('proj', mcp_instructions='something')
    buckets.update('proj', mcp_instructions='')
    assert buckets.get('proj').mcp_instructions == ''


def test_update_missing_returns_none(buckets):
    assert buckets.update('ghost', description='x') is None


def test_delete(buckets):
    buckets.create('proj')
    assert buckets.delete('proj') is True
    assert buckets.get('proj') is None


def test_delete_missing_returns_false(buckets):
    assert buckets.delete('ghost') is False
