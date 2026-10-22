'''Review comment storage service for source-anchored discussion threads.'''

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

import git

from ..models import ReviewMessage, ReviewReplyCreate, ReviewThread, ReviewThreadCreate, \
    ReviewThreadUpdate, User

logger = logging.getLogger(__name__)

STORE_RELATIVE = '.tino/comments.json'


class ReviewPathError(ValueError):
    '''Raised when a review thread targets an invalid or missing source path.'''


class ReviewThreadNotFound(KeyError):
    '''Raised when a review thread id is not present in the bucket store.'''


class ReviewService:
    '''CRUD operations for hidden, git-backed review comment metadata.'''

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._slug_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _slug_lock(self, slug: str) -> threading.Lock:
        '''Return a per-slug lock for read-modify-write operations.'''
        with self._locks_guard:
            lock = self._slug_locks.get(slug)
            if lock is None:
                lock = threading.Lock()
                self._slug_locks[slug] = lock
            return lock

    def _bucket_path(self, slug: str) -> Path:
        return self.data_dir / slug

    def _store_path(self, slug: str) -> Path:
        return self._bucket_path(slug) / STORE_RELATIVE

    @staticmethod
    def _empty_store() -> dict:
        return {'threads': [], 'version': 1}

    def _read_store(self, slug: str) -> dict:
        store = self._store_path(slug)
        if not store.exists():
            return self._empty_store()
        data = json.loads(store.read_text(encoding='utf-8'))
        data.setdefault('version', 1)
        data.setdefault('threads', [])
        return data

    def _write_store(self, slug: str, data: dict, user: User) -> None:
        root = self._bucket_path(slug)
        store = self._store_path(slug)
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(
            json.dumps(data, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )
        self._commit_metadata(root, user)

    @staticmethod
    def _commit_metadata(root: Path, user: User) -> None:
        repo = git.Repo(root)
        try:
            repo.index.add([STORE_RELATIVE])
            if not repo.is_dirty(index=True, working_tree=False, untracked_files=True):
                return
            actor = git.Actor(user.username, user.email or f'{user.username}@tino')
            repo.index.commit(
                'Update review comments\n\nTino-Meta: true',
                author=actor,
                committer=actor,
            )
        finally:
            repo.close()

    def _validate_path(self, slug: str, path: str) -> None:
        pure = PurePosixPath(path)
        if (
            not path
            or pure.is_absolute()
            or any(part in {'', '..'} or part.startswith('.') for part in pure.parts)
        ):
            raise ReviewPathError(path)

        root = self._bucket_path(slug).resolve()
        target = (root / path).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ReviewPathError(path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _message(body: str, user: User) -> ReviewMessage:
        return ReviewMessage(
            id=uuid4().hex,
            author=user.username,
            body=body.strip(),
            created_at=ReviewService._now(),
        )

    @staticmethod
    def _find(data: dict, thread_id: str) -> dict:
        for thread in data['threads']:
            if thread['id'] == thread_id:
                return thread
        raise ReviewThreadNotFound(thread_id)

    def list(
        self, slug: str, path: str | None = None,
        status: str = 'open',
    ) -> list[ReviewThread]:
        '''List review threads, optionally filtered by source path and status.'''
        data = self._read_store(slug)
        threads = data['threads']
        if path is not None:
            threads = [thread for thread in threads if thread['path'] == path]
        if status != 'all':
            threads = [thread for thread in threads if thread['status'] == status]
        return [ReviewThread(**thread) for thread in threads]

    def create(self, slug: str, body: ReviewThreadCreate, user: User) -> ReviewThread:
        '''Create a new review thread anchored to an existing visible source file.'''
        self._validate_path(slug, body.path)
        with self._slug_lock(slug):
            data = self._read_store(slug)
            thread = ReviewThread(
                id=uuid4().hex,
                path=body.path,
                anchor=body.anchor,
                created_by=user.username,
                created_at=self._now(),
                messages=[self._message(body.body, user)],
            )
            data['threads'].append(thread.model_dump())
            self._write_store(slug, data, user)
            logger.info('Created review thread %s in %s/%s', thread.id, slug, body.path)
            return thread

    def reply(
        self, slug: str, thread_id: str,
        body: ReviewReplyCreate, user: User,
    ) -> ReviewThread:
        '''Append a reply to an existing review thread.'''
        with self._slug_lock(slug):
            data = self._read_store(slug)
            thread = self._find(data, thread_id)
            thread['messages'].append(self._message(body.body, user).model_dump())
            self._write_store(slug, data, user)
            logger.info('Replied to review thread %s in %s', thread_id, slug)
            return ReviewThread(**thread)

    def update(
        self, slug: str, thread_id: str,
        body: ReviewThreadUpdate, user: User,
    ) -> ReviewThread:
        '''Change a review thread's open/resolved status.'''
        with self._slug_lock(slug):
            data = self._read_store(slug)
            thread = self._find(data, thread_id)
            thread['status'] = body.status
            if body.status == 'resolved':
                thread['resolved_by'] = user.username
                thread['resolved_at'] = self._now()
            else:
                thread['resolved_by'] = None
                thread['resolved_at'] = None
            self._write_store(slug, data, user)
            logger.info('Updated review thread %s in %s to %s', thread_id, slug, body.status)
            return ReviewThread(**thread)
