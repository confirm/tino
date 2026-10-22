'''Tests for TemplateService: Universe index, local packages and ``typst init``.'''

import subprocess
from types import SimpleNamespace

import pytest

from tino.models import TemplateInit
from tino.services import template as template_module
from tino.services.template import TemplateService, _group_by_package, _version_key

INDEX = [
    {'name': 'letter', 'version': '0.2.0', 'description': 'new',
     'authors': ['A'], 'template': {'entrypoint': 'letter.typ'}},
    {'name': 'letter', 'version': '0.10.0', 'description': 'newest',
     'authors': ['A'], 'template': {'path': 'template'}},
    {'name': 'Alpha', 'version': '1.0.0', 'template': {'entrypoint': 'x.typ'}},
    {'name': 'library-only', 'version': '1.0.0'},
]


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


@pytest.fixture
def fake_index(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return _FakeResponse(INDEX)

    monkeypatch.setattr(template_module.httpx, 'get', fake_get)
    return calls


# ── helpers ──

@pytest.mark.parametrize('version, expected', [
    ('1.2.3', (1, 2, 3)),
    ('0.10.0', (0, 10, 0)),
    ('1.0.0-rc1', (1, 0, 0)),
])
def test_version_key(version, expected):
    assert _version_key(version) == expected


def test_group_by_package_sorts_versions_and_names():
    grouped = _group_by_package([
        {'name': 'b', 'version': '0.9.0'},
        {'name': 'b', 'version': '0.10.0', 'description': 'latest'},
        {'name': 'A', 'version': '1.0.0', 'namespace': 'local'},
    ])
    assert [(g['namespace'], g['name']) for g in grouped] == [('local', 'A'), ('preview', 'b')]
    assert grouped[1]['versions'] == ['0.10.0', '0.9.0']
    assert grouped[1]['description'] == 'latest'
    assert grouped[1]['entrypoint'] == 'main.typ'


# ── Typst Universe ──

def test_universe_filters_and_groups(fake_index, tmp_path):
    templates = TemplateService(tmp_path).list_typst_universe_templates()
    assert [t['name'] for t in templates] == ['Alpha', 'letter']
    letter = templates[1]
    assert letter['versions'] == ['0.10.0', '0.2.0']
    assert letter['description'] == 'newest'
    assert letter['entrypoint'] == 'main.typ'
    assert templates[0]['authors'] == []
    assert fake_index[0][0] == template_module.INDEX_URL


def test_universe_is_cached(fake_index, tmp_path):
    svc = TemplateService(tmp_path)
    svc.list_typst_universe_templates()
    svc.list_typst_universe_templates()
    assert len(fake_index) == 1


def test_universe_cache_expires(fake_index, tmp_path, monkeypatch):
    svc = TemplateService(tmp_path)
    svc.list_typst_universe_templates()
    real = template_module.time.monotonic()
    monkeypatch.setattr(template_module.time, 'monotonic',
                        lambda: real + template_module.CACHE_TTL + 1)
    svc.list_typst_universe_templates()
    assert len(fake_index) == 2


# ── Local packages ──

def _package(root, namespace, name, version, body):
    path = root / namespace / name / version
    path.mkdir(parents=True)
    (path / 'typst.toml').write_text(body)


def test_local_without_package_dir(tmp_path):
    assert TemplateService(tmp_path).list_local_templates() == []
    assert TemplateService(tmp_path, tmp_path / 'missing').list_local_templates() == []


def test_local_templates(tmp_path):
    pkgs = tmp_path / 'pkgs'
    _package(pkgs, 'local', 'memo', '1.0.0',
             '[package]\ndescription = "Memo"\nauthors = ["X"]\n'
             '[template]\nentrypoint = "memo.typ"\n')
    _package(pkgs, 'local', 'memo', '1.1.0', '[package]\n[template]\n')
    _package(pkgs, 'local', 'lib', '1.0.0', '[package]\nname = "lib"\n')
    _package(pkgs, 'local', 'broken', '1.0.0', 'not = [valid toml')
    (pkgs / 'typst.toml').write_text('[template]\n')  # wrong depth

    templates = TemplateService(tmp_path, pkgs).list_local_templates()
    assert [(t['namespace'], t['name'], t['versions']) for t in templates] == [
        ('local', 'memo', ['1.1.0', '1.0.0']),
    ]


# ── typst init ──

def _fake_typst(created_files, returncode=0, stderr=''):
    '''Return a subprocess.run stand-in that "initializes" a project.'''
    calls = []

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        out = __import__('pathlib').Path(cmd[-1])
        if returncode == 0:
            for rel, content in created_files.items():
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                (out / rel).write_text(content)
        return SimpleNamespace(returncode=returncode, stderr=stderr, stdout='')

    return fake_run, calls


def _body(**kwargs):
    return TemplateInit(name='letter', version='0.1.0', **kwargs)


def test_init_copies_files_into_bucket(files, bucket, data_dir, monkeypatch):
    fake_run, calls = _fake_typst({'main.typ': 'hi', 'assets/logo.svg': '<svg/>'})
    monkeypatch.setattr(subprocess, 'run', fake_run)

    TemplateService(data_dir, data_dir / 'pkgs').init_template(bucket, _body())

    assert files.read(bucket, 'main.typ')['content'] == 'hi'
    assert files.read(bucket, 'assets/logo.svg')['content'] == '<svg/>'
    cmd = calls[0]
    assert cmd[:2] == ['typst', 'init']
    assert '--package-path' in cmd
    assert '@preview/letter:0.1.0' in cmd


def test_init_into_target_dir(files, bucket, data_dir, monkeypatch):
    fake_run, calls = _fake_typst({'main.typ': 'hi'})
    monkeypatch.setattr(subprocess, 'run', fake_run)
    TemplateService(data_dir).init_template(bucket, _body(target_dir='docs/letter'))
    assert files.read(bucket, 'docs/letter/main.typ')['content'] == 'hi'
    assert '--package-path' not in calls[0]


def test_init_missing_bucket(data_dir):
    with pytest.raises(FileNotFoundError):
        TemplateService(data_dir).init_template('ghost', _body())


def test_init_rejects_target_dir_traversal(bucket, data_dir):
    with pytest.raises(RuntimeError):
        TemplateService(data_dir).init_template(bucket, _body(target_dir='../../x'))


def test_init_reports_typst_errors(bucket, data_dir, monkeypatch):
    fake_run, _ = _fake_typst({}, returncode=1, stderr='error: package not found')
    monkeypatch.setattr(subprocess, 'run', fake_run)
    with pytest.raises(RuntimeError, match='package not found'):
        TemplateService(data_dir).init_template(bucket, _body())


def test_init_refuses_to_overwrite(files, bucket, data_dir, monkeypatch):
    files.write(bucket, 'main.typ', 'mine')
    fake_run, _ = _fake_typst({'main.typ': 'theirs', 'other.typ': 'x'})
    monkeypatch.setattr(subprocess, 'run', fake_run)

    with pytest.raises(FileExistsError, match='main.typ'):
        TemplateService(data_dir).init_template(bucket, _body())

    assert files.read(bucket, 'main.typ')['content'] == 'mine'
    assert files.read(bucket, 'other.typ') is None
