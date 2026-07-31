"""Pruebas del reparto por dirección real (GFH) — el contrato manda."""
from datetime import date

from bolsa.cargas.maestros import carga_divisiones
from bolsa.modelo import ClavePlaza
from bolsa.motor import conciliar, reparte_dias

from conftest import bolsa, contrato, propuesta, saldo_inicial

CORTE = date(2026, 7, 2)
LIMITE = date(2026, 12, 31)


def _d(s):
    return date.fromisoformat(s)


def _escribe_xlsx(ruta, hoja, filas):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = hoja
    for r in filas:
        ws.append(r)
    wb.save(ruta)


def test_carga_contratos_agrupa_tramos_y_resuelve_division(tmp_path):
    div = tmp_path / "Divisiones_Plazas_GFHs.xlsx"
    _escribe_xlsx(div, "Hoja1", [
        ["ID Plaza", "DG", "ID GFH", "División asignada", "Nivel"],
        ["E130E", "Celador", "GFHA", "DEAE", "AE"],
        ["E130E", "Celador", "GFHB", "DGSG", "SG"],
    ])
    from bolsa.cargas.maestros import carga_divisiones
    from bolsa.cargas.periodicas import carga_contratos
    divisiones = carga_divisiones(div)
    assert divisiones[("E130E", "GFHA")] == "DEAE"

    contr = tmp_path / "Contratos_PeopleNet.xlsx"
    _escribe_xlsx(contr, "Query", [
        ["ID RH", "Núm. periodo", "Inicio Plaza", "Fin Plaza", "Id. Cláusula",
         "Motivo inicio", "ID Plaza", "Descripción Plaza", "Inicio GFH", "Fin GFH",
         "id. GFH1", "Nombre GFH"],
        ["11111111H", 5, "01/07/2026", "31/07/2026", "S9b1a", "ENF", "E130E", "Celador",
         "01/07/2026", "15/07/2026", "GFHA", "A"],
        ["11111111H", 5, "01/07/2026", "31/07/2026", "S9b1a", "ENF", "E130E", "Celador",
         "16/07/2026", "31/07/2026", "GFHB", "B"],
    ])
    contratos = carga_contratos(contr, divisiones)
    assert len(contratos) == 1                 # una fila por (idrh, periodo)
    assert len(contratos[0].tramos) == 2       # dos tramos GFH
    assert contratos[0].divisiones == ["DEAE", "DGSG"]


def test_reparte_dias_dos_tramos():
    from bolsa.modelo import TramoGFH
    tramos = [
        TramoGFH(_d("2026-07-01"), _d("2026-07-15"), "G1", "n", "DEAE"),
        TramoGFH(_d("2026-07-16"), None, "G2", "n", "DGSG"),
    ]
    reparto, sin = reparte_dias(_d("2026-07-01"), _d("2026-07-31"), tramos)
    assert reparto == {"DEAE": 15, "DGSG": 16}
    assert sin == 0
    assert sum(reparto.values()) + sin == 31


def test_reparte_dias_con_hueco():
    from bolsa.modelo import TramoGFH
    tramos = [TramoGFH(_d("2026-07-10"), _d("2026-07-20"), "G1", "n", "DEAE")]
    reparto, sin = reparte_dias(_d("2026-07-01"), _d("2026-07-31"), tramos)
    assert reparto == {"DEAE": 11}    # 10..20
    assert sin == 20                  # 1..9 (9) + 21..31 (11)


def test_direccion_real_del_contrato_manda():
    # propuesta en DEAP, pero el contrato se ejecuta en DEAE
    p = propuesta(id_plaza="E071A2", direccion="DEAP", clausula="S9b1a",
                  inicio="2026-07-10", fin="2026-07-31")
    c = contrato(id_plaza="E071A2", clausula="S9b1a", inicio="2026-07-10",
                 fin=None, division="DEAE")
    _, si_ap = saldo_inicial(direccion="DEAP", base=1000)
    _, si_ae = saldo_inicial(direccion="DEAE", base=1000)
    res = conciliar({si_ap.clave: si_ap, si_ae.clave: si_ae},
                    [p], [c], [], [], [bolsa("S9b1a")])
    f_ap = next(f for f in res.detalle if f.direccion_codigo == "DEAP")
    f_ae = next(f for f in res.detalle if f.direccion_codigo == "DEAE")
    assert f_ap.saldo_calculado == 1000          # la propuesta NO consume DEAP
    assert f_ae.saldo_calculado == 1000 - 22     # consume DEAE (dirección real)
    det = res.detalle_propuestas[0]
    assert det.direccion_distinta
    assert det.direccion_efectiva == "DEAE"


def test_contrato_con_cambio_de_gfh_reparte_entre_direcciones():
    # medio contrato en DEAE, medio en DGSG
    p = propuesta(id_plaza="E130E", direccion="DEAE", clausula="S9b1a",
                  inicio="2026-07-01", fin="2026-07-31")
    c = contrato(id_plaza="E130E", clausula="S9b1a", inicio="2026-07-01", fin="2026-07-31",
                 tramos=[("2026-07-01", "2026-07-15", "DEAE"),
                         ("2026-07-16", "2026-07-31", "DGSG")])
    _, si_ae = saldo_inicial(id_plaza="E130E", direccion="DEAE", base=500)
    _, si_gs = saldo_inicial(id_plaza="E130E", direccion="DGSG", base=500)
    res = conciliar({si_ae.clave: si_ae, si_gs.clave: si_gs},
                    [p], [c], [], [], [bolsa("S9b1a")])
    f_ae = next(f for f in res.detalle if f.direccion_codigo == "DEAE")
    f_gs = next(f for f in res.detalle if f.direccion_codigo == "DGSG")
    assert f_ae.saldo_calculado == 500 - 15
    assert f_gs.saldo_calculado == 500 - 16
    # suma consumida = 31 días repartidos
    assert (500 - f_ae.saldo_calculado) + (500 - f_gs.saldo_calculado) == 31
