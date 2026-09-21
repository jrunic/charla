---
id: 202609211905
projeto: charla
tipo: tutorial
escopo: repo:charla
plataforma: "*"
status: ativo
dominios: [tecnologia]
descricao: Passo a passo completo do primeiro uso do charla, para as duas plataformas — pensado para ser seguido por um agente sem intervenção humana.
tags: [tutorial, primeiro-uso, cli]
---

# charla — primeiro uso, passo a passo completo

Este tutorial cobre a sequência inteira, do zero até ler uma mensagem e um
anexo de verdade. Ele é escrito para ser seguido **por um agente**, sem
depender de o humano completar nenhum passo implícito — cada passo diz o
comando exato, o que esperar, e o que fazer se a saída for diferente do
esperado. Vocabulário de saída (schema JSON, códigos de saída, mensagens
de erro) está todo em `docs/referencias/comandos-e-saida.md` — este
tutorial referencia aquele documento em vez de repetir, mas nomeia cada
decisão que depende dele.

## Pré-requisitos (checar antes do Passo 1)

1. **WhatsApp Desktop instalado, logado, e aberto pelo menos uma vez**
   nesta máquina — nas duas plataformas o `charla` lê o que o app já
   gravou, nunca inicia sessão nova.
   - No macOS, confirmar que o arquivo existe:
     `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`
   - No Windows, o `charla` detecta sozinho (Passo 1) — não precisa
     checar antes.
2. **Python 3.12 ou mais novo, já instalado**, fora de qualquer ambiente
   virtual do `charla` — o `.pyz` não precisa de `pip install` nem de
   `venv`, mas precisa de um interpretador Python real no sistema.
   Confirmar com `python3 --version` (ou `python --version` no Windows).
3. **`charla.pyz` em algum caminho conhecido** — este tutorial usa
   `charla.pyz` relativo ao diretório atual; substituir pelo caminho real
   se estiver em outro lugar.

Se qualquer pré-requisito falhar, **parar aqui** e resolver antes — os
passos seguintes presumem que os três estão satisfeitos.

## Passo 1 — Primeira chamada: listar conversas

```
python3 charla.pyz conversas
```

**Resultado esperado**: `exit=0`, JSON no stdout com a chave `conversas`
(lista, possivelmente longa — centenas de entradas é normal). Cada item
tem `id`, `nome`, `natureza`, `total_mensagens`, `ultima_mensagem_em`
(schema completo: `comandos-e-saida.md` → `charla conversas`).

**Se `exit != 0`**: ler o JSON de **stderr** (não stdout — a saída de
erro vai para outro canal), e resolver pela causa antes de continuar:

| Situação medida | Causa provável | Ação |
|---|---|---|
| `exit=4`, menciona "UWP não encontrado" | Windows: WhatsApp instalado não é a versão da Microsoft Store | Fora de escopo desta versão do `charla` — parar, reportar ao humano |
| `exit=4`, menciona "ChatStorage.sqlite não encontrado" | macOS: WhatsApp Desktop não está instalado/logado | Voltar ao pré-requisito 1 |
| `exit=4`, menciona "sistema operacional não suportado" | Rodando em Linux ou outro SO | Fora de escopo — o `charla` só suporta Windows e macOS |
| `exit=5` | Windows: falha na cadeia de decifra (várias causas nomeadas, lista completa em `comandos-e-saida.md`) | A maioria das mensagens sugere "reinicie o WhatsApp Desktop e tente de novo" — fazer isso uma vez antes de escalar |
| `exit=2`, saída não é JSON | Erro de sintaxe do próprio comando (não deveria acontecer seguindo este tutorial ao pé da letra) | Conferir se o comando foi digitado exatamente como acima |

Se `avisos` aparecer no JSON de sucesso (só acontece no Windows — ver
Passo 3), **não é erro** — anotar e seguir; será resolvido no Passo 3 se
for necessário.

## Passo 2 — Escolher uma conversa e ler as mensagens

Do resultado do Passo 1, escolher um `id` de uma conversa com
`total_mensagens > 0` (conversa vazia devolve lista vazia, não é erro, mas
não serve para testar o fluxo completo). Copiar o valor de `id`
**literalmente** — é um JID do WhatsApp, não transformar.

```
python3 charla.pyz mensagens --conversa "<id copiado>"
```

(usar aspas em volta do valor — `id` de conversa direta pode conter `@` e
outros caracteres que alguns shells interpretam.)

**Resultado esperado**: `exit=0`, JSON no stdout com a chave `mensagens`
(lista, ordenada cronologicamente). Cada item tem `id`, `conversa_id`,
`texto`, `instante`, `autor` (schema completo: `comandos-e-saida.md` →
`charla mensagens`).

**Casos a checar na saída**, antes de seguir para o Passo 3:

- **Lista vazia** (`{"mensagens": []}`, `exit=0`): não é erro — pode ser
  `id` de uma conversa que existe mas nunca teve mensagem escrita, ou
  `id` que não corresponde a nenhuma conversa (as duas situações são
  indistinguíveis nesta saída, medido). Se o `total_mensagens` do Passo 1
  era `> 0` para este `id`, algo está errado — reconferir o `id` copiado.
- **Algum `autor` é `null`**: no macOS, isso só acontece em mensagem de
  sistema (raro, esperado). **No Windows, é comum** e tem resolução — ver
  Passo 3.
- **Campo `avisos` presente**: **só no Windows**. Segue para o Passo 3.

Se `avisos` **não** apareceu (garantido no macOS; comum no Windows quando
`habilitar-autor-windows` já rodou antes), **pular o Passo 3** e ir direto
ao Passo 4.

## Passo 3 — Windows apenas: habilitar resolução de autor

Este passo **só se aplica se**: a plataforma é Windows **e** o Passo 1 ou
2 trouxe `avisos` no JSON, ou algum `autor`/`nome` de grupo veio `null`
sem explicação óbvia.

**No macOS, este comando sempre recusa** (`exit=4`, mensagem "só se aplica
no Windows") — não rodar este passo no macOS; se `avisos` nunca apareceu
no Passo 1/2, o autor já está resolvido por desenho, não há passo extra.

```
python3 charla.pyz habilitar-autor-windows
```

**O que este comando faz de fato** (para o agente saber o que esperar,
não só o resultado): reinicia o WhatsApp Desktop automaticamente — mata o
processo e relança pelo próprio sistema, **uma vez**. Não precisa
escanear QR de novo. Antes do JSON de resultado, uma linha informativa
sai em stderr avisando disso — não é erro, é aviso para quem está
acompanhando.

**Resultado esperado**: `exit=0`,
`{"status": "debug habilitado, WhatsApp reiniciado"}` no stdout. Leva
alguns segundos (o comando espera até ~15s pela porta de debug abrir após
o relançamento).

**Se `exit=5`**: duas mensagens possíveis (texto exato em
`comandos-e-saida.md`) — registro do Windows recusou escrita (checar
permissão da conta de usuário), ou a porta nunca abriu (rodar numa sessão
de console real, não numa sessão SSH não-interativa — medido que isso
falha silenciosamente por design do Windows, não é bug do `charla`).

**Depois deste comando rodar com sucesso, repetir o Passo 2** — a mesma
chamada a `mensagens` deve vir sem `avisos` e com `autor` resolvido
(exceto os `null` residuais que o CDP não cobrir — não é garantido 100%,
mas deve melhorar).

## Passo 4 — Ler um anexo (se houver mídia na conversa)

**No Windows, este comando sempre recusa hoje** — `exit=1`, mensagem fixa
dizendo que mídia não está implementada nesta plataforma (motivo medido
em `comandos-e-saida.md`). Não é erro de uso, é limitação conhecida —
**pular este passo inteiro no Windows**.

**No macOS**: funciona, mas exige um `id` de item de mídia que **não vem
exposto em nenhuma saída anterior** (lacuna real, documentada em
`comandos-e-saida.md` → `charla anexo`) — não há, hoje, um caminho
padrão para um agente descobrir esse `id` só a partir de `conversas`/
`mensagens`. Se o objetivo é só validar que o comando funciona, qualquer
`id` numérico serve para exercitar o caminho de erro:

```
python3 charla.pyz anexo "999999999"
```

**Resultado esperado** (id inexistente, caso comum de teste): `exit=1`,
`{"erro": "anexo 999999999 não encontrado"}` em stderr — recusa nomeada,
não stack trace. Se por acaso o `id` escolhido existir de verdade,
`exit=0` com `{"anexo": {...}}` no stdout, `tipo` em
`imagem`/`documento`/`audio`/`desconhecido`, e `caminho_absoluto`
apontando para um arquivo real no disco.

## Resumo do fluxo completo

```
conversas
  │
  ├─ escolhe id com total_mensagens > 0
  │
mensagens --conversa <id>
  │
  ├─ avisos presente? (só Windows)
  │     sim → habilitar-autor-windows → repetir mensagens
  │     não → segue
  │
anexo <id-de-midia>          (macOS: funciona · Windows: sempre recusa, pular)
```

Os quatro comandos existem nas duas plataformas; o que muda é o
comportamento de cada um — nunca presumir que o comportamento do Windows
vale no macOS ou vice-versa sem checar `comandos-e-saida.md`.

## Referências

- `docs/referencias/comandos-e-saida.md` — schema completo, toda mensagem
  de erro, tabela de códigos de saída
- `docs/arquitetura.md` — mapa estrutural do repo
- `README.md` — resumo curto, para leitura humana rápida
