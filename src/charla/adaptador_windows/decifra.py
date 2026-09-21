"""Cadeia de decifra DPAPI-NG do WhatsApp Desktop UWP para Windows.

Provada contra conta real em 19-20/09/2026 — documento técnico interno
do autor, fora deste repositório. Cada função aqui corresponde a um
passo nomeado naquele documento.

AES via pycryptodome (Decisão 3, revista 20/09/2026 e 21/09/2026). No
Windows, vendorizado — a extração/ajuste de sys.path acontece uma vez, no
import deste módulo. Fora do Windows (dev/CI), `pycryptodome` entra como
dependência de `dev` normal (pyproject.toml, Task 1) — o ambiente de
desenvolvimento tem `pip` de verdade, diferente da máquina do mentorado, e
o import é o mesmo `from Crypto.Cipher import AES` nos dois casos, só o
CAMINHO de onde `Crypto` vem que muda.

**Achado `bloqueia` 1 da revisão dev-10 (2ª rodada, 20/09/2026), corrigido
21/09/2026**: a versão anterior chamava `garantir_pycryptodome_disponivel()`
incondicionalmente — o wheel vendorizado é `win_amd64`, então
`from Crypto.Cipher import AES` derrubava a coleta de teste inteira em
macOS/Linux/CI (`OSError: Cannot load native module`), medido. E como o
carregador insere no INÍCIO de `sys.path`, nem instalar `pycryptodome` de
verdade no ambiente de dev resolvia — o vendorizado sombreava."""
import ctypes
import hashlib
import struct
import sys

from charla.adaptador_windows.localizacao import localizar_pasta_de_sessao

if sys.platform == "win32":
    from charla._vendor.pycryptodome_carregador import garantir_pycryptodome_disponivel
    garantir_pycryptodome_disponivel()

from Crypto.Cipher import AES

STATIC_BYTES = bytes.fromhex("23a7f19c11e5bd784235c96f85d24913")
OUID_SALT = bytes.fromhex("6300760031006700310067007600")
PBKDF_ITERATIONS = 10000
MAGIC_SQLITE = b"SQLite format 3\x00"


def obter_oduid() -> bytes:
    """Passo 1: ODUID via clipc.dll — identidade do dispositivo, sem admin."""
    clipc = ctypes.WinDLL("clipc.dll")
    fn = clipc.GetOfflineDeviceUniqueID
    fn.restype = ctypes.c_int32
    fn.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_ubyte),
                   ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                   ctypes.POINTER(ctypes.c_ubyte), ctypes.c_uint32, ctypes.c_uint32]
    salt_buf = (ctypes.c_ubyte * len(OUID_SALT))(*OUID_SALT)
    method = ctypes.c_uint32(0)
    cb = ctypes.c_uint32(32)
    out = (ctypes.c_ubyte * 32)()
    res = fn(len(OUID_SALT), salt_buf, ctypes.byref(method), ctypes.byref(cb), out, 0, 0)
    if res != 0:
        raise RuntimeError(f"GetOfflineDeviceUniqueID falhou: código {res}")
    return bytes(out[:cb.value])


def obter_segredo_de_sessao() -> bytes:
    """Passo 2: segredo protegido por usuário via NCryptProtectSecret, sem admin."""
    ncrypt = ctypes.WinDLL("ncrypt.dll")
    create_desc = ncrypt.NCryptCreateProtectionDescriptor
    create_desc.restype = ctypes.c_int32
    create_desc.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
    protect = ncrypt.NCryptProtectSecret
    protect.restype = ctypes.c_int32
    protect.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_ubyte),
                         ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32)]
    close_desc = ncrypt.NCryptCloseProtectionDescriptor
    local_free = ctypes.windll.kernel32.LocalFree

    h_desc = ctypes.c_void_p()
    if create_desc("LOCAL=user", 0, ctypes.byref(h_desc)) != 0:
        raise RuntimeError("NCryptCreateProtectionDescriptor falhou")
    buf = (ctypes.c_ubyte * len(STATIC_BYTES))(*STATIC_BYTES)
    ptr_out = ctypes.c_void_p()
    size_out = ctypes.c_uint32()
    if protect(h_desc, 0, buf, len(STATIC_BYTES), None, None,
               ctypes.byref(ptr_out), ctypes.byref(size_out)) != 0:
        raise RuntimeError("NCryptProtectSecret falhou")
    protegido = ctypes.string_at(ptr_out, size_out.value)
    local_free(ptr_out)
    close_desc(h_desc)
    return protegido[:32]


def decrypt_page(chave: bytes, numero_da_pagina: int, dado_da_pagina: bytes) -> bytes:
    """AES-256-OFB por página — IV é o número da página (4 bytes, little
    endian) mais os últimos 12 bytes da própria página cifrada. NÃO é
    involução: aplicar duas vezes não recupera o original, porque os
    últimos 12 bytes da saída diferem dos da entrada (fazem parte do IV) —
    ver tests/test_decifra.py e o achado 2/3 da revisão dev-10."""
    iv = struct.pack("<I", numero_da_pagina) + dado_da_pagina[-12:]
    cifrador = AES.new(chave, AES.MODE_OFB, iv=iv)
    return cifrador.decrypt(dado_da_pagina)


def validar_chave_pelo_oraculo(client_key: bytes, nome_da_pasta_de_sessao: str) -> bool:
    """Critério de sucesso 6 da spec: SHA1(client_key) tem que bater com o
    nome real da pasta de sessão. Nunca aceitar uma chave sem essa checagem."""
    return hashlib.sha1(client_key).hexdigest().upper() == nome_da_pasta_de_sessao.upper()


def decrypt_db_file(chave: bytes, caminho_entrada, caminho_saida) -> None:
    """Decifra um banco .db inteiro, página a página, preservando os bytes
    de header que ficam em claro (0x10:0x18 — page size e afins)."""
    from pathlib import Path
    caminho_entrada = Path(caminho_entrada)
    caminho_saida = Path(caminho_saida)
    dados = caminho_entrada.read_bytes()
    tam_pagina = 4096
    header_original = dados[0x10:0x18]
    saida = bytearray()
    for i in range(0, len(dados), tam_pagina):
        pagina = dados[i:i + tam_pagina]
        if len(pagina) < tam_pagina:
            break
        saida += decrypt_page(chave, i // tam_pagina + 1, pagina)
    saida[0x10:0x18] = header_original
    caminho_saida.write_bytes(bytes(saida))


def _atualizar_checksum_wal(dados: bytes, offset: int, tamanho: int, s0: int, s1: int,
                             big_endian: bool) -> tuple[int, int]:
    mascara = 0xFFFFFFFF
    for i in range(offset, offset + tamanho, 8):
        if big_endian:
            x0 = struct.unpack_from(">I", dados, i)[0]
            x1 = struct.unpack_from(">I", dados, i + 4)[0]
        else:
            x0 = struct.unpack_from("<I", dados, i)[0]
            x1 = struct.unpack_from("<I", dados, i + 4)[0]
        s0 = (s0 + x0 + s1) & mascara
        s1 = (s1 + x1 + s0) & mascara
    return s0, s1


def decrypt_db_wal_file(chave: bytes, caminho_entrada, caminho_saida) -> None:
    """Decifra o -wal, recalculando o checksum de cada frame — o SQLite
    rejeita o arquivo se o checksum não bater com o conteúdo decifrado."""
    from pathlib import Path
    caminho_entrada = Path(caminho_entrada)
    caminho_saida = Path(caminho_saida)
    dados = caminho_entrada.read_bytes()
    tam_pagina = 4096
    tam_header = 32
    tam_header_de_pagina = 24

    header_arquivo = bytearray(dados[:tam_header])
    magic = struct.unpack_from(">I", header_arquivo, 0)[0]
    big_endian = magic == 0x377F0683
    s0 = struct.unpack_from(">I", header_arquivo, 24)[0]
    s1 = struct.unpack_from(">I", header_arquivo, 28)[0]

    saida = bytearray()
    saida += header_arquivo
    i = tam_header
    while i + tam_header_de_pagina + tam_pagina <= len(dados):
        header_frame = bytearray(dados[i:i + tam_header_de_pagina])
        pagina = dados[i + tam_header_de_pagina:i + tam_header_de_pagina + tam_pagina]
        indice_pagina = struct.unpack_from(">I", header_frame, 0)[0]
        decifrada = bytearray(decrypt_page(chave, indice_pagina, pagina))
        if indice_pagina == 1:
            decifrada[0x10:0x18] = pagina[0x10:0x18]
        s0, s1 = _atualizar_checksum_wal(bytes(header_frame), 0, 8, s0, s1, big_endian)
        s0, s1 = _atualizar_checksum_wal(bytes(decifrada), 0, len(decifrada), s0, s1, big_endian)
        header_frame[16:20] = struct.pack(">I", s0)
        header_frame[20:24] = struct.pack(">I", s1)
        saida += header_frame
        saida += decifrada
        i += tam_header_de_pagina + tam_pagina
    caminho_saida.write_bytes(bytes(saida))


def carvear_chaves_de_cliente(caminho_wal_decifrado) -> list[bytes]:
    """Carving heurístico da tabela `settings` (session.db-wal decifrado)
    por client_key — não há como ler via SQL porque o WAL sozinho não é um
    banco válido sem o arquivo principal correspondente."""
    from pathlib import Path
    dados = Path(caminho_wal_decifrado).read_bytes()
    tam_pagina = struct.unpack_from(">I", dados, 8)[0]
    offset = 32
    resultados = []
    while offset + 24 + tam_pagina <= len(dados):
        p_ini, p_fim = offset + 24, offset + 24 + tam_pagina
        cursor = p_ini
        while cursor < p_fim - 15:
            tam_header_registro = dados[cursor]
            if 5 <= tam_header_registro <= 9:
                t_conta = dados[cursor + 1]
                t_client_key = dados[cursor + 2]
                t_timestamp = dados[cursor + 4]
                if (t_client_key >= 12 and t_client_key % 2 == 0 and 1 <= t_timestamp <= 6
                        and (t_conta == 0 or t_conta <= 6)):
                    tam_blob = (t_client_key - 12) // 2
                    if 16 <= tam_blob <= 64:
                        tam_col1 = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}.get(t_conta, 0)
                        inicio_dado = cursor + tam_header_registro + tam_col1
                        if inicio_dado + tam_blob <= p_fim:
                            resultados.append(dados[inicio_dado:inicio_dado + tam_blob])
                            cursor += tam_header_registro + tam_col1 + tam_blob - 1
            cursor += 1
        offset += 24 + tam_pagina
    return resultados


def carvear_chaves_de_nativesettings(caminho_wal_decifrado) -> list[tuple[int, bytes]]:
    """Carving heurístico da tabela `settings` de nativeSettings.db-wal
    decifrado — devolve pares (tipo, chave). Tipo 1 = genericStorage.db,
    tipo 2 = contacts.db/abprops.db/contactsState.db/mediaDownloads.db/
    metaconfig.db (medido, ver documento técnico)."""
    from pathlib import Path
    dados = Path(caminho_wal_decifrado).read_bytes()
    tam_pagina = struct.unpack_from(">I", dados, 8)[0]
    offset = 32
    resultados = []
    while offset + 24 + tam_pagina <= len(dados):
        p_ini, p_fim = offset + 24, offset + 24 + tam_pagina
        cursor = p_ini
        while cursor < p_fim - 10:
            tam_header_registro = dados[cursor]
            if tam_header_registro == 3:
                t_chave, t_valor = dados[cursor + 1], dados[cursor + 2]
                chave_valida = (1 <= t_chave <= 6) or t_chave in (8, 9)
                valor_valido = (t_valor == 0) or (t_valor >= 12 and t_valor % 2 == 0)
                if chave_valida and valor_valido:
                    tam_chave = 0
                    if t_chave == 8:
                        valor_da_chave = 0
                    elif t_chave == 9:
                        valor_da_chave = 1
                    else:
                        tam_chave = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}[t_chave]
                        k_ini = cursor + tam_header_registro
                        if k_ini + tam_chave <= p_fim:
                            if tam_chave == 1:
                                valor_da_chave = struct.unpack_from("b", dados, k_ini)[0]
                            elif tam_chave == 2:
                                valor_da_chave = struct.unpack_from(">h", dados, k_ini)[0]
                            elif tam_chave == 4:
                                valor_da_chave = struct.unpack_from(">i", dados, k_ini)[0]
                            else:
                                valor_da_chave = None
                        else:
                            valor_da_chave = None
                    tam_blob, blob = 0, None
                    if t_valor >= 12:
                        tam_blob = (t_valor - 12) // 2
                        v_ini = cursor + tam_header_registro + tam_chave
                        if v_ini + tam_blob <= p_fim and tam_blob > 0:
                            blob = dados[v_ini:v_ini + tam_blob]
                    if isinstance(valor_da_chave, int) and blob is not None:
                        resultados.append((valor_da_chave, blob))
                        cursor += tam_header_registro + tam_chave + tam_blob - 1
            cursor += 1
        offset += 24 + tam_pagina
    return resultados


def decifrar_bases_da_sessao(pasta_local_state, pasta_trabalho):
    """Orquestra a cadeia inteira: sessão → client_key → nativeSettings →
    genericStorage/contacts. Levanta RuntimeError com causa nomeada quando
    o oráculo rejeita a chave (localizar_pasta_de_sessao — a pasta derivada
    de SHA1(client_key) não existir É a rejeição; validar_chave_pelo_oraculo
    fica como utilitário testado para verificação manual, não é chamado
    aqui porque seria tautológico contra um nome que já vem do hash),
    quando o WAL necessário está ausente/curto, ou quando o carving não
    devolve um tipo de chave esperado (critérios 6, 7 e 13 da spec — nunca
    stack trace crua).

    Decifra `.db` E `.db-wal` das QUATRO bases (session, nativeSettings,
    genericStorage, contacts) — achado 9 da revisão dev-10, confirmado por
    medição: com o app aberto, genericStorage.db-wal chega a 24% do
    tamanho do .db principal, com escrita minutos antes. Pular o WAL não é
    caso de borda; é ler retrato velho sempre que o app está em uso."""
    from pathlib import Path
    pasta_local_state = Path(pasta_local_state)
    pasta_trabalho = Path(pasta_trabalho)

    caminho_session = pasta_local_state / "session.db"
    caminho_session_wal = pasta_local_state / "session.db-wal"
    _exigir_arquivo_existe(caminho_session)
    _exigir_wal_valido(caminho_session_wal)

    segredo_de_sessao = obter_segredo_de_sessao()
    decrypt_db_file(segredo_de_sessao, caminho_session, pasta_trabalho / "session.dec.db")
    decrypt_db_wal_file(segredo_de_sessao, caminho_session_wal, pasta_trabalho / "session.dec.db-wal")

    candidatos = carvear_chaves_de_cliente(pasta_trabalho / "session.dec.db-wal")
    if not candidatos:
        raise RuntimeError(
            "Nenhuma client_key encontrada no WAL de session.db — reinicie "
            "o WhatsApp Desktop e tente de novo."
        )
    client_key = candidatos[-1]

    nome_da_pasta_de_sessao = hashlib.sha1(client_key).hexdigest().upper()
    # localizar_pasta_de_sessao (localizacao.py, Task 6) faz a checagem e
    # levanta RuntimeError nomeado -- religada aqui em vez de duplicar a
    # checagem inline (achado ajusta da revisão dev-10, 2ª rodada: a função
    # nascia e nunca era chamada). A pasta existir já É o oráculo (achado
    # 6/12): SHA1(client_key) só bate com o nome real da pasta se a chave
    # carveada estiver correta -- derivar o nome, nunca escolher a pasta
    # existente arbitrariamente.
    pasta_de_sessao = localizar_pasta_de_sessao(pasta_local_state, nome_da_pasta_de_sessao)

    oduid = obter_oduid()
    aux_key = hashlib.pbkdf2_hmac("sha256", client_key, oduid, PBKDF_ITERATIONS, dklen=32)
    iv = hashlib.pbkdf2_hmac("sha256", aux_key, oduid, PBKDF_ITERATIONS, dklen=16)
    cifrador_db_key = AES.new(aux_key, AES.MODE_CBC, iv=iv)
    db_key = cifrador_db_key.encrypt(_pad_pkcs7(STATIC_BYTES))

    caminho_native = pasta_de_sessao / "nativeSettings.db"
    caminho_native_wal = pasta_de_sessao / "nativeSettings.db-wal"
    _exigir_arquivo_existe(caminho_native)
    _exigir_wal_valido(caminho_native_wal)
    caminho_native_dec = pasta_trabalho / "nativeSettings.dec.db"
    decrypt_db_file(db_key, caminho_native, caminho_native_dec)
    decrypt_db_wal_file(db_key, caminho_native_wal, pasta_trabalho / "nativeSettings.dec.db-wal")
    _exigir_magic_sqlite(caminho_native_dec, "nativeSettings (db_key)")

    por_tipo: dict[int, list[bytes]] = {}
    for tipo, chave in carvear_chaves_de_nativesettings(pasta_trabalho / "nativeSettings.dec.db-wal"):
        por_tipo.setdefault(tipo, []).append(chave)

    if 1 not in por_tipo or 2 not in por_tipo:
        tipos_achados = sorted(por_tipo.keys())
        raise RuntimeError(
            "O carving de nativeSettings.db-wal não encontrou os tipos de "
            f"chave esperados (precisa de 1 e 2; achou {tipos_achados}). O "
            "formato pode ter mudado numa atualização do WhatsApp, ou o "
            "WAL foi consolidado (checkpoint) antes da leitura — reinicie "
            "o WhatsApp Desktop e tente de novo."
        )
    chave_generic_storage = por_tipo[1][-1]
    chave_contacts = por_tipo[2][-1]

    caminho_gs = pasta_de_sessao / "genericStorage.db"
    caminho_gs_wal = pasta_de_sessao / "genericStorage.db-wal"
    _exigir_arquivo_existe(caminho_gs)
    _exigir_wal_valido(caminho_gs_wal)
    caminho_gs_dec = pasta_trabalho / "genericStorage.dec.db"
    decrypt_db_file(chave_generic_storage, caminho_gs, caminho_gs_dec)
    decrypt_db_wal_file(chave_generic_storage, caminho_gs_wal,
                         pasta_trabalho / "genericStorage.dec.db-wal")
    _exigir_magic_sqlite(caminho_gs_dec, "genericStorage (chave tipo 1, carveada)")

    caminho_contacts = pasta_de_sessao / "contacts.db"
    caminho_contacts_wal = pasta_de_sessao / "contacts.db-wal"
    _exigir_arquivo_existe(caminho_contacts)
    _exigir_wal_valido(caminho_contacts_wal)
    caminho_contacts_dec = pasta_trabalho / "contacts.dec.db"
    decrypt_db_file(chave_contacts, caminho_contacts, caminho_contacts_dec)
    decrypt_db_wal_file(chave_contacts, caminho_contacts_wal,
                         pasta_trabalho / "contacts.dec.db-wal")
    _exigir_magic_sqlite(caminho_contacts_dec, "contacts (chave tipo 2, carveada)")


_TAMANHO_HEADER_WAL = 32


def _exigir_wal_valido(caminho_wal) -> None:
    """Checa existência e tamanho mínimo (32 bytes, o header do formato
    WAL) ANTES de chamar decrypt_db_wal_file — sem isso, `Path.read_bytes()`
    levanta `FileNotFoundError` cru se o arquivo não existir, e
    `struct.unpack_from` levanta `struct.error` cru se ele existir mas for
    menor que o header (achado `bloqueia` da revisão dev-10, 2ª rodada:
    cinco caminhos de falha terminavam em stack trace, este é dois deles).
    `main()` só captura `RuntimeError` — por isso a recusa aqui é
    `RuntimeError`, não a exceção original."""
    from pathlib import Path
    caminho_wal = Path(caminho_wal)
    if not caminho_wal.exists():
        raise RuntimeError(
            f"{caminho_wal.name} ausente — o WhatsApp precisa estar aberto "
            "e ter escrito nessa base para a cadeia de decifra funcionar "
            "(distinto de schema incompatível)."
        )
    tamanho = caminho_wal.stat().st_size
    if tamanho < _TAMANHO_HEADER_WAL:
        raise RuntimeError(
            f"{caminho_wal.name} existe mas tem só {tamanho} bytes — menor "
            f"que o header do formato WAL ({_TAMANHO_HEADER_WAL} bytes). "
            "Pode ter sido consolidado (checkpoint) no meio da leitura; "
            "tente de novo."
        )


def _exigir_arquivo_existe(caminho) -> None:
    """Checa existência do `.db` principal ANTES de `decrypt_db_file` —
    achado `bloqueia` da revisão dev-10 (3ª rodada): `Path.read_bytes()`
    levantava `FileNotFoundError` cru, que `main()` não captura. Simétrico
    a `_exigir_wal_valido`, para o arquivo que não tem formato WAL."""
    from pathlib import Path
    caminho = Path(caminho)
    if not caminho.exists():
        raise RuntimeError(
            f"{caminho.name} ausente em {caminho.parent} — a instalação do "
            "WhatsApp Desktop parece incompleta ou corrompida."
        )


def _exigir_magic_sqlite(caminho_decifrado, chave_usada_para: str) -> None:
    """Confere o magic number do SQLite (`MAGIC_SQLITE`, definida no topo
    deste módulo) logo após decifrar — achado `bloqueia` da revisão dev-10
    (3ª rodada): o carving de `nativeSettings.db-wal` é heurístico e
    devolve **lista**; pegar `[-1]` sem validar significa que uma chave
    tipo 1/2 plausível e errada produzia 57 MB de lixo, e o erro que
    chegava ao mentorado vinha de dentro de `leitura.py`
    (`sqlite3.DatabaseError: file is not a database`), fora de qualquer
    `except`. `client_key` tem o oráculo SHA1 (a pasta existir); as chaves
    carveadas por tipo não tinham nenhum até este check."""
    from pathlib import Path
    caminho_decifrado = Path(caminho_decifrado)
    inicio = caminho_decifrado.read_bytes()[:len(MAGIC_SQLITE)]
    if inicio != MAGIC_SQLITE:
        raise RuntimeError(
            f"{caminho_decifrado.name} não começa com o cabeçalho SQLite "
            f"depois de decifrado — a chave usada para {chave_usada_para} "
            "está errada. O carving pode ter devolvido uma chave plausível "
            "e errada; reinicie o WhatsApp Desktop e tente de novo."
        )


def _pad_pkcs7(dado: bytes, tamanho_bloco: int = 16) -> bytes:
    tam_padding = tamanho_bloco - (len(dado) % tamanho_bloco)
    return dado + bytes([tam_padding]) * tam_padding
