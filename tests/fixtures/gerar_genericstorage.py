"""Gera um genericStorage.dec.db sintético — schema real, dado inventado.
Sem cifra: os testes de leitura.py operam sobre o banco JÁ decifrado, então
a fixture pula a cadeia de decifra por completo."""
import sqlite3
from pathlib import Path


def gerar(caminho: Path) -> None:
    con = sqlite3.connect(caminho)
    con.execute("""
        CREATE TABLE message (
          rowid INTEGER PRIMARY KEY,
          id TEXT,
          chatId TEXT,
          timestamp TEXT,
          text TEXT
        )
    """)
    linhas = [
        (1, "1000000001", "5511999990001@lid", "1789600001", "oi, tudo bem?"),
        (2, "1000000002", "5511999990001@lid", "1789600010", "tudo, e você?"),
        (3, "1000000003", "120363021901138870@g.us", "1789600020", "bom dia grupo"),
        (4, "1000000004", "120363021901138870@g.us", "1789600030", "bom dia!"),
        (5, "1000000005", "120363021901138870@g.us", "1789600040", "alguém viu o combinado?"),
    ]
    con.executemany(
        "INSERT INTO message (rowid, id, chatId, timestamp, text) VALUES (?, ?, ?, ?, ?)",
        linhas,
    )
    con.commit()
    con.close()
