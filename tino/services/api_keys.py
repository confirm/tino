'''Service for managing global API keys stored in ``api_keys.yml``.'''

import hashlib
import secrets
from datetime import date
from logging import getLogger
from pathlib import Path

import yaml

logger = getLogger(__name__)

_TOKEN_PREFIX = 'tino_'


def _hash(token: str) -> str:
    return 'sha256:' + hashlib.sha256(token.encode()).hexdigest()


class ApiKeyService:
    '''Manages API keys persisted in a single YAML file.

    File format::

        keys:
          - id: key_abc123
            hash: "sha256:..."
            label: "Claude Desktop MCP"
            created: "2026-06-04"
            access:
              my-bucket: editor
              reports:   viewer
    '''

    def __init__(self, path: Path) -> None:
        self._path = path
        self._cache_mtime: float | None = None
        self._keys: list[dict] = []
        self._by_hash: dict[str, dict] = {}

    # ── Private helpers ──

    def _load(self) -> list[dict]:
        '''Return all key records, re-reading the file only when it has changed.

        The parsed keys and a ``hash → record`` index are cached and refreshed
        when the file's mtime changes (or after a local write, which clears the
        cached mtime). This keeps :meth:`verify` an O(1) in-memory lookup on the
        per-request hot path instead of a disk read plus YAML parse every time.
        '''
        try:
            mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            self._keys = []
            self._by_hash = {}
            self._cache_mtime = None
            return self._keys

        if mtime != self._cache_mtime:
            with open(self._path, encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            self._keys = data.get('keys', [])
            self._by_hash = {k['hash']: k for k in self._keys if 'hash' in k}
            self._cache_mtime = mtime

        return self._keys

    def _save(self, keys: list[dict]) -> None:
        with open(self._path, 'w', encoding='utf-8') as f:
            yaml.dump({'keys': keys}, f, default_flow_style=False, allow_unicode=True)
        # Force the next _load to re-read and rebuild the index. Clearing the
        # mtime (rather than trusting the freshly written one) avoids a stale
        # read if two writes land within the filesystem's mtime resolution.
        self._cache_mtime = None

    @staticmethod
    def _strip_hash(record: dict) -> dict:
        return {k: v for k, v in record.items() if k != 'hash'}

    # ── Public API ──

    def create(self, label: str, access: dict[str, str]) -> tuple[str, dict]:
        '''Generate a new API key.

        :returns: ``(raw_token, key_record)`` — the raw token is shown once and never stored.
        '''
        raw = _TOKEN_PREFIX + secrets.token_hex(32)
        record = {
            'id': 'key_' + secrets.token_hex(8),
            'hash': _hash(raw),
            'label': label,
            'created': str(date.today()),
            'access': access,
        }
        keys = [*self._load(), record]
        self._save(keys)
        logger.info('API key created: %s (%s)', record['id'], label)
        return raw, self._strip_hash(record)

    def verify(self, token: str) -> dict | None:
        '''Return the key record for *token*, or ``None`` if the token is invalid.'''
        if not token.startswith(_TOKEN_PREFIX):
            return None
        self._load()
        record = self._by_hash.get(_hash(token))
        return self._strip_hash(record) if record is not None else None

    def list_keys(self) -> list[dict]:
        '''Return all key records without hashes.'''
        return [self._strip_hash(k) for k in self._load()]

    def revoke(self, key_id: str) -> bool:
        '''Remove the key with the given ID. Returns ``True`` if found and removed.'''
        keys = self._load()
        new_keys = [k for k in keys if k.get('id') != key_id]
        if len(new_keys) == len(keys):
            return False
        self._save(new_keys)
        logger.info('API key revoked: %s', key_id)
        return True

    def update(self, key_id: str, label: str | None, access: dict[str, str] | None) -> dict | None:
        '''Update the label and/or access map for a key.

        :returns: The updated key record (without hash), or ``None`` if not found.
        '''
        keys = self._load()
        for key in keys:
            if key.get('id') == key_id:
                if label is not None:
                    key['label'] = label
                if access is not None:
                    key['access'] = access
                self._save(keys)
                logger.info('API key updated: %s', key_id)
                return self._strip_hash(key)
        return None
