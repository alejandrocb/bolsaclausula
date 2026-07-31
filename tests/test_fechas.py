from datetime import date

from bolsa.fechas import dias_inclusivos, fin_computable, parse_fecha, solapan


def test_conteo_inclusivo_mismo_dia():
    assert dias_inclusivos(date(2026, 7, 10), date(2026, 7, 10)) == 1


def test_conteo_inclusivo_incluye_fines_de_semana():
    # 10/07 (vie) a 31/07 = 22 días naturales inclusive
    assert dias_inclusivos(date(2026, 7, 10), date(2026, 7, 31)) == 22


def test_conteo_intervalo_invalido():
    assert dias_inclusivos(date(2026, 7, 31), date(2026, 7, 10)) == 0
    assert dias_inclusivos(None, date(2026, 7, 10)) == 0


def test_fin_computable_abierto_topa_limite():
    limite = date(2026, 12, 31)
    assert fin_computable(None, None, False, limite) == limite


def test_fin_computable_cerrado_toma_el_menor():
    limite = date(2026, 12, 31)
    # contrato cierra antes que la propuesta -> manda el contrato
    assert fin_computable(date(2026, 9, 30), date(2026, 8, 15), True, limite) == date(2026, 8, 15)


def test_fin_computable_2027_se_recorta():
    limite = date(2026, 12, 31)
    assert fin_computable(date(2027, 6, 30), None, False, limite) == limite


def test_parse_varios_formatos():
    assert parse_fecha("2026-07-10 09:14:08") == date(2026, 7, 10)
    assert parse_fecha("10/07/2026") == date(2026, 7, 10)
    assert parse_fecha("") is None
    assert parse_fecha(None) is None


def test_solape_fin_vacio_es_abierto():
    limite = date(2026, 12, 31)
    assert solapan(date(2026, 7, 1), None, date(2026, 12, 1), None, limite)
    assert not solapan(date(2026, 7, 1), date(2026, 7, 15),
                       date(2026, 8, 1), date(2026, 8, 15), limite)
