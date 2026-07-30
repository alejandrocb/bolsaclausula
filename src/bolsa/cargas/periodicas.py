"""Carga de los cinco ficheros periódicos (exportaciones completas)."""
from __future__ import annotations

from ..config import CONFIG
from ..fechas import parse_fecha
from ..modelo import (
    BolsaPeopleNet,
    Contrato,
    Movimiento,
    Propuesta,
    SaldoActual,
)
from . import dicts_desde_filas, entero, lee_csv, lee_ods


def carga_propuestas(ruta, config=CONFIG) -> list[Propuesta]:
    m = config.mapeo["propuestas"]
    col = m["columnas"]
    fmt = m.get("formato_fecha")
    out = []
    for r in lee_csv(ruta, m["delimitador"]):
        out.append(Propuesta(
            propuesta_id=r[col["propuesta_id"]].strip(),
            id_plaza=r[col["categoria_codigo"]].strip(),
            direccion_codigo=r[col["direccion_codigo"]].strip(),
            clausula=r[col["clausula"]].strip(),
            estado=r[col["estado"]].strip(),
            sub_estado=r.get(col["sub_estado"], "").strip(),
            fecha_autorizacion=parse_fecha(r.get(col["fecha_autorizacion"]), fmt),
            fecha_inicio=parse_fecha(r.get(col["fecha_inicio"]), fmt),
            fecha_fin=parse_fecha(r.get(col["fecha_fin"]), fmt),
            idrh=r.get(col["idrh"], "").strip(),
            propuesta_original_id=r.get(col["propuesta_original_id"], "").strip(),
            propuesta_sustituta_id=r.get(col["propuesta_sustituta_id"], "").strip(),
        ))
    return out


def carga_contratos(ruta, config=CONFIG) -> list[Contrato]:
    m = config.mapeo["contratos"]
    col = m["columnas"]
    fmt = m.get("formato_fecha")
    filas = lee_ods(ruta, m.get("hoja"))
    out = []
    for r in dicts_desde_filas(filas):
        idrh = r.get(col["idrh"], "").strip()
        if not idrh:
            continue
        out.append(Contrato(
            idrh=idrh,
            num_periodo=r.get(col["num_periodo"], "").strip(),
            id_plaza=r.get(col["id_plaza"], "").strip(),
            clausula=r.get(col["clausula"], "").strip(),
            fecha_inicio=parse_fecha(r.get(col["fecha_inicio"]), fmt),
            fecha_fin=parse_fecha(r.get(col["fecha_fin"]), fmt),
            motivo_inicio=r.get(col["motivo_inicio"], "").strip(),
        ))
    return out


def carga_movimientos(ruta, config=CONFIG) -> list[Movimiento]:
    m = config.mapeo["movimientos"]
    col = m["columnas"]
    fmt = m.get("formato_fecha")
    out = []
    for r in lee_csv(ruta, m["delimitador"]):
        out.append(Movimiento(
            movimiento_id=r[col["movimiento_id"]].strip(),
            bolsa_dias_id=r.get(col["bolsa_dias_id"], "").strip(),
            propuesta_id=r.get(col["propuesta_id"], "").strip(),
            fecha_movimiento=parse_fecha(r.get(col["fecha_movimiento"]), fmt),
            tipo_movimiento=r.get(col["tipo_movimiento"], "").strip(),
            importe=entero(r[col["importe"]]),
            id_plaza=r.get(col["categoria_codigo"], "").strip(),
            direccion_codigo=r.get(col["direccion_codigo"], "").strip(),
            clausula=r.get(col["clausula"], "").strip(),
        ))
    return out


def carga_saldo_actual(ruta, config=CONFIG) -> list[SaldoActual]:
    m = config.mapeo["saldo_actual"]
    col = m["columnas"]
    out = []
    for r in lee_csv(ruta, m["delimitador"]):
        out.append(SaldoActual(
            bolsa_dias_id=r[col["bolsa_dias_id"]].strip(),
            direccion_codigo=r[col["direccion_codigo"]].strip(),
            categoria_id=r[col["categoria_id"]].strip(),
            id_plaza=r[col["categoria_codigo"]].strip(),
            clausula=r[col["clausula"]].strip(),
            bolsa_dias_inicial=entero(r[col["bolsa_dias_inicial"]]),
            bolsa_dias_restante=entero(r[col["bolsa_dias_restante"]]),
        ))
    return out


def carga_bolsa_peoplenet(ruta, config=CONFIG) -> list[BolsaPeopleNet]:
    import openpyxl

    m = config.mapeo["bolsa_peoplenet"]
    col = m["columnas"]
    fila_cab = int(m.get("fila_cabecera", 2))
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    ws = wb[m["hoja"]]
    filas = list(ws.iter_rows(min_row=fila_cab, values_only=True))
    if not filas:
        return []
    cabecera = [str(c).strip() if c is not None else "" for c in filas[0]]
    idx = {nombre: cabecera.index(col[nombre]) for nombre in col}
    out = []
    for fila in filas[1:]:
        if fila is None or all(c is None for c in fila):
            continue
        def val(nombre):
            i = idx[nombre]
            return fila[i] if i < len(fila) else None
        anio = val("anio")
        if anio is None:
            continue
        out.append(BolsaPeopleNet(
            anio=entero(anio),
            clausula=str(val("clausula")).strip(),
            dias_contratacion=entero(val("dias_contratacion")),
            dias_usados=entero(val("dias_usados")),
            comentario=str(val("comentario") or "").strip(),
        ))
    return out
