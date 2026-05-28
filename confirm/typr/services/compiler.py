'''Typst compiler service. Shells out to the system `typst` binary to produce SVG or PDF output.'''

import subprocess
import tempfile
from pathlib import Path

_COMPILE_TIMEOUT = 30


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

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'page-{n}.svg'
            self._run(source, output, bucket_dir, fmt='svg')

            pages = []
            for svg_file in sorted(Path(tmp).glob('page-*.svg')):
                pages.append(svg_file.read_text(encoding='utf-8'))

            return pages

    def compile_pdf(self, slug: str, path: str) -> Path:
        '''Compile a Typst file and return the path to the resulting PDF.

        Writes to a temporary file; the caller is responsible for deleting it
        (typically via a BackgroundTask on the FileResponse).
        Raises FileNotFoundError if the source file doesn't exist,
        or RuntimeError if compilation fails (with the stderr message).
        '''
        bucket_dir, source = self._resolve_source(slug, path)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            output = Path(tmp.name)

        try:
            self._run(source, output, bucket_dir)
        except Exception:
            output.unlink(missing_ok=True)
            raise

        return output

    # ── Internal ──

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
            raise RuntimeError(result.stderr.strip() or 'Compilation failed')

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
