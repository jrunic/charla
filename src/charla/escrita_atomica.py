"""Escrita do destino que `anexo --destino` recebe — sempre atômica
(tudo ou nada, nunca arquivo truncado) e sempre validada ANTES de
qualquer trabalho caro (conexão CDP, download, decifra, cópia). Critério
5 da spec `20260922-1029-spec-charla-anexo-windows.md`."""
import os
import shutil
import tempfile
from pathlib import Path


def validar_destino(destino: Path) -> None:
    """Levanta ValueError com causa nomeada se `destino` não puder
    receber um arquivo. Barata de propósito — chamada antes de abrir
    qualquer conexão CDP ou baixar qualquer byte.

    Achado real de execução: checar `destino.is_dir()` ANTES da pasta
    pai levanta `PermissionError` crua quando a pasta pai não tem
    permissão de leitura/execução — `stat()` em qualquer caminho dentro
    dela falha antes mesmo de chegar na checagem de diretório. A pasta
    pai se confere primeiro; `is_dir()` só roda depois de saber que dá
    para ler ali."""
    pasta_pai = destino.parent
    if not pasta_pai.exists():
        raise ValueError(f"pasta {pasta_pai} não existe")
    if not os.access(pasta_pai, os.W_OK):
        raise ValueError(f"sem permissão de escrita em {pasta_pai}")
    if destino.is_dir():
        raise ValueError(f"destino {destino} é um diretório, não um arquivo")


def escrever_bytes(destino: Path, dados: bytes) -> None:
    """Escreve em arquivo temporário no MESMO diretório do destino e
    substitui por cima só depois de confirmar os bytes completos —
    nunca deixa arquivo truncado se algo falhar no meio."""
    validar_destino(destino)
    fd, tmp_nome = tempfile.mkstemp(dir=str(destino.parent), prefix=".charla-tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
        os.replace(tmp_nome, destino)
    except BaseException:
        Path(tmp_nome).unlink(missing_ok=True)
        raise


def copiar(origem: Path, destino: Path) -> None:
    """Cópia atômica de um arquivo já existente — mesmo mecanismo de
    `escrever_bytes`, sem carregar o arquivo inteiro em memória de uma
    vez (usa `shutil.copyfile`, que copia em blocos)."""
    validar_destino(destino)
    fd, tmp_nome = tempfile.mkstemp(dir=str(destino.parent), prefix=".charla-tmp-")
    os.close(fd)
    try:
        shutil.copyfile(origem, tmp_nome)
        os.replace(tmp_nome, destino)
    except BaseException:
        Path(tmp_nome).unlink(missing_ok=True)
        raise
