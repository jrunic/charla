# achado bloqueia da revisao dev-10 do Plano 2: subprocess/sys/Path
# continuam sem uso neste arquivo, mas json volta a ser necessario para os
# testes de dispatch por SO abaixo (json.loads sobre capsys).
import json

from tests.fixtures.gerar_contacts import gerar as gerar_contacts
from tests.fixtures.gerar_genericstorage import gerar as gerar_generic_storage


def _rodar_cli(argv, caminho_gs, caminho_contacts):
    from charla.cli import montar_parser

    parser = montar_parser()
    args = parser.parse_args(argv)
    return args.funcao(args, caminho_generic_storage=caminho_gs, caminho_contacts=caminho_contacts)


def test_comando_conversas_devolve_json_com_as_conversas_esperadas(tmp_path, monkeypatch):
    # porta de debug fechada de proposito — mesma razao do teste de
    # mensagens: sem isso, resolver_nomes_de_grupo faria chamada de rede
    # real a 127.0.0.1:9222
    monkeypatch.setattr("charla.cli.resolver_nomes_de_grupo", lambda ids, porta=9222: {})
    caminho_gs = tmp_path / "gs.db"
    caminho_contacts = tmp_path / "contacts.db"
    gerar_generic_storage(caminho_gs)
    gerar_contacts(caminho_contacts)

    saida = _rodar_cli(["conversas"], caminho_gs, caminho_contacts)
    ids = {c["id"] for c in saida["conversas"]}
    assert ids == {"5511999990001@lid", "120363021901138870@g.us"}


def test_comando_mensagens_e_deterministico_entre_duas_chamadas(tmp_path, monkeypatch):
    # a porta de debug fica fechada de proposito neste teste — resolver
    # autor via CDP faria chamada de rede real a 127.0.0.1:9222, lenta e
    # dependente do ambiente (achado da revisao dev-10); o determinismo que
    # este teste mede e o do CAMINHO OFFLINE, que e o que roda em CI
    monkeypatch.setattr(
        "charla.cli.resolver_autores", lambda ids, chat_id, porta=9222: {}
    )
    caminho_gs = tmp_path / "gs.db"
    caminho_contacts = tmp_path / "contacts.db"
    gerar_generic_storage(caminho_gs)
    gerar_contacts(caminho_contacts)

    saida1 = _rodar_cli(["mensagens", "--conversa", "120363021901138870@g.us"], caminho_gs, caminho_contacts)
    saida2 = _rodar_cli(["mensagens", "--conversa", "120363021901138870@g.us"], caminho_gs, caminho_contacts)
    assert saida1 == saida2


def test_comando_anexo_no_windows_recusa_com_causa_nomeada(tmp_path):
    from charla.cli import comando_anexo

    class ArgsFalsos:
        id = "abc"

    resultado = comando_anexo(ArgsFalsos(), caminho_generic_storage=None, caminho_contacts=None)
    assert resultado["erro"] is not None
    # achado de execucao (dev-04): o texto da mensagem e "nao ESTA
    # implementada", nao "nao implementada" contiguo -- o teste original do
    # plano checava a substring errada.
    assert "não está implementada" in resultado["erro"].lower()


from unittest.mock import patch


def test_main_decifra_as_bases_antes_de_chamar_o_comando(tmp_path, monkeypatch):
    # este teste roda em qualquer SO: mocka as funcoes de ctypes-dependentes
    # da cadeia de decifra, e so confere que main() as chama na ordem certa.
    # achado do Plano 2 (execucao real): sem mockar sys.platform, este teste
    # rodava no macOS real de quem executa a suite e caia no dispatch
    # macOS -- chegou a ler o ChatStorage.sqlite REAL da maquina, vazando
    # dado pessoal na saida capturada do teste. sys.platform="win32" fixa
    # o caminho Windows que o teste sempre pretendeu exercitar.
    #
    # achado real do Plano 3 (execucao real, rodando so este arquivo
    # isolado -- `pytest tests/test_cli.py`, sem test_decifra.py na mesma
    # coleta): decifra.py so foi tornado LAZY em cli.py neste plano (era
    # import no topo antes), e o import ANTECIPADO aqui, sob a plataforma
    # REAL (darwin), e o que garante que o guard `if sys.platform ==
    # "win32":` de decifra.py tome o ramo seguro (nunca tenta extrair o
    # zip vendorizado win_amd64 de verdade). Sem esta linha, o import de
    # decifra.py so acontece DENTRO de main()/patch() -- ja com
    # sys.platform mockado -- e o guard acha que esta em Windows de
    # verdade, tenta carregar binario .pyd real, e quebra com OSError
    # (`Cannot load native module 'Crypto.Util._cpuid_c'`) numa maquina
    # macOS de verdade. Reproduzido isolando este arquivo antes da correcao.
    import charla.adaptador_windows.decifra  # noqa: F401

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("sys.argv", ["charla", "conversas"])

    with patch("charla.cli.localizar_pasta_local_state") as m_localizar, \
         patch("charla.adaptador_windows.decifra.decifrar_bases_da_sessao") as m_decifrar, \
         patch("charla.cli.ler_conversas", return_value=[]):
        m_localizar.return_value = tmp_path
        from charla.cli import main
        codigo = main()

    assert codigo == 0
    m_decifrar.assert_called_once()


def test_main_reconfigura_stdout_para_utf8_antes_de_imprimir(tmp_path, monkeypatch):
    """Achado de execucao real contra maquina Windows real: console do
    Windows abre stdout no codepage local (cp1252), e nome de conversa/grupo
    com emoji (medido: um grupo real com U+1F91D) faz o print() de
    json.dumps(..., ensure_ascii=False) levantar UnicodeEncodeError -- depois
    de decifra e leitura terem funcionado. main() reconfigura para utf-8
    antes do primeiro print; este teste finge um stdout que só aceita
    ASCII até ser reconfigurado, para confirmar que a chamada acontece.
    Mesmo achado do teste acima: sys.platform fixado em win32 para não
    cair no dispatch macOS real. Mesmo achado do Plano 3 sobre import
    antecipado de decifra.py -- ver comentário no teste anterior."""
    import charla.adaptador_windows.decifra  # noqa: F401

    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("sys.argv", ["charla", "conversas"])

    class _StdoutQueFingeCodepageLocal:
        def __init__(self):
            self.reconfigurado = False
            self.escrito = []

        def reconfigure(self, encoding):
            assert encoding == "utf-8"
            self.reconfigurado = True

        def write(self, texto):
            if not self.reconfigurado and any(ord(c) > 127 for c in texto):
                raise UnicodeEncodeError("cp1252", texto, 0, 1, "character maps to <undefined>")
            self.escrito.append(texto)

        def flush(self):
            pass

    stdout_falso = _StdoutQueFingeCodepageLocal()
    monkeypatch.setattr("sys.stdout", stdout_falso)
    monkeypatch.setattr("sys.stderr.reconfigure", lambda encoding: None)

    from charla.modelo import Conversa

    conversa_com_emoji = Conversa(id="1@g.us", nome="Time \U0001f91d", natureza="coletiva",
                                   total_mensagens=1, ultima_mensagem_em=1)

    with patch("charla.cli.localizar_pasta_local_state") as m_localizar, \
         patch("charla.adaptador_windows.decifra.decifrar_bases_da_sessao"), \
         patch("charla.cli.ler_conversas", return_value=[conversa_com_emoji]), \
         patch("charla.cli.resolver_nomes_de_grupo", return_value={}):
        m_localizar.return_value = tmp_path
        from charla.cli import main
        codigo = main()

    assert codigo == 0
    assert stdout_falso.reconfigurado is True
    assert any("\U0001f91d" in t for t in stdout_falso.escrito)


def test_main_recusa_plataforma_nao_suportada(monkeypatch, capsys):
    import charla.cli as cli_mod
    monkeypatch.setattr(cli_mod.sys, "platform", "linux")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "conversas"])

    codigo = cli_mod.main()

    assert codigo == 4
    erro = json.loads(capsys.readouterr().err)
    assert "linux" in erro["erro"]


def test_main_macos_chama_adaptador_macos(tmp_path, monkeypatch, capsys):
    import charla.cli as cli_mod
    from charla.modelo import Conversa

    banco = tmp_path / "ChatStorage.sqlite"
    banco.write_bytes(b"")

    monkeypatch.setattr(cli_mod.sys, "platform", "darwin")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "conversas"])
    monkeypatch.setattr(
        "charla.adaptador_macos.localizacao.localizar_chat_storage", lambda: banco
    )
    monkeypatch.setattr(
        "charla.adaptador_macos.leitura.ler_conversas",
        lambda caminho: [
            Conversa(id="1", nome="X", natureza="direta", total_mensagens=1, ultima_mensagem_em=1)
        ],
    )

    codigo = cli_mod.main()

    assert codigo == 0
    resultado = json.loads(capsys.readouterr().out)
    assert resultado["conversas"][0]["id"] == "1"


def test_main_habilitar_autor_windows_recusa_fora_do_windows(monkeypatch, capsys):
    import charla.cli as cli_mod
    monkeypatch.setattr(cli_mod.sys, "platform", "darwin")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "habilitar-autor-windows"])

    codigo = cli_mod.main()

    assert codigo == 4
    erro = json.loads(capsys.readouterr().err)
    assert "Windows" in erro["erro"]


def test_importar_cli_nao_exige_crypto_fora_do_windows():
    """Achado real de execucao (Plano 3, validacao do .pyz em maquina
    limpa): `charla.adaptador_windows.decifra` faz `from Crypto.Cipher
    import AES` incondicionalmente fora do win32 (dev/CI tem
    pycryptodome real instalado). Import de `decifrar_bases_da_sessao` no
    TOPO de cli.py forcava todo comando -- inclusive `conversas` no macOS
    -- a carregar esse modulo, e numa maquina sem pip install isso
    quebra mesmo quando o comando nunca toca o Adaptador Windows.
    Reproduzido de verdade: `python3 dist/charla.pyz conversas` contra o
    .pyz real, sem pycryptodome instalado, falhava com
    ModuleNotFoundError antes da correcao. Este teste roda em subprocesso
    limpo (sem herdar sys.modules dos outros testes deste arquivo, que
    ja importaram decifra.py via patch) e confere que importar charla.cli
    sozinho NAO importa charla.adaptador_windows.decifra."""
    import subprocess
    import sys

    codigo_python = (
        "import charla.cli; import sys; "
        "assert 'charla.adaptador_windows.decifra' not in sys.modules, "
        "'cli.py importou decifra.py so por ser importado'"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo_python],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_main_macos_anexo_inexistente_recusa_nomeada_sem_stack_trace(tmp_path, monkeypatch, capsys):
    """Achado real (sessão de documentação, medindo antes de escrever):
    ler_anexo do Adaptador macOS levanta ValueError quando o id não
    existe, e nada em cli.py tratava isso -- reproduzido de verdade
    contra o .pyz real (`charla anexo 99999999`), stack trace crua e
    `exit=1` por comportamento padrão do Python, não por desenho. Viola
    o critério 13 da spec (nunca stack trace crua). Corrigido: ValueError
    vira {"erro": ...} + saída JSON limpa, mesmo padrão de todo outro
    erro nomeado do produto."""
    import charla.cli as cli_mod

    banco = tmp_path / "ChatStorage.sqlite"
    banco.write_bytes(b"")

    monkeypatch.setattr(cli_mod.sys, "platform", "darwin")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "anexo", "99999999"])
    monkeypatch.setattr(
        "charla.adaptador_macos.localizacao.localizar_chat_storage", lambda: banco
    )

    def _levanta_nao_encontrado(caminho, anexo_id):
        raise ValueError(f"anexo {anexo_id} não encontrado")

    monkeypatch.setattr(
        "charla.adaptador_macos.leitura.ler_anexo", _levanta_nao_encontrado
    )

    codigo = cli_mod.main()

    assert codigo == 1
    saida = capsys.readouterr()
    erro = json.loads(saida.err)
    assert "99999999" in erro["erro"]


def test_main_macos_excecao_inesperada_vira_erro_nomeado_sem_stack_trace(
    tmp_path, monkeypatch, capsys
):
    """Achado bloqueia da revisão independente da documentação (21/09/2026):
    só ValueError era capturado em _main_macos -- qualquer outra exceção
    (ex.: sqlite3.DatabaseError por banco corrompido/schema divergente numa
    atualização do WhatsApp, risco que o próprio CONTEXTO.md nomeia) escapava
    crua, contradizendo a promessa de comandos-e-saida.md de que 'exit==2 +
    saída não-JSON' é o único caso de saída não-JSON. Reproduzido de verdade
    antes da correção: banco corrompido produzia traceback Python cru em
    stderr com exit=1."""
    import sqlite3

    import charla.cli as cli_mod

    banco = tmp_path / "ChatStorage.sqlite"
    banco.write_bytes(b"")

    monkeypatch.setattr(cli_mod.sys, "platform", "darwin")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "conversas"])
    monkeypatch.setattr(
        "charla.adaptador_macos.localizacao.localizar_chat_storage", lambda: banco
    )

    def _levanta_banco_corrompido(caminho):
        raise sqlite3.DatabaseError("file is not a database")

    monkeypatch.setattr(
        "charla.adaptador_macos.leitura.ler_conversas", _levanta_banco_corrompido
    )

    codigo = cli_mod.main()

    assert codigo == 1
    saida = capsys.readouterr()
    erro = json.loads(saida.err)
    assert "not a database" in erro["erro"]


def test_main_windows_excecao_inesperada_vira_erro_nomeado_sem_stack_trace(
    tmp_path, monkeypatch, capsys
):
    """Mesmo achado do teste macOS acima, lado Windows: em _main_windows,
    args.funcao(...) rodava FORA do try/except que só envolvia
    decifrar_bases_da_sessao -- exceção do adaptador (ex.: schema mudado numa
    atualização do WhatsApp) escapava crua."""
    import charla.adaptador_windows.decifra  # noqa: F401
    import charla.cli as cli_mod

    monkeypatch.setattr(cli_mod.sys, "platform", "win32")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "conversas"])

    with patch("charla.cli.localizar_pasta_local_state") as m_localizar, \
         patch("charla.adaptador_windows.decifra.decifrar_bases_da_sessao"), \
         patch("charla.cli.resolver_nomes_de_grupo", return_value={}), \
         patch(
             "charla.cli.ler_conversas",
             side_effect=RuntimeError("schema inesperado: coluna sumiu"),
         ):
        m_localizar.return_value = tmp_path
        codigo = cli_mod.main()

    assert codigo == 1
    saida = capsys.readouterr()
    erro = json.loads(saida.err)
    assert "schema inesperado" in erro["erro"]


def test_main_versao_imprime_charla_e_o_numero_sem_tocar_plataforma(monkeypatch, capsys):
    """`versao` responde antes de qualquer dispatch por sys.platform --
    roda em qualquer SO, sem WhatsApp instalado, sem decifra. Formato
    "charla X.Y.Z" -- CI faz `awk '{print $2}'` sobre esta saida pra
    conferir tag == versao do pacote, mesmo padrao do koine."""
    import charla.cli as cli_mod
    from charla._version import __version__

    monkeypatch.setattr(cli_mod.sys, "platform", "um-so-que-nao-existe")
    monkeypatch.setattr(cli_mod.sys, "argv", ["charla", "versao"])

    codigo = cli_mod.main()

    assert codigo == 0
    saida = capsys.readouterr().out.strip()
    assert saida == f"charla {__version__}"
