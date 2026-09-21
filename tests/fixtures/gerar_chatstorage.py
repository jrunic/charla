"""Gera um ChatStorage.sqlite sintético com o schema ZWA* real, para os
testes do Adaptador macOS rodarem sem depender do app instalado nem de
dado real de conta nenhuma."""
import sqlite3
from pathlib import Path

# epoca Core Data: segundos desde 2001-01-01. 780000000 ~= 26/09/2025.
_EPOCA_BASE = 780000000


def gerar_chatstorage(caminho: Path) -> None:
    con = sqlite3.connect(caminho)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE ZWACHATSESSION (
            Z_PK INTEGER PRIMARY KEY,
            Z_ENT INTEGER, Z_OPT INTEGER,
            ZSESSIONTYPE INTEGER,
            ZCONTACTJID TEXT,
            ZPARTNERNAME TEXT,
            ZMESSAGECOUNTER INTEGER,
            ZLASTMESSAGEDATE REAL
        )
    """)
    cur.execute("""
        CREATE TABLE ZWAMESSAGE (
            Z_PK INTEGER PRIMARY KEY,
            Z_ENT INTEGER, Z_OPT INTEGER,
            ZCHATSESSION INTEGER,
            ZTEXT TEXT,
            ZMESSAGEDATE REAL,
            ZISFROMME INTEGER,
            ZGROUPMEMBER INTEGER,
            ZFROMJID TEXT,
            ZMEDIAITEM INTEGER,
            ZMESSAGETYPE INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE ZWAGROUPMEMBER (
            Z_PK INTEGER PRIMARY KEY,
            Z_ENT INTEGER, Z_OPT INTEGER,
            ZCHATSESSION INTEGER,
            ZMEMBERJID TEXT,
            ZCONTACTNAME TEXT,
            ZFIRSTNAME TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE ZWAMEDIAITEM (
            Z_PK INTEGER PRIMARY KEY,
            Z_ENT INTEGER, Z_OPT INTEGER,
            ZMEDIALOCALPATH TEXT,
            ZFILESIZE INTEGER
        )
    """)

    # Conversa direta (natureza 0): "Ana", 2 mensagens
    cur.execute(
        "INSERT INTO ZWACHATSESSION VALUES (1, 1, 1, 0, '5511999990002@s.whatsapp.net', 'Ana', 2, ?)",
        (_EPOCA_BASE + 200,),
    )
    cur.execute(
        "INSERT INTO ZWAMESSAGE (Z_PK, Z_ENT, Z_OPT, ZCHATSESSION, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZGROUPMEMBER, ZFROMJID, ZMEDIAITEM, ZMESSAGETYPE) "
        "VALUES (1, 1, 1, 1, 'oi', ?, 0, NULL, '5511999990002@s.whatsapp.net', NULL, 0)",
        (_EPOCA_BASE + 100,),
    )
    cur.execute(
        "INSERT INTO ZWAMESSAGE (Z_PK, Z_ENT, Z_OPT, ZCHATSESSION, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZGROUPMEMBER, ZFROMJID, ZMEDIAITEM, ZMESSAGETYPE) "
        "VALUES (2, 1, 1, 1, 'oi, tudo bem?', ?, 1, NULL, NULL, NULL, 0)",
        (_EPOCA_BASE + 200,),
    )

    # Conversa grupo (natureza 1): 2 membros, 2 mensagens + 1 de sistema
    cur.execute(
        "INSERT INTO ZWACHATSESSION VALUES (2, 1, 1, 1, '111222333@g.us', 'Equipe', 3, ?)",
        (_EPOCA_BASE + 400,),
    )
    cur.execute("INSERT INTO ZWAGROUPMEMBER VALUES (1, 1, 1, 2, '556511112222@lid', '', '')")
    cur.execute("INSERT INTO ZWAGROUPMEMBER VALUES (2, 1, 1, 2, '556533334444@lid', 'Marcos', '')")
    cur.execute(
        "INSERT INTO ZWAMESSAGE (Z_PK, Z_ENT, Z_OPT, ZCHATSESSION, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZGROUPMEMBER, ZFROMJID, ZMEDIAITEM, ZMESSAGETYPE) "
        "VALUES (3, 1, 1, 2, 'bom dia', ?, 0, 1, '111222333@g.us', NULL, 0)",
        (_EPOCA_BASE + 300,),
    )
    cur.execute(
        # ZMESSAGETYPE=1 (imagem) -- medido contra instalação real em 21/09/2026 (Task 4)
        "INSERT INTO ZWAMESSAGE (Z_PK, Z_ENT, Z_OPT, ZCHATSESSION, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZGROUPMEMBER, ZFROMJID, ZMEDIAITEM, ZMESSAGETYPE) "
        "VALUES (4, 1, 1, 2, 'bom dia!', ?, 0, 2, '111222333@g.us', 1, 1)",
        (_EPOCA_BASE + 350,),
    )
    cur.execute(
        "INSERT INTO ZWAMESSAGE (Z_PK, Z_ENT, Z_OPT, ZCHATSESSION, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZGROUPMEMBER, ZFROMJID, ZMEDIAITEM, ZMESSAGETYPE) "
        "VALUES (5, 1, 1, 2, NULL, ?, 0, NULL, '111222333@g.us', NULL, 0)",
        (_EPOCA_BASE + 400,),
    )

    # Anexo da mensagem 4 (imagem) -- tipo vem de ZWAMESSAGE.ZMESSAGETYPE, nao de coluna em ZWAMEDIAITEM
    cur.execute(
        "INSERT INTO ZWAMEDIAITEM VALUES (1, 1, 1, 'Media/111222333@g.us/9/f/foto.jpg', 204800)"
    )

    # Conversa tipo 3 (status) - não deve aparecer em conversas()
    cur.execute(
        "INSERT INTO ZWACHATSESSION VALUES (3, 1, 1, 3, '5511988887777@status', NULL, 5, ?)",
        (_EPOCA_BASE + 50,),
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    import sys
    gerar_chatstorage(Path(sys.argv[1]))
