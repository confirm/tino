'''Tests for DOCX export: Typst's HTML export converted to DOCX by pandoc.

The ``typst``/``pandoc``-marked tests run the real CLIs and are skipped when
either is missing.
'''

import io
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tino import dependencies
from tino.services import compiler as compiler_module
from tino.services.compiler import CompileError, CompilerService, PandocMissing

from .conftest import NOBODY, VIEWER

needs_tools = pytest.mark.skipif(
    shutil.which('typst') is None or shutil.which('pandoc') is None,
    reason='typst and/or pandoc CLI not installed',
)


class FakeTools:  # pylint: disable=too-few-public-methods
    '''subprocess.run stand-in for both ``typst`` and ``pandoc``.'''

    def __init__(self):
        self.calls = []
        self.typst = SimpleNamespace(returncode=0, stderr='')
        self.pandoc = SimpleNamespace(returncode=0, stderr='')

    def __call__(self, cmd, **_kwargs):
        self.calls.append(cmd)
        if cmd[0] == 'typst':
            if self.typst.returncode == 0:
                Path(cmd[-1]).write_text('<html><body><h1>Hi</h1></body></html>')
            return SimpleNamespace(returncode=self.typst.returncode,
                                   stderr=self.typst.stderr, stdout='')
        if self.pandoc.returncode == 0:
            Path(cmd[cmd.index('--output') + 1]).write_bytes(b'PK-fake-docx')
        return SimpleNamespace(returncode=self.pandoc.returncode,
                               stderr=self.pandoc.stderr, stdout='')

    def cmd(self, tool):
        return next(c for c in self.calls if c[0] == tool)

    def ran(self, tool):
        return any(c[0] == tool for c in self.calls)


@pytest.fixture
def tools(monkeypatch):
    '''Fake typst/pandoc, with pandoc reported as installed.'''
    fake = FakeTools()
    monkeypatch.setattr(subprocess, 'run', fake)
    monkeypatch.setattr(compiler_module.shutil, 'which',
                        lambda name: f'/usr/bin/{name}' if name == 'pandoc' else None)
    return fake


@pytest.fixture
def no_pandoc(monkeypatch):
    monkeypatch.setattr(compiler_module.shutil, 'which', lambda name: None)


@pytest.fixture
def compiler(data_dir):
    return CompilerService(data_dir)


@pytest.fixture
def doc(files, bucket):
    files.write(bucket, 'sub/doc.typ', '= Hi')
    return 'sub/doc.typ'


# ── CompilerService ──

def test_pandoc_available(monkeypatch):
    monkeypatch.setattr(compiler_module.shutil, 'which', lambda name: '/usr/bin/pandoc')
    assert CompilerService.pandoc_available() is True
    monkeypatch.setattr(compiler_module.shutil, 'which', lambda name: None)
    assert CompilerService.pandoc_available() is False


def test_compile_docx_pipeline(compiler, bucket, doc, tools):
    output = compiler.compile_docx(bucket, doc)
    try:
        assert output.suffix == '.docx'
        assert output.read_bytes() == b'PK-fake-docx'
    finally:
        output.unlink()

    typst = tools.cmd('typst')
    assert typst[typst.index('--format') + 1] == 'html'
    assert typst[typst.index('--features') + 1] == 'html'

    pandoc = tools.cmd('pandoc')
    assert '--sandbox' in pandoc
    assert pandoc[pandoc.index('--from') + 1] == 'html'
    assert pandoc[pandoc.index('--to') + 1] == 'docx'
    assert pandoc[-1] == typst[-1]                      # converts typst's HTML output
    assert '--reference-doc' not in pandoc
    assert not Path(typst[-1]).exists()                 # temp HTML cleaned up


def _reference(pandoc_cmd):
    return Path(pandoc_cmd[pandoc_cmd.index('--reference-doc') + 1])


def test_reference_doc_next_to_source_wins(compiler, files, bucket, doc, tools):
    files.upload(bucket, 'reference.docx', b'root')
    files.upload(bucket, 'sub/reference.docx', b'local')
    compiler.compile_docx(bucket, doc).unlink()
    assert _reference(tools.cmd('pandoc')).read_bytes() == b'local'


def test_reference_doc_falls_back_to_bucket_root(compiler, files, bucket, doc, tools):
    files.upload(bucket, 'reference.docx', b'root')
    compiler.compile_docx(bucket, doc).unlink()
    assert _reference(tools.cmd('pandoc')).read_bytes() == b'root'


def test_reference_doc_symlink_outside_bucket_ignored(compiler, bucket, doc, data_dir, tools):
    (data_dir / 'secret.docx').write_bytes(b'secret')
    (data_dir / bucket / 'reference.docx').symlink_to(data_dir / 'secret.docx')
    compiler.compile_docx(bucket, doc).unlink()
    assert '--reference-doc' not in tools.cmd('pandoc')


def test_typst_failure_raises_compile_error(compiler, bucket, doc, tools):
    tools.typst.returncode, tools.typst.stderr = 1, 'error: boom\n  ┌─ sub/doc.typ:1:1'
    with pytest.raises(CompileError) as exc:
        compiler.compile_docx(bucket, doc)
    assert exc.value.diagnostics[0]['line'] == 1
    assert not tools.ran('pandoc')


def test_pandoc_failure_raises_and_cleans_up(compiler, bucket, doc, data_dir, tools):
    bucket_dir = (data_dir / bucket).resolve()
    tools.pandoc.returncode, tools.pandoc.stderr = 1, f'pandoc: cannot read {bucket_dir}/x'
    with pytest.raises(RuntimeError, match='cannot read x') as exc:
        compiler.compile_docx(bucket, doc)
    assert not isinstance(exc.value, CompileError)
    pandoc = tools.cmd('pandoc')
    assert not Path(pandoc[pandoc.index('--output') + 1]).exists()


def test_pandoc_missing(compiler, bucket, doc, no_pandoc, monkeypatch):  # pylint: disable=unused-argument
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('nothing should run'))
    with pytest.raises(PandocMissing):
        compiler.compile_docx(bucket, doc)


def test_missing_source(compiler, bucket, tools):  # pylint: disable=unused-argument
    with pytest.raises(FileNotFoundError):
        compiler.compile_docx(bucket, 'ghost.typ')


# ── HTTP ──

URL = '/api/buckets/proj/compile/docx/sub/doc.typ'


@pytest.fixture
def http_doc(acl_bucket):  # pylint: disable=unused-argument
    dependencies.get_file_service().write('proj', 'sub/doc.typ', '= Hi')


def test_http_docx(login, http_doc, tools):  # pylint: disable=unused-argument
    resp = login(VIEWER).get(URL)
    assert resp.status_code == 200
    assert resp.content == b'PK-fake-docx'
    assert resp.headers['content-type'] == (
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    assert 'doc.docx' in resp.headers['content-disposition']


def test_http_docx_without_pandoc_is_501(login, http_doc, no_pandoc):  # pylint: disable=unused-argument
    resp = login(VIEWER).get(URL)
    assert resp.status_code == 501
    assert 'pandoc' in resp.json()['detail']


def test_http_docx_typst_error_has_diagnostics(login, http_doc, tools):  # pylint: disable=unused-argument
    tools.typst.returncode, tools.typst.stderr = 1, 'error: unknown variable: x'
    detail = login(VIEWER).get(URL).json()['detail']
    assert detail['diagnostics'][0]['message'] == 'unknown variable: x'


def test_http_docx_pandoc_error_is_422(login, http_doc, tools):  # pylint: disable=unused-argument
    tools.pandoc.returncode, tools.pandoc.stderr = 1, 'pandoc: oops'
    resp = login(VIEWER).get(URL)
    assert resp.status_code == 422
    assert resp.json()['detail'] == 'pandoc: oops'


def test_http_docx_missing_and_forbidden(login, http_doc, tools):  # pylint: disable=unused-argument
    assert login(VIEWER).get('/api/buckets/proj/compile/docx/ghost.typ').status_code == 404
    assert login(NOBODY).get(URL).status_code == 403


def test_config_reports_docx_export(client, monkeypatch):
    monkeypatch.setattr(compiler_module.shutil, 'which', lambda name: '/usr/bin/pandoc')
    assert client.get('/api/config').json()['docxExport'] is True
    monkeypatch.setattr(compiler_module.shutil, 'which', lambda name: None)
    assert client.get('/api/config').json()['docxExport'] is False


# ── real typst + pandoc ──

def _docx_text(data: bytes) -> tuple[str, zipfile.ZipFile]:
    archive = zipfile.ZipFile(io.BytesIO(data))
    xml = archive.read('word/document.xml').decode()
    return ' '.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', xml)), archive


REAL_DOC = '''\
#let layout-grid(..args) = context {
  if target() == "html" { table(stroke: none, ..args) } else { grid(..args) }
}

= Vertrag

Dies ist ein *Test*.

#grid(columns: 2, [Dropped A], [Dropped B])

#layout-grid(columns: 2, [John Smith], [ACME])
'''


@needs_tools
@pytest.mark.typst
@pytest.mark.pandoc
def test_real_docx_export(compiler, files, bucket):
    files.write(bucket, 'doc.typ', REAL_DOC)
    output = compiler.compile_docx(bucket, 'doc.typ')
    try:
        text, archive = _docx_text(output.read_bytes())
    finally:
        output.unlink()

    assert 'Vertrag' in text and 'Test' in text
    assert 'John Smith' in text and 'ACME' in text      # target()-aware grid survives
    assert 'Dropped A' not in text                      # plain grids are dropped by Typst
    assert '<w:tbl>' in archive.read('word/document.xml').decode()


@needs_tools
@pytest.mark.typst
@pytest.mark.pandoc
def test_real_docx_uses_reference_doc(compiler, files, bucket):
    reference = subprocess.run(['pandoc', '--print-default-data-file', 'reference.docx'],
                               capture_output=True, check=True).stdout
    files.upload(bucket, 'reference.docx', reference)
    files.write(bucket, 'doc.typ', '= Hello')
    output = compiler.compile_docx(bucket, 'doc.typ')
    try:
        assert 'Hello' in _docx_text(output.read_bytes())[0]
    finally:
        output.unlink()


@needs_tools
@pytest.mark.typst
@pytest.mark.pandoc
def test_real_docx_sandbox_blocks_local_files(compiler, files, bucket, data_dir):
    secret = data_dir / 'secret.png'
    secret.write_bytes(b'\x89PNG\r\n\x1a\nsecret')
    files.write(bucket, 'doc.typ',
                f'= Hi\n#html.elem("img", attrs: (src: "file://{secret}"))\n')
    output = compiler.compile_docx(bucket, 'doc.typ')
    try:
        _, archive = _docx_text(output.read_bytes())
    finally:
        output.unlink()
    assert not [n for n in archive.namelist() if n.startswith('word/media')]
