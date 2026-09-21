"""Extrai o pycryptodome vendorizado (Decisão 3 do plano — dado bruto
dentro do pacote, não importável de dentro do .pyz) para uma pasta real em
disco na primeira execução, e a insere em sys.path antes de importar.

Medido: zipimport não carrega extensão nativa (.pyd/.so) de dentro de um
zip; extrair para disco antes de importar funciona. Cache por hash do zip
vendorizado, para trocar de versão não colidir com uma extração antiga e
para reinstalar a mesma versão não re-extrair à toa."""
import hashlib
import importlib.resources
import sys
import zipfile
from pathlib import Path

_NOME_ARQUIVO_ZIP = "pycryptodome_win_amd64.zip"
_PASTA_CACHE_BASE = Path.home() / ".cache" / "charla" / "_vendor"


def _extrair_e_inserir_em_path(caminho_zip: Path) -> Path:
    """Núcleo do mecanismo — recebe o CAMINHO REAL de um zip (não o recurso
    do pacote) e faz a extração idempotente + ajuste de sys.path. Separado
    de `garantir_pycryptodome_disponivel` para ser testável sem depender de
    `importlib.resources` nem do zip vendorizado real (ver
    tests/test_pycryptodome_carregador.py, que usa um zip de exemplo)."""
    dados_zip = caminho_zip.read_bytes()
    hash_zip = hashlib.sha256(dados_zip).hexdigest()[:16]
    pasta_extraida = _PASTA_CACHE_BASE / hash_zip

    marcador = pasta_extraida / "Crypto" / "__init__.py"
    if not marcador.exists():
        pasta_extraida.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(caminho_zip) as zf:
            zf.extractall(pasta_extraida)

    caminho_str = str(pasta_extraida)
    if caminho_str not in sys.path:
        sys.path.insert(0, caminho_str)
    return pasta_extraida


def garantir_pycryptodome_disponivel() -> None:
    """Chamado uma vez, antes do primeiro `from Crypto... import ...` real
    (ver decifra.py). Resolve o recurso do pacote para um caminho real em
    disco (`importlib.resources.as_file` — funciona rodando da fonte e de
    dentro de um `.pyz`) e delega em `_extrair_e_inserir_em_path`."""
    recurso = importlib.resources.files("charla._vendor").joinpath(_NOME_ARQUIVO_ZIP)
    with importlib.resources.as_file(recurso) as caminho_zip_real:
        _extrair_e_inserir_em_path(caminho_zip_real)
