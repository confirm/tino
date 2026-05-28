'''Bucket management service. Each bucket is a git repo on disk with a .meta.yml.'''

import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

import git
import yaml

from ..models import AccessEntry, BucketInfo

META_FILE = '.meta.yml'
GITATTRIBUTES = Path(__file__).resolve().parent.parent / 'gitattributes'


class BucketService:
    '''CRUD operations for buckets (git-backed project directories).'''

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._slug_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _slug_lock(self, slug: str) -> threading.Lock:
        '''Return a per-slug lock that serializes meta read-modify-write.'''
        with self._locks_guard:
            lock = self._slug_locks.get(slug)
            if lock is None:
                lock = threading.Lock()
                self._slug_locks[slug] = lock
            return lock

    def _path(self, slug: str) -> Path:
        '''Resolve a bucket slug to its directory path.'''
        return self.data_dir / slug

    @staticmethod
    def _read_meta(path: Path) -> dict:
        '''Parse the .meta.yml file from a bucket directory.'''
        meta_file = path / META_FILE

        if meta_file.exists():
            return yaml.safe_load(meta_file.read_text()) or {}

        return {}

    @staticmethod
    def _write_meta(path: Path, meta: dict) -> None:
        '''Write metadata to the bucket's .meta.yml file.'''
        (path / META_FILE).write_text(
            yaml.dump(meta, default_flow_style=False),
        )

    @staticmethod
    def _get_created(path: Path) -> str | None:
        '''Derive the creation timestamp from the initial commit of .meta.yml.'''
        try:
            repo = git.Repo(path)
            try:
                commits = list(repo.iter_commits(paths=META_FILE, max_count=1))
                if commits:
                    ts = datetime.fromtimestamp(commits[-1].committed_date, tz=timezone.utc)
                    return ts.isoformat()
            finally:
                repo.close()

        except (git.InvalidGitRepositoryError, git.GitCommandError):
            pass

        return None

    def _to_info(self, slug: str, path: Path) -> BucketInfo:
        '''Build a BucketInfo response from the bucket directory on disk.'''
        meta = self._read_meta(path)

        return BucketInfo(
            slug=slug,
            description=meta.get('description', ''),
            created=self._get_created(path),
            access=[AccessEntry(**a) for a in meta.get('access', [])],
        )

    @staticmethod
    def _apply_shared_gitattributes(repo: git.Repo) -> None:
        '''Point the repo at the app-level shared .gitattributes.'''
        if GITATTRIBUTES.is_file():
            repo.config_writer().set_value(
                'core', 'attributesFile', str(GITATTRIBUTES),
            ).release()

    def list(self) -> list[BucketInfo]:
        '''List all buckets (directories with a .git folder) in the data dir.'''
        buckets = []

        for entry in sorted(self.data_dir.iterdir()):
            if entry.is_dir() and (entry / '.git').is_dir():
                buckets.append(self._to_info(entry.name, entry))

        return buckets

    def get(self, slug: str) -> BucketInfo | None:
        '''Get a single bucket by slug, or None if it doesn't exist.'''
        path = self._path(slug)

        if not path.is_dir() or not (path / '.git').is_dir():
            return None

        return self._to_info(slug, path)

    def create(
        self, slug: str, description: str = '',
        access: list[AccessEntry] | None = None,
    ) -> BucketInfo:
        '''Create a new bucket: mkdir, git init, write .meta.yml, initial commit.'''
        path = self._path(slug)

        if path.is_dir() and any(path.iterdir()):
            raise FileExistsError(slug)

        path.mkdir(parents=True, exist_ok=True)

        meta = {'description': description}
        if access:
            meta['access'] = [a.model_dump() for a in access]
        self._write_meta(path, meta)

        repo = git.Repo.init(path)
        try:
            self._apply_shared_gitattributes(repo)
            repo.index.add([META_FILE])
            repo.index.commit('Initialize bucket\n\nTypr-Meta: true')
        finally:
            repo.close()

        return self._to_info(slug, path)

    def update(
        self, slug: str, description: str | None = None,
        access: list[AccessEntry] | None = None,
    ) -> BucketInfo | None:
        '''Update a bucket's .meta.yml. Only provided fields are changed.'''
        # Read-modify-write of .meta.yml must be serialized per-slug.
        # Two concurrent updates could otherwise lose each other's changes
        # (each reads the same starting state, last write wins).
        with self._slug_lock(slug):
            path = self._path(slug)

            if not path.is_dir():
                return None

            meta = self._read_meta(path)
            if description is not None:
                meta['description'] = description
            if access is not None:
                meta['access'] = [a.model_dump() for a in access]

            self._write_meta(path, meta)

            repo = git.Repo(path)
            try:
                repo.index.add([META_FILE])
                repo.index.commit('Update bucket metadata\n\nTypr-Meta: true')
            finally:
                repo.close()

            return self._to_info(slug, path)

    def delete(self, slug: str) -> bool:
        '''Delete a bucket and its entire git repo from disk.'''
        path = self._path(slug)

        if not path.is_dir():
            return False

        shutil.rmtree(path)

        return True
