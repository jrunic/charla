---
id: 202609201033
projeto: charla
tipo: arquitetura
escopo: repo:charla
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Mapa estrutural do repo charla — módulos, fluxos críticos, schema, deploy. Carga sob demanda.
tags: [arquitetura, Python]
---

# Arquitetura do Projeto: charla

> **Mapa fino (espinha de navegação, ADR 20260713).** Este arquivo diz *o que existe e onde* e
> **aponta** para `explicacoes/` — nunca duplica conteúdo de design. Se uma seção crescer em prosa
> de "por quê", mova para `docs/explicacoes/` e deixe só o ponteiro. O `dev-08 auditar`
> fiscaliza mapa gordo.

## Visão geral

CLI Python, um subcomando por operação (`conversas`, `mensagens`, `anexo`,
`habilitar-autor-windows`). `main()` dispatcha por `sys.platform`: no
Windows, decifra as bases num diretório temporário e chama a função do
comando; no macOS, localiza o `ChatStorage.sqlite` do WhatsApp Desktop
nativo e lê direto (`mode=ro`, sem decifra, sem cópia). Plano 1 (Windows) e
Plano 2 (macOS) implementados.

```
charla/
├── README.md         — entrypoint humano
├── CONTEXTO.md       — padrões técnicos + restrições (carga default; raiz — jd-agente lê aqui)
├── GLOSSARIO.md      — linguagem do domínio (quando existir)
├── docs/
│   ├── arquitetura.md — mapa fino (este arquivo)
│   ├── decisoes/      — ADRs locais ao produto
│   ├── dominio/       — modelo de domínio (neg-02)
│   └── {tutoriais,guias,referencias,explicacoes}/ — quadrantes Diátaxis
└── [src/, tests/, migrations/, scripts/, ...]

O trabalho — `roadmap.md`, spec, plano, diário — não vive aqui: vive na pasta
de trabalho declarada em `CONTEXTO.md` §Onde o trabalho acontece (ADR
`20260913-o-repo-guarda-o-produto-e-a-pasta-guarda-o-trabalho`).
```

## Módulos principais

| Módulo | Responsabilidade |
|---|---|
| `src/charla/modelo.py` | `Conversa`, `Mensagem`, `Anexo` — domínio comum, agnóstico de SO |
| `src/charla/cli.py` | `argparse`, dispatch de comando, serialização JSON, códigos de saída |
| `src/charla/__main__.py` | Entrypoint `python -m charla` |
| `src/charla/_vendor/pycryptodome_carregador.py` | Extrai `pycryptodome` vendorizado (win_amd64) para disco na primeira execução |
| `src/charla/_vendor/pycryptodome_win_amd64.zip` | Wheel `win_amd64` do `pycryptodome`, reempacotado como dado bruto |
| `src/charla/_vendor/websocket/` | `websocket-client` vendorizado por cópia direta (puro Python) — cliente CDP |
| `src/charla/adaptador_windows/localizacao.py` | Acha a instalação UWP, detecta arquitetura, recusa se não suportada |
| `src/charla/adaptador_windows/decifra.py` | Cadeia DPAPI-NG completa — ODUID, segredo de sessão, AES-OFB/CBC por página, WAL, carving, oráculo SHA1, orquestração (`decifrar_bases_da_sessao`) |
| `src/charla/adaptador_windows/sessao_temporaria.py` | Context manager do diretório temporário — cria, decifra, garante limpeza |
| `src/charla/adaptador_windows/leitura.py` | Consultas SQL sobre os bancos decifrados → `Conversa`/`Mensagem` |
| `src/charla/adaptador_windows/autor_cdp.py` | Cliente CDP — habilitar debug, abrir conversa por `chatId`, resolver autor e nome de grupo |
| `src/charla/adaptador_windows/ambiente_windows.py` | Grava a porta de debug em `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` via `winreg`, preservando o que já existir |
| `src/charla/adaptador_macos/localizacao.py` | Localiza `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`, recusa nomeada se ausente |
| `src/charla/adaptador_macos/leitura.py` | Consultas SQL direto (`mode=ro`) sobre o `ChatStorage.sqlite` real → `Conversa`/`Mensagem`/`Anexo`; natureza dos 5 `ZSESSIONTYPE`, autor por 3 ramos (`ZISFROMME`/parceiro direto/`ZGROUPMEMBER`), tipo de mídia por `ZWAMESSAGE.ZMESSAGETYPE` |

## Fluxos críticos

**Windows** — `main()`: localizar instalação → decifrar 4 bases (`.db` +
`.db-wal`: session, nativeSettings, genericStorage, contacts) num
diretório temporário → ler conversas/mensagens do SQLite decifrado →
resolver autor/nome de grupo via CDP quando a porta de debug está aberta
(degrade gracioso se não estiver) → serializar JSON → apagar o diretório
temporário (mesmo se o comando falhar no meio).

**macOS** — `main()`: localizar `ChatStorage.sqlite` → abrir conexão
`mode=ro` direto no arquivo original (sem cópia, sem `VACUUM INTO` — medido:
`VACUUM INTO` estoura o teto de performance do critério 8) → ler
conversas/mensagens/anexo, autor já resolvido por SQL puro (sem CDP, sem
processo externo) → serializar JSON. Sem diretório temporário — não há
decifra nem cópia a limpar.

## Schema/persistência

**Windows**: SQLite dos bancos do WhatsApp Desktop UWP (não é schema
próprio do `charla`) — tabelas `message` (genericStorage.db) e
`UserStatuses` (contacts.db), sempre lidas, nunca escritas.

**macOS**: SQLite do `ChatStorage.sqlite` nativo, schema `ZWA*` (Core Data)
— `ZWACHATSESSION`, `ZWAMESSAGE`, `ZWAGROUPMEMBER`, `ZWAMEDIAITEM`, sempre
lidas via `mode=ro`, nunca escritas (verificado por hash antes/depois).

## Deploy

`scripts/build-pyz.py` monta `dist/charla.pyz` via `zipapp` da stdlib —
copia `src/charla/` inteiro para um stage, escreve o próprio
`__main__.py` na raiz do stage (com `raise SystemExit(main())` —
`zipapp.create_archive(main=...)` gera um `__main__.py` que descarta o
código de saída, achado real corrigido no Plano 3) e gera o zip a partir
do stage. O `_vendor/pycryptodome_win_amd64.zip` viaja **intacto**
dentro do `.pyz` como dado bruto — nunca é importado de dentro do zip
(`zipimport` não carrega extensão nativa), só extraído para
`~/.cache/charla/_vendor/<hash>/` e inserido em `sys.path` na primeira vez
que o Adaptador Windows precisa dele (`pycryptodome_carregador.py`).

**O import de `decifra.py` em `cli.py` é lazy, de propósito** — achado real
de execução no Plano 3: import no topo do arquivo forçava `Crypto` a
carregar em **todo** comando, inclusive `conversas` no macOS, e numa
máquina limpa sem `pip install` isso quebrava o `.pyz` inteiro fora do
Windows. `decifrar_bases_da_sessao` só é importado dentro de
`_main_windows()`, mesma fronteira de dependência que `_main_macos` já usa.

Validado de ponta a ponta contra o `.pyz` real, rodado com Python fora do
`.venv` de desenvolvimento (`env -u PYTHONPATH /opt/homebrew/bin/python3.12
dist/charla.pyz ...`), contra o WhatsApp real deste Mac — `conversas`,
`mensagens` e `anexo` os três funcionando, mesmas contagens da validação
do Plano 2. Windows fica como pendência nomeada (não medida nesta sessão).

## Testes

`pytest`, runner canônico `pytest -v` (`.venv/bin/pytest -v` num venv
local). Fixtures sintéticas em `tests/fixtures/` (schema real, dado
inventado) — incluindo o par cifrado/decifrado de
`tests/fixtures/pagina_sintetica_*.bin`, construído algebricamente com
chave conhecida, que é o oráculo de `decrypt_page`. Teste que exige `ctypes` do Windows
(`obter_oduid`, `obter_segredo_de_sessao`) é marcado `windows_real` e pula
explicitamente fora do Windows.

## Estado atual

Plano 1 (Adaptador Windows) e Plano 2 (Adaptador macOS) implementados —
ver `CONTEXTO.md` §Estado Atual para as datas e os links dos planos.
