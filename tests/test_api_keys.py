'''Tests for ApiKeyService: create/verify/revoke/update and the mtime cache.'''


def test_create_and_verify_roundtrip(api_keys):
    raw, rec = api_keys.create('CI', {'reports': 'viewer'})
    got = api_keys.verify(raw)
    assert got is not None
    assert got['id'] == rec['id']
    assert got['access'] == {'reports': 'viewer'}
    assert 'hash' not in got


def test_verify_rejects_bad_prefix(api_keys):
    assert api_keys.verify('not_a_token') is None


def test_verify_rejects_forged_token(api_keys):
    api_keys.create('CI', {})
    assert api_keys.verify('tino_' + '0' * 64) is None


def test_verify_on_missing_file_returns_none(api_keys):
    assert api_keys.verify('tino_whatever') is None


def test_update_access_is_reflected(api_keys):
    raw, rec = api_keys.create('CI', {'r': 'viewer'})
    api_keys.update(rec['id'], None, {'r': 'editor'})
    assert api_keys.verify(raw)['access'] == {'r': 'editor'}


def test_revoke(api_keys):
    raw, rec = api_keys.create('CI', {})
    assert api_keys.revoke(rec['id']) is True
    assert api_keys.verify(raw) is None
    assert api_keys.revoke(rec['id']) is False


def test_list_keys_strips_hashes(api_keys):
    _, rec = api_keys.create('CI', {})
    listed = api_keys.list_keys()
    assert all('hash' not in k for k in listed)
    assert [k['id'] for k in listed] == [rec['id']]


def test_verify_served_from_cache_without_disk_reread(api_keys):
    # White-box: create() invalidates the cache, so verify once to re-prime it,
    # then poison the in-memory index. With the file's mtime unchanged, verify()
    # must serve from the (now-empty) cache rather than re-reading disk — the
    # optimisation that keeps auth off the disk hot path.
    raw, _ = api_keys.create('CI', {})
    assert api_keys.verify(raw) is not None  # primes the mtime cache
    api_keys._by_hash.clear()                # pylint: disable=protected-access
    assert api_keys.verify(raw) is None      # served from cache, not disk


def test_cache_invalidation_rereads_from_disk(api_keys):
    raw, _ = api_keys.create('CI', {})
    api_keys.verify(raw)                      # prime the cache
    api_keys._by_hash.clear()                # pylint: disable=protected-access
    api_keys._cache_mtime = None             # pylint: disable=protected-access
    assert api_keys.verify(raw) is not None  # invalidation forces a re-read
