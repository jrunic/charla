---
id: 202609201033
projeto: charla
tipo: index
escopo: repo:charla
plataforma: "*"
status: ativo
descricao: Padrões técnicos canônicos e restrições do repo charla — carga default da sessão.
tags: [contexto, dev-skills, Python]
---

# CONTEXTO.md — charla

## Propósito

CLI local que lê diretamente os bancos de dados do WhatsApp Desktop (Windows e
macOS) na máquina do usuário, sem servidor, sem captura ativa e sem cifra de
terceiro a resolver — só torna consultável o que o app oficial já grava. Dá a
mentorados sem infraestrutura própria a mesma capacidade que o `malote` dá a
quem tem host 24/7: um agente com acesso ao próprio histórico de conversas.

## Agente padrão

**Tech** (SRE Agentic) — guardião deste repositório. Modo de atuação: Código + SRE Agentic
(Autocura Assistida). Outros agentes podem ler/contribuir; mudanças estruturais passam por Tech.

## Stack

- **Linguagem:** Python 3.12+, **stdlib-only em CÓDIGO PRÓPRIO** — mesma
  filosofia do `koine` (produto irmão na mesma frota, mesma razão de existir:
  mentorado já tem Python instalado por causa dele). `ctypes` (stdlib) cobre
  `clipc.dll`/`ncrypt.dll`. **Exceção decidida no Plano 1 (20/09/2026,
  revista por medição — `pyaes` puro-Python media 274x mais lento que o
  teto de usabilidade, 129s contra 0,47s para decifrar 57MB):**
  `pycryptodome` (componente nativo, `.pyd` no Windows) entra vendorizado
  como **dado bruto** dentro do pacote/`.pyz` — não importável de dentro do
  zip (medido: `zipimport` não carrega extensão nativa), extraído para
  `~/.cache/charla/_vendor/` no primeiro uso no Windows. Só o wheel
  `win_amd64` — o Adaptador macOS não usa AES. ADR:
  `docs/decisoes/20260920-vendoriza-pycryptodome-para-decifra-windows.md`.
- **Banco:** nenhum próprio — lê os bancos SQLite/cifrados que o WhatsApp
  Desktop já grava na máquina do usuário; sem Acervo persistido (ver spec v1)
- **Distribuição:** **zipapp** (`charla.pyz`), no molde do `koine.pyz` — o
  mentorado roda `python3 charla.pyz conversas`, sem `pip install`, sem
  ambiente virtual, sem resolução de dependência na máquina de destino.
  `pycryptodome` (ver Linguagem, acima) e `websocket-client` (pura Python,
  cliente CDP) entram vendorizados no `.pyz` — `websocket-client` por cópia
  direta (`src/charla/_vendor/websocket/`, sem mecanismo de extração,
  porque é puro Python), `dependencies = []` no `pyproject.toml`. Fechado
  no Plano 1 (achado `bloqueia` "websocket-client sem ADR" da revisão
  dev-10, 2ª rodada).
- **Deploy:** nenhum — CLI local, invocada sob demanda. Sem servidor, sem
  serviço, sem cron, sem frota.
- **Decisão registrada em ADR local**: `docs/decisoes/20260920-charla-em-python-com-distribuicao-zipapp.md`
  — Python (não Node) e zipapp (não npm/PyPI) foram escolhas com alternativa
  real rejeitada, não convenção óbvia.

## Padrões Técnicos

### Naming

Estilo pela convenção da comunidade Python (PEP 8); **vocabulário pelo
`GLOSSARIO.md`** (a criar quando o primeiro termo for resolvido — reaproveita
vocabulário do `malote` como conhecimento, sem importar o pacote):

- **Arquivos e módulos:** `snake_case.py`
- **Funções e variáveis:** `snake_case`
- **Classes:** `PascalCase`
- **Constantes:** `UPPER_SNAKE`

Termo de domínio no código é o termo do glossário, em pt-BR (`Conversa`,
`Mensagem`, `Anexo`) — sem acento em identificador. Fora do domínio, vale o
inglês da comunidade.

### Linguagem

- **Nome do repo e do binário:** `charla` — nome comercial próprio, sem
  prefixo de organização nem de ferramenta interna (mesma audiência do
  `malote`; ADR `20260808-naming-por-audiencia-do-artefato`)
- **Identificadores no código:** termo de domínio em pt-BR pelo glossário; o
  resto em inglês
- **Comentários inline:** pt-BR
- **Documentação:** pt-BR
- **Commits:** tipo conventional em inglês (`feat:`, `fix:`...), descrição em
  pt-BR

### Segredos

- **Onde:** `.env` local, nunca commitado, com `.env.example` versionado.
  A v1 não tem credencial de rede nem serviço externo (sem modo rede, sem
  Chave de Acesso); `.env` só entra se alguma configuração local emergir no
  plano (ex.: caminho customizado do WhatsApp Desktop)

### Bibliotecas

- **Política:** requer ADR — reforçada pela filosofia stdlib-only do `koine`:
  dependência externa é exceção que se vendoriza, não hábito. Repo nasce
  privado mas pode ir a público (mesmo caminho do malote); dependência nova
  entra com justificativa em `docs/decisoes/`
- **Atuais:** nenhuma ainda — o código nasce no Plano 0/1 (spec v1, documento
  interno do autor, fora deste repositório).
  Sabida como necessária: implementação de AES-OFB para a cadeia Windows
  (`pycryptodome` no protótipo já provado, a vendorizar) — `ctypes` para
  `clipc.dll`/`ncrypt.dll` já é stdlib, zero porte

### Estrutura

```
CONTEXTO.md GLOSSARIO.md — contratos vivos (raiz)
docs/arquitetura.md — mapa fino
docs/decisoes/  — ADRs locais
docs/dominio/   — modelo de domínio (neg-02)
docs/{tutoriais,guias,referencias,explicacoes}/ — quadrantes Diátaxis (ADR 20260620)

src/charla/  — pacote da aplicação: núcleo agnóstico de SO (modelo.py) + um
               pacote Adaptador por plataforma (adaptador_windows/, com
               localizacao.py/decifra.py/sessao_temporaria.py/leitura.py/
               autor_cdp.py/ambiente_windows.py — não um arquivo único; o
               Adaptador macOS nasce no Plano 2) + _vendor/ para dependência
               vendorizada — mesmo espírito do koine, layout adaptado ao
               tamanho real de cada adaptador
tests/       — pytest, `test_*.py`
```

### Testes

- **Framework:** pytest
- **Pasta:** `tests/`, arquivos `test_*.py`
- **Runner canônico:** `pytest` (ou `python -m pytest` se `.venv` não estiver
  no PATH)

### Build/Run

- **Setup:** `pip install -e '.[dev]'` — aspas simples obrigatórias: sem
  elas o zsh tenta globar `[dev]` e falha com `no matches found` (medido).
  Ambiente de desenvolvimento; a distribuição final não usa `pip install`
  (ver Stack)
- **Testes:** `pytest`
- **Run (dev):** `python -m charla <comando>`
- **Build (release):** empacotar `charla.pyz` — mecanismo exato a definir no
  plano de distribuição, no molde do `release.yml` do koine (GitHub Actions:
  pytest → build do zip → publicação em GitHub Releases)

### Lint/Format

- **Lint + Format:** `ruff`

## Onde o trabalho acontece

**Pasta de trabalho:** `13-processos/manter-malote` — é lá que a sessão abre.

| Artefato | Lar canônico |
|---|---|
| Roadmap de ciclos (`roadmap.md`) | pasta de trabalho |
| Spec, plano, arquivo de apoio | pasta de trabalho, em `11-tarefas/` |
| Diário de sessão | pasta de trabalho, em `91-diario/` |
| Discussão de negócio, issue | pasta de trabalho |
| **Código, testes, migrations** | **este repo** |
| **Documentação do produto** (Diátaxis) | **este repo**, `docs/` |
| **Modelo de domínio, GLOSSARIO.md** | **este repo** |
| **ADR de contrato da ferramenta** | **este repo**, `docs/decisoes/` |
| **README, CHANGELOG** | **este repo** |

**As skills leem esta seção** em vez de inferir. Repo que não declara deixa a
skill sem informação, e sem informação ela erra.

Escrever o eco no CONTEXTO.md da pasta de trabalho, apontando de volta para este
repo — os dois se referenciam.

## Leitura obrigatória antes de spec/plano

- `docs/arquitetura.md` — mapa estrutural
- `GLOSSARIO.md` — vocabulário do domínio (usar estes termos, nunca sinônimos)
- `docs/dominio/` — modelo formal dos contextos que o trabalho toca
- `roadmap.md` da pasta de trabalho — incremento ativo e fronteiras (contrato
  do Passo 0 do dev-02; ainda não existe — nasce da spec v1 quando o Passo 0
  do próximo `dev-02`/`dev-03` rodar)

## Restrições

Hard limits sempre relevantes durante a sessão (ADR `20260609-eliminacao-do-84-ia.md` — substitui antigo `docs/84-ia/restricoes.md`).

- **Runner de testes canônico:** `pytest`
- **Idioma da saída para humano:** pt-BR
- **Comentários inline:** pt-BR
- **Nome do repo e do binário:** `charla`, nome comercial próprio, sem
  prefixo de organização nem de ferramenta interna
- **Nada neste repo nomeia pessoa real, cliente, host ou caminho de máquina
  do autor** — em código, fixture, comentário, exemplo e mensagem de commit.
  Dado de exemplo é sintético (mesma disciplina do `malote`). **Sem
  exceção:** `tests/fixtures/pagina_sintetica_genericstorage_cifrada.bin`
  e `..._decifrada.bin` (Plano 1, Task 4) eram um par de página REAL,
  capturado de uma instalação Windows real de teste, até 21/09/2026 —
  substituído por um par sintético construído algebricamente com chave
  conhecida (mesma técnica de `_cifrar_arquivo_para_teste` em
  `tests/test_decifra.py`), antes da abertura pública do repositório.
  Motivo original da exceção (ainda válido, mas não mais exige dado real):
  `decrypt_page` não é involução (o IV depende dos últimos 12 bytes da
  própria entrada), então o oráculo de teste não pode ser a função
  aplicada sobre si mesma — a construção algébrica resolve isso sem
  precisar de captura real. Medido antes de decidir pela troca: a página
  real tinha 4068 de 4096 bytes zerados e zero strings legíveis (nem em
  tamanho 4) — o risco concreto era baixo, mas a decisão foi não versionar
  nenhum byte de conta real de qualquer forma. `.gitignore` do repo
  protege `tests/fixtures/*.bin` com exceção nomeada, para a próxima
  fixture binária não entrar por descuido.
- **Sem persistência própria de longo prazo, e sem persistência intermediária
  além da execução do comando.** O `charla` não acumula um Acervo (decisão da
  spec v1) — nenhum banco decifrado sobrevive em disco além do comando que o
  gerou
- **Sem modo rede, sem servidor, sem Chave de Acesso** — o `charla` roda
  sempre na mesma máquina que o WhatsApp Desktop, single-user, por desenho.
  Qualquer proposta de superfície de rede é mudança de escopo, não extensão
  natural
- **Risco de engenharia reversa no Adaptador Windows é herdado e nomeado,
  nunca escondido** — a cadeia de decifra do Windows não é documentada pela
  Microsoft nem pelo WhatsApp; quebra sem aviso em atualização do app. ADR
  local registra qual versão do WhatsApp Desktop foi validada, no molde da
  ADR `20260824-adocao-de-biblioteca-nao-oficial-para-recepcao-ao-vivo` do
  `malote` — a nascer quando o Adaptador Windows for escrito (Plano 1)
- **Implementação que contradiz `docs/dominio/` ou `GLOSSARIO.md` atualiza o doc no mesmo commit;** divergência que vira decisão arquitetural → dev-07-cria-adr (ADR `20260705-familia-neg-skills-negocio`)


## Decisões Herdadas (explícitas)

Repetidas aqui mesmo presentes em AMBIENTE.md / USUARIO.md / AGENTE.md, para evitar herança implícita:

- Kebab-case em paths + comentários em pt-BR (AMBIENTE.md global)
- Python 3.12 / Node 22 LTS pinados; sem `.python-version` ou `.nvmrc` (ADR `20260511-versoes-fixas-runtime-frota`)
- Segredos OAuth em jedi-secrets (ADR `20260510-oauth2-google-credenciais-infra-jedi-secrets`)
- Sem comandos git destrutivos sem confirmação; hook `dev-20-bloqueia-comandos-perigosos` em produção
- Ferramentas canônicas vencem APIs diretas (ADR `ferramentas-canonicas.md`)
- Padrão Ação Documentada para destrutivos (ADR `padrao-acao-documentada.md`)
- Infra genérica antes do tenant específico (ADR `infra-generica-antes-do-tenant-especifico.md`)
- Conhecimento destilado em `docs/`; restrições em `CONTEXTO.md` (ADR `20260609-eliminacao-do-84-ia.md`)

## Decisões Locais Divergentes

- **Não pina versão de Python**, ao contrário da regra herdada acima (Python
  3.12 pinado). O contrato é **piso** (`3.12+`), não pinagem — mesmo
  precedente do `koine` e mesma razão do `malote` para Node: produto que roda
  na máquina de terceiro (aqui, o mentorado) não amarra a versão exata de
  quem o escreveu.
- **Python em vez de Node/TypeScript** — divergência da stack que o `malote`
  (produto irmão) usa. Decisão com alternativa real rejeitada (Node foi a
  escolha inicial desta spec, revertida em 20/09/2026): o motivo é o
  `koine` já exigir Python no ambiente do mentorado, tornando Python a
  escolha que não introduz uma segunda linguagem/runtime a instalar. ADR
  local: `docs/decisoes/20260920-charla-em-python-com-distribuicao-zipapp.md`.
- **Distribuição por zipapp, não por gerenciador de pacote** (nem `npm`, nem
  `pip`/PyPI) — mesmo ADR acima. Elimina a etapa de instalação inteira: o
  mentorado só precisa do `.pyz` e do Python que já tem.
- **Sem prefixo de organização no repo e no binário** — a audiência externa
  define a convenção (ADR `20260808-naming-por-audiencia-do-artefato`).

## Estado Atual

- 2026-09-21 — **Revisão independente da documentação exaustiva achou dois
  defeitos reais de código, ambos corrigidos.** `advisor` seguiu
  indisponível; substituído pelo mesmo padrão de `dev-10-revisa-artefato`
  já usado nos Planos 1-3 — Agent sem contexto da sessão, medindo contra o
  código real. Achados `bloqueia`: (1) `_main_macos` só capturava
  `ValueError`, `_main_windows` só capturava `RuntimeError` da cadeia de
  decifra — qualquer outra exceção do Adaptador (banco corrompido, schema
  divergente numa atualização do WhatsApp) escapava com stack trace crua,
  contradizendo a promessa do documento de que "exit==2 + saída não-JSON"
  é o único caso de saída não-JSON. Corrigido: alargado para `Exception`
  nos dois pontos de dispatch, TDD com reprodução real do bug (banco
  corrompido de verdade, `RuntimeError` de schema) antes do fix. (2) a
  lista de mensagens de `exit=5` dizia "exaustiva" com 9 itens — faltavam
  3 (`GetOfflineDeviceUniqueID`, `NCryptCreateProtectionDescriptor`,
  `NCryptProtectSecret`, passos 1 e 2 da cadeia), achadas por
  `grep -n "raise RuntimeError"` nos dois arquivos; lista renumerada para
  12 itens na ordem real de execução. Achado `ajusta`: `visao-geral.md`
  lia como se `anexo` só existisse no macOS — corrigido para "funciona no
  macOS, sempre recusa no Windows". Suíte: **59 passed + 1 skip** (2 testes
  novos, um por plataforma, reproduzindo o bug antes do fix).
- 2026-09-21 — **Documentação Diátaxis exaustiva para consumo por agente:
  `docs/referencias/comandos-e-saida.md` e `docs/tutoriais/primeiro-uso.md`.**
  Pedido explícito: quem consome tutorial/referência são os
  agentes dos mentorados, não humanos — cobertura exaustiva de sintaxe e
  schema, medida contra o código real, não presumida. Referência: schema
  JSON campo a campo dos 4 comandos; os valores de `natureza` **divergem
  por plataforma** (Windows: 2 valores; macOS: 4) — documentado lado a
  lado para não presumir paridade; as 12 mensagens exatas de `exit=5` da
  cadeia de decifra Windows (revisadas em 21/09/2026, ver entrada abaixo);
  tabela completa de código de saída
  (0/1/2/4/5 — confirmado por grep exaustivo, nenhum outro existe).
  Tutorial: passo a passo com tabela causa→ação por código de saída em
  cada passo, pensado para ser seguido sem intervenção humana. **Dois
  achados reais, corrigidos no caminho, medindo o código antes de
  documentar** (nenhum dos dois tinha teste antes): (1) `ler_anexo` do
  Adaptador macOS levantava `ValueError` sem tratamento quando o `id` não
  existia — stack trace crua, violava o critério 13 da spec; corrigido
  para `{"erro": ...}` JSON limpo. (2) **O mais grave**: o `.pyz`
  distribuído sempre saía com `exit=0`, mesmo em erro —
  `zipapp.create_archive(main="charla.cli:main")` gera um `__main__.py`
  que descarta o valor de retorno de `main()`, quebrando os critérios
  4/6/7/13 da spec especificamente no artefato distribuído (rodando
  `python -m charla` da fonte o exit code sempre esteve certo, porque
  `src/charla/__main__.py` já fazia `raise SystemExit(main())`).
  Corrigido: `build-pyz.py` escreve seu próprio `__main__.py` (idêntico
  ao da fonte) em vez de usar `main=`. Suíte: **57 passed + 1 skip**,
  `ruff check` limpo. `docs/explicacoes/visao-geral.md` também preenchido
  (era placeholder do bootstrap com `tags: [..., Node]` residual).
- 2026-09-21 — **Plano 3 (Empacotamento `.pyz` + documentação de usuário)
  implementado, TDD inline, 6 tasks.** Revisado por Agent independente sem
  contexto da sessão (2 achados `bloqueia` e 1 `ajusta`, todos aplicados
  antes da execução — plano completo em documento interno do autor, fora
  deste repositório).
  `scripts/build-pyz.py` monta `dist/charla.pyz` via `zipapp` da stdlib
  (precedente `koine.pyz`). **Achado real
  corrigido no caminho, o mais importante desta rodada**: `cli.py`
  importava `decifrar_bases_da_sessao` de `adaptador_windows.decifra` no
  **topo do arquivo**, e `decifra.py` faz `from Crypto.Cipher import AES`
  incondicionalmente fora do Windows — todo comando, inclusive `conversas`
  no macOS, forçava o carregamento de `Crypto`. Rodando o `.pyz` de
  verdade numa máquina sem `pip install` (o próprio requisito do critério
  14), isso quebrava com `ModuleNotFoundError`, medido: reproduzido com
  `env -u PYTHONPATH /opt/homebrew/bin/python3.12 dist/charla.pyz
  conversas` antes da correção (`exit=1`), corrigido depois (`exit=0`,
  0,13s). Fix: import de `decifra.py` virou lazy dentro de
  `_main_windows()`, mesma fronteira de dependência que `_main_macos` já
  usa. Um segundo achado, causado pela própria correção: rodar só
  `tests/test_cli.py` isolado expunha um bug de ordem de import nos dois
  testes que mockam `sys.platform="win32"` — corrigido importando
  `decifra.py` explicitamente antes do mock, nos dois testes, travando o
  módulo no ramo seguro independente da ordem de coleta do pytest (medido
  com a suíte isolada e com a ordem invertida). **Validação real via o
  `.pyz` de verdade**, Python fora do `.venv` de desenvolvimento, contra
  o WhatsApp real deste Mac: `conversas` (1.219, mesmas contagens),
  `mensagens` (8 mensagens, autor resolvido) e `anexo` (arquivo real no
  disco) — os três funcionando pelo artefato distribuível, não só por
  `python -m charla`. `README.md` reescrito (era o placeholder do
  bootstrap, com `tags: [readme, Node]` residual da decisão de stack
  revertida). Suíte: **55 passed + 1 skip**, `ruff check` limpo.
  **Windows fica como pendência nomeada** — validar o `.pyz` de verdade
  contra uma máquina Windows real exige provisionar uma de novo; decisão
  de se/quando rodar, não bloqueia este plano.
- 2026-09-21 — **Plano 2 (Adaptador macOS) implementado, TDD inline, 8
  tasks.** Revisado por Agent independente sem contexto da sessão (3
  achados `bloqueia` e 2 `ajusta`, todos aplicados antes da execução —
  plano completo em documento interno do autor, fora deste repositório).
  Leitura direta via `sqlite3` `mode=ro` no `ChatStorage.sqlite` original
  (medido: `VACUUM INTO` estoura o teto de performance do critério 8 —
  11,3s contra 65ms-1,78s do `mode=ro`), sem decifra, sem diretório
  temporário. Natureza dos 5 valores de `ZSESSIONTYPE` (direta/grupo/
  lista-de-transmissao/comunidade nomeados; status excluído — decisão
  confirmada, spec critério 8 atualizada). Autor por 3 ramos
  (`ZISFROMME`/parceiro direto/`ZGROUPMEMBER` — achado real: `ZFROMJID` é
  constante em mensagem de grupo, quem dá o remetente é o FK
  `ZGROUPMEMBER`). Tipo de mídia por `ZWAMESSAGE.ZMESSAGETYPE` (a hipótese
  original do plano, `ZWAMEDIAITEM.ZMEDIAWATYPE`, não existe — medido e
  corrigido durante a execução da Task 4: 1=imagem, 8=documento, 3=áudio;
  demais códigos — vídeo, sticker — caem em `"desconhecido"`, não
  adivinhados). CLI passou a dispatchar por `sys.platform` em vez de
  presumir Windows (`_main_windows`/`_main_macos`). **Achado de execução
  real, corrigido no caminho**: dois testes Windows do Plano 1 não mockavam
  `sys.platform` e, após o dispatch entrar, passaram a rodar contra a
  instalação macOS **real** desta máquina — um deles chegou a imprimir dado
  pessoal real (nome/telefone de conversas) na saída capturada do teste;
  corrigido fixando `sys.platform="win32"` nos dois. Suíte: **51 passed + 1
  skip** (mesmo skip do Plano 1, fora do Windows), `ruff check` limpo.
  **Validação real contra a instalação deste MacBook CONCLUÍDA no mesmo
  dia** — `conversas` real em 0,23s com as mesmas contagens medidas (1.219
  Conversas, 946/269/3/1 por natureza), `mensagens` real numa Conversa
  direta e num grupo (autor resolvido em 100% dos casos, zero `None`),
  `anexo` real apontando para arquivo que existe de fato no disco, hash
  SHA-256 idêntico antes/depois confirmando não-escrita no banco original.
  Scratch com dado pessoal removido via Ação Documentada. Nenhuma
  pendência de validação restante deste plano.
- 2026-09-21 — **Plano 1 (Adaptador Windows) VALIDADO DE PONTA A PONTA
  contra Windows real — pendência fechada.** Três rodadas de teste real
  numa VM Windows provisionada para o teste:
  1. **Suíte completa rodando no Windows de fato**: 38 passed (o teste
     `windows_real`, que pula no macOS, passou de verdade contra
     `clipc.dll`/`ncrypt.dll`).
  2. **`conversas`/`mensagens`/`anexo` contra a instalação real**: decifrou
     as 4 bases, resolveu nome de **81/81 grupos** via CDP, recusa nomeada
     de `anexo` funcionando. Achado real corrigido no caminho: `main()`
     quebrava com `UnicodeEncodeError` (console Windows abre em `cp1252`,
     nome de grupo com emoji) — corrigido com
     `sys.stdout.reconfigure(encoding="utf-8")`, teste com poder escrito.
  3. **`habilitar-autor-windows` de ponta a ponta**: primeira tentativa via
     SSH (conta restrita da VM) mostrou `taskkill`/`tasklist`/
     PowerShell negados por política de grupo — a recusa nomeada
     (`EsperaDeDebugFalhou`, código 5) funcionou corretamente nesse
     cenário. Repetido depois numa sessão de **console interativo real**
     (script de teste dedicado):
     `taskkill` matou o processo de verdade, `reg delete` limpou a
     variável, `charla habilitar-autor-windows` gravou o registro,
     relançou o WhatsApp sozinho via `explorer.exe`, e a porta de debug
     **abriu de fato** (`http_status=200`, código de saída 0) — confirma
     que o mecanismo funciona quando a conta tem controle de processo.
  Suíte final: **38 testes passando + 1 skip explícito** (fora do Windows).
  `ruff check` limpo.
- 2026-09-20 — **repositório criado, privado**, via `dev-01-define-padroes`.
  Spec v1 já escrita e revisada antes do bootstrap — documento interno do
  autor, fora deste repositório (rascunho, revisão independente aplicada,
  sabatinada em 20/09).
  Decisão de fatiamento: Plano 0 (sessão de medição Windows contra máquina
  real) → Plano 1 (Adaptador Windows) → Plano 2 (Adaptador macOS) → Plano 3
  se necessário (distribuição).
- 2026-09-20 — **stack corrigida de Node/TypeScript para Python, ainda no
  bootstrap, antes de qualquer código.** Motivo: o `koine` já
  exige Python no ambiente do mentorado — critério de adoção decide a favor
  de não introduzir uma segunda linguagem. Distribuição decidida como
  zipapp (`charla.pyz`), no molde do `koine.pyz`, eliminando também a etapa
  de instalação via gerenciador de pacote. ADR local escrita:
  `docs/decisoes/20260920-charla-em-python-com-distribuicao-zipapp.md`.
  Nenhum código ainda — este commit é só o esqueleto.

## Pendências

- [x] Plano 0 — sessão de medição Windows (produziu documentos técnicos
      internos do autor, que fundamentam a spec v1)
- [x] Plano 1 via dev-03-escreve-plano — Adaptador Windows. **Implementado
      em 21/09/2026 via `dev-04`, e VALIDADO de ponta a ponta contra uma
      máquina Windows real no mesmo dia** — ver §Estado Atual. Nenhuma
      pendência de validação restante.
- [x] Plano 2 via dev-03-escreve-plano — Adaptador macOS. **Implementado
      em 21/09/2026, TDD inline, e VALIDADO de ponta a ponta contra este
      MacBook no mesmo dia** — ver §Estado Atual. Nenhuma pendência de
      validação restante.
- [x] Plano 3 — mecanismo de build/distribuição do `charla.pyz`.
      **Implementado em 21/09/2026** — macOS validado real contra o `.pyz`
      distribuído; **Windows fica como pendência nomeada de validação do
      artefato empacotado** (a lógica do Adaptador Windows já está
      validada via Plano 1, o que falta é rodar o `.pyz` em si numa
      máquina Windows).
- [x] Setup de testes (pytest, `pyproject.toml`, primeiro teste exemplar) —
      feito no Plano 1, Task 1/2
- [x] `GLOSSARIO.md` — escrito no Plano 1, Task 1 (Conversa, Mensagem, Anexo)
- [x] ADR local do risco de engenharia reversa (Windows) — escrita no Plano
      1, Task 1: `docs/decisoes/20260920-risco-de-engenharia-reversa-whatsapp-windows.md`.
      **Pendência que essa ADR nomeia e não fecha:** a versão validada é a
      do motor WebView2 (`Edg/153.0.4234.32`), não a versão do pacote
      WhatsApp Desktop UWP em si (`Get-AppxPackage`) — medir isso é
      trabalho futuro, não deste plano.

## Referências

- [[docs/arquitetura.md]] — mapa estrutural do repo (mapa fino, isento — carga sob demanda)
- [[docs/explicacoes/visao-geral.md]] — o quê e por quê (quadrante explicação, carga sob demanda)
- [[docs/decisoes/]] — ADRs locais
