"""Testa só o MECANISMO de extração — não importa Crypto.Cipher.AES de
verdade aqui, porque os .pyd vendorizados são win_amd64 e este teste roda
em qualquer SO (CI é Linux). O que se testa: dado um zip de exemplo (não o
pycryptodome real), extrair para o diretório de cache e inserir em
sys.path funciona e é idempotente."""
import sys
import zipfile

from charla._vendor.pycryptodome_carregador import _extrair_e_inserir_em_path


def test_extrai_uma_vez_e_reusa_na_segunda_chamada(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "charla._vendor.pycryptodome_carregador._PASTA_CACHE_BASE", tmp_path / "cache"
    )

    zip_exemplo = tmp_path / "exemplo.zip"
    with zipfile.ZipFile(zip_exemplo, "w") as zf:
        zf.writestr("Crypto/__init__.py", "")
        zf.writestr("Crypto/marca.txt", "conteudo original")

    pasta1 = _extrair_e_inserir_em_path(zip_exemplo)
    assert (pasta1 / "Crypto" / "marca.txt").read_text() == "conteudo original"
    assert str(pasta1) in sys.path

    (pasta1 / "Crypto" / "marca.txt").write_text("modificado a mao")
    pasta2 = _extrair_e_inserir_em_path(zip_exemplo)
    assert pasta2 == pasta1
    assert (pasta2 / "Crypto" / "marca.txt").read_text() == "modificado a mao", (
        "segunda chamada nao deveria re-extrair, entao a modificacao a mao sobrevive"
    )
