"""Resolve autor de mensagem via conexão ao runtime do WhatsApp em
execução — o app UWP embute um WebView2 completo carregando
web.whatsapp.com (medido contra instalação Windows real, documento
técnico interno do autor). Autor não está em nenhum banco em disco;
existe só em memória, no runtime JS."""
import json
import subprocess
import time
import urllib.request

from charla._vendor import websocket  # vendorizado, Task 3 -- nao e pip install
from charla.adaptador_windows.ambiente_windows import FALHOU, garantir_porta_de_debug

PORTA_PADRAO = 9222
VARIAVEL_DE_AMBIENTE = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"
NOME_DO_PACOTE_UWP = "5319275A.WhatsAppDesktop_cv1g1gvanyjgm"


def porta_de_debug_esta_aberta(porta: int = PORTA_PADRAO, timeout_s: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{porta}/json/version", timeout=timeout_s
        ) as resp:
            return resp.status == 200
    except OSError:
        return False


def achar_pagina_principal(porta: int = PORTA_PADRAO) -> dict | None:
    with urllib.request.urlopen(f"http://127.0.0.1:{porta}/json/list", timeout=3) as resp:
        paginas = json.loads(resp.read())
    for p in paginas:
        if p.get("type") == "page" and "web.whatsapp.com" in p.get("url", ""):
            return p
    return None


class ErroDeAvaliacaoJS(Exception):
    """O runtime JS do WhatsApp Web levantou exceção, ou o socket estourou
    timeout — ver ClienteCDP.avaliar. Distinto de resultado vazio (que é
    valor `None`/`{}` legítimo, não erro)."""


class ClienteCDP:
    """Uma conexão WebSocket ao endpoint de debug de uma página."""

    def __init__(self, websocket_url: str, timeout_s: float = 15.0):
        self._ws = websocket.create_connection(
            websocket_url, timeout=timeout_s, suppress_origin=True
        )
        self._contador = 0

    def avaliar(self, expressao_js: str):
        """Levanta ErroDeAvaliacaoJS se o JS lançar exceção (ex.:
        `window.require('WAWebCollections')` deixar de existir numa
        atualização do WhatsApp — risco central declarado na spec) ou se o
        socket estourar timeout. Quem chama decide se isso vira aviso
        nomeado (Decisão 2/4) ou propaga."""
        self._contador += 1
        meu_id = self._contador
        self._ws.send(json.dumps({
            "id": meu_id,
            "method": "Runtime.evaluate",
            "params": {"expression": expressao_js, "returnByValue": True, "awaitPromise": True},
        }))
        try:
            while True:
                resp = json.loads(self._ws.recv())
                if resp.get("id") == meu_id:
                    break
        except (websocket.WebSocketTimeoutException, OSError) as e:
            raise ErroDeAvaliacaoJS(f"timeout ou erro de socket aguardando resposta CDP: {e}") from e

        if "exceptionDetails" in resp.get("result", {}):
            detalhe = resp["result"]["exceptionDetails"]
            texto = detalhe.get("exception", {}).get("description") or detalhe.get("text") or "sem detalhe"
            raise ErroDeAvaliacaoJS(f"JS lançou exceção: {texto}")

        resultado = resp.get("result", {}).get("result", {})
        if resultado.get("type") == "string":
            return json.loads(resultado["value"])
        return resultado.get("value")

    def enviar(self, metodo: str, params: dict):
        self._contador += 1
        meu_id = self._contador
        self._ws.send(json.dumps({"id": meu_id, "method": metodo, "params": params}))
        try:
            while True:
                resp = json.loads(self._ws.recv())
                if resp.get("id") == meu_id:
                    return resp
        except (websocket.WebSocketTimeoutException, OSError) as e:
            raise ErroDeAvaliacaoJS(f"timeout ou erro de socket em {metodo}: {e}") from e

    def fechar(self):
        self._ws.close()


class EsperaDeDebugFalhou(RuntimeError):
    """habilitar_debug_e_reiniciar esperou e a porta de debug nunca abriu,
    OU o registro do Windows recusou a escrita — achado da revisão dev-10:
    o caminho mais provável de falha é silencioso (o app relança no
    processo certo mas a porta nunca responde). Aqui isso vira recusa
    nomeada, nunca sucesso presumido. Herda de RuntimeError (não de
    Exception) para main() capturar sem tratamento especial — achado
    `bloqueia` novo 9 da revisão dev-10, 2ª rodada."""


def habilitar_debug_e_reiniciar(
    porta: int = PORTA_PADRAO, tentativas_de_espera: int = 15, intervalo_s: float = 1.0,
) -> None:
    """Grava a variável de ambiente (preservando o que já existir — ver
    ambiente_windows.py) e reinicia o WhatsApp — só chamado por
    `charla habilitar-autor-windows`, nunca implicitamente por `mensagens`
    (Decisão 2 do plano: reiniciar o app é opt-in, uma vez, não a cada
    comando). Precisa rodar numa sessão interativa — falha silenciosa por
    SSH não-interativo já foi medida (ver documento técnico, "armadilha de
    sessão").

    ATENÇÃO (Decisão 2, revista 20/09/2026, achado não confirmado M8): a
    variável `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` é GLOBAL do usuário —
    afeta todo processo WebView2, não só o WhatsApp. Fica aberta enquanto
    a porta que `garantir_porta_de_debug` gravou continuar lá; não existe
    comando simétrico de desligar nesta versão do plano — pendência
    nomeada, não resolvida aqui. O que a Task 11 revisada resolve é outro
    eixo: preservar qualquer argumento que o usuário já tivesse, em vez de
    apagá-lo em silêncio (era `setx`; não é mais)."""
    status = garantir_porta_de_debug(porta)
    if status == FALHOU:
        raise EsperaDeDebugFalhou(
            "não consegui gravar a porta de debug no registro do Windows "
            "(HKCU\\Environment) — verifique permissão de escrita na "
            "própria conta de usuário."
        )
    subprocess.run(
        ["taskkill", "/IM", "WhatsApp.Root.exe", "/T", "/F"],
        check=False, capture_output=True,
    )
    time.sleep(2)
    subprocess.run(
        ["explorer.exe", f"shell:appsFolder\\{NOME_DO_PACOTE_UWP}!App"],
        check=False,
    )
    for _ in range(tentativas_de_espera):
        if porta_de_debug_esta_aberta(porta):
            return
        time.sleep(intervalo_s)
    raise EsperaDeDebugFalhou(
        f"a porta de debug {porta} não abriu depois de reiniciar o "
        "WhatsApp — pode ser sessão SSH não-interativa (a variável precisa "
        "ser definida numa sessão de console real, não remota) ou o app "
        "não ter relançado. Tente reiniciar o WhatsApp manualmente."
    )


def montar_expressao_busca_autores(ids_de_mensagem: list[str]) -> str:
    """Busca no Msg collection do runtime os autores das mensagens cujo
    rowId bate com id (SQLite) — chave de junção confirmada por medição
    (documento técnico, seção "A chave que liga o SQLite ao runtime JS").
    Só devolve author — nunca o texto (já temos do SQLite)."""
    ids_json = json.dumps([int(i) for i in ids_de_mensagem])
    return f"""
    JSON.stringify((() => {{
      const {{ Msg }} = window.require('WAWebCollections');
      const alvo = new Set({ids_json});
      const todos = Msg.getModelsArray ? Msg.getModelsArray() : [];
      const achados = {{}};
      for (const m of todos) {{
        const a = m.attributes;
        if (alvo.has(a.rowId)) {{
          achados[String(a.rowId)] = (a.author && a.author._serialized) || null;
        }}
      }}
      return achados;
    }})())
    """


def montar_expressao_abrir_chat_e_marcar(chat_id: str) -> str:
    """Abre a conversa alvo por chatId via Cmd.openChatAt — determinístico,
    não depende de clique/viewport/virtualização (medido, substitui o
    clique cego que a versão anterior deste plano tinha — achado 13 da
    revisão dev-10, 1ª rodada).

    **Revisado em 21/09/2026 (achado `bloqueia` 3 da revisão dev-10, 2ª
    rodada)**: a versão anterior chamava `markChatUnread` sem condição,
    marcando como NÃO LIDA toda conversa consultada — inclusive as que já
    estavam lidas. Correção: ler o estado (`chat.unreadCount`)
    **antes** de abrir, e só restaurar `markChatUnread` quando a conversa
    já estava não lida. Se ela já estava lida, não faz nada — o efeito
    (incerto) de `openChatAt` sobre o estado de lida deixa de importar,
    porque não há nada a restaurar."""
    # IIFE assíncrona SEM `await` solto no topo — testado contra máquina
    # Windows real (documento técnico, seção CDP); `ClienteCDP.avaliar` já pede
    # `awaitPromise: true` e `returnByValue: true`, então a Promise
    # devolvida por esta IIFE é aguardada pelo protocolo, sem precisar de
    # `JSON.stringify` manual.
    chat_id_json = json.dumps(chat_id)
    return f"""
    (async () => {{
      const {{ Chat }} = window.require('WAWebCollections');
      const {{ Cmd }} = window.require('WAWebCmd');
      const chat = Chat.get({chat_id_json});
      if (!chat) return {{ ok: false, motivo: 'chat_nao_encontrado' }};
      const jaEstavaNaoLida = (chat.unreadCount || 0) > 0;
      await Cmd.openChatAt({{ chat }});
      await new Promise(r => setTimeout(r, 1200));
      if (!jaEstavaNaoLida) {{
        return {{ ok: true, restaurou_nao_lida: false }};
      }}
      try {{
        await Cmd.markChatUnread(chat, {{ markUnread: true }});
      }} catch (e) {{
        // rede de seguranca best-effort - falha aqui nao aborta a resolucao de autor
      }}
      return {{ ok: true, restaurou_nao_lida: true }};
    }})()
    """


def montar_expressao_busca_nomes_de_grupo(chat_ids: list[str]) -> str:
    """Decisão 4 (20/09/2026): `contacts.db` resolve nome de contato, nunca
    de grupo (medido) — nome de grupo só existe no runtime JS, via
    `WAWebCollections.Chat` (confirmado: 5 grupos reais testados, 100% com
    nome). Mesmo padrão de degrade gracioso do autor."""
    ids_json = json.dumps(chat_ids)
    return f"""
    JSON.stringify((() => {{
      const {{ Chat }} = window.require('WAWebCollections');
      const alvo = new Set({ids_json});
      const achados = {{}};
      for (const c of Chat.getModelsArray()) {{
        const id = c.id._serialized;
        if (alvo.has(id)) {{
          achados[id] = c.name || (c.contact ? c.contact.name : null) || null;
        }}
      }}
      return achados;
    }})())
    """


def _conectar_ao_whatsapp(porta: int) -> "ClienteCDP | None":
    """Resolve a página principal e abre a conexão CDP — devolve None em
    qualquer falha (porta fechou entre a sonda e a chamada, handshake
    recusado — o `403 Forbidden` de `Origin` está medido como armadilha
    real, JSON malformado). Extraído para não duplicar entre
    resolver_autores e resolver_nomes_de_grupo. Achado `bloqueia` da
    revisão dev-10 (2ª rodada): `achar_pagina_principal`
    (urlopen/json.loads crus) e `ClienteCDP.__init__`
    (`websocket.create_connection`) ficavam fora de qualquer `try` nas
    duas funções."""
    try:
        pagina = achar_pagina_principal(porta)
    except (OSError, ValueError):
        return None
    if pagina is None:
        return None
    try:
        return ClienteCDP(pagina["webSocketDebuggerUrl"])
    except (websocket.WebSocketException, OSError):
        return None


def resolver_autores(ids_de_mensagem: list[str], chat_id: str, porta: int = PORTA_PADRAO) -> dict[str, str | None]:
    """Ponto de entrada usado por `charla mensagens`. Devolve um dict
    id -> jid do autor (None quando a mensagem segue sem carregar mesmo
    depois de abrir a conversa). Nunca levanta exceção por falta de autor
    nem por falha do runtime JS — quem chama decide o que fazer com o
    resultado parcial (Decisão 2 do plano: degrade gracioso, nunca falha o
    comando inteiro)."""
    if not porta_de_debug_esta_aberta(porta):
        return {}

    cliente = _conectar_ao_whatsapp(porta)
    if cliente is None:
        return {}

    try:
        try:
            # ValueError: montar_expressao_busca_autores faz int(i) -- id
            # não-numérico (borda; a medição diz sempre 9 dígitos) não pode
            # virar stack trace (achado ajusta da revisão dev-10, 2ª rodada)
            achados = cliente.avaliar(montar_expressao_busca_autores(ids_de_mensagem)) or {}
        except (ErroDeAvaliacaoJS, ValueError):
            return {}
        # `avaliar` pode devolver None legitimamente (ex.: JS retornou
        # undefined) -- o `or {}` acima e o `or {}` abaixo evitam que isso
        # vire TypeError em "not in"/.update(), que era exatamente a forma
        # do defeito original (achado ajusta da revisao dev-10, 2a rodada)
        faltando = [i for i in ids_de_mensagem if str(i) not in achados]
        if faltando:
            try:
                cliente.avaliar(montar_expressao_abrir_chat_e_marcar(chat_id))
                achados_depois = cliente.avaliar(montar_expressao_busca_autores(faltando)) or {}
                achados.update(achados_depois)
            except ErroDeAvaliacaoJS:
                pass  # resultado parcial (o que já tinha achado) ainda e valido
        return achados
    finally:
        cliente.fechar()


def resolver_nomes_de_grupo(chat_ids: list[str], porta: int = PORTA_PADRAO) -> dict[str, str | None]:
    """Ponto de entrada usado por `charla conversas` (Decisão 4). Mesma
    política de degrade gracioso de resolver_autores: porta fechada ou
    falha do JS devolve dict vazio, nunca exceção."""
    if not chat_ids or not porta_de_debug_esta_aberta(porta):
        return {}

    cliente = _conectar_ao_whatsapp(porta)
    if cliente is None:
        return {}

    try:
        try:
            # or {} -- achado bloqueia da revisao dev-10 (3a rodada): faltava
            # aqui (o irmao resolver_autores ja tinha, comentado la)
            return cliente.avaliar(montar_expressao_busca_nomes_de_grupo(chat_ids)) or {}
        except ErroDeAvaliacaoJS:
            return {}
    finally:
        cliente.fechar()
