"""Leitura do ChatStorage.sqlite — Adaptador macOS. Leitura direta via
mode=ro, sem cópia (medido: VACUUM INTO estoura o teto de performance do
critério 8; mode=ro não disputa lock com o app escrevendo)."""
import contextlib
import sqlite3
from pathlib import Path

from charla.modelo import Anexo, Conversa, Mensagem

_EPOCA_CORE_DATA = 978307200  # segundos entre 2001-01-01 e 1970-01-01

_NATUREZA_POR_TIPO = {
    0: "direta",
    1: "grupo",
    2: "lista-de-transmissao",
    # 3 = status individual por contato -- nao e Conversa, filtrado antes de virar Conversa
    4: "comunidade",
}

# medido em 21/09/2026 (Task 4) contra instalacao real: ZMESSAGETYPE de
# ZWAMESSAGE, join por ZWAMESSAGE.ZMEDIAITEM = ZWAMEDIAITEM.Z_PK -- NAO existe
# coluna de tipo em ZWAMEDIAITEM. So os 3 tipos que o criterio 11 exige ficam
# mapeados; video (2), sticker (15) e os demais caem no fallback.
_TIPO_MEDIA_POR_CODIGO = {
    1: "imagem",
    3: "audio",
    8: "documento",
}


def _conectar_ro(caminho: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)


def ler_conversas(caminho: Path) -> list[Conversa]:
    with contextlib.closing(_conectar_ro(caminho)) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT Z_PK, ZCONTACTJID, ZPARTNERNAME, ZSESSIONTYPE,
                   ZMESSAGECOUNTER, ZLASTMESSAGEDATE
            FROM ZWACHATSESSION
            WHERE ZSESSIONTYPE IN (0, 1, 2, 4)
            ORDER BY Z_PK
        """)
        linhas = cur.fetchall()

    conversas = []
    for pk, jid, nome, tipo, contador, ultima_data in linhas:
        ultima_mensagem_em = (
            int(ultima_data + _EPOCA_CORE_DATA) if ultima_data is not None else None
        )
        conversas.append(
            Conversa(
                id=jid,
                nome=nome,
                natureza=_NATUREZA_POR_TIPO[tipo],
                total_mensagens=contador or 0,
                ultima_mensagem_em=ultima_mensagem_em,
            )
        )
    return conversas


def _resolver_autor(cur, chat_pk, natureza, zisfromme, zgroupmember):
    if zisfromme:
        return "eu"
    if natureza == "direta":
        cur.execute("SELECT ZPARTNERNAME, ZCONTACTJID FROM ZWACHATSESSION WHERE Z_PK = ?", (chat_pk,))
        nome, jid = cur.fetchone()
        return nome or jid
    # grupo / lista-de-transmissao / comunidade
    if zgroupmember is None:
        return None
    cur.execute(
        "SELECT ZMEMBERJID, ZCONTACTNAME, ZFIRSTNAME FROM ZWAGROUPMEMBER WHERE Z_PK = ?",
        (zgroupmember,),
    )
    linha = cur.fetchone()
    if linha is None:
        return None
    jid, nome, primeiro_nome = linha
    return nome or primeiro_nome or jid


def ler_mensagens(caminho: Path, conversa_id: str) -> list[Mensagem]:
    with contextlib.closing(_conectar_ro(caminho)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT Z_PK, ZSESSIONTYPE FROM ZWACHATSESSION WHERE ZCONTACTJID = ?",
            (conversa_id,),
        )
        linha = cur.fetchone()
        if linha is None:
            return []
        chat_pk, tipo = linha
        natureza = _NATUREZA_POR_TIPO.get(tipo, "desconhecida")

        cur.execute(
            """
            SELECT Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZGROUPMEMBER
            FROM ZWAMESSAGE
            WHERE ZCHATSESSION = ?
            ORDER BY ZMESSAGEDATE ASC
            """,
            (chat_pk,),
        )
        linhas = cur.fetchall()

        mensagens = []
        for pk, texto, data, zisfromme, zgroupmember in linhas:
            autor = _resolver_autor(cur, chat_pk, natureza, zisfromme, zgroupmember)
            mensagens.append(
                Mensagem(
                    id=str(pk),
                    conversa_id=conversa_id,
                    texto=texto,
                    instante=int(data + _EPOCA_CORE_DATA),
                    autor=autor,
                )
            )
    return mensagens


def ler_anexo(caminho: Path, anexo_id: str) -> Anexo:
    with contextlib.closing(_conectar_ro(caminho)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT mi.ZMEDIALOCALPATH, m.ZMESSAGETYPE, m.ZCHATSESSION
            FROM ZWAMEDIAITEM mi
            JOIN ZWAMESSAGE m ON m.ZMEDIAITEM = mi.Z_PK
            WHERE mi.Z_PK = ?
            """,
            (int(anexo_id),),
        )
        linha = cur.fetchone()
        if linha is None:
            raise ValueError(f"anexo {anexo_id} não encontrado")
        caminho_relativo, codigo_tipo, chat_pk = linha

        cur.execute("SELECT ZCONTACTJID FROM ZWACHATSESSION WHERE Z_PK = ?", (chat_pk,))
        (conversa_id,) = cur.fetchone()

    pasta_group_container = caminho.parent
    caminho_absoluto = pasta_group_container / "Message" / caminho_relativo
    tipo = _TIPO_MEDIA_POR_CODIGO.get(codigo_tipo, "desconhecido")

    return Anexo(
        id=anexo_id,
        conversa_id=conversa_id,
        tipo=tipo,
        caminho_absoluto=str(caminho_absoluto),
    )
