"""Domínio comum do charla — agnóstico de sistema operacional."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Conversa:
    id: str
    nome: str | None
    natureza: str  # valores divergem por plataforma -- ver docs/referencias/comandos-e-saida.md
    # Windows: "direta" | "coletiva"
    # macOS: "direta" | "grupo" | "lista-de-transmissao" | "comunidade"
    total_mensagens: int
    ultima_mensagem_em: int | None  # timestamp unix, segundos

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "natureza": self.natureza,
            "total_mensagens": self.total_mensagens,
            "ultima_mensagem_em": self.ultima_mensagem_em,
        }


@dataclass(frozen=True, slots=True)
class Mensagem:
    id: str
    conversa_id: str
    texto: str
    instante: int  # timestamp unix, segundos
    autor: str | None  # None quando não resolvido -- resolução diverge por
    # plataforma: Windows via CDP (adaptador_windows/autor_cdp.py, pode
    # ficar None); macOS via SQL direto ("eu" | nome | JID, None só em
    # mensagem de sistema) -- ver docs/referencias/comandos-e-saida.md

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "conversa_id": self.conversa_id,
            "texto": self.texto,
            "instante": self.instante,
            "autor": self.autor,
        }


@dataclass(frozen=True, slots=True)
class Anexo:
    id: str
    conversa_id: str
    tipo: str  # "imagem" | "documento" | "audio" | "desconhecido" (macOS,
    # código de ZMESSAGETYPE sem mapa confirmado -- ex. video, sticker).
    # `anexo` sempre recusa no Windows hoje (não implementado) -- ver
    # docs/referencias/comandos-e-saida.md
    caminho_absoluto: str

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "conversa_id": self.conversa_id,
            "tipo": self.tipo,
            "caminho_absoluto": self.caminho_absoluto,
        }
