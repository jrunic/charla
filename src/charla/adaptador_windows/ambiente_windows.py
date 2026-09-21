"""Grava/lê WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS em HKCU\\Environment,
preservando o que já estiver lá — mesmo padrão usado em outro projeto
Python desta mesma prática de desenvolvimento para editar variável de
ambiente do Windows, porque `setx` trunca a variável em 1024 caracteres
EM SILÊNCIO e grava sempre REG_SZ, destruindo o tipo original da entrada.

Duas camadas: a LÓGICA (composição de string) é pura e roda em qualquer
SO; o ACESSO AO REGISTRO é costurado, porque `winreg` não existe fora do
Windows e o CI é POSIX-only."""
import re

_PREFIXO_PORTA = "--remote-debugging-port="

ADICIONADO = "adicionado"
JA_ESTAVA = "ja_estava"
SUBSTITUIDO = "substituido"
FALHOU = "falhou"

REG_EXPAND_SZ = 2  # winreg.REG_EXPAND_SZ, sem importar winreg fora do Windows
_CHAVE = "Environment"
_VALOR = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"


_PADRAO_PORTA = re.compile(re.escape(_PREFIXO_PORTA) + r"\S+")


def compor_argumentos(valor: str, porta: int) -> tuple[str | None, str]:
    """O valor novo da variável, ou (None, status) quando não há nada a
    escrever. Só a NOSSA entrada (`--remote-debugging-port=`) é tocada —
    qualquer outro argumento do usuário fica byte a byte, mesmo princípio
    usado para editar entradas de PATH sem destruir o resto do valor.

    **Correção da revisão dev-10 (3ª rodada):** a versão anterior fazia
    `valor.split()` / `" ".join(partes)` — colapsa qualquer sequência de
    espaços e RE-TOKENIZA argumento entre aspas (`--user-data-dir="C:\\Program
    Files\\x"` virava três tokens). Substituição via regex, tocando só o
    span do NOSSO token — tudo em volta (espaçamento, aspas, ordem) fica
    intocado, porque não há split/join nenhum."""
    nosso_token = f"{_PREFIXO_PORTA}{porta}"
    if _PADRAO_PORTA.search(valor):
        substituido = _PADRAO_PORTA.sub(nosso_token, valor, count=1)
        if substituido == valor:
            return None, JA_ESTAVA
        return substituido, SUBSTITUIDO
    if not valor:
        return nosso_token, ADICIONADO
    return f"{valor} {nosso_token}", ADICIONADO


class RegistroDeAmbienteUsuario:
    """Acesso a HKCU\\Environment — só existe no Windows; `import winreg`
    dentro dos métodos, para o módulo continuar importável em CI POSIX-only."""

    def ler(self) -> tuple[str | None, int | None]:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE) as k:
                valor, tipo = winreg.QueryValueEx(k, _VALOR)
                return valor, tipo
        except FileNotFoundError:
            return None, None

    def gravar(self, valor: str, tipo: int) -> None:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CHAVE, 0,
                             winreg.KEY_READ | winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, _VALOR, 0, tipo, valor)


def _user32():
    import ctypes
    return ctypes.windll.user32


def broadcast() -> bool:
    """WM_SETTINGCHANGE via SendMessageTimeoutW — best-effort, com prazo,
    para processo novo enxergar a variável sem precisar de logoff — nunca o
    `SendMessage` bloqueante, que penduraria o comando numa janela que não
    responde."""
    WM_SETTINGCHANGE = 0x001A
    HWND_BROADCAST = 0xFFFF
    SMTO_ABORTIFHUNG = 0x0002
    try:
        _user32().SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                                       "Environment", SMTO_ABORTIFHUNG, 2000, None)
        return True
    except (OSError, AttributeError):
        return False


def garantir_porta_de_debug(porta: int, *, reg=None, notificar=None) -> str:
    """Garante que WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS tem a porta de
    debug certa, preservando qualquer outro argumento que já estivesse lá.
    Nunca levanta — registro negado por política vira FALHOU, e quem chama
    (habilitar_debug_e_reiniciar) segue com a orientação manual."""
    reg = reg if reg is not None else RegistroDeAmbienteUsuario()
    notificar = notificar if notificar is not None else broadcast

    try:
        valor, tipo = reg.ler()
    except (OSError, ImportError):
        return FALHOU

    novo, status = compor_argumentos(valor or "", porta)
    if novo is None:
        return status

    try:
        reg.gravar(novo, tipo if tipo is not None else REG_EXPAND_SZ)
    except (OSError, ImportError):
        return FALHOU

    notificar()
    return status
