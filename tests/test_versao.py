import re
from pathlib import Path

import pytest

from charla._version import __version__

REPO = Path(__file__).resolve().parent.parent


def test_versao_unica_pyproject_e_pacote():
    """Mesmo guard do koine — fonte de verdade é `_version.py`;
    `pyproject.toml` tem que refletir o mesmo número, senão o CI publica
    release com tag e conteúdo divergentes em silêncio (já aconteceu uma
    vez no malote — motivo do guard existir)."""
    src = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"$', src, re.MULTILINE)
    assert m, "pyproject.toml sem campo version"
    assert m.group(1) == __version__


def test_changelog_tem_secao_da_versao_de_release():
    """Espelho local do gate do workflow (awk sobre `## [<versao>]`) —
    release oficial sem entrada no CHANGELOG falha aqui antes de falhar
    no CI."""
    if "-" in __version__:
        pytest.skip("versão de desenvolvimento — gate só vale para release")
    log = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in log
