---
id: 202609201901
projeto: charla
tipo: decisao
status: aprovado
escopo: repo:charla
plataforma: "*"
dominios: [tecnologia]
descricao: "ADR local — vendorizar pycryptodome como dado bruto (win_amd64), com auto-extração no primeiro uso, para a cadeia de decifra Windows"
tags: [adr, dependencia, criptografia]
---

# ADR: vendorizar `pycryptodome` (dado bruto, auto-extraído) para a cadeia de decifra Windows

## Status

Aprovado, 2026-09-20. Substitui a decisão original (`pyaes` puro-Python),
revista no mesmo dia por medição.

## Contexto

A cadeia de decifra do WhatsApp Desktop no Windows (provada num documento
técnico interno do autor, fora deste repositório) precisa de AES-256 em
modo OFB e CBC. Não existe AES na stdlib do Python.

A primeira versão desta ADR escolheu `pyaes` (pura Python) para manter a
filosofia stdlib-only do repositório (`CONTEXTO.md`: "nada de
`.pyd`/`.so`/`.dll`" importado como dependência de terceiro). Medido antes
deste plano ser escrito: `pyaes` decifra 57 MB (tamanho real do
`genericStorage.db` de produção) em **129,1 s**; `pycryptodome` (núcleo C)
faz o mesmo em **0,47 s** — 274x mais rápido. 129 s de espera na primeira
consulta do mentorado não é aceitável (História de Usuário 1, uso
interativo).

## Decisão

Vendorizar `pycryptodome` — não como dependência `pip`, e não importável de
dentro do `.pyz` (medido: `zipimport` não carrega módulo de extensão nativa
de dentro de zip). O wheel `win_amd64` oficial (baixado do PyPI, sem
executar nada dele) é reempacotado como **dado bruto**,
`src/charla/_vendor/pycryptodome_win_amd64.zip`, dentro do pacote/`.pyz`.
Na primeira execução, `pycryptodome_carregador.py` extrai esse zip para
`~/.cache/charla/_vendor/<hash-do-zip>/` e insere essa pasta em `sys.path`
antes de importar `Crypto.Cipher.AES` — confirmado por teste local que essa
extração-antes-de-importar funciona (o problema é só importar **de dentro**
do zip, não importar um pacote com extensão nativa em geral).

Só o wheel `win_amd64` entra — a cadeia de decifra é exclusiva do Adaptador
Windows; o Adaptador macOS lê SQLite puro, sem cifra, sem AES.

## Consequências

- **Positivo:** decifra volta a ser sub-segundo (medido: 0,47s/57MB), dentro
  do teto de usabilidade interativa. Distribuição continua sendo um arquivo
  `.pyz` só, sem `pip install` — a extração acontece do próprio pacote.
- **Negativo:** o `.pyz` cresce (~1-2 MB do wheel comprimido). Aceito — é
  pequeno frente ao ganho de usabilidade.
- **Negativo:** primeira execução no Windows faz uma extração de disco (uma
  vez, cacheada por hash do zip vendorizado — reinstalar a mesma versão do
  `charla` não re-extrai).
- **Negativo:** código vendorizado não recebe atualização automática de
  segurança — trocar de versão do `pycryptodome` exige rebaixar/regravar o
  zip vendorizado à mão. Mesma classe de dívida que qualquer vendorização.
- **Mecanismo novo, não usado em nenhum outro projeto do autor** (o `koine`
  vendoriza `PyYAML`, que é pura Python e não precisa de extração — não é
  precedente direto para binário nativo). Primeira vez que este padrão é
  usado; se funcionar bem aqui, generalizar para outro caso é decisão
  futura, não deste plano.

## Alternativas Consideradas

| Alternativa | Por que não |
|---|---|
| `pyaes` (pura Python, decisão original) | 274x mais lento, medido — inviabiliza uso interativo |
| `pycryptodome` via `pip install` separado | Quebra o critério 14 da spec (rodar de `charla.pyz` sem `pip install`) |
| `cryptography` (pyca) vendorizado do mesmo jeito | Também tem componente nativo (Rust/OpenSSL); `pycryptodome` é mais simples de reempacotar (um único wheel puro-C, sem toolchain Rust) |
| Implementar AES do zero neste repo | Código de cifra novo e não revisado por terceiros é risco maior que vendorizar uma implementação madura e testada |
| Recortar à mão só os `.pyd` estritamente necessários | Risco de "faltou um módulo" só descoberto em campo, sem poder testar import real no Windows durante a escrita deste plano — vendoriza-se `Crypto/` inteiro (~1,8 MB comprimido) |

## Referências

- Documento técnico sobre a cadeia de decifra Windows, a spec v1 do
  `charla` e a revisão do Plano 1 — documentos internos do autor, fora
  deste repositório
