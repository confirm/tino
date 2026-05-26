'''File management service. Reads/writes files within bucket git repos.'''

import shutil
from datetime import datetime, timezone
from pathlib import Path

from ..models import FileEntry

IGNORED = {'.git', '.meta.yml'}


class FileService:
    '''CRUD operations for files within a bucket's working tree.'''

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def _bucket_path(self, slug: str) -> Path:
        '''Resolve a bucket slug to its directory path.'''
        return self.data_dir / slug

    @staticmethod
    def _safe_path(bucket_path: Path, file_path: str) -> Path | None:
        '''Resolve a file path and reject any traversal outside the bucket.'''
        resolved = (bucket_path / file_path).resolve()

        if not str(resolved).startswith(str(bucket_path.resolve())):
            return None

        return resolved

    def list(self, slug: str) -> list[FileEntry]:
        '''List all files and directories in a bucket, excluding .git and .meta.yml.'''
        root = self._bucket_path(slug)

        if not root.is_dir():
            return []

        entries = []
        for item in sorted(root.rglob('*')):
            rel = item.relative_to(root)

            if any(p in IGNORED or p.startswith('.') for p in rel.parts):
                continue

            entries.append(FileEntry(
                path=str(rel),
                type='directory' if item.is_dir() else 'file',
            ))

        return entries

    def read(self, slug: str, file_path: str) -> dict | None:
        '''Read a file's content and modification time, or None if not found.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, file_path)

        if target is None or not target.is_file():
            return None

        mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc).isoformat()

        try:
            content = target.read_text(encoding='utf-8')

        except UnicodeDecodeError:
            return {'binary': True, 'content': None, 'modified': mtime}

        return {'content': content, 'modified': mtime}

    def write(self, slug: str, file_path: str, content: str) -> str | None:
        '''Write content to a file. Returns the ISO mtime on success, None on invalid path.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, file_path)

        if target is None:
            return None

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

        return datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc).isoformat()

    def create(self, slug: str, file_path: str, content: str = '') -> bool:
        '''Create a new file. Returns False if it already exists or the path is invalid.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, file_path)

        if target is None or target.exists():
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

        return True

    def upload(self, slug: str, file_path: str, data: bytes) -> bool:
        '''Write raw bytes to a file. Creates parent dirs as needed.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, file_path)

        if target is None:
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        return True

    def resolve(self, slug: str, file_path: str) -> Path | None:
        '''Return the absolute path to a file, or None if invalid/missing.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, file_path)

        if target is None or not target.is_file():
            return None

        return target

    def rename_dir(self, slug: str, old_path: str, new_path: str) -> list[str] | None:
        '''Rename a directory. Returns list of affected file paths, or None on error.'''
        root   = self._bucket_path(slug)
        source = self._safe_path(root, old_path)
        dest   = self._safe_path(root, new_path)

        if source is None or dest is None or not source.is_dir():
            return None

        if dest.exists():
            return None

        dest.parent.mkdir(parents=True, exist_ok=True)
        affected = [str(f.relative_to(root)) for f in source.rglob('*') if f.is_file()]

        source.rename(dest)

        return affected

    def delete_dir(self, slug: str, dir_path: str) -> list[str] | None:
        '''Delete a directory and all its contents. Returns affected file paths.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, dir_path)

        if target is None or not target.is_dir():
            return None

        affected = [str(f.relative_to(root)) for f in target.rglob('*') if f.is_file()]

        shutil.rmtree(target)

        return affected

    def delete(self, slug: str, file_path: str) -> bool:
        '''Delete a file. Returns False if not found.'''
        root   = self._bucket_path(slug)
        target = self._safe_path(root, file_path)

        if target is None or not target.is_file():
            return False

        target.unlink()

        return True
