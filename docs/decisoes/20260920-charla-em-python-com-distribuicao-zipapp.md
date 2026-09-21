---
id: 202609201800
projeto: charla
tipo: decisao
status: aprovado
data: 2026-09-20
escopo: repo:charla
plataforma: "*"
dominios: [tecnologia]
descricao: "ADR — o charla é escrito em Python, não Node/TypeScript, e distribuído como zipapp, não por gerenciador de pacote — porque o mentorado já tem Python instalado por causa do koine"
tags: [adr, decisao, stack, distribuicao, python, zipapp, koine]
---

# ADR — Stack Python e distribuição por zipapp

## Status

Aprovado — 2026-09-20.

## Contexto

O bootstrap inicial deste repositório (mesmo dia) escolheu Node/TypeScript,
por precedente direto: é a stack do `malote`, produto irmão de onde o
`charla` reaproveita vocabulário e lições de desenho. A cadeia de decifra do
WhatsApp Desktop no Windows — a peça mais arriscada do produto — só existe
provada em Python (`pycryptodome` + `ctypes` para `clipc.dll`/`ncrypt.dll`,
provado num documento técnico interno do autor, fora deste repositório),
então a escolha por Node implicava portar essa cadeia inteira antes de ela
rodar em produção — risco já nomeado na revisão da spec v1 (documento
interno do autor, fora deste repositório).

Revisitando a decisão no mesmo dia, entrou um critério que não estava em
jogo até então: **o público do `charla` já roda o `koine`**, outro
produto da mesma frota, que exige Python no ambiente local do mentorado. Isso
muda o cálculo — não é "qual stack o time prefere", é "qual stack o mentorado
já tem instalada por outro motivo".

## Decisão

**O `charla` é escrito em Python 3.12+, stdlib-first, e distribuído como
zipapp (`charla.pyz`) — não como pacote npm ou PyPI.**

Duas escolhas, uma justificativa comum:

1. **Python, não Node/TypeScript.** O mentorado alvo do `charla` já tem
   Python instalado — é pré-requisito do `koine`. Escolher Node introduziria
   uma segunda linguagem/runtime só para este produto, e a cadeia de decifra
   mais arriscada da v1 (Windows) já está provada em Python, sem porte
   nenhum: `ctypes` é stdlib, e só a implementação de AES precisa de
   dependência externa vendorizada.
2. **Zipapp, não gerenciador de pacote.** Segue o precedente do `koine.pyz`:
   o mentorado roda `python3 charla.pyz <comando>` sem `pip install`, sem
   ambiente virtual, sem resolução de dependência na máquina de destino — a
   dependência de AES é vendorizada dentro do próprio zip, mesmo padrão do
   PyYAML vendorizado em `koine/src/koine/_vendor/`.

## Consequências

### Positivas

- **Zero segunda linguagem a instalar.** O critério de adoção —
  "o público real não é técnico, e já tem Python por causa do koine" — é
  atendido sem fricção adicional.
- **A cadeia de decifra Windows entra quase sem porte.** O código já provado
  ponta a ponta (documento técnico de 19-20/09/2026) é Python; o trabalho
  vira adaptação de estrutura, não reescrita em outra linguagem.
- **Zipapp elimina a etapa de instalação inteira** — não só a escolha de
  linguagem, mas o próprio `pip install`/`npm install` desaparece como passo
  que pode falhar na máquina do mentorado.
- **Precedente de operação já existe na frota** (`koine`): build via GitHub
  Actions, publicação em GitHub Releases, filosofia stdlib-first testada em
  produto irmão.

### Negativas

- **Abandona o trabalho já feito no bootstrap Node** (CONTEXTO.md preenchido,
  primeiro commit) — custo pequeno porque nenhum código de aplicação tinha
  sido escrito ainda, só esqueleto e documentação.
- **O `charla` diverge da stack do `malote`**, apesar de reaproveitar
  vocabulário dele — quem olhar os dois repositórios juntos precisa deste ADR
  para entender por que não são a mesma stack, dado que a spec original
  também presumia Node por analogia direta ao malote.
- **`pycryptodome` (ou equivalente) vendorizado** ainda precisa ser escolhido
  e testado no Plano 1 — vendorizar biblioteca com componente em C exige
  mais cuidado que vendorizar YAML puro-Python (o `koine` evita justamente
  esse caso, "nada de `.pyd`/`.so`/`.dll`" no próprio `CONTEXTO.md` dele). Se
  não houver forma pura-Python viável de AES-OFB, essa cláusula do precedente
  do koine não se sustenta sem ajuste, e vira decisão a reabrir no Plano 1.

### Implementação

- `src/charla/` é o pacote; `_vendor/` recebe dependência externa vendorizada,
  no molde do `koine`.
- Build do `charla.pyz` documentado quando o Plano 1 (Adaptador Windows)
  definir o mecanismo exato — não existe hoje.
- `CONTEXTO.md` deste repo já reflete a stack Python (Stack, Padrões
  Técnicos, Decisões Locais Divergentes).

## Escopo

Vale para este repositório inteiro — é decisão de stack, não de um módulo.
Não vincula o `malote` nem qualquer outro produto da frota: cada um decide a
própria stack pelo próprio público.

## Alternativas Consideradas

| Alternativa | Por que não |
|---|---|
| **Node/TypeScript** (escolha original do bootstrap) | consistente com o `malote`, mas exige porte da cadeia de decifra Windows inteira, e o público real do `charla` não tem Node instalado por nenhum outro motivo |
| **Python + `pip install`/PyPI** | resolve a linguagem, mas mantém uma etapa de instalação que o zipapp elimina — fricção real para mentorado não-técnico |
| **Python + zipapp, mas com dependência externa não vendorizada** (`pip install pycryptodome` à parte) | reintroduz resolução de dependência na máquina de destino, o problema que o zipapp existe para eliminar |

## Referências

- Documento técnico sobre a cadeia de decifra Windows (provada em Python) e
  a spec v1 do `charla` — documentos internos do autor, fora deste
  repositório
- `koine/CONTEXTO.md` — precedente de stack stdlib-only e distribuição por
  zipapp
