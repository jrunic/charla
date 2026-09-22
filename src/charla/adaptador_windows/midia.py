"""Extrai bytes de mídia recebida no WhatsApp Desktop Windows.

Medido em 22/09/2026 contra mensagem real (documento técnico interno do
autor, whatsapp-desktop-windows-medicao-anexo-cdp-charla.md): o Blob
decifrado pelo runtime JS (`downloadMedia()`) não é acessível por
nenhum caminho de objeto testado — o mecanismo que funciona é CDP só
para METADADO (`directPath`/`mediaKey`/`mimetype`, já em `m.attributes`
sem precisar abrir a conversa), e os bytes vêm de download HTTPS direto
+ decifra local pelo protocolo público de mídia do WhatsApp (mesmo
algoritmo que `whatsapp-web.js`/`Baileys` usam — não é engenharia
reversa nossa).

Mesmo guard de vendorização que `decifra.py` já usa: `from Crypto.Cipher
import AES` incondicionalmente quebraria em Windows real fora da ordem
de import atual — hoje funciona só porque `_main_windows` importa
`decifra` (que já extrai o zip vendorizado) antes de qualquer dispatch,
inclusive para `anexo`. Repetir o guard aqui remove essa dependência de
ordem implícita entre módulos."""
import base64
import hashlib
import hmac
import sys
import urllib.request

if sys.platform == "win32":
    from charla._vendor.pycryptodome_carregador import garantir_pycryptodome_disponivel
    garantir_pycryptodome_disponivel()
from Crypto.Cipher import AES

from charla.adaptador_windows.autor_cdp import (
    PORTA_PADRAO,
    ErroDeAvaliacaoJS,
    _conectar_ao_whatsapp,  # uso interno de autor_cdp.py -- decisao explicita de
    # cruzar a fronteira em vez de duplicar a logica de conexao CDP aqui
    porta_de_debug_esta_aberta,
)

_INFO_POR_TIPO = {
    "image": b"WhatsApp Image Keys",
    "video": b"WhatsApp Video Keys",
    "audio": b"WhatsApp Audio Keys",
    "document": b"WhatsApp Document Keys",
}


class ConexaoComWhatsAppIndisponivel(RuntimeError):
    """Porta de debug fechada ou runtime JS não respondeu. Diferente de
    `resolver_autores` (degrade gracioso, dict vazio), `anexo` não tem
    resultado parcial que valha a pena escrever no destino — levanta,
    sempre."""


class DecifraDeMidiaFalhou(RuntimeError):
    """MAC não bateu — chave errada, blob corrompido no download, ou o
    formato do protocolo mudou. Nunca escreve arquivo parcial: quem
    chama só recebe bytes depois desta função retornar com sucesso."""


def montar_expressao_busca_metadado_midia(id_mensagem: str) -> str:
    """Varre TODAS as mensagens carregadas em memória pelo WhatsApp Web,
    de qualquer conversa — medido: dispensa abrir a conversa e dispensa
    `chat_id`, ao contrário do que a spec original presumia (achado do
    Plano 0)."""
    return f"""
    JSON.stringify((() => {{
      const {{ Msg }} = window.require('WAWebCollections');
      const alvo = {int(id_mensagem)};
      const todos = Msg.getModelsArray ? Msg.getModelsArray() : [];
      for (const m of todos) {{
        const a = m.attributes;
        if (a.rowId === alvo) {{
          if (!a.directPath || !a.mediaKey) return null;
          return {{
            directPath: a.directPath,
            mediaKey: a.mediaKey,
            mimetype: a.mimetype || null,
          }};
        }}
      }}
      return null;
    }})())
    """


def resolver_metadado_midia(id_mensagem: str, porta: int = PORTA_PADRAO) -> dict | None:
    """Devolve {directPath, mediaKey, mimetype} ou None (id não bate com
    nenhuma mensagem carregada, ou a mensagem não é mídia). Levanta
    ConexaoComWhatsAppIndisponivel se a conexão em si falhar."""
    if not porta_de_debug_esta_aberta(porta):
        raise ConexaoComWhatsAppIndisponivel(
            "conexão com o WhatsApp em execução não está disponível — "
            "rode 'charla habilitar-autor-windows' uma vez para habilitar."
        )
    cliente = _conectar_ao_whatsapp(porta)
    if cliente is None:
        raise ConexaoComWhatsAppIndisponivel(
            "conexão com o WhatsApp em execução não está disponível — "
            "rode 'charla habilitar-autor-windows' uma vez para habilitar."
        )
    try:
        try:
            return cliente.avaliar(montar_expressao_busca_metadado_midia(id_mensagem))
        except (ErroDeAvaliacaoJS, ValueError) as e:
            raise ConexaoComWhatsAppIndisponivel(str(e)) from e
    finally:
        cliente.fechar()


def _hkdf_expand(media_key: bytes, tamanho: int, info: bytes) -> bytes:
    """HKDF-SHA256, salt de 32 zeros, sem passo de extract separado —
    `media_key` já é o IKM. Algoritmo público do protocolo de mídia do
    WhatsApp, verificado de ponta a ponta contra mensagem real (MAC
    bate, magic bytes corretos, tamanho exato — ver documento técnico)."""
    salt = b"\x00" * 32
    prk = hmac.new(salt, media_key, hashlib.sha256).digest()
    saida = b""
    bloco = b""
    contador = 1
    while len(saida) < tamanho:
        bloco = hmac.new(prk, bloco + info + bytes([contador]), hashlib.sha256).digest()
        saida += bloco
        contador += 1
    return saida[:tamanho]


def baixar_e_decifrar(direct_path: str, media_key_b64: str, mimetype: str) -> bytes:
    """Baixa o blob cifrado (`directPath` funciona como token de
    capacidade — sem autenticação adicional, medido) e decifra pelo
    protocolo público de mídia do WhatsApp. Levanta DecifraDeMidiaFalhou
    se o MAC não bater — nunca devolve bytes não verificados."""
    url = "https://mmg.whatsapp.net" + direct_path
    req = urllib.request.Request(url, headers={"User-Agent": "WhatsApp/2.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        cifrado = resp.read()

    media_key = base64.b64decode(media_key_b64)
    tipo = (mimetype or "").split("/")[0]
    info = _INFO_POR_TIPO.get(tipo, _INFO_POR_TIPO["image"])
    expandido = _hkdf_expand(media_key, 112, info)
    iv, cipher_key, mac_key = expandido[:16], expandido[16:48], expandido[48:80]

    corpo_cifrado, mac_recebido = cifrado[:-10], cifrado[-10:]
    mac_calculado = hmac.new(mac_key, iv + corpo_cifrado, hashlib.sha256).digest()[:10]
    if not hmac.compare_digest(mac_calculado, mac_recebido):
        raise DecifraDeMidiaFalhou(
            "a verificação de integridade (MAC) da mídia baixada falhou — "
            "a chave pode estar errada, o download veio corrompido, ou o "
            "formato do protocolo mudou numa atualização do WhatsApp."
        )

    decifrador = AES.new(cipher_key, AES.MODE_CBC, iv=iv)
    bruto = decifrador.decrypt(corpo_cifrado)
    pad = bruto[-1]
    return bruto[:-pad] if 1 <= pad <= 16 else bruto
