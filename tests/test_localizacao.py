import pytest

from charla.adaptador_windows.localizacao import (
    ArquiteturaNaoSuportada,
    localizar_pasta_local_state,
)


def test_localizar_pasta_local_state_acha_uwp(tmp_path):
    pacotes = tmp_path / "Packages"
    pasta_uwp = pacotes / "5319275A.WhatsAppDesktop_cv1g1gvanyjgm" / "LocalState"
    pasta_uwp.mkdir(parents=True)
    resultado = localizar_pasta_local_state(raiz_packages=pacotes)
    assert resultado == pasta_uwp


def test_localizar_pasta_local_state_recusa_quando_ausente(tmp_path):
    pacotes = tmp_path / "Packages"
    pacotes.mkdir()
    with pytest.raises(ArquiteturaNaoSuportada, match="UWP"):
        localizar_pasta_local_state(raiz_packages=pacotes)
