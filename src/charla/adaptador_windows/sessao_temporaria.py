"""Ciclo de vida do diretório de trabalho com os bancos decifrados.

Critério de sucesso 5 da spec: nenhum banco decifrado sobrevive no disco
depois que o comando termina — mesmo se o comando falhar no meio. Context
manager garante isso via try/finally, não como responsabilidade de quem
chama."""
import contextlib
import shutil
import sys
import tempfile
from pathlib import Path


@contextlib.contextmanager
def diretorio_de_trabalho():
    caminho = Path(tempfile.mkdtemp(prefix="charla-"))
    try:
        yield caminho
    finally:
        # ignore_errors=True de propósito: uma falha AQUI não pode mascarar
        # a exceção original que estava se propagando pelo `yield` (ex.:
        # decifrar_bases_da_sessao falhou -- é essa causa que main() precisa
        # ver, não um erro de remoção). Mas silêncio total era o hazard —
        # achado ajusta da revisão dev-10 (2ª rodada, NÃO RESOLVIDO na 1ª):
        # verificar DEPOIS e avisar, sem levantar.
        shutil.rmtree(caminho, ignore_errors=True)
        if caminho.exists():
            print(
                f"AVISO: não consegui remover {caminho} — bancos decifrados "
                "podem ter sobrevivido no disco (handle aberto, permissão). "
                "Apague manualmente.",
                file=sys.stderr,
            )
