---
id: 202609212030
projeto: charla
tipo: nota
escopo: repo:charla
plataforma: "*"
status: ativo
descricao: Changelog do charla — o que mudou em cada versão publicada, com âncora por tag.
tags: [changelog, release, python]
---

# Changelog

All notable changes to charla are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-09-22

### Adicionado — `charla anexo` funciona no Windows, com destino escolhido

`charla anexo <id> --destino <caminho>` extrai mídia recebida de
verdade no Windows — antes sempre recusava (mídia não implementada).
Mecanismo: CDP extrai só metadado (`directPath`/`mediaKey`/`mimetype`,
já em memória, sem abrir conversa nem precisar de `chat_id`); os bytes
vêm de download HTTPS direto contra o CDN do WhatsApp e decifra local
em Python pelo protocolo público de mídia do WhatsApp (HKDF-SHA256 +
AES-256-CBC + verificação HMAC — mesmo algoritmo que
`whatsapp-web.js`/`Baileys` usam). `--destino` é **obrigatório** no
Windows (a mídia não existe como arquivo até ser extraída).

No macOS, `--destino` passa a existir como **opcional** — sem ele,
comportamento idêntico à v0.1.0 (só devolve o caminho do arquivo
original); com ele, copia o arquivo para o destino escolhido e
`caminho_absoluto` passa a apontar para a cópia. Interface simétrica
nas duas plataformas.

Escrita e cópia são sempre atômicas (arquivo temporário + substituição
só no final) — nunca deixam arquivo truncado no destino se algo falhar
no meio.

**No Windows, o `id` de anexo passou a ser o mesmo `id` de Mensagem**
que `mensagens` já expõe (antes não havia forma de obter esse `id`,
porque o comando sempre recusava).

### Limitações conhecidas desta versão

- Só `image` foi verificada de ponta a ponta contra bytes reais no
  Windows; `video`/`audio`/`document` usam o mesmo algoritmo
  documentado, não testados contra arquivo real.
- Mensagem de mídia fora da janela que o WhatsApp Web já carregou em
  memória (conversa nunca aberta na sessão, histórico muito antigo)
  não foi medida — pode devolver "não encontrado" mesmo a mídia
  existindo.

## [0.1.0] — 2026-09-21

### Adicionado — primeiro release público

CLI local que lê os bancos do WhatsApp Desktop na própria máquina do
usuário — `conversas`, `mensagens` e `anexo`, sempre lendo o que o app
já gravou, nunca acumulando histórico próprio, nunca enviando nada para
fora.

- **macOS**: lê `ChatStorage.sqlite` direto, sem cifra, com `VACUUM INTO`
  para retrato consistente sem interromper o app. Natureza de conversa
  (`direta`/`grupo`/`lista-de-transmissao`/`comunidade`) e autor de
  mensagem resolvidos via SQL puro. Validado de ponta a ponta contra
  instalação real.
- **Windows** (app UWP/Microsoft Store): decifra local via cadeia
  DPAPI-NG (ODUID + segredo de sessão + carving heurístico de chaves),
  sem privilégio de administrador. Autor de mensagem de grupo resolvido
  via conexão CDP ao runtime WebView2 do próprio WhatsApp em execução
  (`charla habilitar-autor-windows`, roda uma vez). Validado de ponta a
  ponta contra máquina Windows real, incluindo a cadeia completa de
  decifra e a resolução de autor via CDP.
- **Distribuição**: `charla.pyz` (zipapp da stdlib), sem `pip install`,
  sem ambiente virtual — baixa e roda com qualquer Python 3.12+ instalado.
  `pycryptodome` (Windows) e `websocket-client` vendorizados dentro do
  próprio artefato.
- **Documentação Diátaxis exaustiva**, pensada para consumo por agente
  (não só humano): referência completa de comandos, schema JSON e
  códigos de saída (`docs/referencias/comandos-e-saida.md`), tutorial de
  primeiro uso passo a passo (`docs/tutoriais/primeiro-uso.md`).

### Limitações conhecidas desta versão

- **Empacotamento `.pyz` validado só no macOS.** A lógica do Adaptador
  Windows está validada de ponta a ponta (item acima), mas o artefato
  `charla.pyz` especificamente ainda não foi rodado contra uma máquina
  Windows real — só via `python -m charla` da fonte. Validação do
  artefato empacotado no Windows fica para a próxima versão.
- **Cadeia de decifra Windows validada numa única máquina/conta.**
  Reprodução numa segunda máquina/conta distintas, para descartar
  acaso, ainda não aconteceu.
- **`anexo` recusa sempre no Windows** — o WhatsApp Desktop para Windows
  não guarda caminho de arquivo amigável para mídia recebida (medido);
  suporte a mídia no Windows não é desta versão.
- **Risco herdado, nomeado desde o início**: a cadeia de decifra e a
  resolução de autor via CDP não são documentadas pela Microsoft nem
  pelo WhatsApp — podem quebrar sem aviso numa atualização do app. Ver
  `docs/decisoes/20260920-risco-de-engenharia-reversa-whatsapp-windows.md`.
