import struct
from pathlib import Path

from charla.adaptador_windows.decifra import decrypt_page

_PASTA_FIXTURES = Path(__file__).parent / "fixtures"


def test_par_sintetico_tem_a_marca_estrutural_do_iv():
    """Par sintético (nenhum byte vindo de conta real — construído
    algebricamente com chave conhecida, mesma técnica de
    `_cifrar_arquivo_para_teste` abaixo). Este teste NÃO é o oráculo de
    correção de `decrypt_page` (isso é o teste seguinte) — é evidência
    estrutural de que o par é consistente com a fórmula documentada: os
    últimos 12 bytes mudam entre cifrado e decifrado, porque fazem parte
    do IV da própria página (medido, achado 2/3 da revisão dev-10, 1ª
    rodada). Fixture original era um par real capturado de conta real;
    substituída por construção sintética equivalente antes da abertura
    pública do repositório, para não versionar nenhum byte de conta real
    mesmo sem dado legível nele (medido: a página real tinha 4068 de 4096
    bytes zerados e zero strings legíveis)."""
    cifrada = (_PASTA_FIXTURES / "pagina_sintetica_genericstorage_cifrada.bin").read_bytes()
    decifrada_esperada = (_PASTA_FIXTURES / "pagina_sintetica_genericstorage_decifrada.bin").read_bytes()
    assert len(cifrada) == 4096
    assert len(decifrada_esperada) == 4096
    assert cifrada != decifrada_esperada
    assert cifrada[-12:] != decifrada_esperada[-12:]


def test_decrypt_page_recupera_o_original_com_chave_conhecida():
    """**Este** é o oráculo de correção — achado `bloqueia` 2 da revisão
    dev-10 (2ª rodada): o teste anterior nunca chamava `decrypt_page`.
    Constrói um par (cifrado, decifrado) GENUINAMENTE consistente com a
    fórmula real do IV, com chave conhecida — mesma técnica algébrica de
    `tests/test_decifra.py::_cifrar_arquivo_para_teste` (Task 5), aqui numa
    página só: escolhe a cauda T do cifrado, deriva o keystream desse IV, e
    resolve os últimos 12 bytes do original como `T XOR keystream[-12:]`.
    Não usa a função sob teste para gerar o próprio oráculo."""
    from Crypto.Cipher import AES

    chave = b"\x33" * 32
    numero_pagina = 5
    corpo = (b"conteudo de teste, arbitrario, 4084 bytes de corpo " * 90)[:4084]
    assert len(corpo) == 4084  # 4096 - 12 (os 12 finais sao resolvidos abaixo)

    tail_do_cifrado = b"\xaa" * 12
    iv = struct.pack("<I", numero_pagina) + tail_do_cifrado
    keystream = AES.new(chave, AES.MODE_OFB, iv=iv).encrypt(b"\x00" * 4096)
    tail_do_original = bytes(a ^ b for a, b in zip(tail_do_cifrado, keystream[-12:]))
    original_completo = corpo + tail_do_original
    assert len(original_completo) == 4096

    cifrada = bytes(a ^ b for a, b in zip(original_completo, keystream))
    assert cifrada[-12:] == tail_do_cifrado, "construção inconsistente — não deveria acontecer"

    assert decrypt_page(chave, numero_pagina, cifrada) == original_completo


# --- Task 5: arquivo, WAL e carving ---
import sqlite3

from Crypto.Cipher import AES

from charla.adaptador_windows.decifra import decrypt_db_file, validar_chave_pelo_oraculo


def test_decrypt_db_file_recupera_o_conteudo_original(tmp_path):
    chave = b"\x11" * 32
    original = tmp_path / "original.sqlite"
    con = sqlite3.connect(original)
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO t (v) VALUES ('ola')")
    con.commit()
    con.close()
    corpo_desejado = original.read_bytes()

    cifrado_bytes, decifrado_esperado = _cifrar_arquivo_para_teste(chave, corpo_desejado)
    cifrado = tmp_path / "cifrado.db"
    cifrado.write_bytes(cifrado_bytes)

    destino = tmp_path / "decifrado.db"
    decrypt_db_file(chave, cifrado, destino)

    assert destino.read_bytes() == decifrado_esperado


def _cifrar_arquivo_para_teste(chave: bytes, corpo_desejado: bytes) -> tuple[bytes, bytes]:
    """Constrói um par (cifrado, decifrado) GENUINAMENTE consistente com a
    fórmula real do IV — sem chamar decrypt_page sobre o próprio resultado
    (esse era o defeito do achado 2/3 da revisão dev-10: auto-referência não
    é oráculo). Devolve (cifrado, decifrado_esperado) — os DOIS construídos
    juntos, então comparar a saída de decrypt_db_file contra
    decifrado_esperado é válido por construção, não por reaplicar a função
    sob teste.

    A fórmula real (whatsapp-desktop-windows-uwp-decifra-local.md:226) é
    `iv = pgno + pagina_data[-12:]`, onde `pagina_data` é o que
    `decrypt_page` RECEBE — ou seja, o CIFRADO. Escolhemos os últimos 12
    bytes do CIFRADO (T) livremente, computamos o keystream para esse IV, e
    resolvemos os últimos 12 bytes do ORIGINAL como `T XOR keystream[-12:]`
    — construção puramente algébrica (XOR é a própria inversa). Como o
    corpo de teste é gerado por nós (não uma página SQLite real como a da
    Task 4), forçar esses 12 bytes não corrompe nada que o teste verifique.

    A região 0x10:0x18 da página 1 recebe tratamento à parte: é a que
    `decrypt_db_file` copia do CIFRADO por cima do resultado (o formato
    real a transmite em claro) — para o teste fechar, o CIFRADO precisa ter
    ali o valor VERDADEIRO do original, não o resultado da cifra.
    (`struct` já vem do import no topo do arquivo, Task 4 Step 2 —
    achado bloqueia da revisão dev-10, 3ª rodada: o import local aqui
    virou redundante quando o topo ganhou `import struct`.)"""
    tam_pagina = 4096
    plaintext = bytearray(corpo_desejado)
    if len(plaintext) % tam_pagina:
        plaintext += b"\x00" * (tam_pagina - len(plaintext) % tam_pagina)

    cifrado = bytearray()
    for i in range(0, len(plaintext), tam_pagina):
        numero_pagina = i // tam_pagina + 1
        pagina_original = bytearray(plaintext[i:i + tam_pagina])

        tail_do_cifrado = bytes([0x99]) * 12  # T, escolha arbitraria e fixa -> determinismo
        iv = struct.pack("<I", numero_pagina) + tail_do_cifrado
        keystream = AES.new(chave, AES.MODE_OFB, iv=iv).encrypt(b"\x00" * tam_pagina)
        pagina_original[-12:] = bytes(a ^ b for a, b in zip(tail_do_cifrado, keystream[-12:]))

        pagina_cifrada = bytearray(a ^ b for a, b in zip(bytes(pagina_original), keystream))
        assert bytes(pagina_cifrada[-12:]) == tail_do_cifrado, "construção inconsistente — não deveria acontecer"

        if numero_pagina == 1:
            pagina_cifrada[0x10:0x18] = pagina_original[0x10:0x18]

        plaintext[i:i + tam_pagina] = pagina_original
        cifrado += pagina_cifrada

    return bytes(cifrado), bytes(plaintext)


def test_validar_chave_pelo_oraculo_aceita_par_correto():
    client_key = b"\x22" * 20
    nome_pasta = __import__("hashlib").sha1(client_key).hexdigest().upper()
    assert validar_chave_pelo_oraculo(client_key, nome_pasta) is True


def test_validar_chave_pelo_oraculo_recusa_par_errado():
    client_key = b"\x22" * 20
    assert validar_chave_pelo_oraculo(client_key, "0" * 40) is False


# --- Task 15: documenta o que so roda em Windows real ---
import sys

import pytest


@pytest.mark.windows_real
@pytest.mark.skipif(sys.platform != "win32", reason="obter_oduid/obter_segredo_de_sessao exigem clipc.dll/ncrypt.dll do Windows")
def test_obter_oduid_e_obter_segredo_de_sessao_exigem_windows_real():
    """Não executado em CI — documenta que existe, e por que pula, em vez
    de a ausência do teste ser silenciosa."""
    from charla.adaptador_windows.decifra import obter_oduid, obter_segredo_de_sessao
    assert len(obter_oduid()) == 32
    assert len(obter_segredo_de_sessao()) == 32
