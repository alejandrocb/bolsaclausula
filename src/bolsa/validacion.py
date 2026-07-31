"""Validación cruzada: consumo esperado (motor) vs movimientos registrados.

Los movimientos NO alteran el cálculo (que usa el consumo neto); aquí se
comprueba que lo que Propuestas restó/devolvió realmente coincide con lo
esperado, y se detectan movimientos anómalos (sin propuesta o con
plaza/cláusula/dirección incoherente).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .config import CONFIG
from .modelo import Movimiento, Propuesta


@dataclass
class FilaValidacion:
    propuesta_id: str
    idrh: str
    id_plaza: str
    direccion_codigo: str
    clausula: str
    computa: bool
    esperado_con_tope: Optional[int]     # consumo bruto calculado (tope 31/12)
    esperado_sin_tope: Optional[int]     # días completos de la propuesta
    registrado_nueva: int                # Σ importe NUEVA_SOLICITUD
    diferencia: Optional[int]            # registrado - esperado_con_tope
    devolucion_prevista: int
    devolucion_registrada: int
    devolucion_pendiente: int
    nota: str = ""


@dataclass
class Anomalia:
    movimiento_id: str
    propuesta_id: str
    tipo_movimiento: str
    importe: int
    id_plaza: str
    direccion_codigo: str
    clausula: str
    incidencias: str


@dataclass
class ResultadoValidacion:
    por_propuesta: list[FilaValidacion] = field(default_factory=list)
    anomalos: list[Anomalia] = field(default_factory=list)
    resumen: dict = field(default_factory=dict)


def valida_movimientos(
    propuestas: list[Propuesta],
    movimientos: list[Movimiento],
    detalles: list,                      # list[DetallePropuesta]
    fecha_limite: date,
    config=CONFIG,
) -> ResultadoValidacion:
    from .fechas import dias_inclusivos

    prop_by_id = {p.propuesta_id: p for p in propuestas}
    det_by_id = {d.propuesta_id: d for d in detalles}
    consumo_tipos = set(config.parametros.get("movimientos_consumo", []))

    consumo_nueva: dict[str, int] = defaultdict(int)
    devol_reg: dict[str, int] = defaultdict(int)
    res = ResultadoValidacion()

    devol_tipos = set(config.parametros.get("movimientos_devolucion", []))
    for m in movimientos:
        p = prop_by_id.get(m.propuesta_id)
        problemas = []
        if not m.propuesta_id:
            problemas.append("movimiento sin propuesta_id")
        elif p is None:
            problemas.append("propuesta inexistente en Propuestas")
        else:
            if m.clausula and p.clausula and m.clausula != p.clausula:
                problemas.append(f"cláusula mov={m.clausula} vs prop={p.clausula}")
            if m.id_plaza and p.id_plaza and m.id_plaza != p.id_plaza:
                problemas.append(f"plaza mov={m.id_plaza} vs prop={p.id_plaza}")
            if (m.direccion_codigo and p.direccion_codigo
                    and m.direccion_codigo != p.direccion_codigo):
                problemas.append("dirección distinta")
        if m.tipo_movimiento in consumo_tipos:
            consumo_nueva[m.propuesta_id] += m.importe
        if m.tipo_movimiento in devol_tipos and m.importe < 0:
            devol_reg[m.propuesta_id] += -m.importe
        if problemas:
            res.anomalos.append(Anomalia(
                movimiento_id=m.movimiento_id, propuesta_id=m.propuesta_id,
                tipo_movimiento=m.tipo_movimiento, importe=m.importe,
                id_plaza=m.id_plaza, direccion_codigo=m.direccion_codigo,
                clausula=m.clausula, incidencias="; ".join(problemas),
            ))

    # solo interesan las que computan (posteriores al corte) o tienen movimiento
    ids = {pid for pid, d in det_by_id.items() if d.computa}
    ids |= set(consumo_nueva) | set(devol_reg)
    n_computan = n_con_mov = n_dif = 0
    for pid in sorted(ids):
        d = det_by_id.get(pid)
        p = prop_by_id.get(pid)
        reg = consumo_nueva.get(pid, 0)
        esperado_con = d.consumo_bruto if (d and d.computa) else None
        esperado_sin = None
        if p is not None:
            esperado_sin = dias_inclusivos(p.fecha_inicio, p.fecha_fin) or None
        dif = (reg - esperado_con) if (esperado_con is not None and pid in consumo_nueva) else None
        nota = ""
        if p is not None and p.fecha_fin and p.fecha_fin > fecha_limite:
            nota = "propuesta con fin > 31/12/2026 (recorte esperado)"
        if d and d.computa:
            n_computan += 1
        if pid in consumo_nueva:
            n_con_mov += 1
        if dif not in (None, 0):
            n_dif += 1
        res.por_propuesta.append(FilaValidacion(
            propuesta_id=pid,
            idrh=p.idrh if p else "",
            id_plaza=p.id_plaza if p else "",
            direccion_codigo=p.direccion_codigo if p else "",
            clausula=p.clausula if p else "",
            computa=bool(d and d.computa),
            esperado_con_tope=esperado_con,
            esperado_sin_tope=esperado_sin,
            registrado_nueva=reg,
            diferencia=dif,
            devolucion_prevista=d.devolucion_prevista if d else 0,
            devolucion_registrada=devol_reg.get(pid, 0),
            devolucion_pendiente=d.devolucion_pendiente if d else 0,
            nota=nota,
        ))

    cobertura = round(100 * n_con_mov / n_computan, 1) if n_computan else 0.0
    res.resumen = dict(
        propuestas_que_computan=n_computan,
        con_movimiento_registrado=n_con_mov,
        cobertura_pct=cobertura,
        movimientos_anomalos=len(res.anomalos),
        propuestas_con_diferencia=n_dif,
    )
    return res
