"""Testes de scripts.build_pyz_lib."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_pyz_lib import montar_stage


def test_montar_stage_copia_pacote_charla_inteiro(tmp_path):
    stage = montar_stage(tmp_path)

    assert (stage / "charla" / "cli.py").exists()
    assert (stage / "charla" / "modelo.py").exists()
    assert (stage / "charla" / "adaptador_windows" / "decifra.py").exists()
    assert (stage / "charla" / "adaptador_macos" / "leitura.py").exists()


def test_montar_stage_preserva_o_zip_vendorizado(tmp_path):
    stage = montar_stage(tmp_path)

    zip_vendorizado = stage / "charla" / "_vendor" / "pycryptodome_win_amd64.zip"
    assert zip_vendorizado.exists()
    assert zip_vendorizado.stat().st_size > 0


def test_montar_stage_nao_copia_pycache(tmp_path):
    stage = montar_stage(tmp_path)

    encontrados = list(stage.rglob("__pycache__"))
    assert encontrados == []


def test_montar_stage_escreve_main_com_systemexit(tmp_path):
    """Achado real (sessão de documentação, medindo antes de escrever):
    zipapp.create_archive(main="charla.cli:main") gera um __main__.py que
    faz só `charla.cli.main()`, SEM `raise SystemExit(...)` -- o valor de
    retorno de main() (o código de saída inteiro) é descartado, e o
    processo do .pyz SEMPRE sai com código 0, mesmo em erro. Reproduzido
    contra o .pyz real: `charla.pyz anexo <id-inexistente>` imprimia o
    JSON de erro certo no stderr e saía com `exit=0` -- quebra critérios
    4/6/7/13 da spec especificamente no artefato distribuído (rodando `python
    -m charla` da fonte, o exit code sempre esteve certo, porque
    src/charla/__main__.py já faz `raise SystemExit(main())`). Corrigido:
    montar_stage() escreve esse MESMO __main__.py na raiz do stage, e
    build-pyz.py para de passar main= para zipapp.create_archive (a doc
    da stdlib diz que main= e __main__.py próprio são mutuamente
    exclusivos)."""
    stage = montar_stage(tmp_path)

    main_py = stage / "__main__.py"
    assert main_py.exists()
    conteudo = main_py.read_text()
    assert "from charla.cli import main" in conteudo
    assert "raise SystemExit(main())" in conteudo
