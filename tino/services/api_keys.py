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

    # ── Private helpers ──

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        with open(self._path, encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return data.get('keys', [])

    def _save(self, keys: list[dict]) -> None:
        with open(self._path, 'w', encoding='utf-8') as f:
            yaml.dump({'keys': keys}, f, default_flow_style=False, allow_unicode=True)

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
        keys = self._load()
        keys.append(record)
        self._save(keys)
        logger.info('API key created: %s (%s)', record['id'], label)
        return raw, self._strip_hash(record)

    def verify(self, token: str) -> dict | None:
        '''Return the key record for *token*, or ``None`` if the token is invalid.'''
        if not token.startswith(_TOKEN_PREFIX):
            return None
        h = _hash(token)
        for key in self._load():
            if key.get('hash') == h:
                return self._strip_hash(key)
        return None

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
