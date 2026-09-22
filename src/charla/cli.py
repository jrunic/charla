"""CLI do charla — dispacha comando, chama o adaptador certo, serializa
JSON."""
import argparse
import json
import sys

from charla._version import __version__
from charla.adaptador_windows.autor_cdp import (
    habilitar_debug_e_reiniciar,
    resolver_autores,
    resolver_nomes_de_grupo,
)
from charla.adaptador_windows.leitura import ler_conversas, ler_mensagens
from charla.adaptador_windows.localizacao import (
    ArquiteturaNaoSuportada,
    localizar_pasta_local_state,
)
from charla.adaptador_windows.sessao_temporaria import diretorio_de_trabalho

# achado real de execucao (Plano 3, validacao do .pyz em maquina limpa):
# charla.adaptador_windows.decifra importa `from Crypto.Cipher import AES`
# incondicionalmente fora do win32 (linha propositalmente fora do guard
# de sys.platform, ver docstring de decifra.py -- o dev/CI tem
# pycryptodome real instalado). Import no topo deste arquivo forçava
# TODO comando -- inclusive `conversas` no macOS -- a carregar Crypto, e
# numa maquina limpa sem pip install isso quebra com ModuleNotFoundError
# mesmo quando o comando nunca toca o Adaptador Windows. Corrigido
# adiando o import para dentro de _main_windows(), mesma fronteira de
# dependencia que _main_macos ja usa para o Adaptador macOS.

_AVISO_AUTOR_NAO_RESOLVIDO = (
    "autor/nome de grupo não resolvido — a conexão com o WhatsApp em "
    "execução não está disponível. Rode 'charla habilitar-autor-windows' "
    "uma vez para habilitar."
)


def comando_conversas(args, caminho_generic_storage=None, caminho_contacts=None):
    """Decisão 4 (20/09/2026): tenta resolver nome de grupo via CDP —
    `contacts.db` só tem nome de contato, nunca de grupo (medido). Degrade
    gracioso: porta fechada não falha o comando, grupo fica com `nome:
    null` e o aviso nomeado, igual ao padrão de `mensagens`."""
    conversas = ler_conversas(caminho_generic_storage, caminho_contacts)
    ids_de_grupo = [c.id for c in conversas if c.natureza == "coletiva"]
    nomes_de_grupo = resolver_nomes_de_grupo(ids_de_grupo) if ids_de_grupo else {}

    avisos = []
    # achado ajusta da revisao dev-10 (2a rodada): "not nomes_de_grupo" so
    # disparava com dict vazio -- grupo resolvido pela metade saia sem aviso
    resolvidos = sum(1 for i in ids_de_grupo if nomes_de_grupo.get(i))
    if ids_de_grupo and resolvidos < len(ids_de_grupo):
        avisos.append(
            f"{_AVISO_AUTOR_NAO_RESOLVIDO} ({resolvidos} de {len(ids_de_grupo)} "
            "grupos com nome resolvido)"
        )

    conversas_com_nome = [
        c if c.nome is not None or c.id not in nomes_de_grupo
        else type(c)(id=c.id, nome=nomes_de_grupo.get(c.id), natureza=c.natureza,
                      total_mensagens=c.total_mensagens, ultima_mensagem_em=c.ultima_mensagem_em)
        for c in conversas
    ]
    resultado = {"conversas": [c.para_dict() for c in conversas_com_nome]}
    if avisos:
        resultado["avisos"] = avisos
    return resultado


def comando_mensagens(args, caminho_generic_storage=None, caminho_contacts=None):
    mensagens = ler_mensagens(caminho_generic_storage, args.conversa)
    avisos = []
    autores = resolver_autores([m.id for m in mensagens], args.conversa)
    # achado ajusta da revisao dev-10 (2a rodada): "if not autores" so
    # disparava com dict TOTALMENTE vazio -- 3 resolvidos de 500 mensagens
    # saia sem aviso nenhum, que é o vazio silencioso do critério 13.
    if len(autores) < len(mensagens):
        avisos.append(
            f"{_AVISO_AUTOR_NAO_RESOLVIDO} ({len(autores)} de {len(mensagens)} "
            "mensagens com autor resolvido)"
        )
    mensagens_com_autor = [
        type(m)(id=m.id, conversa_id=m.conversa_id, texto=m.texto,
                 instante=m.instante, autor=autores.get(m.id))
        for m in mensagens
    ]
    resultado = {"mensagens": [m.para_dict() for m in mensagens_com_autor]}
    if avisos:
        resultado["avisos"] = avisos
    return resultado


def comando_anexo(args, caminho_generic_storage=None, caminho_contacts=None):
    from pathlib import Path

    from charla.adaptador_windows.midia import (
        ConexaoComWhatsAppIndisponivel,
        DecifraDeMidiaFalhou,
        baixar_e_decifrar,
        resolver_metadado_midia,
    )
    from charla.escrita_atomica import escrever_bytes, validar_destino

    if not args.destino:
        return {
            "erro": (
                "--destino é obrigatório no Windows — a mídia não existe "
                "como arquivo até ser extraída; informe onde salvar."
            )
        }
    destino = Path(args.destino)
    try:
        validar_destino(destino)
    except ValueError as e:
        return {"erro": str(e)}

    try:
        metadado = resolver_metadado_midia(args.id)
    except ConexaoComWhatsAppIndisponivel as e:
        return {"erro": str(e)}
    if metadado is None:
        return {"erro": f"anexo {args.id} não encontrado"}

    try:
        dados = baixar_e_decifrar(metadado["directPath"], metadado["mediaKey"], metadado["mimetype"])
    except (DecifraDeMidiaFalhou, OSError) as e:
        return {"erro": str(e)}

    escrever_bytes(destino, dados)
    return {"anexo": {"id": args.id, "caminho_absoluto": str(destino.resolve())}}


def comando_habilitar_autor_windows(args, **kwargs):
    print(
        "O charla vai reiniciar o WhatsApp Desktop para habilitar a "
        "resolução de autor. Isso acontece uma vez só; o WhatsApp volta a "
        "abrir sozinho, sem precisar escanear QR de novo.",
        file=sys.stderr,
    )
    habilitar_debug_e_reiniciar()
    return {"status": "debug habilitado, WhatsApp reiniciado"}


def comando_conversas_macos(args, caminho=None):
    from charla.adaptador_macos.leitura import ler_conversas as ler_conversas_macos
    conversas = ler_conversas_macos(caminho)
    return {"conversas": [c.para_dict() for c in conversas]}


def comando_mensagens_macos(args, caminho=None):
    from charla.adaptador_macos.leitura import ler_mensagens as ler_mensagens_macos
    mensagens = ler_mensagens_macos(caminho, args.conversa)
    return {"mensagens": [m.para_dict() for m in mensagens]}


def comando_anexo_macos(args, caminho=None):
    from pathlib import Path

    from charla.adaptador_macos.leitura import ler_anexo as ler_anexo_macos
    from charla.escrita_atomica import copiar

    anexo = ler_anexo_macos(caminho, args.id)
    # args.destino sempre existe (o parser compartilhado ja tem
    # --destino desde comando_anexo do Windows) -- sem getattr defensivo
    destino = args.destino
    if destino:
        destino_path = Path(destino)
        copiar(Path(anexo.caminho_absoluto), destino_path)
        anexo = type(anexo)(
            id=anexo.id, conversa_id=anexo.conversa_id, tipo=anexo.tipo,
            caminho_absoluto=str(destino_path.resolve()),
        )
    return {"anexo": anexo.para_dict()}


_COMANDOS_MACOS = {
    "conversas": comando_conversas_macos,
    "mensagens": comando_mensagens_macos,
    "anexo": comando_anexo_macos,
}


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="charla")
    subs = parser.add_subparsers(required=True, dest="comando")

    p_conversas = subs.add_parser("conversas")
    p_conversas.set_defaults(funcao=comando_conversas)

    p_mensagens = subs.add_parser("mensagens")
    p_mensagens.add_argument("--conversa", required=True)
    p_mensagens.set_defaults(funcao=comando_mensagens)

    p_anexo = subs.add_parser("anexo")
    p_anexo.add_argument("id")
    p_anexo.add_argument("--destino")
    p_anexo.set_defaults(funcao=comando_anexo)

    p_habilitar = subs.add_parser("habilitar-autor-windows")
    p_habilitar.set_defaults(funcao=comando_habilitar_autor_windows)

    subs.add_parser("versao")

    return parser


def _main_windows(args) -> int:
    from charla.adaptador_windows.decifra import decifrar_bases_da_sessao

    try:
        pasta_local_state = localizar_pasta_local_state()
    except ArquiteturaNaoSuportada as e:
        print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 4

    if args.funcao is comando_habilitar_autor_windows:
        # EsperaDeDebugFalhou herda de RuntimeError (Task 11, revisado
        # 21/09/2026) -- achado bloqueia da revisao dev-10 (2a rodada): esta
        # chamada nunca tinha try nenhum, e ficava fora do bloco abaixo.
        try:
            resultado = comando_habilitar_autor_windows(args)
        except RuntimeError as e:
            print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
            return 5
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0

    if args.funcao is comando_anexo:
        # anexo no Windows nao precisa da cadeia de decifra do SQLite --
        # metadado de midia vem do runtime JS via CDP (achado do Plano 0
        # do incremento de anexo, 22/09/2026), mesmo desvio de
        # habilitar-autor-windows, sem abrir diretorio_de_trabalho.
        try:
            resultado = comando_anexo(args)
        except Exception as e:  # noqa: BLE001 -- rede de seguranca deliberada
            print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
            return 1
        # comando_anexo DEVOLVE {"erro": ...} nos casos de recusa nomeada
        # (destino ausente, invalido, id nao encontrado) -- nunca levanta
        # nesses casos, entao o try/except acima so pega excecao
        # inesperada. Bifurca o canal aqui, mesmo contrato que
        # comandos-e-saida.md ja documenta (erro vai pra stderr sem
        # indent, sucesso vai pra stdout com indent=2) -- mesmo padrao
        # que _main_macos ja segue.
        if "erro" in resultado:
            print(json.dumps(resultado, ensure_ascii=False), file=sys.stderr)
            return 1
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0

    with diretorio_de_trabalho() as pasta_trabalho:
        try:
            decifrar_bases_da_sessao(pasta_local_state, pasta_trabalho)
        except RuntimeError as e:
            print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
            return 5

        try:
            resultado = args.funcao(
                args,
                caminho_generic_storage=pasta_trabalho / "genericStorage.dec.db",
                caminho_contacts=pasta_trabalho / "contacts.dec.db",
            )
        except Exception as e:  # noqa: BLE001 -- rede de seguranca deliberada, ver comentario
            # achado bloqueia da revisao independente da documentacao
            # (21/09/2026): so RuntimeError da cadeia de decifra era
            # tratado -- excecao do adaptador (schema mudado numa
            # atualizacao do WhatsApp, banco corrompido etc) escapava
            # crua, contradizendo a promessa de comandos-e-saida.md de
            # que "exit==2 + saida nao-JSON" e o unico caso de saida
            # nao-JSON.
            print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
            return 1

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if "erro" not in resultado else 1


def _main_macos(args) -> int:
    from charla.adaptador_macos.localizacao import (
        ChatStorageNaoEncontrado,
        localizar_chat_storage,
    )

    if args.comando == "habilitar-autor-windows":
        print(
            json.dumps(
                {
                    "erro": (
                        "habilitar-autor-windows só se aplica no Windows — "
                        "no macOS o autor é resolvido direto por SQL, sem "
                        "esse passo."
                    )
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 4

    try:
        caminho = localizar_chat_storage()
    except ChatStorageNaoEncontrado as e:
        print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 4

    try:
        resultado = _COMANDOS_MACOS[args.comando](args, caminho=caminho)
    except Exception as e:  # noqa: BLE001 -- rede de seguranca deliberada, ver comentario
        # achado real (sessao de documentacao, medindo antes de escrever):
        # ler_anexo levanta ValueError quando o id nao existe, e nada
        # aqui tratava isso -- reproduzido contra o .pyz real
        # (`charla anexo 99999999`), stack trace crua + exit=1 por
        # comportamento padrao do Python, nao por desenho. Viola o
        # criterio 13 da spec (nunca stack trace crua).
        # achado bloqueia da revisao independente da documentacao
        # (21/09/2026): so ValueError era capturado -- qualquer outra
        # excecao (ex.: sqlite3.DatabaseError por banco corrompido)
        # escapava crua pelo mesmo mecanismo. Alargado para Exception.
        print(json.dumps({"erro": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if "erro" not in resultado else 1


def main() -> int:
    # achado de execucao real (validacao contra maquina Windows real):
    # o console do Windows abre stdout/stderr no codepage local (cp1252),
    # nao UTF-8 -- nome de conversa/grupo com emoji (medido: um grupo real
    # trazia U+1F91D) faz o print() de json.dumps(..., ensure_ascii=False)
    # levantar UnicodeEncodeError, quebrando o comando inteiro depois de a
    # decifra e a leitura terem funcionado. reconfigure() existe desde
    # Python 3.7 e é no-op em stream que ja e utf-8 (macOS/Linux).
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = montar_parser()
    args = parser.parse_args()

    if args.comando == "versao":
        # despachado ANTES do dispatch por sys.platform, de proposito:
        # nao depende de WhatsApp instalado, nem de decifra, nem de
        # nenhum adaptador -- roda em qualquer SO. Formato "charla X.Y.Z",
        # mesmo padrao do koine (CI le com `awk '{print $2}'`).
        print(f"charla {__version__}")
        return 0

    if sys.platform == "win32":
        return _main_windows(args)
    if sys.platform == "darwin":
        return _main_macos(args)

    print(
        json.dumps(
            {"erro": f"sistema operacional não suportado pelo charla: {sys.platform}"},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 4
