'''Typst compiler service. Shells out to the system `typst` binary to produce SVG output.'''

import subprocess
import tempfile
from pathlib import Path


class CompilerService:
    '''Compiles .typ files to SVG by invoking the Typst CLI.'''

    def __init__(self, data_dir: Path, package_dir: Path | None = None):
        self.data_dir = data_dir
        self.package_dir = package_dir

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
        bucket_dir = (self.data_dir / slug).resolve()
        source = (bucket_dir / path).resolve()
        if not str(source).startswith(str(bucket_dir)):
            raise FileNotFoundError(f'{path} is outside the bucket')
        if not source.is_file():
            raise FileNotFoundError(f'{path} not found in bucket {slug}')

        with tempfile.TemporaryDirectory() as tmp:
            output_pattern = Path(tmp) / 'page-{n}.svg'
            cmd = ['typst', 'compile', '--format', 'svg']
            if self.package_dir:
                cmd.extend(['--package-path', str(self.package_dir)])
            cmd.extend([str(source), str(output_pattern)])
            result = subprocess.run(
                cmd,
                cwd=str(self.data_dir / slug),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or 'Compilation failed')

            pages = []
            for svg_file in sorted(Path(tmp).glob('page-*.svg')):
                pages.append(svg_file.read_text(encoding='utf-8'))

            return pages

    def compile_pdf(self, slug: str, path: str) -> Path:
        '''Compile a Typst file and return the path to the resulting PDF.

        Raises FileNotFoundError if the source file doesn't exist,
        or RuntimeError if compilation fails (with the stderr message).
        '''
        bucket_dir = (self.data_dir / slug).resolve()
        source = (bucket_dir / path).resolve()
        if not str(source).startswith(str(bucket_dir)):
            raise FileNotFoundError(f'{path} is outside the bucket')
        if not source.is_file():
            raise FileNotFoundError(f'{path} not found in bucket {slug}')

        output = bucket_dir / '.typst-output.pdf'
        cmd = ['typst', 'compile']
        if self.package_dir:
            cmd.extend(['--package-path', str(self.package_dir)])
        cmd.extend([str(source), str(output)])
        result = subprocess.run(
            cmd,
            cwd=str(bucket_dir),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or 'Compilation failed')

        return output
