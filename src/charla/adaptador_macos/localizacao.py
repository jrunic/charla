"""Localiza o ChatStorage.sqlite do WhatsApp Desktop nativo no macOS."""
from pathlib import Path

_CAMINHO_RELATIVO_GROUP_CONTAINER = (
    "Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite"
)


class ChatStorageNaoEncontrado(RuntimeError):
    pass


def localizar_chat_storage() -> Path:
    caminho = Path.home() / _CAMINHO_RELATIVO_GROUP_CONTAINER
    if not caminho.exists():
        raise ChatStorageNaoEncontrado(
            "ChatStorage.sqlite não encontrado em "
            f"{caminho} — o WhatsApp Desktop (App Store) está instalado e "
            "logado nesta conta?"
        )
    return caminho
