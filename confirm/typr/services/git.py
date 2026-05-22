'''Git operations service. Wraps GitPython to expose status, commit, log, diff, and restore.'''

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import git as gitpython

from ..models import CommitInfo, DiffEntry, FileStatus


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
    def _to_commit_info(c) -> CommitInfo:
        '''Convert a git commit object to a CommitInfo model.'''
        return CommitInfo(
            sha=c.hexsha,
            message=c.message.strip(),
            author=str(c.author),
            timestamp=datetime.fromtimestamp(c.committed_date, tz=timezone.utc).isoformat(),
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
               author: str = 'Typr', email: str = '') -> CommitInfo:
        '''Stage the specified files and create a commit.'''
        with self._open(slug) as repo:
            working_dir = Path(repo.working_dir).resolve()
            safe = [f for f in files
                    if str((working_dir / f).resolve()).startswith(str(working_dir))]
            existing = [f for f in safe if (working_dir / f).exists()]
            deleted = [f for f in safe if not (working_dir / f).exists()]

            if existing:
                repo.index.add(existing)
            if deleted:
                repo.index.remove(deleted, working_tree=False)

            actor = gitpython.Actor(author, email or f'{author}@typr')
            c = repo.index.commit(message, author=actor)
            return self._to_commit_info(c)

    def log(self, slug: str, path: str | None = None, max_count: int = 50) -> list[CommitInfo]:
        '''Return commit history, optionally filtered to a single file.'''
        with self._open(slug) as repo:
            kwargs: dict = {'max_count': max_count}
            if path:
                kwargs['paths'] = path
            return [self._to_commit_info(c) for c in repo.iter_commits(**kwargs)]

    def diff(self, slug: str, path: str | None = None) -> list[DiffEntry]:
        '''Return unified diffs for modified files in the working tree.'''
        with self._open(slug) as repo:
            diff_text = repo.git.diff(path) if path else repo.git.diff()
            return self._parse_diff(diff_text)

    @staticmethod
    def _parse_diff(diff_text: str) -> list[DiffEntry]:
        '''Parse unified diff output into DiffEntry models.'''
        if not diff_text:
            return []

        entries = []
        current_path = None
        current_lines: list[str] = []
        for line in diff_text.split('\n'):
            if line.startswith('diff --git'):
                if current_path:
                    entries.append(DiffEntry(path=current_path, diff='\n'.join(current_lines)))
                parts = line.split(' b/')
                current_path = parts[-1] if len(parts) > 1 else 'unknown'
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

    def show(self, slug: str, ref: str, path: str) -> str | None:
        '''Return a file's content at a specific commit ref, or None if not found.'''
        with self._open(slug) as repo:
            try:
                blob = repo.commit(ref).tree / path
                return blob.data_stream.read().decode('utf-8')
            except (KeyError, gitpython.GitCommandError):
                return None

    def restore(self, slug: str, ref: str, paths: list[str]) -> list[str]:
        '''Restore files from a specific commit into the working tree.'''
        with self._open(slug) as repo:
            working_dir = Path(repo.working_dir).resolve()
            restored = []
            for p in paths:
                target = (working_dir / p).resolve()
                if not str(target).startswith(str(working_dir)):
                    continue
                try:
                    content = (repo.commit(ref).tree / p).data_stream.read().decode('utf-8')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding='utf-8')
                    restored.append(p)
                except (KeyError, gitpython.GitCommandError):
                    pass
            return restored
