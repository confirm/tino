'''Template service. Fetches the Typst package index and runs typst init.'''

import shutil
import subprocess
import tempfile
import time
import tomllib
from logging import getLogger
from pathlib import Path

import httpx

logger = getLogger(__name__)

INDEX_URL = 'https://packages.typst.org/preview/index.json'
CACHE_TTL = 3600  # 1 hour


class TemplateService:
    '''Fetches Typst templates and initializes buckets from them.'''

    def __init__(self, data_dir: Path, package_dir: Path | None = None):
        self.data_dir                  = data_dir
        self.package_dir               = package_dir
        self._cache: list[dict] | None = None
        self._cache_time: float        = 0

    def list_templates(self) -> list[dict]:
        '''Return all Typst packages that are templates (have a template field).'''
        now = time.monotonic()
        if self._cache is not None and (now - self._cache_time) < CACHE_TTL:
            return self._cache

        resp = httpx.get(INDEX_URL, timeout=15)
        resp.raise_for_status()
        packages = resp.json()

        templates = [
            {
                'authors': pkg.get('authors', []),
                'description': pkg.get('description', ''),
                'entrypoint': pkg['template'].get('entrypoint', 'main.typ'),
                'name': pkg['name'],
                'version': pkg['version'],
            }
            for pkg in packages
            if pkg.get('template')
        ]

        self._cache      = templates
        self._cache_time = now

        return templates

    def init_template(
        self, slug: str, name: str, version: str,
        namespace: str = 'preview',
    ) -> None:
        '''Run typst init in a temp directory, then copy files into the bucket.

        This avoids the "project directory already exists" error that occurs
        when the bucket directory already contains .git or .meta.yml.

        Raises FileNotFoundError if the bucket doesn't exist,
        or RuntimeError if typst init fails.
        '''
        bucket_dir = (self.data_dir / slug).resolve()
        if not bucket_dir.is_dir():
            raise FileNotFoundError(f'Bucket {slug} not found')

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'project'
            cmd = ['typst', 'init']

            if self.package_dir:
                cmd.extend(['--package-path', str(self.package_dir)])

            cmd.extend([f'@{namespace}/{name}:{version}', str(out)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    result.stderr.strip() or 'Template init failed',
                )

            conflicts = _find_conflicts(out, bucket_dir)
            if conflicts:
                names = ', '.join(sorted(conflicts))
                raise FileExistsError(
                    f'Files already exist: {names}',
                )

            for item in out.iterdir():
                dest = bucket_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)

    def list_local_templates(self) -> list[dict]:
        '''Scan the package directory for local packages that provide templates.

        Looks for ``typst.toml`` files with a ``[template]`` section under
        ``{package_dir}/{namespace}/{name}/{version}/``.
        '''
        if not self.package_dir or not self.package_dir.is_dir():
            return []

        templates = []
        for toml_path in self.package_dir.rglob('typst.toml'):
            parts = toml_path.relative_to(self.package_dir).parts
            expected_depth = 4
            if len(parts) != expected_depth:
                continue

            namespace, name, version, _ = parts
            try:
                data = tomllib.loads(
                    toml_path.read_text(encoding='utf-8'),
                )
            except (OSError, tomllib.TOMLDecodeError):
                logger.warning('Skipping invalid %s', toml_path)
                continue

            if 'template' not in data:
                continue

            pkg = data.get('package', {})
            tpl = data['template']
            templates.append({
                'authors': pkg.get('authors', []),
                'description': pkg.get('description', ''),
                'entrypoint': tpl.get('entrypoint', 'main.typ'),
                'name': name,
                'namespace': namespace,
                'version': version,
            })

        return templates


def _find_conflicts(src: Path, dest: Path) -> list[str]:
    '''Return relative paths from src that already exist under dest.'''
    conflicts = []

    for item in src.rglob('*'):
        if not item.is_file():
            continue

        rel = item.relative_to(src)

        if (dest / rel).exists():
            conflicts.append(str(rel))

    return conflicts
