import stat

import pytest

from charla.escrita_atomica import copiar, escrever_bytes, validar_destino


def test_validar_destino_aceita_caminho_gravavel(tmp_path):
    destino = tmp_path / "saida.bin"
    validar_destino(destino)  # não levanta


def test_validar_destino_recusa_pasta_pai_inexistente(tmp_path):
    destino = tmp_path / "pasta-que-nao-existe" / "saida.bin"
    with pytest.raises(ValueError, match="não existe"):
        validar_destino(destino)


def test_validar_destino_recusa_diretorio_existente(tmp_path):
    with pytest.raises(ValueError, match="diretório"):
        validar_destino(tmp_path)


def test_validar_destino_recusa_pasta_sem_permissao_de_escrita(tmp_path):
    pasta_sem_permissao = tmp_path / "trancada"
    pasta_sem_permissao.mkdir()
    pasta_sem_permissao.chmod(stat.S_IREAD)
    try:
        with pytest.raises(ValueError, match="permissão"):
            validar_destino(pasta_sem_permissao / "saida.bin")
    finally:
        pasta_sem_permissao.chmod(stat.S_IRWXU)  # senão tmp_path não limpa


def test_escrever_bytes_grava_o_conteudo(tmp_path):
    destino = tmp_path / "saida.bin"
    escrever_bytes(destino, b"conteudo de teste")
    assert destino.read_bytes() == b"conteudo de teste"


def test_escrever_bytes_nao_deixa_arquivo_temporario_para_tras(tmp_path):
    destino = tmp_path / "saida.bin"
    escrever_bytes(destino, b"x")
    restantes = list(tmp_path.iterdir())
    assert restantes == [destino]


def test_escrever_bytes_substitui_arquivo_existente_por_inteiro(tmp_path):
    destino = tmp_path / "saida.bin"
    destino.write_bytes(b"conteudo antigo bem maior que o novo")
    escrever_bytes(destino, b"novo")
    assert destino.read_bytes() == b"novo"


def test_escrever_bytes_recusa_destino_invalido_antes_de_qualquer_escrita(tmp_path):
    destino = tmp_path / "pasta-inexistente" / "saida.bin"
    with pytest.raises(ValueError):
        escrever_bytes(destino, b"nunca deveria ser escrito")
    assert not destino.parent.exists()


def test_copiar_produz_arquivo_identico(tmp_path):
    origem = tmp_path / "origem.bin"
    origem.write_bytes(b"bytes originais")
    destino = tmp_path / "copia.bin"
    copiar(origem, destino)
    assert destino.read_bytes() == origem.read_bytes()
    assert destino != origem
