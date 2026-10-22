'''Tests for FileService: path-traversal safety and CRUD round-trips.'''

import io
import zipfile

import pytest


def test_write_read_roundtrip(files, bucket):
    assert files.write(bucket, 'a.typ', 'hello') is not None
    assert files.read(bucket, 'a.typ')['content'] == 'hello'


def test_read_missing_returns_none(files, bucket):
    assert files.read(bucket, 'nope.typ') is None


@pytest.mark.parametrize('evil', [
    '../escape.txt',
    '../../etc/passwd',
    'sub/../../escape.txt',
    '/etc/passwd',
])
def test_write_rejects_traversal(files, bucket, evil, data_dir):
    assert files.write(bucket, evil, 'pwned') is None
    assert not (data_dir / 'escape.txt').exists()


@pytest.mark.parametrize('evil', ['../escape.txt', '/etc/passwd'])
def test_read_rejects_traversal(files, bucket, evil):
    assert files.read(bucket, evil) is None


def test_create_then_duplicate(files, bucket):
    assert files.create(bucket, 'new.typ', 'x') is True
    assert files.create(bucket, 'new.typ', 'y') is False


def test_list_excludes_meta_git_and_dotfiles(files, bucket, data_dir):
    files.write(bucket, 'visible.typ', 'x')
    files.write(bucket, 'sub/nested.typ', 'y')
    (data_dir / bucket / '.hidden').write_text('secret')

    paths = {e.path for e in files.list(bucket)}
    assert {'visible.typ', 'sub', 'sub/nested.typ'} <= paths
    assert '.meta.yml' not in paths
    assert '.git' not in paths
    assert '.hidden' not in paths


def test_list_marks_directories(files, bucket):
    files.write(bucket, 'sub/nested.typ', 'y')
    by_path = {e.path: e.type for e in files.list(bucket)}
    assert by_path['sub'] == 'directory'
    assert by_path['sub/nested.typ'] == 'file'


def test_rename(files, bucket):
    files.write(bucket, 'old.typ', 'x')
    assert files.rename(bucket, 'old.typ', 'new.typ') is True
    assert files.read(bucket, 'old.typ') is None
    assert files.read(bucket, 'new.typ')['content'] == 'x'


def test_rename_missing_source(files, bucket):
    assert files.rename(bucket, 'ghost.typ', 'new.typ') is False


def test_rename_dest_exists(files, bucket):
    files.write(bucket, 'a.typ', '1')
    files.write(bucket, 'b.typ', '2')
    assert files.rename(bucket, 'a.typ', 'b.typ') is False


def test_delete(files, bucket):
    files.write(bucket, 'gone.typ', 'x')
    assert files.delete(bucket, 'gone.typ') is True
    assert files.delete(bucket, 'gone.typ') is False


def test_binary_read_flagged(files, bucket, data_dir):
    (data_dir / bucket / 'img.bin').write_bytes(b'\xff\xfe\x00\x01')
    assert files.read(bucket, 'img.bin')['binary'] is True


def test_unzip_skips_zip_slip(files, bucket, data_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('safe.txt', 'ok')
        zf.writestr('../evil.txt', 'pwned')

    extracted = files.unzip(bucket, buf.getvalue())
    assert 'safe.txt' in extracted
    assert '../evil.txt' not in extracted
    assert not (data_dir / 'evil.txt').exists()
