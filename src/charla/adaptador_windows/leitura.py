"""Consultas SQL sobre os bancos decifrados — devolve o modelo comum
(Conversa, Mensagem). Nunca resolve autor aqui — ver autor_cdp.py.

Conexões abrem com `contextlib.closing` — achado ajusta da revisão dev-10
(2ª rodada, NÃO RESOLVIDO na 1ª): `con.close()` solto no fim da função
não roda se uma exceção estourar no meio (ex.: SQL malformado), e no
Windows conexão aberta é handle aberto, que é exatamente o que impede
`diretorio_de_trabalho` de remover o banco decifrado depois."""
import contextlib
import sqlite3
from pathlib import Path

from charla.modelo import Conversa, Mensagem

_SUFIXO_COLETIVA = "@g.us"
_SUFIXOS_DIRETA_CONHECIDOS = ("@lid", "@s.whatsapp.net")


def _natureza(chat_id: str) -> str:
    """Achado `ajusta` da revisão dev-10 (2ª rodada, NÃO RESOLVIDO desde a
    1ª): classificar tudo que não termina em `@g.us` como "direta" também
    engole sufixos que não são nenhum dos dois (`@broadcast`, status) — a
    MESMA ambiguidade que o `malote` mede e ainda não fechou (#826), sem
    dado de produção aqui para decidir diferente. Não resolvido às cegas:
    os sufixos conhecidos ficam nomeados, e o comportamento para o
    desconhecido continua sendo "direta" (não quebra nada hoje), mas
    explícito — quem for medir isso no Windows tem onde acrescentar."""
    if chat_id.endswith(_SUFIXO_COLETIVA):
        return "coletiva"
    return "direta"  # inclui @lid, @s.whatsapp.net (conhecidos) e qualquer outro (nao medido)


def ler_conversas(caminho_generic_storage: Path, caminho_contacts: Path) -> list[Conversa]:
    with contextlib.closing(sqlite3.connect(f"file:{caminho_generic_storage}?mode=ro", uri=True)) as con_gs:
        linhas = con_gs.execute("""
            SELECT chatId, COUNT(*) as total, MAX(CAST(timestamp AS INTEGER)) as ultima
            FROM message
            GROUP BY chatId
        """).fetchall()

    nomes_por_jid = _carregar_nomes(caminho_contacts)

    conversas = []
    for chat_id, total, ultima in linhas:
        conversas.append(Conversa(
            id=chat_id,
            nome=nomes_por_jid.get(chat_id),
            natureza=_natureza(chat_id),
            total_mensagens=total,
            ultima_mensagem_em=ultima,
        ))
    return conversas


def _carregar_nomes(caminho_contacts: Path) -> dict[str, str]:
    with contextlib.closing(sqlite3.connect(f"file:{caminho_contacts}?mode=ro", uri=True)) as con:
        linhas = con.execute(
            "SELECT DbLid, ContactName, PushName FROM UserStatuses WHERE DbLid IS NOT NULL"
        ).fetchall()
    nomes = {}
    for db_lid, contact_name, push_name in linhas:
        nome = contact_name or push_name
        if nome:
            nomes[db_lid] = nome
    return nomes


def ler_mensagens(caminho_generic_storage: Path, conversa_id: str) -> list[Mensagem]:
    # ORDER BY composto (instante, rowid) — instante sozinho nao desempata
    # quando duas mensagens caem no mesmo segundo (medido: acontece), e
    # rowid sozinho e ordem de INSERCAO local, que diverge de ordem
    # cronologica quando um vinculo novo importa historico em lote (medido:
    # 14 meses de historico em 3 horas). Mesmo precedente do cursor composto
    # do malote.
    with contextlib.closing(sqlite3.connect(f"file:{caminho_generic_storage}?mode=ro", uri=True)) as con:
        linhas = con.execute(
            "SELECT id, text, CAST(timestamp AS INTEGER) FROM message "
            "WHERE chatId = ? ORDER BY CAST(timestamp AS INTEGER) ASC, rowid ASC",
            (conversa_id,),
        ).fetchall()
    return [
        Mensagem(id=id_, conversa_id=conversa_id, texto=texto, instante=instante, autor=None)
        for id_, texto, instante in linhas
    ]
