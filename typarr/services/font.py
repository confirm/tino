'''Font management service. Lists, uploads, and deletes custom font files.'''

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_EXTENSIONS = {'.ttf', '.otf', '.woff', '.woff2'}


class FontService:
    '''Manages font files in a flat directory.'''

    def __init__(self, font_dir: Path):
        self.font_dir = font_dir

    def list(self) -> list[dict]:
        '''Return all installed fonts sorted by filename.'''
        if not self.font_dir.is_dir():
            return []
        return sorted(
            (
                {'filename': f.name, 'size': f.stat().st_size}
                for f in self.font_dir.iterdir()
                if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
            ),
            key=lambda e: e['filename'].lower(),
        )

    def upload(self, filename: str, data: bytes) -> bool:
        '''Write a font file. Returns False if the filename is invalid.'''
        if not self._is_valid(filename):
            return False
        (self.font_dir / filename).write_bytes(data)
        logger.info('Uploaded font %s (%d bytes)', filename, len(data))
        return True

    def delete(self, filename: str) -> bool:
        '''Delete a font file. Returns False if not found or invalid.'''
        if not self._is_valid(filename):
            return False
        target = self.font_dir / filename
        if not target.is_file():
            return False
        target.unlink()
        logger.info('Deleted font %s', filename)
        return True

    def _is_valid(self, filename: str) -> bool:
        '''Check that the filename has a valid extension and no path traversal.'''
        if '/' in filename or '\\' in filename or filename.startswith('.'):
            return False
        if Path(filename).suffix.lower() not in VALID_EXTENSIONS:
            return False
        resolved = (self.font_dir / filename).resolve()
        return resolved.parent == self.font_dir.resolve()
