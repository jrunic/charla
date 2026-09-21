from charla.modelo import Anexo, Conversa, Mensagem


def test_conversa_serializa_para_dict():
    c = Conversa(id="123@g.us", nome="Grupo Teste", natureza="coletiva",
                 total_mensagens=10, ultima_mensagem_em=1789686509)
    d = c.para_dict()
    assert d == {
        "id": "123@g.us",
        "nome": "Grupo Teste",
        "natureza": "coletiva",
        "total_mensagens": 10,
        "ultima_mensagem_em": 1789686509,
    }


def test_mensagem_sem_autor_serializa_autor_null():
    m = Mensagem(id="999889713", conversa_id="123@g.us", texto="oi",
                  instante=1789686509, autor=None)
    assert m.para_dict()["autor"] is None


def test_anexo_serializa_para_dict():
    a = Anexo(id="abc123", conversa_id="123@g.us", tipo="imagem",
              caminho_absoluto="/tmp/foto.jpg")
    assert a.para_dict() == {
        "id": "abc123",
        "conversa_id": "123@g.us",
        "tipo": "imagem",
        "caminho_absoluto": "/tmp/foto.jpg",
    }
