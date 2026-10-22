'''Tests for CompilerService: command building, path safety and error handling.

The ``typst``-marked tests run the real CLI and are skipped when it is missing.
'''

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tino.services.compiler import CompileError, CompilerService, parse_diagnostics

needs_typst = pytest.mark.skipif(shutil.which('typst') is None, reason='typst CLI not installed')


@pytest.fixture
def compiler(data_dir):
    return CompilerService(data_dir)


def _fake_run(pages=1, returncode=0, stderr=''):
    '''A subprocess.run stand-in that writes fake SVG/PDF output.'''
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        output = cmd[-1]
        if returncode == 0:
            if '{n}' in output:
                for n in range(1, pages + 1):
                    Path(output.replace('{n}', str(n))).write_text(f'<svg>{n}</svg>')
            else:
                Path(output).write_bytes(b'%PDF')
        return SimpleNamespace(returncode=returncode, stderr=stderr, stdout='')

    return fake_run, calls


# ── command building ──

def test_build_cmd_minimal(compiler, tmp_path):
    cmd = compiler._build_cmd('src.typ', 'out.pdf', tmp_path)  # pylint: disable=protected-access
    assert cmd == ['typst', 'compile', '--root', str(tmp_path), 'src.typ', 'out.pdf']


def test_build_cmd_full(tmp_path):
    fonts = tmp_path / 'fonts'
    fonts.mkdir()
    svc = CompilerService(tmp_path, tmp_path / 'pkgs', fonts)
    cmd = svc._build_cmd('s', 'o', tmp_path, fmt='svg')  # pylint: disable=protected-access
    assert cmd[cmd.index('--format') + 1] == 'svg'
    assert cmd[cmd.index('--package-path') + 1] == str(tmp_path / 'pkgs')
    assert cmd[cmd.index('--font-path') + 1] == str(fonts)


def test_build_cmd_skips_missing_font_dir(tmp_path):
    svc = CompilerService(tmp_path, font_dir=tmp_path / 'missing')
    assert '--font-path' not in svc._build_cmd('s', 'o', tmp_path)  # pylint: disable=protected-access


# ── source resolution ──

def test_missing_source(compiler, bucket):
    with pytest.raises(FileNotFoundError):
        compiler.compile_svg(bucket, 'ghost.typ')


def test_traversal_source(compiler, bucket, data_dir):
    (data_dir / 'outside.typ').write_text('x')
    with pytest.raises(FileNotFoundError, match='outside the bucket'):
        compiler.compile_pdf(bucket, '../outside.typ')


# ── compile (mocked typst) ──

def test_compile_svg_returns_pages_in_order(compiler, files, bucket, monkeypatch):
    files.write(bucket, 'a.typ', 'x')
    fake_run, calls = _fake_run(pages=3)
    monkeypatch.setattr(subprocess, 'run', fake_run)

    assert compiler.compile_svg(bucket, 'a.typ') == ['<svg>1</svg>', '<svg>2</svg>', '<svg>3</svg>']
    cmd, kwargs = calls[0]
    assert kwargs['cwd'] == str((compiler.data_dir / bucket).resolve())
    assert kwargs['timeout'] > 0


def test_compile_pdf_returns_temp_file(compiler, files, bucket, monkeypatch):
    files.write(bucket, 'a.typ', 'x')
    monkeypatch.setattr(subprocess, 'run', _fake_run()[0])
    pdf = compiler.compile_pdf(bucket, 'a.typ')
    try:
        assert pdf.read_bytes() == b'%PDF'
    finally:
        pdf.unlink()


def test_compile_error_raises_with_stderr(compiler, files, bucket, monkeypatch):
    files.write(bucket, 'a.typ', 'x')
    monkeypatch.setattr(subprocess, 'run', _fake_run(returncode=1, stderr='error: boom')[0])
    with pytest.raises(RuntimeError, match='boom'):
        compiler.compile_svg(bucket, 'a.typ')


def test_compile_pdf_error_cleans_temp_file(compiler, files, bucket, monkeypatch):
    files.write(bucket, 'a.typ', 'x')
    fake_run, calls = _fake_run(returncode=1)
    monkeypatch.setattr(subprocess, 'run', fake_run)
    with pytest.raises(RuntimeError, match='Compilation failed'):
        compiler.compile_pdf(bucket, 'a.typ')
    assert not Path(calls[0][0][-1]).exists()


def test_version(monkeypatch):
    monkeypatch.setattr(subprocess, 'run',
                        lambda *a, **k: SimpleNamespace(stdout='typst 0.15.1\n'))
    assert CompilerService.version() == 'typst 0.15.1'


# ── diagnostics ──

TYPST_STDERR = '''\
error: unknown variable: foo
  ┌─ main.typ:3:2
  │
3 │ #foo
  │  ^^^

warning: unused import
  ┌─ lib/util.typ:12:10
  │
12 │ #import "x.typ": y
'''


def test_parse_diagnostics_errors_and_warnings():
    assert parse_diagnostics(TYPST_STDERR) == [
        {'severity': 'error', 'message': 'unknown variable: foo',
         'file': 'main.typ', 'line': 3, 'column': 2},
        {'severity': 'warning', 'message': 'unused import',
         'file': 'lib/util.typ', 'line': 12, 'column': 10},
    ]


def test_parse_diagnostics_without_location():
    assert parse_diagnostics('error: failed to load file (access denied)') == [
        {'severity': 'error', 'message': 'failed to load file (access denied)',
         'file': None, 'line': None, 'column': None},
    ]


def test_parse_diagnostics_keeps_first_location():
    stderr = 'error: boom\n  ┌─ a.typ:1:1\n  ┌─ b.typ:9:9\n'
    [diag] = parse_diagnostics(stderr)
    assert (diag['file'], diag['line']) == ('a.typ', 1)


def test_parse_diagnostics_help_block_closes_error():
    stderr = 'error: boom\nhelp: try this\n  ┌─ other.typ:5:5\n'
    [diag] = parse_diagnostics(stderr)
    assert diag['file'] is None


def test_parse_diagnostics_ignores_location_before_header():
    assert parse_diagnostics('  ┌─ stray.typ:1:1\nerror: x\n')[0]['file'] is None


def test_parse_diagnostics_path_with_colon_and_spaces():
    [diag] = parse_diagnostics('error: x\n  ┌─ my docs/a:b.typ:7:3\n')
    assert (diag['file'], diag['line'], diag['column']) == ('my docs/a:b.typ', 7, 3)


@pytest.mark.parametrize('stderr', ['', 'some random output', 'Error: not typst format'])
def test_parse_diagnostics_nothing_to_parse(stderr):
    assert parse_diagnostics(stderr) == []


def test_compile_error_is_runtime_error():
    exc = CompileError('', [])
    assert isinstance(exc, RuntimeError)
    assert str(exc) == 'Compilation failed'
    assert exc.diagnostics == []


def test_compile_error_strips_absolute_paths(compiler, files, bucket, monkeypatch):
    files.write(bucket, 'sub/a.typ', 'x')
    bucket_dir = (compiler.data_dir / bucket).resolve()
    stderr = f'error: boom\n  ┌─ {bucket_dir}/sub/a.typ:2:4\n\nin {compiler.data_dir}\n'
    monkeypatch.setattr(subprocess, 'run', _fake_run(returncode=1, stderr=stderr)[0])

    with pytest.raises(CompileError) as exc:
        compiler.compile_svg(bucket, 'sub/a.typ')

    assert str(bucket_dir) not in str(exc.value)
    assert str(compiler.data_dir) not in str(exc.value)
    assert exc.value.diagnostics[0]['file'] == 'sub/a.typ'
    assert exc.value.diagnostics[0]['line'] == 2


def test_compile_pdf_error_has_diagnostics(compiler, files, bucket, monkeypatch):
    files.write(bucket, 'a.typ', 'x')
    monkeypatch.setattr(subprocess, 'run', _fake_run(returncode=1, stderr=TYPST_STDERR)[0])
    with pytest.raises(CompileError) as exc:
        compiler.compile_pdf(bucket, 'a.typ')
    assert [d['severity'] for d in exc.value.diagnostics] == ['error', 'warning']


# ── real typst ──

@needs_typst
@pytest.mark.typst
def test_real_compile_svg(compiler, files, bucket):
    files.write(bucket, 'a.typ', '= Hello\n#pagebreak()\nWorld')
    pages = compiler.compile_svg(bucket, 'a.typ')
    assert len(pages) == 2
    assert all(p.lstrip().startswith('<svg') for p in pages)


@needs_typst
@pytest.mark.typst
def test_real_compile_pdf(compiler, files, bucket):
    files.write(bucket, 'a.typ', 'Hello')
    pdf = compiler.compile_pdf(bucket, 'a.typ')
    try:
        assert pdf.read_bytes().startswith(b'%PDF')
    finally:
        pdf.unlink()


@needs_typst
@pytest.mark.typst
def test_real_compile_error(compiler, files, bucket):
    files.write(bucket, 'a.typ', 'ok\n#undefined-function()')
    with pytest.raises(CompileError) as exc:
        compiler.compile_svg(bucket, 'a.typ')
    [diag] = [d for d in exc.value.diagnostics if d['severity'] == 'error']
    assert (diag['file'], diag['line']) == ('a.typ', 2)
    assert str(compiler.data_dir) not in str(exc.value)
