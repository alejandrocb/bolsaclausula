"""Fixtures y factorías para las pruebas."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bolsa.modelo import (  # noqa: E402
    BolsaPeopleNet, ClavePlaza, Contrato, Movimiento, Propuesta,
    SaldoActual, SaldoInicial,
)


def d(txt):
    return date.fromisoformat(txt)


def propuesta(pid="1", id_plaza="E071A2", direccion="DEAP", clausula="S9b1a",
              estado="APROBADA", sub_estado="MECANIZADA",
              autorizacion="2026-07-10", inicio="2026-07-10", fin="2026-07-31",
              idrh="12345678Z", original="", sustituta=""):
    return Propuesta(
        propuesta_id=pid, id_plaza=id_plaza, direccion_codigo=direccion,
        clausula=clausula, estado=estado, sub_estado=sub_estado,
        fecha_autorizacion=d(autorizacion) if autorizacion else None,
        fecha_inicio=d(inicio) if inicio else None,
        fecha_fin=d(fin) if fin else None,
        idrh=idrh, propuesta_original_id=original, propuesta_sustituta_id=sustituta,
    )


def contrato(idrh="12345678Z", periodo="1", id_plaza="E071A2", clausula="S9b1a",
             inicio="2026-07-10", fin=None, motivo="ENF"):
    return Contrato(
        idrh=idrh, num_periodo=periodo, id_plaza=id_plaza, clausula=clausula,
        fecha_inicio=d(inicio) if inicio else None,
        fecha_fin=d(fin) if fin else None, motivo_inicio=motivo,
    )


def saldo_inicial(id_plaza="E071A2", direccion="DEAP", clausula="S9b1a",
                  base=1000, nuevos=0, recuperados=0, direccion_nombre="Dir AP",
                  categoria="Enfermera/o"):
    post = base - nuevos + recuperados
    clave = ClavePlaza(id_plaza, direccion, clausula)
    return clave, SaldoInicial(
        clave=clave, direccion_id="7", direccion_nombre=direccion_nombre,
        descripcion_categoria=categoria, saldo_postcontrol=post,
        saldo_base_02_07=base, nuevos_control=nuevos, recuperados_control=recuperados,
        origen_ajustes="",
    )


def movimiento(mid="1", pid="1", tipo="DEVOLUCION_SOLICITUD", importe=-10,
               id_plaza="E071A2", direccion="DEAP", clausula="S9b1a",
               fecha="2026-07-27"):
    return Movimiento(
        movimiento_id=mid, bolsa_dias_id="b1", propuesta_id=pid,
        fecha_movimiento=d(fecha), tipo_movimiento=tipo, importe=importe,
        id_plaza=id_plaza, direccion_codigo=direccion, clausula=clausula,
    )


def bolsa(clausula="S9b1a", contratacion=100000, usados=50000):
    return BolsaPeopleNet(anio=2026, clausula=clausula,
                          dias_contratacion=contratacion, dias_usados=usados)


@pytest.fixture
def bolsas():
    return [bolsa("N91c", 100000, 50000), bolsa("S9b1a", 200000, 100000)]
