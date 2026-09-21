# achado bloqueia da revisao dev-10 (3a rodada): Path nunca era usado aqui
# (os testes usam o Path que diretorio_de_trabalho() ja devolve)
from charla.adaptador_windows.sessao_temporaria import diretorio_de_trabalho


def test_diretorio_de_trabalho_apaga_ao_sair_do_context_manager():
    caminho_capturado = None
    with diretorio_de_trabalho() as d:
        caminho_capturado = d
        assert d.is_dir()
        (d / "teste.txt").write_text("x")
    assert not caminho_capturado.exists()


def test_diretorio_de_trabalho_apaga_mesmo_quando_o_bloco_levanta_excecao():
    caminho_capturado = None
    try:
        with diretorio_de_trabalho() as d:
            caminho_capturado = d
            raise RuntimeError("falha simulada")
    except RuntimeError:
        pass
    assert not caminho_capturado.exists()


def test_diretorio_de_trabalho_avisa_no_stderr_se_remocao_sobreviver(capsys, monkeypatch):
    """Achado ajusta da revisão dev-10 (2ª rodada): `ignore_errors=True`
    engolia falha de remoção em silêncio total. Agora avisa, sem levantar
    (levantar aqui mascararia uma exceção real do bloco `with`)."""
    import charla.adaptador_windows.sessao_temporaria as modulo

    monkeypatch.setattr(modulo.shutil, "rmtree", lambda *a, **k: None)  # nunca remove de verdade
    with diretorio_de_trabalho() as d:
        pass
    assert d.exists()  # a pasta real sobrevive porque o rmtree foi substituido
    saida_erro = capsys.readouterr().err
    assert "AVISO" in saida_erro and str(d) in saida_erro
    d.rmdir()  # limpeza manual do teste, ja que o mock impediu a remocao real
