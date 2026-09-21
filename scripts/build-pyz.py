"""Monta dist/charla.pyz a partir de src/charla/. Uso:
    python3 scripts/build-pyz.py [--out DIR]

Mesmo mecanismo (zipapp da stdlib) usado em outro projeto Python desta
prática de desenvolvimento. Achado real (sessão de documentação, medindo antes de
escrever): zipapp.create_archive(main="charla.cli:main") gera um
__main__.py que faz só `charla.cli.main()`, sem `raise SystemExit(...)` —
descarta o código de saída, e o .pyz SEMPRE sai com exit=0, mesmo em erro
(reproduzido contra o .pyz real). montar_stage() escreve o próprio
__main__.py na raiz do stage (idêntico a src/charla/__main__.py), e por
isso este script NÃO passa main= para create_archive — a doc da stdlib diz
que main= e __main__.py próprio são mutuamente exclusivos."""
import argparse
import shutil
import sys
import zipapp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pyz_lib import REPO, montar_stage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "dist"))
    ns = ap.parse_args()

    pasta_saida = Path(ns.out)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    stage = montar_stage(pasta_saida)
    pyz = pasta_saida / "charla.pyz"
    zipapp.create_archive(
        stage,
        target=pyz,
        interpreter="/usr/bin/env python3",
    )

    shutil.rmtree(stage)

    print(f"pyz: {pyz}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
