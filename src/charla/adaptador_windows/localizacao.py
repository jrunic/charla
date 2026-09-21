"""Localiza a instalação do WhatsApp Desktop no Windows e detecta a
arquitetura — só UWP é suportada (critério 4 da spec: recusa nomeada para
as demais, nunca tenta a cadeia errada em silêncio)."""
import os
from pathlib import Path

NOME_PACOTE_UWP = "5319275A.WhatsAppDesktop_cv1g1gvanyjgm"


class ArquiteturaNaoSuportada(Exception):
    """Levantada quando o WhatsApp Desktop instalado não é a arquitetura
    UWP — única suportada nesta versão (fora de escopo: WebView2 standalone
    e legada, ver 'Fora de Escopo' da spec)."""


def localizar_pasta_local_state(raiz_packages: Path | None = None) -> Path:
    if raiz_packages is None:
        # %LOCALAPPDATA%, não Path.home()/"AppData"/"Local" -- é o que a
        # medição nomeia (whatsapp-desktop-windows-medicao-plano0-charla.md)
        # e o que sobrevive a redirecionamento de pasta (perfil corporativo,
        # OneDrive Known Folder Move). Achado ajusta da revisão dev-10
        # (2ª rodada, NÃO RESOLVIDO na 1ª): Path.home() presumia o layout.
        local_appdata = os.environ.get("LOCALAPPDATA")
        raiz_packages = Path(local_appdata) / "Packages" if local_appdata \
            else Path.home() / "AppData" / "Local" / "Packages"
    pasta = raiz_packages / NOME_PACOTE_UWP / "LocalState"
    if not pasta.is_dir():
        raise ArquiteturaNaoSuportada(
            "WhatsApp Desktop UWP não encontrado em "
            f"{raiz_packages / NOME_PACOTE_UWP}. O charla só suporta a "
            "arquitetura UWP (Microsoft Store) nesta versão — WebView2 "
            "standalone e instalações legadas não foram medidas."
        )
    return pasta


def localizar_pasta_de_sessao(pasta_local_state: Path, nome_da_pasta: str) -> Path:
    """A pasta EXISTIR já é o oráculo de validação da chave (achado 6/12 da
    revisão dev-10): `nome_da_pasta` vem de `SHA1(client_key)`, então achar
    a pasta só acontece quando a chave carveada é a correta. `RuntimeError`,
    não `FileNotFoundError` — main() só captura RuntimeError, e este é um
    ponto real de chamada agora (achado ajusta da revisão dev-10, 2ª
    rodada: esta função nascia e nunca era chamada; decifrar_bases_da_sessao
    duplicava a checagem inline)."""
    pasta = pasta_local_state / "sessions" / nome_da_pasta
    if not pasta.is_dir():
        raise RuntimeError(
            f"A pasta de sessão derivada de SHA1(client_key) ({nome_da_pasta}) "
            f"não existe em {pasta_local_state / 'sessions'} — a chave "
            "carveada não bate com nenhuma sessão real. A cadeia pode ter "
            "quebrado numa atualização do WhatsApp."
        )
    return pasta
