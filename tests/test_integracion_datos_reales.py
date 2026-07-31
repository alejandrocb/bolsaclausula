"""Pruebas de integración sobre los datos reales (si están presentes en data/).

Se saltan automáticamente si la carpeta data/ no existe (p.ej. en CI sin los
ficheros con datos personales).
"""
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DATA_INI = RAIZ / "data" / "inicial"
DATA_PER = RAIZ / "data" / "periodicas"

pytestmark = pytest.mark.skipif(
    not (DATA_INI.exists() and DATA_PER.exists()),
    reason="Datos reales no presentes (data/ está en .gitignore)",
)


def _busca(carpeta, patron):
    xs = sorted(Path(carpeta).glob(patron))
    return xs[-1] if xs else None


def test_corte_inicial_cuadra_al_100():
    from bolsa.cargas.inicial import carga_saldo_inicial
    si = carga_saldo_inicial(_busca(DATA_INI, "*auditoria*.csv"))
    descuadres = [k for k, v in si.items() if not v.cuadra()]
    assert descuadres == []


def test_auditoria_y_postcontrol_coinciden():
    from bolsa.cargas.inicial import carga_saldo_inicial, carga_postcontrol
    si = carga_saldo_inicial(_busca(DATA_INI, "*auditoria*.csv"))
    post = carga_postcontrol(_busca(DATA_INI, "*post_control*.csv"))
    for k, v in post.items():
        if k in si:
            assert si[k].saldo_postcontrol == v


def test_conciliacion_completa_mantiene_identidad_contable():
    from bolsa.cli import ejecuta
    res = ejecuta(DATA_INI, DATA_PER, RAIZ / "salidas")["resultado"]
    for f in res.detalle:
        assert f.saldo_calculado == (
            f.saldo_postcontrol - f.consumo_posterior
            + f.devolucion_posterior + f.devolucion_cierre + f.ajuste_peoplenet
        )
    # el ajuste PeopleNet (cláusula+dirección) mueve saldo dentro de la MISMA
    # plaza; la suma global sobre cláusulas prioritarias es <= 0 (parte puede
    # marcharse a cláusulas no prioritarias vía contrato).
    total_ajuste = sum(f.ajuste_peoplenet for f in res.detalle)
    assert total_ajuste <= 0


def test_movimientos_ids_unicos():
    from bolsa.cargas.periodicas import carga_movimientos
    from bolsa.importaciones import dedup_movimientos
    mov = carga_movimientos(_busca(DATA_PER, "MovimientosBolsa*.csv"))
    assert len(mov) == len(dedup_movimientos(mov))
