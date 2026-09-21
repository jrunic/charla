"""Testes de charla.adaptador_macos.leitura."""
import hashlib

from charla.adaptador_macos.leitura import ler_anexo, ler_conversas, ler_mensagens
from tests.fixtures.gerar_chatstorage import gerar_chatstorage


def test_ler_conversas_devolve_direta_e_grupo_com_natureza_correta(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    conversas = ler_conversas(banco)
    por_id = {c.id: c for c in conversas}

    assert por_id["5511999990002@s.whatsapp.net"].natureza == "direta"
    assert por_id["5511999990002@s.whatsapp.net"].nome == "Ana"
    assert por_id["5511999990002@s.whatsapp.net"].total_mensagens == 2

    assert por_id["111222333@g.us"].natureza == "grupo"
    assert por_id["111222333@g.us"].nome == "Equipe"
    assert por_id["111222333@g.us"].total_mensagens == 3


def test_ler_conversas_nao_inclui_tipo_status(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    conversas = ler_conversas(banco)
    ids = [c.id for c in conversas]

    assert "5511988887777@status" not in ids
    assert len(conversas) == 2


def test_ler_mensagens_resolve_autor_direta_eu_e_parceiro(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    direta_id = "5511999990002@s.whatsapp.net"
    mensagens = ler_mensagens(banco, direta_id)

    assert len(mensagens) == 2
    assert mensagens[0].texto == "oi"
    assert mensagens[0].autor == "Ana"
    assert mensagens[1].texto == "oi, tudo bem?"
    assert mensagens[1].autor == "eu"


def test_ler_mensagens_resolve_autor_grupo_via_groupmember(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    mensagens = ler_mensagens(banco, "111222333@g.us")
    por_texto = {m.texto: m for m in mensagens if m.texto is not None}

    # membro sem nome (ZCONTACTNAME vazio) -> cai no JID
    assert por_texto["bom dia"].autor == "556511112222@lid"
    # membro com nome (ZCONTACTNAME preenchido) -> usa o nome
    assert por_texto["bom dia!"].autor == "Marcos"


def test_ler_mensagens_autor_none_quando_groupmember_nulo(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    mensagens = ler_mensagens(banco, "111222333@g.us")
    mensagem_sistema = next(m for m in mensagens if m.texto is None)

    assert mensagem_sistema.autor is None


def test_ler_anexo_devolve_caminho_absoluto_e_tipo(tmp_path):
    grupo = tmp_path / "Library" / "Group Containers" / "group.net.whatsapp.WhatsApp.shared"
    grupo.mkdir(parents=True)
    banco = grupo / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    anexo = ler_anexo(banco, "1")

    assert anexo.tipo == "imagem"
    assert anexo.caminho_absoluto.endswith(
        "Group Containers/group.net.whatsapp.WhatsApp.shared/Message/Media/111222333@g.us/9/f/foto.jpg"
    )


def _sha256(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def test_leitura_nao_escreve_no_arquivo_original(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)
    hash_antes = _sha256(banco)

    ler_conversas(banco)
    ler_mensagens(banco, "111222333@g.us")

    assert _sha256(banco) == hash_antes


def test_leitura_e_deterministica_entre_duas_execucoes(tmp_path):
    banco = tmp_path / "ChatStorage.sqlite"
    gerar_chatstorage(banco)

    primeira = [c.para_dict() for c in ler_conversas(banco)]
    segunda = [c.para_dict() for c in ler_conversas(banco)]

    assert primeira == segunda
