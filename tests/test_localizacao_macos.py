"""Testes de charla.adaptador_macos.localizacao."""
from pathlib import Path

import pytest

from charla.adaptador_macos.localizacao import (
    ChatStorageNaoEncontrado,
    localizar_chat_storage,
)


def test_localizar_chat_storage_devolve_caminho_quando_existe(tmp_path, monkeypatch):
    grupo = tmp_path / "Library" / "Group Containers" / "group.net.whatsapp.WhatsApp.shared"
    grupo.mkdir(parents=True)
    banco = grupo / "ChatStorage.sqlite"
    banco.write_bytes(b"")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    resultado = localizar_chat_storage()
    assert resultado == banco


def test_localizar_chat_storage_recusa_nomeada_quando_ausente(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    with pytest.raises(ChatStorageNaoEncontrado, match="WhatsApp Desktop"):
        localizar_chat_storage()
