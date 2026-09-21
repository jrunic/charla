---
id: 202609201033
projeto: charla
tipo: nota
escopo: repo:charla
plataforma: "*"
status: ativo
descricao: README do repo charla — entrypoint humano e guia de instalação para quem vai usar o charla.
tags: [readme, python, cli, whatsapp]
---

# charla

CLI local que lê os bancos de dados do WhatsApp Desktop na sua própria
máquina — sem enviar nada para fora, sem servidor, sem conta de terceiro.
Funciona no Windows (app UWP/Microsoft Store) e no macOS (app da App
Store).

## Instalação

Baixe `charla.pyz` (arquivo único, sem instalação) da
[página de releases](https://github.com/jrunic/charla/releases/latest) e
rode com o Python já instalado na sua máquina — versão 3.12 ou mais
nova, sem precisar de `pip install` nem de ambiente virtual:

```
python3 charla.pyz conversas
```

Pré-requisito: o WhatsApp Desktop instalado, logado, e aberto pelo menos
uma vez nesta máquina.

## Comandos

- `charla.pyz conversas` — lista as conversas, com nome, natureza
  (direta/grupo/etc.) e contagem de mensagens.
- `charla.pyz mensagens --conversa <id>` — lista as mensagens de uma
  conversa, em ordem cronológica, com autor.
- `charla.pyz anexo <id>` — devolve o caminho absoluto do arquivo de mídia
  no disco (imagem, documento ou áudio).
- `charla.pyz habilitar-autor-windows` — só no Windows: habilita a
  resolução de autor de mensagem de grupo (precisa rodar uma vez; reinicia
  o WhatsApp automaticamente).

Toda saída é JSON, para uso por outro programa ou agente.

## O que o charla NÃO faz

Não envia mensagem, não modifica o WhatsApp, não sobe dado para nenhum
servidor. Lê o que o próprio app já gravou localmente, a cada execução —
não guarda histórico próprio, não fica rodando em segundo plano.

## Para agentes e desenvolvedores

- `CONTEXTO.md` — padrões técnicos e restrições (comece aqui)
- `GLOSSARIO.md` — linguagem do domínio
- `roadmap.md` — incrementos e estado
- `docs/` — arquitetura, domínio, decisões e documentação (Diátaxis)
