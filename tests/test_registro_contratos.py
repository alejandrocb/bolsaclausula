"""Registro persistente de contratos: congelado del alta y detección de nuevos."""
from datetime import date

from bolsa.registro_contratos import RegistroContratos
from conftest import contrato


def test_primera_aparicion_marca_nuevos_y_congela_alta(tmp_path):
    ruta = tmp_path / "estado" / "registro_contratos.csv"
    c = contrato(idrh="11111111H", periodo="5", inicio="2026-07-10", fin=None)
    c.alta = date(2026, 7, 12)

    reg = RegistroContratos.carga(ruta)
    reg.actualiza([c], date(2026, 8, 4))
    reg.guarda(ruta)
    assert ("11111111H", "5") in reg.nuevos
    info = reg.info()[("11111111H", "5")]
    assert info["alta_congelada"] == date(2026, 7, 12)
    assert info["primera_aparicion"] == date(2026, 8, 4)
    assert info["nuevo"] is True


def test_segunda_importacion_no_es_nuevo_y_mantiene_alta(tmp_path):
    ruta = tmp_path / "estado" / "registro_contratos.csv"
    c = contrato(idrh="11111111H", periodo="5", inicio="2026-07-10", fin=None)
    c.alta = date(2026, 7, 12)
    reg = RegistroContratos.carga(ruta)
    reg.actualiza([c], date(2026, 8, 4))
    reg.guarda(ruta)

    # segunda importación: el contrato fue modificado (alta 'actual' distinta)
    c.alta = date(2026, 8, 20)
    reg2 = RegistroContratos.carga(ruta)
    reg2.actualiza([c], date(2026, 8, 11))
    assert reg2.nuevos == set()                      # ya no es nuevo
    info = reg2.info()[("11111111H", "5")]
    assert info["alta_congelada"] == date(2026, 7, 12)   # se mantiene congelada
    assert info["nuevo"] is False


def test_contrato_sin_fechas_usa_fecha_importacion(tmp_path):
    ruta = tmp_path / "estado" / "registro_contratos.csv"
    c = contrato(idrh="22222222J", periodo="1")
    c.alta = None
    reg = RegistroContratos.carga(ruta)
    reg.actualiza([c], date(2026, 8, 4))
    assert reg.info()[("22222222J", "1")]["alta_congelada"] == date(2026, 8, 4)
