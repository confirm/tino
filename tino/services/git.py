'''Git operations service. Wraps GitPython to expose status, commit, log, diff, and restore.'''

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import git as gitpython

from ..models import CommitInfo, DiffEntry, FileStatus

logger = logging.getLogger(__name__)

# Stand-in "parent" for diffing a root commit: git's well-known empty-tree SHA.
_EMPTY_TREE_SHA = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


class GitService:
    '''Git operations on bucket repositories (status, commit, log, diff, restore).'''

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    @contextmanager
    def _open(self, slug: str):
        '''Open a git repo and ensure it is closed after use.'''
        repo = gitpython.Repo(self.data_dir / slug)

        try:
            yield repo
        finally:
            repo.close()

    @staticmethod
    def _to_commit_info(c, deleted: bool = False) -> CommitInfo:
        '''Convert a git commit object to a CommitInfo model.'''
        return CommitInfo(
            sha=c.hexsha,
            message=c.message.strip(),
            author=str(c.author),
            timestamp=datetime.fromtimestamp(c.committed_date, tz=timezone.utc).isoformat(),
            deleted=deleted,
        )

    def status(self, slug: str) -> list[FileStatus]:
        '''Return the working tree status of all user files (excludes .meta.yml and dotfiles).'''
        with self._open(slug) as repo:
            result = []

            for path in repo.untracked_files:
                if not path.startswith('.'):
                    result.append(FileStatus(path=path, status='untracked'))

            for d in repo.index.diff(None):
                if not d.a_path.startswith('.'):
                    status = 'deleted' if d.deleted_file else 'modified'
                    result.append(FileStatus(path=d.a_path, status=status))

            return result

    def commit(self, slug: str, files: list[str], message: str, *,  # pylint: disable=too-many-arguments
               author: str = 'TINO', email: str = '') -> CommitInfo:
        '''Stage the specified files and create a commit.'''
        with self._open(slug) as repo:
            working_dir = Path(repo.working_dir).resolve()
            safe = [f for f in files
                    if (working_dir / f).resolve().is_relative_to(working_dir)]
            existing = [f for f in safe if (working_dir / f).exists()]
            deleted  = [f for f in safe if not (working_dir / f).exists()]

            if existing:
                repo.index.add(existing)

            if deleted:
                repo.index.remove(deleted, working_tree=False)

            actor  = gitpython.Actor(author, email or f'{author}@tino')
            commit = repo.index.commit(message, author=actor)
            logger.info(
                'Committed %s in %s by %s (%d files)',
                commit.hexsha[:8], slug, author, len(files),
            )

            return self._to_commit_info(commit)

    def log(self, slug: str, path: str | None = None, max_count: int = 50) -> list[CommitInfo]:
        '''Return commit history, optionally filtered to a single file.'''
        with self._open(slug) as repo:
            kwargs: dict = {'max_count': max_count}

            if path:
                kwargs['paths'] = path

            commits      = [c for c in repo.iter_commits(**kwargs)
                            if 'true' not in c.trailers.get('Tino-Meta', [])][:max_count]
            deleted_shas = self._deleted_shas(repo, path) if path else set()

            return [self._to_commit_info(c, c.hexsha in deleted_shas) for c in commits]

    @staticmethod
    def _deleted_shas(repo, path: str) -> set[str]:
        '''Return the set of commit SHAs where `path` was deleted.'''
        output = repo.git.log('--format=%H', '--diff-filter=D', '--', path)
        return set(output.split('\n')) if output else set()

    def diff(self, slug: str, path: str | None = None,
             ref: str | None = None) -> list[DiffEntry]:
        '''Return unified diffs.

        With ``ref=None`` (default) returns working-tree changes vs HEAD.
        With ``ref`` set returns the changes introduced by that commit
        (commit-vs-parent, or commit-vs-empty-tree for the root commit).
        '''
        with self._open(slug) as repo:
            diff_text = self._diff_text(repo, path, ref)
            return self._parse_diff(diff_text)

    @staticmethod
    def _diff_text(repo, path: str | None, ref: str | None) -> str:
        '''Compute the unified-diff text for either the working tree or a commit.'''
        if ref is None:
            return repo.git.diff(path) if path else repo.git.diff()
        commit = repo.commit(ref)
        base = f'{ref}^' if commit.parents else _EMPTY_TREE_SHA
        args = [base, ref]
        if path:
            args.extend(['--', path])
        return repo.git.diff(*args)

    @staticmethod
    def _parse_diff(diff_text: str) -> list[DiffEntry]:
        '''Parse unified diff output into DiffEntry models.'''
        if not diff_text:
            return []

        entries                  = []
        current_path             = None
        current_lines: list[str] = []

        for line in diff_text.split('\n'):

            if line.startswith('diff --git'):
                if current_path:
                    entries.append(DiffEntry(path=current_path, diff='\n'.join(current_lines)))

                parts         = line.split(' b/')
                current_path  = parts[-1] if len(parts) > 1 else 'unknown'
                current_lines = [line]

            else:
                current_lines.append(line)

        if current_path:
            entries.append(DiffEntry(path=current_path, diff='\n'.join(current_lines)))

        return entries

    def tree(self, slug: str, ref: str) -> list[str]:
        '''List all file paths at a specific commit ref.'''
        with self._open(slug) as repo:
            commit = repo.commit(ref)
            return sorted(
                blob.path for blob in commit.tree.traverse()
                if blob.type == 'blob' and not blob.path.startswith('.')
            )

    def show(self, slug: str, ref: str, path: str) -> dict | None:
        '''Return a file's content at a specific commit ref, or None if not found.'''
        with self._open(slug) as repo:
            try:
                blob = repo.commit(ref).tree / path
                content = blob.data_stream.read().decode('utf-8')
                return {'content': content, 'binary': False}
            except KeyError:
                return {'content': None, 'binary': False, 'deleted': True}
            except gitpython.GitCommandError:
                return None
            except UnicodeDecodeError:
                return {'content': None, 'binary': True}

    def show_raw(self, slug: str, ref: str, path: str) -> bytes | None:
        '''Return a file's raw bytes at a specific commit ref, or None if not found.'''
        with self._open(slug) as repo:
            try:
                blob = repo.commit(ref).tree / path
                return blob.data_stream.read()
            except (KeyError, gitpython.GitCommandError):
                return None

    def restore(self, slug: str, ref: str, paths: list[str]) -> list[str]:
        '''Restore files from a specific commit into the working tree.'''
        with self._open(slug) as repo:
            working_dir = Path(repo.working_dir).resolve()
            restored    = []

            for p in paths:
                target = (working_dir / p).resolve()
                if not target.is_relative_to(working_dir):
                    continue
                try:
                    data = (repo.commit(ref).tree / p).data_stream.read()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    restored.append(p)
                except (KeyError, gitpython.GitCommandError):
                    pass

            if restored:
                logger.info('Restored %d files in %s from %s', len(restored), slug, ref[:8])
            return restored
