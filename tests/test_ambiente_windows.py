from charla.adaptador_windows.ambiente_windows import (
    ADICIONADO,
    JA_ESTAVA,
    REG_EXPAND_SZ,
    SUBSTITUIDO,
    compor_argumentos,
    garantir_porta_de_debug,
)


def test_compor_argumentos_acrescenta_quando_variavel_vazia():
    novo, status = compor_argumentos("", porta=9222)
    assert novo == "--remote-debugging-port=9222"
    assert status == ADICIONADO


def test_compor_argumentos_preserva_argumento_de_terceiro():
    novo, status = compor_argumentos("--disable-gpu", porta=9222)
    assert novo == "--disable-gpu --remote-debugging-port=9222"
    assert status == ADICIONADO


def test_compor_argumentos_preserva_quoting_com_espaco_interno():
    # achado bloqueia da revisao dev-10 (3a rodada): a versao anterior
    # fazia valor.split()/" ".join(partes), que colapsava espaco e
    # retokenizava argumento entre aspas -- este teste MORRE com esse
    # defeito de volta (o anterior, com token sem espaco, nao morria)
    valor_com_aspas = '--user-data-dir="C:\\Program Files\\WebView2" --disable-gpu'
    novo, status = compor_argumentos(valor_com_aspas, porta=9222)
    assert novo == valor_com_aspas + " --remote-debugging-port=9222"
    assert status == ADICIONADO


def test_compor_argumentos_e_idempotente_quando_a_porta_ja_e_a_mesma():
    novo, status = compor_argumentos("--remote-debugging-port=9222", porta=9222)
    assert novo is None
    assert status == JA_ESTAVA


def test_compor_argumentos_substitui_so_a_nossa_entrada_quando_porta_diferente():
    novo, status = compor_argumentos(
        "--disable-gpu --remote-debugging-port=9111 --disable-sync", porta=9222,
    )
    assert novo == "--disable-gpu --remote-debugging-port=9222 --disable-sync"
    assert status == SUBSTITUIDO


class _RegistroFalso:
    """Substitui RegistroDeAmbienteUsuario nos testes — sem winreg real,
    então roda em qualquer SO (troca `reg=` no teste em vez de mockar
    `winreg` diretamente)."""

    def __init__(self, valor_inicial=None, tipo_inicial=None):
        self.valor = valor_inicial
        self.tipo = tipo_inicial
        self.escritas = []

    def ler(self):
        return self.valor, self.tipo

    def gravar(self, valor, tipo):
        self.escritas.append((valor, tipo))
        self.valor, self.tipo = valor, tipo


def test_garantir_porta_de_debug_e_idempotente_e_nao_escreve_de_novo():
    reg = _RegistroFalso(valor_inicial="--remote-debugging-port=9222", tipo_inicial=REG_EXPAND_SZ)
    status1 = garantir_porta_de_debug(9222, reg=reg, notificar=lambda: True)
    status2 = garantir_porta_de_debug(9222, reg=reg, notificar=lambda: True)
    assert status1 == status2 == "ja_estava"
    assert len(reg.escritas) == 0


def test_garantir_porta_de_debug_preserva_tipo_original_do_registro():
    reg = _RegistroFalso(valor_inicial="--disable-gpu", tipo_inicial=1)  # REG_SZ
    garantir_porta_de_debug(9222, reg=reg, notificar=lambda: True)
    assert reg.escritas == [("--disable-gpu --remote-debugging-port=9222", 1)]


def test_garantir_porta_de_debug_notifica_o_sistema_apos_escrever():
    chamadas = []
    reg = _RegistroFalso()
    garantir_porta_de_debug(9222, reg=reg, notificar=lambda: chamadas.append(1))
    assert chamadas == [1]


def test_garantir_porta_de_debug_nao_notifica_quando_ja_estava():
    chamadas = []
    reg = _RegistroFalso(valor_inicial="--remote-debugging-port=9222", tipo_inicial=REG_EXPAND_SZ)
    garantir_porta_de_debug(9222, reg=reg, notificar=lambda: chamadas.append(1))
    assert chamadas == []


class _RegistroQueFalhaAoGravar(_RegistroFalso):
    """Achado ajusta da revisão dev-10 (3ª rodada): o ramo FALHOU de
    garantir_porta_de_debug não tinha teste nenhum -- os quatro testes
    acima usam um fake que nunca levanta."""

    def gravar(self, valor, tipo):
        raise OSError("acesso negado (simulado)")


def test_garantir_porta_de_debug_devolve_falhou_quando_registro_recusa_escrita():
    reg = _RegistroQueFalhaAoGravar()
    status = garantir_porta_de_debug(9222, reg=reg, notificar=lambda: True)
    assert status == "falhou"
