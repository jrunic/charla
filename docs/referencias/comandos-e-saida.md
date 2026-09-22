---
id: 202609211900
projeto: charla
tipo: referencia
escopo: repo:charla
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Referência exaustiva de sintaxe, schema JSON de saída e códigos de saída do charla — cada comando, cada campo, cada erro nomeado, medido contra o código real.
tags: [referencia, cli, json, exit-code]
---

# charla — comandos, saída e códigos de saída (referência exaustiva)

Este documento é para consulta programática — por um agente que precisa
decidir o próximo passo a partir da saída do `charla`, não para leitura
corrida. Cada afirmação aqui foi medida contra `src/charla/cli.py`,
`src/charla/modelo.py` e os dois Adaptadores, na versão do repositório em
21/09/2026 (Plano 3 concluído). Se o comportamento mudar, este documento
precisa ser atualizado no mesmo commit — é o contrato do `CONTEXTO.md`.

## Invocação

```
charla.pyz <comando> [argumentos]
```

(ou `python3 -m charla <comando> [argumentos]` rodando da fonte, com
`PYTHONPATH=src` ou instalado em modo editável — mesmo comportamento).

Quatro subcomandos existem, sempre os quatro, nas duas plataformas — o que
muda por plataforma é o que cada um FAZ, não quais existem:

| Subcomando | Argumentos | Existe no Windows | Existe no macOS |
|---|---|---|---|
| `conversas` | nenhum | sim | sim |
| `mensagens` | `--conversa <id>` (obrigatório) | sim | sim |
| `anexo` | `<id>` (posicional, obrigatório) + `--destino <caminho>` (**obrigatório no Windows**, opcional no macOS) | sim | sim |
| `habilitar-autor-windows` | nenhum | sim | sim (sempre recusa — ver abaixo) |

`-h`/`--help` funciona em qualquer nível (`charla.pyz -h`, `charla.pyz
anexo -h`, etc.) — saída padrão do `argparse` para humano, `exit=0`, não
JSON. Não conte com o formato dessa saída para parsing automático.

## Toda saída é JSON — mas em canais diferentes conforme sucesso/erro

- **Sucesso** (`exit=0`): o JSON do resultado vai para **stdout**,
  formatado com `indent=2`, `ensure_ascii=False` (caracteres não-ASCII,
  como emoji em nome de grupo, aparecem literais — não escapados
  `\uXXXX`).
- **Erro nomeado** (qualquer `exit` diferente de 0, exceto os erros de uso
  do `argparse` abaixo): o JSON `{"erro": "<mensagem>"}` vai para
  **stderr**, sem `indent` (uma linha).
- **Erro de uso do `argparse`** (`exit=2`): texto de erro do `argparse`
  para **stderr**, **não é JSON** — ver seção "Erros de uso" no final.

Um agente que só lê stdout nunca vê mensagem de erro nomeada; precisa ler
stderr quando `exit != 0`.

## `charla conversas`

**Windows**: lê `genericStorage.db` (decifrado) agrupando por `chatId`;
resolve `nome` de conversa direta via `contacts.db`; resolve `nome` de
grupo via conexão CDP ao WhatsApp em execução (pode não estar disponível —
ver `avisos`).

**macOS**: lê `ChatStorage.sqlite` direto (`ZWACHATSESSION`); `nome` vem
de `ZPARTNERNAME` para todos os tipos, sem passo de resolução separado —
`avisos` nunca aparece neste comando no macOS.

Schema da saída (`stdout`, sucesso):

```json
{
  "conversas": [
    {
      "id": "string",
      "nome": "string ou null",
      "natureza": "string — ver tabela de valores abaixo",
      "total_mensagens": 0,
      "ultima_mensagem_em": 0
    }
  ],
  "avisos": ["string", "..."]
}
```

- `id`: identificador da conversa (formato de JID do WhatsApp — usar
  **literal**, sem transformação, como valor de `--conversa` em
  `mensagens`).
- `nome`: `null` quando não resolvido. No Windows, `null` é comum para
  conversa direta sem contato salvo e para grupo quando a porta de debug
  está fechada (ver `avisos`). No macOS, `null` só ocorre se
  `ZPARTNERNAME` estiver vazio na origem.
- `natureza`: ver "Valores de `natureza`" abaixo — **os valores possíveis
  são diferentes por plataforma**.
- `total_mensagens`: inteiro, contagem de mensagens naquela conversa.
- `ultima_mensagem_em`: timestamp Unix em **segundos** (não milissegundos),
  ou `null` se a conversa nunca teve mensagem com data (não medido
  ocorrer na prática, mas o tipo permite).
- `avisos`: **chave ausente** quando não há aviso (nunca lista vazia) —
  **só existe no Windows**, e só quando havia pelo menos um grupo na saída
  e a resolução de nome via CDP não cobriu todos. Formato exato da
  string, com contagem:
  `"autor/nome de grupo não resolvido — a conexão com o WhatsApp em execução não está disponível. Rode 'charla habilitar-autor-windows' uma vez para habilitar. (N de M grupos com nome resolvido)"`

### Valores de `natureza`

**Windows** (`_natureza()` em `adaptador_windows/leitura.py`) — **dois**
valores possíveis:

| Valor | Critério |
|---|---|
| `"coletiva"` | `id` termina em `@g.us` |
| `"direta"` | qualquer outro sufixo — inclui `@lid`, `@s.whatsapp.net`, e qualquer sufixo não medido (`@broadcast`, status) também cai aqui hoje, sem discriminante próprio (ambiguidade conhecida, não fechada) |

**macOS** (`adaptador_macos/leitura.py`) — **quatro** valores possíveis
(um quinto tipo interno, `status`, nunca aparece — ver nota):

| Valor | Origem (`ZSESSIONTYPE`) |
|---|---|
| `"direta"` | 0 |
| `"grupo"` | 1 |
| `"lista-de-transmissao"` | 2 |
| `"comunidade"` | 4 |

**Nota**: `ZSESSIONTYPE = 3` (status individual por contato — mecanismo
interno de acompanhamento, sem histórico de mensagem trocada) é
**filtrado antes de virar `Conversa`** — nunca aparece na saída de
`conversas` no macOS, por decisão confirmada (não é bug, não é lista
incompleta).

**Um agente que trata `natureza` genericamente (ex.: "é `direta` ou não")
funciona nas duas plataformas. Um agente que distingue `grupo` de
`lista-de-transmissao` de `comunidade` só pode fazer isso no macOS — no
Windows, todos os três caem em `"coletiva"`.**

## `charla mensagens --conversa <id>`

`<id>` é o valor de `id` que veio de `conversas` — literal, sem decodificar
nem alterar.

**Windows**: lê `message` de `genericStorage.db` filtrando por `chatId`,
ordenado por `(timestamp, rowid)`. Autor é resolvido à parte, via CDP
(`resolver_autores`) — pode ficar `null`.

**macOS**: lê `ZWAMESSAGE` filtrando por `ZCHATSESSION`, ordenado por
`ZMESSAGEDATE`. Autor resolvido por SQL direto, sem passo de rede — só
fica `null` quando a mensagem é de sistema (evento sem `ZGROUPMEMBER`, ex.
entrada/saída de membro de grupo).

Schema da saída (`stdout`, sucesso):

```json
{
  "mensagens": [
    {
      "id": "string",
      "conversa_id": "string",
      "texto": "string ou null",
      "instante": 0,
      "autor": "string ou null"
    }
  ],
  "avisos": ["string", "..."]
}
```

- `texto`: `null` para mensagem sem conteúdo textual (ex.: evento de
  sistema no macOS — entrada/saída de membro).
- `instante`: timestamp Unix em segundos.
- `autor`:
  - **Windows**: `null` quando a resolução via CDP não cobriu a mensagem
    (porta fechada, ou mensagem específica não encontrada no runtime).
  - **macOS**: `"eu"` (literal, string fixa) quando a mensagem é do
    próprio usuário (`ZISFROMME=1`); nome do contato ou JID quando é de
    conversa direta; nome do membro do grupo (ou o JID dele, se sem nome
    resolvido) quando é de grupo/lista-de-transmissão/comunidade;
    `null` só para mensagem de sistema sem membro associado.
- `avisos`: mesma regra de ausência-quando-vazio do comando `conversas`.
  **Só existe no Windows.** Formato exato:
  `"autor/nome de grupo não resolvido — a conexão com o WhatsApp em execução não está disponível. Rode 'charla habilitar-autor-windows' uma vez para habilitar. (N de M mensagens com autor resolvido)"`

**Conversa inexistente**: devolve `{"mensagens": []}` — lista vazia, **não
é erro**, `exit=0`. Não há distinção entre "conversa existe e está vazia"
e "conversa não existe" na saída deste comando, nas duas plataformas.

## `charla anexo <id> [--destino <caminho>]`

`<id>` aqui é o identificador do **item de mídia**, não da conversa —
**no Windows é o `rowId` da própria Mensagem** (o mesmo valor de `id`
que `mensagens` já expõe: uma mensagem tem no máximo uma mídia
associada, então não existe um segundo espaço de identificadores); no
macOS é o `Z_PK` de `ZWAMEDIAITEM`. Nas duas plataformas, **não há,
hoje, um caminho documentado para um consumidor externo descobrir esse
id sem consultar `mensagens`/o banco diretamente** — lacuna real,
registrada, não um mecanismo que só não foi escrito ainda.

### `--destino <caminho>`

**Windows**: **obrigatório**. Sem ele, `exit=1`, antes de conectar ao
WhatsApp ou de qualquer trabalho caro:

```json
{"erro": "--destino é obrigatório no Windows — a mídia não existe como arquivo até ser extraída; informe onde salvar."}
```

**macOS**: opcional. Sem ele, comportamento idêntico ao da v0.1.0 — só
`caminho_absoluto` do arquivo original, nada copiado. Com ele, copia o
arquivo para o destino e `caminho_absoluto` na resposta passa a apontar
para a **cópia**, não para o original.

Nas duas plataformas, `--destino` é caminho de **arquivo**, não de
pasta — quem chama escolhe o nome final; o `charla` não inventa nome a
partir de metadado da mídia. Destino inválido recusa com `exit=1` e
mensagem nomeando a causa específica — nunca deixa arquivo truncado ou
parcial no destino:

```json
{"erro": "pasta /caminho/pai não existe"}
```
```json
{"erro": "sem permissão de escrita em /caminho/pai"}
```
```json
{"erro": "destino /caminho é um diretório, não um arquivo"}
```

### Windows — mecanismo e pré-condição

Exige a mesma pré-condição de `mensagens` (porta de debug do WebView2
habilitada — rode `habilitar-autor-windows` uma vez se ainda não
rodou). Metadado de mídia (`directPath`/`mediaKey`/`mimetype`) vem do
runtime JS do WhatsApp em execução, via CDP — **sem abrir a conversa**,
já disponível em memória para toda mensagem de mídia carregada. Os
bytes em si **não** trafegam pelo protocolo de debug: vêm de um
download HTTPS direto contra o CDN do WhatsApp, decifrados localmente
pelo protocolo público de mídia do WhatsApp (o mesmo que
`whatsapp-web.js`/`Baileys` usam). Não roda a cadeia de decifra do
SQLite (`genericStorage.db` etc.) — `anexo` no Windows não abre nenhum
banco.

Mensagens de erro nomeadas específicas do Windows:

```json
{"erro": "conexão com o WhatsApp em execução não está disponível — rode 'charla habilitar-autor-windows' uma vez para habilitar."}
```
```json
{"erro": "a verificação de integridade (MAC) da mídia baixada falhou — a chave pode estar errada, o download veio corrompido, ou o formato do protocolo mudou numa atualização do WhatsApp."}
```

**Residual não medido**: mensagem de mídia fora da janela que o
WhatsApp Web já carregou em memória (conversa nunca aberta na sessão,
histórico muito antigo) devolve `anexo <id> não encontrado` mesmo que
a mídia exista — não confundir com "mídia realmente não existe".
Só `image` foi verificada de ponta a ponta contra bytes reais;
`video`/`audio`/`document` usam o mesmo algoritmo documentado, não
testados contra arquivo real.

### macOS — mecanismo

Lê `ZWAMEDIAITEM` por `Z_PK`, resolve caminho contra
`<GroupContainer>/Message/`. Schema da saída (`stdout`, sucesso):

```json
{
  "anexo": {
    "id": "string",
    "conversa_id": "string",
    "tipo": "imagem | documento | audio | desconhecido",
    "caminho_absoluto": "string — path absoluto no disco, não os bytes"
  }
}
```

- `tipo`: mapeado de `ZWAMESSAGE.ZMESSAGETYPE` — só 3 códigos têm nome
  confirmado por medição (1=`imagem`, 8=`documento`, 3=`audio`); **todo
  outro código** (inclui vídeo, sticker, e códigos de baixo volume não
  classificados) devolve `"desconhecido"` — não adivinhado.
- `caminho_absoluto`: sem `--destino`, aponta para o arquivo original no
  disco (confirmado por validação real, tamanho batendo com
  `ZFILESIZE`). Com `--destino`, aponta para a cópia. O `charla` **não**
  devolve os bytes no corpo da resposta — quem consome abre o arquivo
  pelo caminho.

**`id` inexistente (nas duas plataformas)**: `exit=1`,
`{"erro": "anexo <id> não encontrado"}` em stderr — recusa nomeada, não
stack trace.

## `charla habilitar-autor-windows`

**Windows**: reinicia o WhatsApp Desktop automaticamente (via
`taskkill` + relançamento), gravando uma variável de ambiente que abre uma
porta de debug do WebView2 — necessário **uma vez** para que `mensagens`/
`conversas` resolvam autor/nome de grupo sem `avisos`. Sem argumentos.
Sucesso (`stdout`, `exit=0`):

```json
{"status": "debug habilitado, WhatsApp reiniciado"}
```

Antes do JSON, uma linha informativa vai para **stderr** (não faz parte
do contrato JSON, é aviso para humano):
`"O charla vai reiniciar o WhatsApp Desktop para habilitar a resolução de autor. Isso acontece uma vez só; o WhatsApp volta a abrir sozinho, sem precisar escanear QR de novo."`

**macOS**: **sempre** recusa, `exit=4` — este comando não faz sentido lá
(autor já é resolvido por SQL direto, sem CDP). Mensagem exata:

```json
{"erro": "habilitar-autor-windows só se aplica no Windows — no macOS o autor é resolvido direto por SQL, sem esse passo."}
```

## Tabela completa de código de saída

Todo código que `charla` pode devolver, medido contra `cli.py` (grep
exaustivo de `return <N>`, nenhum código fora desta tabela existe):

| Código | Significado | Quando |
|---|---|---|
| `0` | Sucesso | Comando executou e devolveu resultado sem `"erro"` no JSON |
| `1` | Erro de dado/estado, não de ambiente | `anexo` Windows sem `--destino`, com `--destino` inválido, `id` não encontrado, ou falha de MAC na decifra de mídia; `anexo` macOS com `id` inexistente ou `--destino` inválido; qualquer comando cujo resultado interno já contivesse a chave `"erro"`; qualquer exceção não prevista levantada pelo Adaptador depois de a decifra/localização terem funcionado (banco corrompido, schema divergente numa atualização do WhatsApp) — capturada por um `except Exception` de rede de segurança em `_main_macos`/`_main_windows`, nunca propaga stack trace crua |
| `2` | Erro de uso da CLI (`argparse`) | Comando ausente, comando desconhecido, `--conversa` ausente em `mensagens`, `id` ausente em `anexo` — **não produz JSON**, ver seção seguinte |
| `4` | Ambiente/plataforma não suportada, ou comando não aplicável nesta plataforma | `ArquiteturaNaoSuportada` (Windows: app não é UWP); `ChatStorageNaoEncontrado` (macOS: `ChatStorage.sqlite` ausente); sistema operacional que não é `win32` nem `darwin`; `habilitar-autor-windows` chamado no macOS |
| `5` | Falha na cadeia de decifra (Windows) ou no mecanismo de resolução de autor via CDP (Windows) | Ver lista exaustiva de mensagens abaixo |

**Não existem** os códigos 3, 6, 7 no `charla` — se algum documento
técnico de outro produto da frota (ex. `malote`, que usa 3/6/7 no modo
rede) for consultado por engano, esses códigos **não se aplicam aqui**.

### Mensagens exatas de `exit=5` (só Windows, cadeia de decifra ou CDP)

Cada uma é `RuntimeError` com mensagem nomeada — nenhuma é stack trace
crua. Lista exaustiva, medida por `grep -n "raise RuntimeError"` em
`adaptador_windows/decifra.py` (9 sítios) e `adaptador_windows/autor_cdp.py`
(2 sítios, subclasse `EsperaDeDebugFalhou`), mais o que
`localizar_pasta_de_sessao` (`adaptador_windows/localizacao.py`) levanta —
**12 mensagens ao todo**. A primeira lista desta seção (medida em
21/09/2026) tinha 9 e faltavam justamente as três dos dois primeiros
passos da cadeia (ODUID, segredo de sessão) — achado da revisão
independente da documentação; corrigido aqui. Ordem abaixo segue a ordem
de execução real de `decifrar_bases_da_sessao`:

1. **`.db-wal` ausente** (qualquer uma das 4 bases — session, nativeSettings, genericStorage, contacts): `"<nome>.db-wal ausente — o WhatsApp precisa estar aberto e ter escrito nessa base para a cadeia de decifra funcionar (distinto de schema incompatível)."`
2. **`.db-wal` menor que 32 bytes** (qualquer uma das 4 bases): `"<nome>.db-wal existe mas tem só N bytes — menor que o header do formato WAL (32 bytes). Pode ter sido consolidado (checkpoint) no meio da leitura; tente de novo."`
3. **`.db` principal ausente** (qualquer uma das 4 bases): `"<nome>.db ausente em <pasta> — a instalação do WhatsApp Desktop parece incompleta ou corrompida."`
4. **Passo 2 (segredo de sessão), `NCryptCreateProtectionDescriptor` falhou**: `"NCryptCreateProtectionDescriptor falhou"`
5. **Passo 2 (segredo de sessão), `NCryptProtectSecret` falhou**: `"NCryptProtectSecret falhou"`
6. **Nenhuma `client_key` carveada do WAL de sessão**: `"Nenhuma client_key encontrada no WAL de session.db — reinicie o WhatsApp Desktop e tente de novo."`
7. **Pasta de sessão (derivada de `SHA1(client_key)`) não existe** — o oráculo de validação de chave rejeitou: `"A pasta de sessão derivada de SHA1(client_key) (<hash>) não existe em <pasta>/sessions — a chave carveada não bate com nenhuma sessão real. A cadeia pode ter quebrado numa atualização do WhatsApp."`
8. **Passo 1 (ODUID), `GetOfflineDeviceUniqueID` falhou**: `"GetOfflineDeviceUniqueID falhou: código <res>"`
9. **Carving de `nativeSettings.db-wal` não achou os dois tipos de chave esperados**: `"O carving de nativeSettings.db-wal não encontrou os tipos de chave esperados (precisa de 1 e 2; achou [...]). O formato pode ter mudado numa atualização do WhatsApp, ou o WAL foi consolidado (checkpoint) antes da leitura — reinicie o WhatsApp Desktop e tente de novo."`
10. **Chave decifrada não começa com o magic number do SQLite** (a chave carveada era plausível e errada — checado para as 3 bases que dependem de carving: nativeSettings, genericStorage, contacts): `"<nome>.dec.db não começa com o cabeçalho SQLite depois de decifrado — a chave usada para <base> está errada. O carving pode ter devolvido uma chave plausível e errada; reinicie o WhatsApp Desktop e tente de novo."`
11. **`habilitar-autor-windows`: registro do Windows recusou a escrita**: `"não consegui gravar a porta de debug no registro do Windows (HKCU\\Environment) — verifique permissão de escrita na própria conta de usuário."`
12. **`habilitar-autor-windows`: porta de debug nunca abriu após reiniciar** (15 tentativas, 1s de intervalo — ~15s de espera): `"a porta de debug 9222 não abriu depois de reiniciar o WhatsApp — pode ser sessão SSH não-interativa (a variável precisa ser definida numa sessão de console real, não remota) ou o app não ter relançado. Tente reiniciar o WhatsApp manualmente."`

Todas têm em comum: a causa nomeada de forma específica o bastante para
saber se vale tentar de novo (a maioria sugere "reinicie o WhatsApp
Desktop e tente de novo") ou se é permanente (permissão de registro,
instalação incompleta, falha de DLL do sistema nos itens 4/5/8).

### Erros de uso (`exit=2`) — não são JSON

Saída do `argparse` da stdlib, sempre em duas linhas no stderr: uma linha
`usage: ...` e uma linha `charla[ <subcomando>]: error: <causa>`. Três
casos medidos:

```
$ charla.pyz
usage: charla [-h] {conversas,mensagens,anexo,habilitar-autor-windows} ...
charla: error: the following arguments are required: comando
```

```
$ charla.pyz foobar
usage: charla [-h] {conversas,mensagens,anexo,habilitar-autor-windows} ...
charla: error: argument comando: invalid choice: 'foobar' (choose from conversas, mensagens, anexo, habilitar-autor-windows)
```

```
$ charla.pyz mensagens
usage: charla mensagens [-h] --conversa CONVERSA
charla mensagens: error: the following arguments are required: --conversa
```

Um agente que precisa distinguir "erro de uso" de "erro de execução" pode
usar `exit == 2` **e** "a saída não é JSON válido" como sinal duplo — os
dois coincidem sempre, medido.

## Contrato de codificação da saída

`sys.stdout`/`sys.stderr` são reconfigurados para UTF-8 explicitamente no
início de `main()` — nome de conversa/grupo com emoji ou caractere fora de
ASCII aparece literal no JSON (`ensure_ascii=False`), nas duas plataformas.
Achado real que motivou isso: o console do Windows abre em `cp1252` por
padrão, e sem essa reconfiguração o comando quebrava com
`UnicodeEncodeError` depois de já ter decifrado e lido os dados.

## Referências

- [[../arquitetura.md]] — mapa estrutural do repo
- [[../../CONTEXTO.md]] — padrões técnicos e histórico de achados reais
- Documentos técnicos de medição do schema macOS e Windows — internos do
  autor, fora deste repositório
