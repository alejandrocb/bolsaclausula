"""Interfaz de línea de comandos de la conciliación.

Uso típico:
    python -m bolsa.cli \
        --inicial data/inicial \
        --periodicas data/periodicas \
        --salida salidas

Genera en la carpeta de salida:
    conciliacion_<fecha>.xlsx   (detalle, resumen, totales, semáforo, auditoría)
    recarga_propuestas_<fecha>.xlsx
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .cargas.inicial import carga_saldo_inicial, carga_postcontrol, carga_diario
from .cargas.maestros import carga_divisiones
from .cargas.periodicas import (
    carga_bolsa_peoplenet,
    carga_contratos,
    carga_movimientos,
    carga_propuestas,
    carga_saldo_actual,
)
from .config import CONFIG
from .equivalencias import Equivalencias
from .exportar import exporta_conciliacion, exporta_recarga
from .importaciones import dedup_movimientos, dedup_propuestas, registra
from .motor import conciliar


def _busca(carpeta: Path, patron: str) -> Path:
    coincidencias = sorted(carpeta.glob(patron))
    if not coincidencias:
        raise FileNotFoundError(f"No se encontró '{patron}' en {carpeta}")
    return coincidencias[-1]


def _busca_op(carpeta: Path, patron: str):
    coincidencias = sorted(Path(carpeta).glob(patron))
    return coincidencias[-1] if coincidencias else None


def ejecuta(dir_inicial: Path, dir_periodicas: Path, dir_salida: Path,
            equivalencias_csv=None, dir_maestros=None) -> dict:
    inic = Path(dir_inicial)
    per = Path(dir_periodicas)
    maes = Path(dir_maestros) if dir_maestros else inic.parent / "maestros"

    ruta_aud = _busca(inic, "*auditoria*.csv")
    ruta_post = _busca(inic, "*post_control*.csv")
    ruta_diario = _busca(inic, "*postcontrol_diario*.csv")
    ruta_prop = _busca(per, "PropuestasContratacion*.csv")
    # el export de contratos puede venir como .xlsx o .ods
    ruta_contr = (_busca_op(per, "Contratos*PeopleNet*.xlsx")
                  or _busca(per, "Contratos*PeopleNet*.ods"))
    ruta_mov = _busca(per, "MovimientosBolsa*.csv")
    ruta_saldo = _busca(per, "SaldoActualPropuestas*.csv")
    # acepta "Bolsa de días…", "Bolsa_de_dias…" y "Bolsa_PeopleNet_a_…"
    ruta_bolsa = (_busca_op(per, "Bolsa*.xlsx") or _busca(per, "Bolsa*d*as*.xlsx"))
    ruta_div = (_busca_op(maes, "Divisiones*.xlsx")
                or _busca_op(per, "Divisiones*.xlsx"))

    print("Cargando corte inicial…", file=sys.stderr)
    saldo_inicial = carga_saldo_inicial(ruta_aud)
    postcontrol = carga_postcontrol(ruta_post)
    _ = carga_diario(ruta_diario)

    # verificación cruzada auditoría <-> post_control
    discrepancias = [k for k, v in postcontrol.items()
                     if k in saldo_inicial and saldo_inicial[k].saldo_postcontrol != v]
    if discrepancias:
        print(f"AVISO: {len(discrepancias)} discrepancias auditoría/post_control",
              file=sys.stderr)

    print("Cargando maestro de divisiones y ficheros periódicos…", file=sys.stderr)
    divisiones = carga_divisiones(ruta_div) if ruta_div else {}
    if not divisiones:
        print("AVISO: sin maestro de Divisiones; la dirección real del contrato "
              "no podrá resolverse (se usará la de la propuesta).", file=sys.stderr)
    propuestas = dedup_propuestas(carga_propuestas(ruta_prop))
    contratos = carga_contratos(ruta_contr, divisiones)
    movimientos = dedup_movimientos(carga_movimientos(ruta_mov))
    saldo_actual = carga_saldo_actual(ruta_saldo)
    bolsa = carga_bolsa_peoplenet(ruta_bolsa)

    equivalencias = Equivalencias.desde_csv(equivalencias_csv)
    from .config import DIR_CONFIG
    plazas_equiv = Equivalencias.desde_csv(
        DIR_CONFIG / "equivalencias_plazas.csv",
        col_a="id_plaza_a", col_b="id_plaza_b")

    importaciones = [
        registra(ruta_aud, "inicial_auditoria", len(saldo_inicial)),
        registra(ruta_post, "inicial_postcontrol", len(postcontrol)),
        registra(ruta_prop, "propuestas", len(propuestas)),
        registra(ruta_contr, "contratos", len(contratos)),
    ] + ([registra(ruta_div, "maestro_divisiones", len(divisiones))] if ruta_div else []) + [
        registra(ruta_mov, "movimientos", len(movimientos)),
        registra(ruta_saldo, "saldo_actual", len(saldo_actual)),
        registra(ruta_bolsa, "bolsa_peoplenet", len(bolsa)),
    ]

    print("Conciliando…", file=sys.stderr)
    res = conciliar(saldo_inicial, propuestas, contratos, movimientos,
                    saldo_actual, bolsa, equivalencias, plazas_equiv)

    sello = datetime.now().strftime("%Y%m%d")
    dir_salida = Path(dir_salida)
    ruta_conc = dir_salida / f"conciliacion_{sello}.xlsx"
    ruta_rec = dir_salida / f"recarga_propuestas_{sello}.xlsx"
    exporta_conciliacion(res, ruta_conc, saldo_inicial, equivalencias, importaciones)
    exporta_recarga(res, ruta_rec)

    # resumen a consola
    if res.devoluciones_cierre:
        tot = sum(c["dias_devueltos"] for c in res.devoluciones_cierre)
        print(f"\nDevoluciones por cierre de contrato (calculadas): "
              f"{len(res.devoluciones_cierre)} contratos, {tot} días "
              f"(ver pestaña A5b).", file=sys.stderr)

    print("\n=== SEMÁFORO ===", file=sys.stderr)
    for s in res.semaforo:
        print(f"  {s['clausula']}: {s['estado']}  "
              f"disponible_tras_compromisos={s['disponible_tras_compromisos']}  "
              f"reserva_pend_sin_contrato={s['reserva_pendiente_sin_contrato']}",
              file=sys.stderr)
    if res.validacion is not None:
        v = res.validacion.resumen
        print("\n=== VALIDACIÓN MOVIMIENTOS (esperado vs registrado) ===", file=sys.stderr)
        print(f"  cobertura: {v['con_movimiento_registrado']}/{v['propuestas_que_computan']}"
              f" ({v['cobertura_pct']}%)  anómalos={v['movimientos_anomalos']}"
              f"  con diferencia={v['propuestas_con_diferencia']}", file=sys.stderr)

    print(f"\nConciliación: {ruta_conc}", file=sys.stderr)
    print(f"Recarga:      {ruta_rec}", file=sys.stderr)
    return {"conciliacion": ruta_conc, "recarga": ruta_rec, "resultado": res}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Conciliación de bolsas N91c / S9b1a")
    p.add_argument("--inicial", default="data/inicial")
    p.add_argument("--periodicas", default="data/periodicas")
    p.add_argument("--salida", default="salidas")
    p.add_argument("--equivalencias", default=None)
    args = p.parse_args(argv)
    ejecuta(Path(args.inicial), Path(args.periodicas), Path(args.salida),
            args.equivalencias)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
