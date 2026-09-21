---
id: 202609201902
projeto: charla
tipo: referencia
status: aprovado
escopo: repo:charla
plataforma: "*"
dominios: [tecnologia]
descricao: "Vocabulário do domínio do charla — Conversa, Mensagem, Anexo"
tags: [glossario, dominio]
---

# GLOSSARIO.md — charla

Vocabulário do domínio do `charla`. Reaproveitado do `malote`
(`15-repositorios/malote/GLOSSARIO.md`) como conhecimento — sem importar o
pacote.

## Conversa

Uma thread de mensagens no WhatsApp — **direta** (entre duas pessoas) ou
**coletiva** (grupo). No Windows, o discriminante é o sufixo do
identificador: `@g.us` é coletiva, `@lid`/`@s.whatsapp.net` é direta
(medido contra instalação Windows real).
Nome de Conversa coletiva não está persistido no banco local (só nome de
contato, para Conversa direta) — resolvido sob demanda, mesma via CDP do
autor (ver Mensagem, abaixo).

## Mensagem

Um envio dentro de uma Conversa — texto, instante, e (quando resolvido)
autor. No Windows o autor não está persistido no banco local; é resolvido
sob demanda via conexão ao processo do WhatsApp em execução (ver
`adaptador_windows/autor_cdp.py`).

## Anexo

Mídia trocada numa Conversa — imagem, documento, áudio. No Windows, fora do
escopo do Plano 1 (ver Decisão 1 do plano): a mídia não tem caminho de
arquivo amigável nesta plataforma.
