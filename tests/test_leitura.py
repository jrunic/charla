from charla.adaptador_windows.leitura import ler_conversas, ler_mensagens
from tests.fixtures.gerar_contacts import gerar as gerar_contacts
from tests.fixtures.gerar_genericstorage import gerar as gerar_generic_storage


def _preparar(tmp_path):
    caminho_gs = tmp_path / "genericStorage.dec.db"
    caminho_contacts = tmp_path / "contacts.dec.db"
    gerar_generic_storage(caminho_gs)
    gerar_contacts(caminho_contacts)
    return caminho_gs, caminho_contacts


def test_ler_conversas_devolve_direta_e_coletiva(tmp_path):
    caminho_gs, caminho_contacts = _preparar(tmp_path)
    conversas = ler_conversas(caminho_gs, caminho_contacts)
    por_id = {c.id: c for c in conversas}

    direta = por_id["5511999990001@lid"]
    assert direta.natureza == "direta"
    assert direta.nome == "Fulano de Teste"
    assert direta.total_mensagens == 2
    assert direta.ultima_mensagem_em == 1789600010

    coletiva = por_id["120363021901138870@g.us"]
    assert coletiva.natureza == "coletiva"
    assert coletiva.total_mensagens == 3
    assert coletiva.ultima_mensagem_em == 1789600040


def test_ler_mensagens_ordenadas_cronologicamente_sem_autor(tmp_path):
    caminho_gs, _ = _preparar(tmp_path)
    mensagens = ler_mensagens(caminho_gs, "120363021901138870@g.us")
    assert [m.texto for m in mensagens] == [
        "bom dia grupo", "bom dia!", "alguém viu o combinado?",
    ]
    assert all(m.autor is None for m in mensagens)


def test_ler_mensagens_conversa_inexistente_devolve_lista_vazia(tmp_path):
    caminho_gs, _ = _preparar(tmp_path)
    assert ler_mensagens(caminho_gs, "nao-existe@g.us") == []
