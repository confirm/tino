'''Search service. Matches a query against file names and content in a bucket.'''

import logging

from ..models import SearchResult, SearchSnippet
from .file import FileService

logger = logging.getLogger(__name__)

#: Files larger than this (bytes) are skipped for content scanning (name still matches).
MAX_FILE_BYTES = 1_000_000

#: Maximum number of matching content lines reported per file.
MAX_SNIPPETS_PER_FILE = 5

#: Matching content lines are trimmed to this many characters.
SNIPPET_MAX_LEN = 200


class SearchService:  # pylint: disable=too-few-public-methods
    '''Search file names and contents within a bucket's working tree.

    Composes :class:`~tino.services.file.FileService` so it reuses the same
    listing rules (``.git``, ``.meta.yml`` and dotfiles are excluded) and the
    path-traversal safety in :meth:`~tino.services.file.FileService.resolve`.
    Permission filtering (which buckets a user may search) is the caller's
    responsibility — see the search router and the MCP ``search`` tool.
    '''

    def __init__(self, file_service: FileService):
        self.files = file_service

    def search_bucket(self, slug: str, query: str, *, limit: int) -> list[SearchResult]:
        '''Return files in *slug* whose name or content matches *query*.

        Matching is case-insensitive substring. At most *limit* files are
        returned. Each result carries whether the file name matched and up to
        :data:`MAX_SNIPPETS_PER_FILE` matching content lines.
        '''
        needle  = query.lower()
        results = []

        for entry in self.files.list(slug):
            if entry.type != 'file':
                continue

            name_match = needle in entry.path.lower()
            snippets   = self._content_snippets(slug, entry.path, needle)

            if name_match or snippets:
                results.append(SearchResult(
                    bucket=slug,
                    path=entry.path,
                    name_match=name_match,
                    snippets=snippets,
                ))

            if len(results) >= limit:
                break

        logger.debug('Search %r in %s: %d result(s)', query, slug, len(results))
        return results

    def _content_snippets(self, slug: str, path: str, needle: str) -> list[SearchSnippet]:
        '''Return matching content lines for a single file (empty if binary/too large).'''
        target = self.files.resolve(slug, path)

        if target is None or target.stat().st_size > MAX_FILE_BYTES:
            return []

        try:
            text = target.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            return []

        if needle not in text.lower():
            return []

        snippets = []
        for number, line in enumerate(text.splitlines(), start=1):
            if needle in line.lower():
                snippets.append(SearchSnippet(line=number, text=line.strip()[:SNIPPET_MAX_LEN]))
                if len(snippets) >= MAX_SNIPPETS_PER_FILE:
                    break

        return snippets
