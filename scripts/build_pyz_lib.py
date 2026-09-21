"""Lógica de montagem do stage para o charla.pyz — separada de
build-pyz.py (nome com hífen, não importável) para ser testável sem gerar
o .pyz completo a cada execução da suíte."""
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACOTE_FONTE = REPO / "src" / "charla"


_MAIN_PY = "from charla.cli import main\nraise SystemExit(main())\n"


def montar_stage(pasta_saida: Path) -> Path:
    """Copia src/charla/ inteiro para <pasta_saida>/_stage/charla/ e
    devolve o caminho do stage (a pasta que contém charla/, pronta para
    zipapp.create_archive). Ignora só __pycache__/*.pyc -- NAO exclui
    *.pyd/*.so/*.dll, porque hoje nao existe nenhum
    binario solto em src/charla/ (o pycryptodome vendorizado vive dentro
    de um .zip, que esses padroes nunca casariam de qualquer forma --
    Decisao de Implementacao 1 do Plano 3, corrigida na revisao dev-10).

    Escreve TAMBÉM um __main__.py na raiz do stage, idêntico a
    src/charla/__main__.py -- achado real: zipapp.create_archive(main=
    "charla.cli:main") gera um __main__.py que só chama charla.cli.main()
    SEM SystemExit, descartando o código de saída. Escrever o nosso
    próprio __main__.py (com `raise SystemExit(main())`) e NÃO passar
    main= para create_archive é o que preserva o código de saída real no
    .pyz -- mesmo contrato que rodar `python -m charla` da fonte já tem."""
    stage = pasta_saida / "_stage"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(
        PACOTE_FONTE,
        stage / "charla",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (stage / "__main__.py").write_text(_MAIN_PY)
    return stage
