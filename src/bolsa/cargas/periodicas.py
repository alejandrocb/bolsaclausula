"""Carga de los cinco ficheros periódicos (exportaciones completas)."""
from __future__ import annotations

import re
from collections import defaultdict

from ..config import CONFIG
from ..fechas import parse_fecha
from ..modelo import (
    BolsaPeopleNet,
    Contrato,
    Movimiento,
    Propuesta,
    SaldoActual,
    TramoGFH,
)
from . import dicts_desde_filas, entero, limpio, lee_csv, lee_tabla


def carga_propuestas(ruta, config=CONFIG) -> list[Propuesta]:
    m = config.mapeo["propuestas"]
    col = m["columnas"]
    fmt = m.get("formato_fecha")
    out = []
    for r in lee_csv(ruta, m["delimitador"]):
        out.append(Propuesta(
            propuesta_id=r[col["propuesta_id"]].strip(),
            id_plaza=r[col["categoria_codigo"]].strip(),
            direccion_codigo=limpio(r[col["direccion_codigo"]]),
            clausula=limpio(r[col["clausula"]]),
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


_RE_PROP = re.compile(r'(?:solicitud\s+contrataci[oó]n|propuesta)\s*[:#]?\s*(\d+)', re.I)


def propuesta_de_comentario(texto: str) -> str:
    """Extrae el propuesta_id del comentario del contrato.

    Formatos: "Solicitud contratacion 64008", "PROPUESTA 91239", o un número
    suelto. Devuelve "" si no hay un id reconocible.
    """
    if not texto:
        return ""
    t = str(texto).strip()
    m = _RE_PROP.search(t)
    if m:
        return m.group(1)
    if t.isdigit():          # comentario que es solo el número de propuesta
        return t
    return ""


def carga_contratos(
    ruta, divisiones: dict[tuple[str, str], str] | None = None, config=CONFIG
) -> list[Contrato]:
    """Carga contratos agrupando filas por (idrh, núm_periodo).

    Cada fila es un TRAMO GFH; se agrupan en un Contrato con su lista de tramos.
    La división real de cada tramo se resuelve con el maestro (id_plaza, gfh).
    """
    m = config.mapeo["contratos"]
    col = m["columnas"]
    fmt = m.get("formato_fecha")
    divisiones = divisiones or {}
    filas = lee_tabla(ruta, m.get("hoja"))

    def val(r, clave):
        return str(r.get(col.get(clave, clave), "") or "").strip()

    grupos: dict[tuple, list[dict]] = defaultdict(list)
    orden: list[tuple] = []
    for r in dicts_desde_filas(filas):
        idrh = val(r, "idrh")
        if not idrh:
            continue
        clave = (idrh, val(r, "num_periodo"), val(r, "id_plaza"),
                 val(r, "fecha_inicio"))
        if clave not in grupos:
            orden.append(clave)
        grupos[clave].append(r)

    out = []
    for clave in orden:
        filas_c = grupos[clave]
        base = filas_c[0]
        idrh = val(base, "idrh")
        id_plaza = val(base, "id_plaza")
        tramos = []
        for r in filas_c:
            gfh = val(r, "gfh_id")
            division = divisiones.get((id_plaza, gfh), "")
            tramos.append(TramoGFH(
                fecha_inicio=parse_fecha(r.get(col["gfh_inicio"]), fmt),
                fecha_fin=parse_fecha(r.get(col["gfh_fin"]), fmt),
                gfh_id=gfh,
                gfh_nombre=val(r, "gfh_nombre"),
                division=division,
            ))
        tramos.sort(key=lambda t: (t.fecha_inicio or parse_fecha("1900-01-01")))
        # enlace directo: primera propuesta referenciada en el comentario
        propuesta_ref = ""
        col_com = col.get("comentario")
        if col_com:
            for r in filas_c:
                ref = propuesta_de_comentario(r.get(col_com, ""))
                if ref:
                    propuesta_ref = ref
                    break
        out.append(Contrato(
            idrh=idrh,
            num_periodo=val(base, "num_periodo"),
            id_plaza=id_plaza,
            clausula=val(base, "clausula"),
            fecha_inicio=parse_fecha(base.get(col["fecha_inicio"]), fmt),
            fecha_fin=parse_fecha(base.get(col["fecha_fin"]), fmt),
            motivo_inicio=val(base, "motivo_inicio"),
            tramos=tramos,
            propuesta_ref=propuesta_ref,
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
