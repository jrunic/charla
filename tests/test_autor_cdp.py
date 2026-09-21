from charla.adaptador_windows.autor_cdp import porta_de_debug_esta_aberta


def test_porta_de_debug_esta_aberta_falso_quando_nada_escuta():
    # porta alta improvável de ter algo escutando durante o teste
    assert porta_de_debug_esta_aberta(porta=59222, timeout_s=0.5) is False


from unittest.mock import patch

import pytest

from charla.adaptador_windows.autor_cdp import EsperaDeDebugFalhou


def test_habilitar_debug_e_reiniciar_recusa_nomeado_se_porta_nunca_abrir():
    from charla.adaptador_windows.autor_cdp import habilitar_debug_e_reiniciar

    with patch("charla.adaptador_windows.autor_cdp.garantir_porta_de_debug", return_value="adicionado"), \
         patch("charla.adaptador_windows.autor_cdp.subprocess.run"), \
         patch("charla.adaptador_windows.autor_cdp.time.sleep"), \
         patch("charla.adaptador_windows.autor_cdp.porta_de_debug_esta_aberta", return_value=False), \
         pytest.raises(EsperaDeDebugFalhou, match="não abriu"):
        habilitar_debug_e_reiniciar(tentativas_de_espera=3, intervalo_s=0.01)


def test_habilitar_debug_e_reiniciar_recusa_nomeado_se_registro_falhar():
    from charla.adaptador_windows.autor_cdp import habilitar_debug_e_reiniciar

    with patch("charla.adaptador_windows.autor_cdp.garantir_porta_de_debug", return_value="falhou"), \
         pytest.raises(EsperaDeDebugFalhou, match="registro"):
        habilitar_debug_e_reiniciar()


from charla.adaptador_windows.autor_cdp import (
    montar_expressao_abrir_chat_e_marcar,
    montar_expressao_busca_autores,
    montar_expressao_busca_nomes_de_grupo,
)


def test_montar_expressao_busca_autores_inclui_os_ids_pedidos():
    expr = montar_expressao_busca_autores(["999889713", "999889714"])
    assert "999889713" in expr
    assert "999889714" in expr
    assert "WAWebCollections" in expr


def test_montar_expressao_abrir_chat_e_marcar_inclui_o_chat_id():
    expr = montar_expressao_abrir_chat_e_marcar("120363021901138870@g.us")
    assert "120363021901138870@g.us" in expr
    assert "openChatAt" in expr
    assert "markChatUnread" in expr
    # a leitura do estado ANTES de abrir e a condicao que so restaura quando
    # ja estava nao lida - achado bloqueia 3 da revisao dev-10 (2a rodada):
    # markChatUnread incondicional marcava toda conversa consultada
    assert "unreadCount" in expr
    assert "jaEstavaNaoLida" in expr


def test_montar_expressao_busca_nomes_de_grupo_inclui_os_ids_pedidos():
    expr = montar_expressao_busca_nomes_de_grupo(["1@g.us", "2@g.us"])
    assert "1@g.us" in expr
    assert "2@g.us" in expr
    assert "WAWebCollections" in expr
