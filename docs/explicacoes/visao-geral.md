---
id: 202609201033
projeto: charla
tipo: explicacao
escopo: repo:charla
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: O quê/para quem em 30 segundos — visão geral do repo charla (quadrante explicação, ADR 20260713).
tags: [explicacao, visao-geral, python]
---

# charla — o quê / para quem

CLI local que dá a um mentorado (sem o produto irmão `malote`) acesso ao
próprio histórico de WhatsApp, direto do banco que o WhatsApp Desktop já
guarda na máquina dele — sem servidor, sem conta de terceiro, sem nada
saindo da máquina.

## Para quem

Mentorados que não têm o `malote` (que pressupõe uma instalação 24/7 numa
máquina própria) e o agente que opera em nome deles. O consumidor típico
não é um humano lendo a saída — é um agente que chama o `charla`, lê o
JSON, e decide o próximo passo (por isso a documentação de referência é
exaustiva: `docs/referencias/comandos-e-saida.md`).

## O que faz

Lê `conversas`, `mensagens` de uma conversa e `anexo` de mídia (funciona no
macOS; no Windows sempre recusa — mídia não implementada nesta versão),
sempre do banco local do WhatsApp Desktop — nunca copia, nunca acumula
histórico próprio, cada chamada lê o estado atual. No Windows, o banco é
cifrado por página (DPAPI-NG) e o `charla` decifra na hora, num diretório
temporário que se apaga sozinho ao final do comando; no macOS, o banco já
é SQLite puro, lido direto. Autor de mensagem de grupo resolve de duas
formas bem diferentes por plataforma — SQL direto no macOS, conexão ao
runtime do WhatsApp em execução (protocolo de debug do Chromium) no
Windows, porque o banco lá não guarda quem escreveu cada mensagem.

## Escopo

Dentro: leitura local, nas duas plataformas onde o WhatsApp Desktop nativo
existe (Windows UWP/Microsoft Store, macOS App Store). Fora: enviar
mensagem, modo rede, múltiplo usuário, captura contínua/ouvinte, qualquer
coisa que grave ou acumule fora do que o próprio WhatsApp já gravou. O
`charla` não promete confidencialidade além do que a máquina local já
garante — mesma postura que o `malote` já declara para o Operador da
instalação.

## Agente responsável

Agente padrão deste repo: **Tech** (SRE Agentic). Toda sessão de código roda sob o comportamento do Tech.
