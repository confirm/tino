'''Typst compiler service. Shells out to the system `typst` binary to produce SVG or PDF output.'''

import logging
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_COMPILE_TIMEOUT = 30

# Typst error/warning header and its `  ┌─ file:line:col` location line.
_SEVERITY_RE = re.compile(r'^(error|warning): ?(.*)$')
_HELP_RE     = re.compile(r'^help:')
_LOCATION_RE = re.compile(r'^\s*┌─\s+(.*):(\d+):(\d+)\s*$')


class CompileError(RuntimeError):
    '''Failed Typst compilation holding its diagnostics and raw stderr.'''

    def __init__(self, stderr: str, diagnostics: list[dict]):
        super().__init__(stderr or 'Compilation failed')
        self.diagnostics = diagnostics


def parse_diagnostics(stderr: str) -> list[dict]:
    '''Pull the individual errors out of Typst's stderr.

    File, line and column are None when Typst gives no position.
    '''
    diagnostics: list[dict] = []
    current: dict | None = None

    for raw_line in stderr.splitlines():
        severity = _SEVERITY_RE.match(raw_line)
        if severity:
            current = {
                'severity': severity.group(1),
                'message': severity.group(2).strip(),
                'file': None, 'line': None, 'column': None,
            }
            diagnostics.append(current)
            continue

        # Skip help blocks, but let them close the current error.
        if _HELP_RE.match(raw_line):
            current = None
            continue

        location = _LOCATION_RE.match(raw_line)
        if location and current and current['file'] is None:
            current['file']   = location.group(1)
            current['line']   = int(location.group(2))
            current['column'] = int(location.group(3))

    return diagnostics


class CompilerService:
    '''Compiles .typ files to SVG or PDF by invoking the Typst CLI.'''

    def __init__(self, data_dir: Path, package_dir: Path | None = None,
                 font_dir: Path | None = None):
        self.data_dir = data_dir
        self.package_dir = package_dir
        self.font_dir = font_dir

    @staticmethod
    def version() -> str:
        '''Return the installed Typst CLI version string.'''
        result = subprocess.run(
            ['typst', '--version'],
            capture_output=True, text=True, check=True,
        )

        return result.stdout.strip()

    def compile_svg(self, slug: str, path: str) -> list[str]:
        '''Compile a Typst file and return a list of SVG strings (one per page).

        Raises FileNotFoundError if the source file doesn't exist,
        or RuntimeError if compilation fails (with the stderr message).
        '''
        bucket_dir, source = self._resolve_source(slug, path)
        logger.debug('Compiling SVG for %s/%s', slug, path)

        return self._render_svgs(source, bucket_dir)

    def compile_pdf(self, slug: str, path: str) -> Path:
        '''Compile a Typst file and return the path to the resulting PDF.

        Writes to a temporary file; the caller is responsible for deleting it
        (typically via a BackgroundTask on the FileResponse).
        Raises FileNotFoundError if the source file doesn't exist,
        or RuntimeError if compilation fails (with the stderr message).
        '''
        bucket_dir, source = self._resolve_source(slug, path)
        logger.info('Compiling PDF for %s/%s', slug, path)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output = Path(tmp.name)

        try:
            self._run(source, output, bucket_dir)
        except Exception:
            output.unlink(missing_ok=True)
            raise

        return output

    # ── Internal ──

    def _render_svgs(self, source, bucket_dir):
        '''Compile a source file to SVG and return one string per page.'''
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'page-{n}.svg'
            self._run(source, output, bucket_dir, fmt='svg')

            return [
                svg_file.read_text(encoding='utf-8')
                for svg_file in sorted(Path(tmp).glob('page-*.svg'))
            ]

    def _resolve_source(self, slug, path):
        '''Validate that the source file exists and is inside the bucket.'''
        bucket_dir = (self.data_dir / slug).resolve()
        source     = (bucket_dir / path).resolve()

        if not source.is_relative_to(bucket_dir):
            raise FileNotFoundError(f'{path} is outside the bucket')

        if not source.is_file():
            raise FileNotFoundError(f'{path} not found in bucket {slug}')

        return bucket_dir, source

    def _run(self, source, output, root, fmt=None):
        '''Build the typst compile command, run it, and raise on failure.'''
        result = subprocess.run(
            self._build_cmd(source, output, root, fmt),
            cwd=str(root),
            capture_output=True, text=True,
            timeout=_COMPILE_TIMEOUT, check=False,
        )

        if result.returncode != 0:
            stderr = self._strip_paths(result.stderr.strip(), root)
            logger.warning('Compilation failed for %s: %s', source, stderr)
            raise CompileError(stderr, parse_diagnostics(stderr))

    def _strip_paths(self, text, root):
        '''Strip absolute paths so only bucket-relative ones reach the client.'''
        for base in (root, self.data_dir):
            text = text.replace(f'{base}/', '').replace(str(base), '')

        return text

    def _build_cmd(self, source, output, root, fmt=None):
        '''Assemble the typst compile argument list.'''
        cmd = ['typst', 'compile']

        if fmt:
            cmd.extend(['--format', fmt])

        if self.package_dir:
            cmd.extend(['--package-path', str(self.package_dir)])

        if self.font_dir and self.font_dir.is_dir():
            cmd.extend(['--font-path', str(self.font_dir)])

        cmd.extend(['--root', str(root), str(source), str(output)])

        return cmd
