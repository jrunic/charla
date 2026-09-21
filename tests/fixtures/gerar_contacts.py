"""Gera um contacts.dec.db sintético — schema real medido contra
instalação Windows real (documento técnico interno do autor)."""
import sqlite3
from pathlib import Path


def gerar(caminho: Path) -> None:
    con = sqlite3.connect(caminho)
    con.execute("""
        CREATE TABLE UserStatuses (
          StatusID INTEGER PRIMARY KEY,
          Jid TEXT,
          DbLid TEXT,
          ContactName TEXT,
          PushName TEXT
        )
    """)
    con.execute(
        "INSERT INTO UserStatuses (Jid, DbLid, ContactName, PushName) VALUES (?, ?, ?, ?)",
        ("5511999990001@s.whatsapp.net", "5511999990001@lid", "Fulano de Teste", "Fulano"),
    )
    con.commit()
    con.close()
