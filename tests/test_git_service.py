'''Tests for GitService: status, commit, log, diff, tree, show and restore.'''

import pytest

from tino.services.git import GitService


def _commit(git_svc, files, bucket, path, content, message='msg'):
    files.write(bucket, path, content)
    return git_svc.commit(bucket, [path], message)


# ── status ──

def test_status_clean_after_create(git_svc, bucket):
    assert git_svc.status(bucket) == []


def test_status_reports_untracked(git_svc, files, bucket):
    files.write(bucket, 'new.typ', 'x')
    assert [(s.path, s.status) for s in git_svc.status(bucket)] == [('new.typ', 'untracked')]


def test_status_reports_modified_and_deleted(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', '1')
    _commit(git_svc, files, bucket, 'b.typ', '1')
    files.write(bucket, 'a.typ', '2')
    files.delete(bucket, 'b.typ')

    status = {s.path: s.status for s in git_svc.status(bucket)}
    assert status == {'a.typ': 'modified', 'b.typ': 'deleted'}


def test_status_hides_dotfiles(git_svc, files, bucket, data_dir):
    (data_dir / bucket / '.secret').write_text('x')
    files.write(bucket, 'visible.typ', 'x')
    assert [s.path for s in git_svc.status(bucket)] == ['visible.typ']


def test_status_on_missing_repo_raises(git_svc):
    with pytest.raises(Exception):
        git_svc.status('ghost')


# ── commit ──

def test_commit_returns_info_with_author(git_svc, files, bucket):
    files.write(bucket, 'a.typ', 'x')
    info = git_svc.commit(bucket, ['a.typ'], '  Add a  \n', author='alice', email='a@x')
    assert info.message == 'Add a'
    assert 'alice' in info.author
    assert len(info.sha) == 40
    assert info.deleted is False
    assert git_svc.status(bucket) == []


def test_commit_default_email_is_derived_from_author(git_svc, files, bucket, data_dir):
    import git  # pylint: disable=import-outside-toplevel
    files.write(bucket, 'a.typ', 'x')
    git_svc.commit(bucket, ['a.typ'], 'm', author='bob')
    repo = git.Repo(data_dir / bucket)
    assert repo.head.commit.author.email == 'bob@tino'
    repo.close()


def test_commit_only_stages_selected_files(git_svc, files, bucket):
    files.write(bucket, 'a.typ', 'x')
    files.write(bucket, 'b.typ', 'y')
    git_svc.commit(bucket, ['a.typ'], 'only a')
    assert [s.path for s in git_svc.status(bucket)] == ['b.typ']


def test_commit_stages_deletions(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', 'x')
    files.delete(bucket, 'a.typ')
    git_svc.commit(bucket, ['a.typ'], 'remove a')
    assert git_svc.status(bucket) == []
    assert 'a.typ' not in git_svc.tree(bucket, 'HEAD')


def test_commit_ignores_traversal_paths(git_svc, files, bucket, data_dir):
    (data_dir / 'outside.txt').write_text('nope')
    files.write(bucket, 'a.typ', 'x')
    git_svc.commit(bucket, ['a.typ', '../outside.txt'], 'm')
    assert git_svc.tree(bucket, 'HEAD') == ['a.typ']


# ── log ──

def test_log_hides_meta_commits(git_svc, bucket, buckets):
    buckets.update(bucket, description='changed')
    assert git_svc.log(bucket) == []


def test_log_newest_first(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', '1', 'first')
    _commit(git_svc, files, bucket, 'a.typ', '2', 'second')
    assert [c.message for c in git_svc.log(bucket)] == ['second', 'first']


def test_log_filtered_by_path(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', '1', 'touch a')
    _commit(git_svc, files, bucket, 'b.typ', '1', 'touch b')
    assert [c.message for c in git_svc.log(bucket, 'a.typ')] == ['touch a']


def test_log_respects_max_count(git_svc, files, bucket):
    for i in range(5):
        _commit(git_svc, files, bucket, 'a.typ', str(i), f'c{i}')
    assert len(git_svc.log(bucket, max_count=2)) == 2


def test_log_flags_deleting_commit(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', '1', 'add')
    files.delete(bucket, 'a.typ')
    git_svc.commit(bucket, ['a.typ'], 'delete')

    log = git_svc.log(bucket, 'a.typ')
    assert [(c.message, c.deleted) for c in log] == [('delete', True), ('add', False)]


# ── diff ──

def test_diff_working_tree(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', 'old\n')
    files.write(bucket, 'a.typ', 'new\n')
    entries = git_svc.diff(bucket)
    assert [e.path for e in entries] == ['a.typ']
    assert '-old' in entries[0].diff
    assert '+new' in entries[0].diff


def test_diff_working_tree_filtered(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', '1\n')
    _commit(git_svc, files, bucket, 'b.typ', '1\n')
    files.write(bucket, 'a.typ', '2\n')
    files.write(bucket, 'b.typ', '2\n')
    assert [e.path for e in git_svc.diff(bucket, 'b.typ')] == ['b.typ']


def test_diff_clean_is_empty(git_svc, bucket):
    assert git_svc.diff(bucket) == []


def test_diff_of_commit_vs_parent(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', 'one\n')
    info = _commit(git_svc, files, bucket, 'a.typ', 'two\n')
    diff = git_svc.diff(bucket, ref=info.sha)[0].diff
    assert '-one' in diff and '+two' in diff


def test_diff_of_commit_with_path(git_svc, files, bucket):
    files.write(bucket, 'a.typ', '1\n')
    files.write(bucket, 'b.typ', '1\n')
    _commit(git_svc, files, bucket, 'c.typ', '0\n')
    files.write(bucket, 'a.typ', '2\n')
    files.write(bucket, 'b.typ', '2\n')
    info = git_svc.commit(bucket, ['a.typ', 'b.typ'], 'both')
    assert [e.path for e in git_svc.diff(bucket, 'a.typ', ref=info.sha)] == ['a.typ']


def test_diff_of_root_commit_uses_empty_tree(tmp_path):
    import git  # pylint: disable=import-outside-toplevel
    repo = git.Repo.init(tmp_path / 'root')
    (tmp_path / 'root' / 'a.typ').write_text('hello\n')
    repo.index.add(['a.typ'])
    sha = repo.index.commit('root').hexsha
    repo.close()

    diff = GitService(tmp_path).diff('root', ref=sha)
    assert [e.path for e in diff] == ['a.typ']
    assert '+hello' in diff[0].diff


def test_parse_diff_handles_multiple_files():
    text = ('diff --git a/x b/x\n--- a/x\n+++ b/x\n'
            'diff --git a/sub/y b/sub/y\n--- a/sub/y\n+++ b/sub/y')
    entries = GitService._parse_diff(text)  # pylint: disable=protected-access
    assert [e.path for e in entries] == ['x', 'sub/y']
    assert entries[1].diff.startswith('diff --git a/sub/y')


def test_parse_diff_empty():
    assert GitService._parse_diff('') == []  # pylint: disable=protected-access


# ── tree / changed_files ──

def test_tree_lists_files_at_ref(git_svc, files, bucket):
    first = _commit(git_svc, files, bucket, 'a.typ', '1')
    _commit(git_svc, files, bucket, 'sub/b.typ', '1')
    assert git_svc.tree(bucket, 'HEAD') == ['a.typ', 'sub/b.typ']
    assert git_svc.tree(bucket, first.sha) == ['a.typ']


def test_tree_hides_meta(git_svc, bucket):
    assert git_svc.tree(bucket, 'HEAD') == []


def test_changed_files_vs_parent(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', '1')
    info = _commit(git_svc, files, bucket, 'b.typ', '1')
    assert git_svc.changed_files(bucket, info.sha) == ['b.typ']


def test_changed_files_includes_both_sides_of_rename(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'old.typ', 'content')
    files.rename(bucket, 'old.typ', 'new.typ')
    info = git_svc.commit(bucket, ['old.typ', 'new.typ'], 'rename')
    assert git_svc.changed_files(bucket, info.sha) == ['new.typ', 'old.typ']


def test_changed_files_root_commit_lists_everything(git_svc, bucket):
    # The bucket's root commit only holds .meta.yml, which is hidden.
    root = git_svc._open(bucket)  # pylint: disable=protected-access
    with root as repo:
        sha = list(repo.iter_commits())[-1].hexsha
    assert git_svc.changed_files(bucket, sha) == []


def test_unknown_ref_raises(git_svc, bucket):
    with pytest.raises(Exception):
        git_svc.tree(bucket, 'deadbeef')


# ── show / show_raw ──

def test_show_returns_historic_content(git_svc, files, bucket):
    first = _commit(git_svc, files, bucket, 'a.typ', 'v1')
    _commit(git_svc, files, bucket, 'a.typ', 'v2')
    assert git_svc.show(bucket, first.sha, 'a.typ') == {'content': 'v1', 'binary': False}


def test_show_missing_path_flags_deleted(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', 'x')
    assert git_svc.show(bucket, 'HEAD', 'ghost.typ')['deleted'] is True


def test_show_binary(git_svc, files, bucket):
    files.upload(bucket, 'img.bin', b'\xff\xfe\x00')
    git_svc.commit(bucket, ['img.bin'], 'bin')
    assert git_svc.show(bucket, 'HEAD', 'img.bin') == {'content': None, 'binary': True}


def test_unknown_ref_is_not_found(git_svc, files, bucket):
    _commit(git_svc, files, bucket, 'a.typ', 'x')
    assert git_svc.show(bucket, 'deadbeef', 'a.typ') is None
    assert git_svc.show_raw(bucket, 'deadbeef', 'a.typ') is None
    assert git_svc.restore(bucket, 'deadbeef', ['a.typ']) == []


def test_show_raw(git_svc, files, bucket):
    files.upload(bucket, 'img.bin', b'\xff\xfe\x00')
    git_svc.commit(bucket, ['img.bin'], 'bin')
    assert git_svc.show_raw(bucket, 'HEAD', 'img.bin') == b'\xff\xfe\x00'
    assert git_svc.show_raw(bucket, 'HEAD', 'ghost') is None


# ── restore ──

def test_restore_old_version(git_svc, files, bucket):
    first = _commit(git_svc, files, bucket, 'a.typ', 'v1')
    _commit(git_svc, files, bucket, 'a.typ', 'v2')
    assert git_svc.restore(bucket, first.sha, ['a.typ']) == ['a.typ']
    assert files.read(bucket, 'a.typ')['content'] == 'v1'


def test_restore_deleted_file_in_subdir(git_svc, files, bucket):
    first = _commit(git_svc, files, bucket, 'sub/a.typ', 'v1')
    files.delete_dir(bucket, 'sub')
    assert git_svc.restore(bucket, first.sha, ['sub/a.typ']) == ['sub/a.typ']
    assert files.read(bucket, 'sub/a.typ')['content'] == 'v1'


def test_restore_skips_missing_and_traversal(git_svc, files, bucket, data_dir):
    sha = _commit(git_svc, files, bucket, 'a.typ', 'v1').sha
    assert git_svc.restore(bucket, sha, ['ghost.typ', '../evil.txt']) == []
    assert not (data_dir / 'evil.txt').exists()
