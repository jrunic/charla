---
id: 202609201903
projeto: charla
tipo: decisao
status: aprovado
escopo: repo:charla
plataforma: "*"
dominios: [tecnologia]
descricao: "ADR local — risco de engenharia reversa da cadeia de decifra Windows: versão validada e compromisso de re-medição"
tags: [adr, risco, engenharia-reversa]
---

# ADR: risco de engenharia reversa da cadeia de decifra Windows

## Status

Aprovado, 2026-09-20.

## Contexto

A cadeia de decifra do WhatsApp Desktop UWP (Windows) não é documentada
pela Microsoft nem pela Meta — foi reconstruída por engenharia reversa
(carving heurístico de chaves, formato de página AES-OFB, derivação
DPAPI-NG), provada contra conta real em 19-20/09/2026. É a mesma classe de
risco que o `malote` já assume para o Baileys (biblioteca de WhatsApp Web
não oficial): pode quebrar sem aviso numa atualização do WhatsApp, e
diferente do Baileys, aqui não há projeto open source mantendo a
compatibilidade — a manutenção é só deste repositório.

## Decisão

1. **A versão do WhatsApp Desktop validada fica registrada aqui, e é
   atualizada a cada re-medição:** build medido em 19-20/09/2026, `Edg/153.0.4234.32`
   (motor WebView2 embutido — confirmado via `http://127.0.0.1:9222/json/version`
   numa instalação Windows real).
2. **Antes de qualquer release que toque `adaptador_windows/decifra.py` ou
   `autor_cdp.py`, re-medir contra uma instalação real** — os testes
   automatizados cobrem a lógica de cada função isoladamente, não a
   integração com `clipc.dll`/`ncrypt.dll`/o runtime JS do WhatsApp, que só
   existe numa máquina Windows real com o app instalado.
3. **Quando a cadeia quebrar** (atualização do WhatsApp muda o formato), a
   falha é sempre nomeada (`RuntimeError` com causa, nunca stack trace crua
   — ver `decifrar_bases_da_sessao` e `ErroDeAvaliacaoJS`), nunca lista
   vazia silenciosa.

## Consequências

- **Positivo:** o risco fica escrito, não implícito — quem for dar
  manutenção sabe que qualquer mudança nessa área exige teste manual contra
  Windows real, e não só suíte automatizada verde.
- **Negativo:** não há como antecipar quando o WhatsApp vai mudar o
  formato. O produto pode parar de funcionar no Windows sem aviso prévio, e
  a única forma de saber é o mentorado reportar erro.

## Referências

- Documentos técnicos sobre a cadeia de decifra Windows e a revisão da spec
  v1 do `charla` — documentos internos do autor, fora deste repositório
