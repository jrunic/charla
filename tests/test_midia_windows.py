import base64
import hashlib
import hmac
import sys
from unittest.mock import patch

import pytest
from Crypto.Cipher import AES

from charla.adaptador_windows.midia import (
    ConexaoComWhatsAppIndisponivel,
    DecifraDeMidiaFalhou,
    _hkdf_expand,
    baixar_e_decifrar,
    resolver_metadado_midia,
)


def test_hkdf_expand_bate_com_vetor_calculado_independentemente():
    """Achado `ajusta` da revisão independente do plano: os testes de
    `baixar_e_decifrar` reaproveitam `_hkdf_expand` também para MONTAR o
    fixture (`_cifrar_para_teste` abaixo) — um mutante nela (ordem de
    concatenação, contador, bloco HMAC) produziria chaves erradas mas
    CONSISTENTES nos dois lados, e passaria mesmo assim. Este teste
    fecha esse buraco: o vetor abaixo foi calculado uma vez, fora deste
    código, rodando a fórmula documentada num shell separado (não
    chamando `_hkdf_expand`) — hardcoded aqui como oráculo fixo."""
    media_key = b"\x42" * 32
    esperado = bytes.fromhex(
        "7b9d37e5f485f99391d3f69cc928b6624748267c31603d3dd216b28ee9af63"
        "de21b2ece2e72bd3a8fd08775b67647b08ca3d5d39e8f24e7ad1f186173935a"
        "fedc2c70818c85be977384f9aceb96cf1c425ab7c4bc0bd252a6ea2d0dca2e1"
        "79ad4c273e4f4783020a0a7fadd3228a2f1e"
    )
    assert _hkdf_expand(media_key, 112, b"WhatsApp Image Keys") == esperado


def _cifrar_para_teste(media_key: bytes, plaintext: bytes, info: bytes) -> bytes:
    """Constrói um blob cifrado consistente com o algoritmo real — usa
    `_hkdf_expand` para derivar as chaves (correção dela já garantida
    pelo teste de vetor acima, independente), cifra com AES-CBC e
    calcula o MAC verdadeiro. Não reaplica `baixar_e_decifrar` sobre o
    próprio resultado; constrói o par (cifrado, original) de fora, e o
    AES-CBC/HMAC aqui são chamados independentemente do que
    `baixar_e_decifrar` faz — o que este teste verifica é a decifra
    (AES+HMAC) de ponta a ponta, não a corretude do HKDF (já fechada
    acima)."""
    expandido = _hkdf_expand(media_key, 112, info)
    iv, cipher_key, mac_key = expandido[:16], expandido[16:48], expandido[48:80]
    pad = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad]) * pad
    cifrador = AES.new(cipher_key, AES.MODE_CBC, iv=iv)
    corpo_cifrado = cifrador.encrypt(padded)
    mac = hmac.new(mac_key, iv + corpo_cifrado, hashlib.sha256).digest()[:10]
    return corpo_cifrado + mac


class _RespostaFalsa:
    def __init__(self, dados: bytes):
        self._dados = dados

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._dados


def test_baixar_e_decifrar_recupera_o_original_com_chave_conhecida():
    media_key = b"\x42" * 32
    plaintext = b"conteudo de imagem sintetico, sem dado real, repetido " * 20
    cifrado = _cifrar_para_teste(media_key, plaintext, b"WhatsApp Image Keys")

    with patch("charla.adaptador_windows.midia.urllib.request.urlopen", return_value=_RespostaFalsa(cifrado)):
        resultado = baixar_e_decifrar("/caminho/qualquer", base64.b64encode(media_key).decode(), "image/jpeg")

    assert resultado == plaintext


def test_baixar_e_decifrar_recusa_quando_mac_nao_bate():
    media_key = b"\x42" * 32
    plaintext = b"conteudo"
    cifrado = bytearray(_cifrar_para_teste(media_key, plaintext, b"WhatsApp Image Keys"))
    cifrado[-1] ^= 0xFF  # corrompe o ultimo byte do MAC

    with patch("charla.adaptador_windows.midia.urllib.request.urlopen", return_value=_RespostaFalsa(bytes(cifrado))), \
         pytest.raises(DecifraDeMidiaFalhou, match="MAC"):
        baixar_e_decifrar("/caminho/qualquer", base64.b64encode(media_key).decode(), "image/jpeg")


def test_resolver_metadado_midia_porta_fechada_levanta_conexao_indisponivel():
    with patch("charla.adaptador_windows.midia.porta_de_debug_esta_aberta", return_value=False), \
         pytest.raises(ConexaoComWhatsAppIndisponivel):
        resolver_metadado_midia("123")


def test_resolver_metadado_midia_mensagem_nao_encontrada_devolve_none():
    cliente_falso = type("C", (), {"avaliar": lambda self, expr: None, "fechar": lambda self: None})()
    with patch("charla.adaptador_windows.midia.porta_de_debug_esta_aberta", return_value=True), \
         patch("charla.adaptador_windows.midia._conectar_ao_whatsapp", return_value=cliente_falso):
        assert resolver_metadado_midia("999") is None


def test_resolver_metadado_midia_sem_conexao_levanta_conexao_indisponivel():
    with patch("charla.adaptador_windows.midia.porta_de_debug_esta_aberta", return_value=True), \
         patch("charla.adaptador_windows.midia._conectar_ao_whatsapp", return_value=None), \
         pytest.raises(ConexaoComWhatsAppIndisponivel):
        resolver_metadado_midia("123")


@pytest.mark.windows_real
@pytest.mark.skipif(sys.platform != "win32", reason="exige WhatsApp Desktop real, aberto, com porta de debug habilitada")
def test_resolve_e_decifra_uma_midia_real_do_whatsapp_aberto():
    """Não executado em CI — documenta que existe, e por que pula, em
    vez de a ausência do teste ser silenciosa (mesmo padrão de
    test_obter_oduid_e_obter_segredo_de_sessao_exigem_windows_real em
    test_decifra.py). Precisa de uma mensagem de mídia real já carregada
    em memória pelo WhatsApp Web -- não hardcoda id nenhum, varre e usa
    a primeira que achar."""
    from charla.adaptador_windows.autor_cdp import _conectar_ao_whatsapp, porta_de_debug_esta_aberta

    assert porta_de_debug_esta_aberta(), "porta de debug fechada -- rode habilitar-autor-windows primeiro"
    cliente = _conectar_ao_whatsapp(9222)
    assert cliente is not None
    try:
        primeira_midia = cliente.avaliar("""
        JSON.stringify((() => {
          const { Msg } = window.require('WAWebCollections');
          const todos = Msg.getModelsArray ? Msg.getModelsArray() : [];
          for (const m of todos) {
            const a = m.attributes;
            if (a.directPath && a.mediaKey) return String(a.rowId);
          }
          return null;
        })())
        """)
    finally:
        cliente.fechar()
    assert primeira_midia is not None, "nenhuma mensagem de mídia carregada em memória -- abra uma conversa com mídia no WhatsApp primeiro"

    metadado = resolver_metadado_midia(primeira_midia)
    assert metadado is not None
    dados = baixar_e_decifrar(metadado["directPath"], metadado["mediaKey"], metadado["mimetype"])
    assert len(dados) > 0
    # não imprime nem persiste os bytes -- só confirma que a decifra
    # (com verificação de MAC embutida em baixar_e_decifrar) teve sucesso
