"""Motor de conciliación reproducible desde el corte inicial 02/07/2026.

Modelo contable (regla 3), por (id_plaza, dirección, cláusula):

    saldo_calculado = saldo_postcontrol
                    − consumo_posterior
                    + devolucion_posterior
                    + ajuste_peoplenet        (± por cláusula real de PeopleNet)

Cada consumo se computa sobre la cláusula DECLARADA de la propuesta; cuando el
contrato real de PeopleNet tiene otra cláusula (regla 5), un `ajuste_peoplenet`
mueve el consumo NETO de la cláusula declarada a la efectiva (suma cero entre
ambas). Así todas las columnas son términos reales y trazables.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .config import CONFIG
from .equivalencias import Equivalencias
from .fechas import dias_inclusivos, fin_computable, parse_fecha
from .modelo import (
    BolsaPeopleNet,
    Contrato,
    Enlace,
    Movimiento,
    Propuesta,
    SaldoActual,
    SaldoInicial,
    ClavePlaza,
)
from . import enlace as _enlace


@dataclass
class DetallePropuesta:
    propuesta_id: str
    idrh: str
    idrh_efectivo: str        # idrh de la propuesta o, si falta, el del contrato
    id_plaza: str
    direccion_codigo: str
    clausula_declarada: str
    clausula_efectiva: str
    fecha_inicio: Optional[date]
    reserva_fin: Optional[date]
    efectivo_fin: Optional[date]
    consumo_bruto: int
    devolucion_prevista: int
    consumo_neto: int
    enlazada: bool
    clausula_distinta: bool
    contrato_cerrado: bool
    laboral: bool
    mecanizada: bool
    computa: bool
    estado: str = ""
    sub_estado: str = ""
    motivo_no_computa: str = ""
    devolucion_registrada: int = 0
    devolucion_pendiente: int = 0
    movimiento_importe: int = 0
    direccion_declarada: str = ""
    direccion_efectiva: str = ""       # división(es) reales del contrato (por tramos)
    direccion_distinta: bool = False
    dias_sin_tramo: int = 0            # días del periodo sin GFH que los cubra
    plaza_distinta: bool = False       # enlazada a contrato de plaza equivalente
    enlace_directo: bool = False       # enlazada por comentario del contrato
    # coherencia del enlace directo (¿el contrato referenciado corresponde?)
    contrato_idrh: str = ""            # DNI del contrato enlazado
    contrato_inicio: Optional[date] = None
    contrato_plaza: str = ""
    coh_dni: str = ""                  # ok | distinto | nie_dni | sin_dni
    coh_fecha: str = ""                # ok | distinto
    coh_plaza: str = ""                # ok | distinto | laboral_estatutario
    coherencia_ok: bool = True         # False si algún eje no cuadra (revisar)


@dataclass
class FilaDetalle:
    id_plaza: str
    direccion_codigo: str
    direccion_nombre: str
    descripcion_categoria: str
    clausula: str
    saldo_base: int = 0
    control_inicial_neto: int = 0        # -nuevos + recuperados del corte
    saldo_postcontrol: int = 0
    consumo_posterior: int = 0
    devolucion_posterior: int = 0
    devolucion_cierre: int = 0       # cierre de contrato posterior al corte (calculada)
    ajuste_peoplenet: int = 0        # relocalización por cláusula/dirección reales
    reserva_pendiente: int = 0
    saldo_calculado: int = 0
    saldo_actual_propuestas: Optional[int] = None
    diferencia: Optional[int] = None
    laboral: bool = False
    nota: str = ""


@dataclass
class ResultadoConciliacion:
    detalle: list[FilaDetalle] = field(default_factory=list)
    detalle_propuestas: list[DetallePropuesta] = field(default_factory=list)
    resumen_direccion: list[dict] = field(default_factory=list)
    totales_clausula: list[dict] = field(default_factory=list)
    semaforo: list[dict] = field(default_factory=list)
    contratos_sin_propuesta: list[Contrato] = field(default_factory=list)
    enlaces: list[Enlace] = field(default_factory=list)
    avisos_corte: list[str] = field(default_factory=list)
    devoluciones_cierre: list[dict] = field(default_factory=list)
    contratos_post_corte: list[dict] = field(default_factory=list)
    validacion: object = None       # ResultadoValidacion (validación cruzada)
    usados_vs_contratos: list[dict] = field(default_factory=list)
    anclado_plaza: list[dict] = field(default_factory=list)       # modo anclado a PeopleNet, por plaza
    anclado_direccion: list[dict] = field(default_factory=list)   # agregado por dirección (control)


def _reserva_fin(prop: Propuesta, fecha_limite: date) -> date:
    """Fin reservado en el momento de autorizar (sin conocer cierre anticipado)."""
    if prop.fecha_fin is not None:
        return min(prop.fecha_fin, fecha_limite)
    return fecha_limite


def reparte_dias(inicio: Optional[date], fin: Optional[date], tramos) -> tuple[dict, int]:
    """Reparte los días inclusivos del intervalo [inicio, fin] entre las
    divisiones de los tramos GFH del contrato.

    Devuelve ({division: días}, días_no_cubiertos). Garantiza que la suma de
    días asignados + no_cubiertos == días inclusivos del intervalo (reparto
    voraz con tope), de modo que la relocalización tenga suma cero.
    """
    total = dias_inclusivos(inicio, fin)
    if total <= 0:
        return {}, 0
    reparto: dict[str, int] = defaultdict(int)
    restante = total
    orden = sorted(tramos, key=lambda t: (t.fecha_inicio or inicio))
    for t in orden:
        if restante <= 0:
            break
        seg_ini = max(inicio, t.fecha_inicio or inicio)
        seg_fin = min(fin, t.fecha_fin or fin)
        d = dias_inclusivos(seg_ini, seg_fin)
        if d <= 0:
            continue
        d = min(d, restante)
        reparto[t.division or ""] += d
        restante -= d
    return dict(reparto), restante


def _es_nie(doc: str) -> bool:
    return bool(doc) and doc[0].upper() in ("X", "Y", "Z")


def _coherencia_directo(prop, contrato, equivalencias, plazas_equiv):
    """Verifica que el contrato enlazado por comentario corresponde con la
    propuesta en DNI (con equivalencias NIE↔DNI), fecha de inicio y plaza.
    Devuelve (coh_dni, coh_fecha, coh_plaza)."""
    # DNI
    if not prop.idrh:
        coh_dni = "sin_dni"
    elif equivalencias.mismos(prop.idrh, contrato.idrh) or prop.idrh == contrato.idrh:
        coh_dni = "ok"
    elif _es_nie(prop.idrh) != _es_nie(contrato.idrh):
        coh_dni = "nie_dni"      # uno es NIE y otro DNI: posible cambio de documento
    else:
        coh_dni = "distinto"
    # fecha de inicio
    coh_fecha = "ok" if prop.fecha_inicio == contrato.fecha_inicio else "distinto"
    # plaza
    pp, pc = prop.id_plaza, contrato.id_plaza
    if not pp or not pc or pp == pc or (plazas_equiv and plazas_equiv.mismos(pp, pc)):
        coh_plaza = "ok"
    elif pp[1:] == pc[1:] and {pp[0].upper(), pc[0].upper()} == {"L", "E"}:
        coh_plaza = "laboral_estatutario"   # misma categoría, laboral vs estatutaria
    else:
        coh_plaza = "distinto"
    return coh_dni, coh_fecha, coh_plaza


def computa_propuesta(
    prop: Propuesta,
    enlace: Enlace,
    fecha_corte: date,
    fecha_limite: date,
    config=CONFIG,
    equivalencias: Optional[Equivalencias] = None,
    plazas_equiv: Optional[Equivalencias] = None,
) -> DetallePropuesta:
    """Calcula el consumo/devolución de UNA propuesta (función pura y testeable)."""
    laboral = config.es_laboral(prop.id_plaza)
    mecanizada = prop.sub_estado == "MECANIZADA"
    clausula_efectiva = enlace.clausula_efectiva
    clausula_distinta = enlace.clausula_distinta

    contrato = enlace.contratos[0] if enlace.contratos else None
    contrato_cerrado = bool(contrato and contrato.cerrado)

    reserva_fin = _reserva_fin(prop, fecha_limite)
    efectivo_fin = fin_computable(
        prop.fecha_fin,
        contrato.fecha_fin if contrato else None,
        contrato_cerrado,
        fecha_limite,
    )
    consumo_bruto = dias_inclusivos(prop.fecha_inicio, reserva_fin)
    consumo_neto = dias_inclusivos(prop.fecha_inicio, efectivo_fin)
    devolucion_prevista = max(0, consumo_bruto - consumo_neto)

    # DNI efectivo: si la propuesta aún no tiene IDRH (p.ej. exportada como
    # APROBADA antes de asignarse), se toma el del contrato enlazado.
    idrh_efectivo = prop.idrh or (contrato.idrh if contrato else "")

    det = DetallePropuesta(
        propuesta_id=prop.propuesta_id,
        idrh=prop.idrh,
        idrh_efectivo=idrh_efectivo,
        id_plaza=prop.id_plaza,
        direccion_codigo=prop.direccion_codigo,
        clausula_declarada=prop.clausula,
        clausula_efectiva=clausula_efectiva,
        fecha_inicio=prop.fecha_inicio,
        reserva_fin=reserva_fin,
        efectivo_fin=efectivo_fin,
        consumo_bruto=consumo_bruto,
        devolucion_prevista=devolucion_prevista,
        consumo_neto=consumo_neto,
        enlazada=enlace.enlazada,
        clausula_distinta=clausula_distinta,
        contrato_cerrado=contrato_cerrado,
        laboral=laboral,
        mecanizada=mecanizada,
        computa=False,
        estado=prop.estado,
        sub_estado=prop.sub_estado,
        direccion_declarada=prop.direccion_codigo,
        plaza_distinta=enlace.plaza_distinta,
        enlace_directo=enlace.enlace_directo,
    )

    # coherencia del enlace directo: ¿el contrato referenciado corresponde?
    if enlace.enlace_directo and contrato is not None:
        det.contrato_idrh = contrato.idrh
        det.contrato_inicio = contrato.fecha_inicio
        det.contrato_plaza = contrato.id_plaza
        det.coh_dni, det.coh_fecha, det.coh_plaza = _coherencia_directo(
            prop, contrato, equivalencias or Equivalencias(), plazas_equiv)
        det.coherencia_ok = (det.coh_dni in ("ok", "sin_dni")
                             and det.coh_fecha == "ok"
                             and det.coh_plaza == "ok")

    # --- ¿computa en el cálculo? ---
    prioritarias = config.clausulas_prioritarias
    if prop.estado not in config.estados_vivos:
        det.motivo_no_computa = f"estado {prop.estado}"
    elif prop.fecha_autorizacion is None:
        det.motivo_no_computa = "sin fecha_autorizacion"
    elif prop.fecha_autorizacion <= fecha_corte:
        det.motivo_no_computa = "autorizada en/antes del corte (ya en base)"
    elif laboral:
        det.motivo_no_computa = "plaza laboral (no consume)"
    elif not (clausula_efectiva in prioritarias or prop.clausula in prioritarias):
        det.motivo_no_computa = "cláusula no prioritaria"
    elif prop.fecha_inicio is None:
        det.motivo_no_computa = "sin fecha_inicio"
    elif not enlace.enlazada and not config.es_reserva_firme(prop.sub_estado):
        # sin contrato y sin aprobación firme -> no reserva
        det.motivo_no_computa = f"reserva no firme (sub_estado {prop.sub_estado})"
    else:
        det.computa = True
    return det


def _indexa_movimientos(movimientos: list[Movimiento], config=CONFIG):
    """Por propuesta: (importe_total, devolucion_registrada)."""
    devol_tipos = set(config.parametros.get("movimientos_devolucion", []))
    imp = defaultdict(int)
    devol = defaultdict(int)
    for m in movimientos:
        if m.propuesta_id:
            imp[m.propuesta_id] += m.importe
            if m.tipo_movimiento in devol_tipos and m.importe < 0:
                devol[m.propuesta_id] += -m.importe
    return imp, devol


def conciliar(
    saldo_inicial: dict[ClavePlaza, SaldoInicial],
    propuestas: list[Propuesta],
    contratos: list[Contrato],
    movimientos: list[Movimiento],
    saldo_actual: list[SaldoActual],
    bolsa_peoplenet: list[BolsaPeopleNet],
    equivalencias: Optional[Equivalencias] = None,
    plazas_equiv: Optional[Equivalencias] = None,
    info_contratos: Optional[dict] = None,
    config=CONFIG,
) -> ResultadoConciliacion:
    fecha_corte = parse_fecha(config.fecha_corte)
    fecha_limite = parse_fecha(config.fecha_limite)
    equivalencias = equivalencias or Equivalencias()
    prioritarias = config.clausulas_prioritarias

    res = ResultadoConciliacion()

    # 0) verificación aritmética del corte
    for si in saldo_inicial.values():
        if not si.cuadra():
            res.avisos_corte.append(
                f"Corte NO cuadra en {si.clave}: {si.saldo_postcontrol} != "
                f"{si.saldo_base_02_07}-{si.nuevos_control}+{si.recuperados_control}"
            )

    # 1) enlaces propuesta <-> contrato
    enlaces = _enlace.enlaza_todas(
        propuestas, contratos, equivalencias, fecha_limite, plazas_equiv)
    res.enlaces = enlaces
    res.contratos_sin_propuesta = _enlace.contratos_sin_propuesta(
        enlaces, contratos, prioritarias
    )

    imp_mov, devol_mov = _indexa_movimientos(movimientos, config)

    # 2) acumuladores por clave
    consumo = defaultdict(int)
    devolucion = defaultdict(int)
    ajuste = defaultdict(int)
    reserva_pend = defaultdict(int)

    for enl in enlaces:
        prop = enl.propuesta
        det = computa_propuesta(prop, enl, fecha_corte, fecha_limite, config,
                                equivalencias, plazas_equiv)
        det.devolucion_registrada = devol_mov.get(prop.propuesta_id, 0)
        det.movimiento_importe = imp_mov.get(prop.propuesta_id, 0)
        det.devolucion_pendiente = max(0, det.devolucion_prevista - det.devolucion_registrada)
        res.detalle_propuestas.append(det)
        if not det.computa:
            continue

        clave_decl = ClavePlaza(prop.id_plaza, prop.direccion_codigo, prop.clausula)

        # consumo y devolución se anotan en la clave DECLARADA de la propuesta
        consumo[clave_decl] += det.consumo_bruto
        devolucion[clave_decl] += det.devolucion_prevista

        if det.enlazada:
            # el contrato manda: se relocaliza el NETO de la clave declarada a la
            # cláusula real + división(es) reales (repartido por tramos GFH)
            contrato = enl.contratos[0]
            clau = det.clausula_efectiva
            reparto, sin_tramo = reparte_dias(
                prop.fecha_inicio, det.efectivo_fin, contrato.tramos)
            ajuste[clave_decl] += det.consumo_neto     # sale de la declarada
            for division, dias in reparto.items():
                destino = ClavePlaza(prop.id_plaza, division or prop.direccion_codigo, clau)
                ajuste[destino] -= dias                # entra en la división real
            if sin_tramo > 0:
                # tramo GFH no cubre parte del periodo -> se queda en la
                # dirección de la propuesta (cláusula real), marcado como excepción
                destino = ClavePlaza(prop.id_plaza, prop.direccion_codigo, clau)
                ajuste[destino] -= sin_tramo
            det.direccion_efectiva = ",".join(sorted(reparto)) or prop.direccion_codigo
            det.dias_sin_tramo = sin_tramo
            det.direccion_distinta = any(
                (dv or prop.direccion_codigo) != prop.direccion_codigo for dv in reparto
            )
        else:
            # sin contrato localizado: reserva pendiente (riesgo de compromiso)
            det.direccion_efectiva = prop.direccion_codigo
            reserva_pend[clave_decl] += det.consumo_neto

    # 2bis) devoluciones por cierre de contrato posterior al corte.
    # Las propuestas PRE-corte tienen su reserva (hasta 31/12) metida en la base
    # postcontrol; si el contrato cierra antes de 31/12, el tramo cierre+1 -> fin
    # reservado debe devolverse. Se calcula UNA vez por contrato (idrh,periodo)
    # y se anota en la clave declarada de la propuesta (revierte la base).
    devol_cierre = defaultdict(int)
    cierres: dict[tuple, dict] = {}
    for enl in enlaces:
        prop = enl.propuesta
        if not enl.enlazada:
            continue
        if prop.estado not in config.estados_vivos:
            continue
        if prop.clausula not in prioritarias:
            continue
        if config.es_laboral(prop.id_plaza):
            continue
        if prop.fecha_autorizacion is None or prop.fecha_autorizacion > fecha_corte:
            continue  # solo reservas PRE-corte (ya en la base)
        c = enl.contratos[0]
        if not c.cerrado or not (fecha_corte < c.fecha_fin < fecha_limite):
            continue
        reservado_fin = min(prop.fecha_fin or fecha_limite, fecha_limite)
        if reservado_fin <= c.fecha_fin:
            continue
        key = (c.idrh, c.num_periodo)
        prev = cierres.get(key)
        if prev is None or reservado_fin > prev["reservado_fin"]:
            cierres[key] = {"prop": prop, "contrato": c, "reservado_fin": reservado_fin}

    for info in cierres.values():
        prop = info["prop"]; c = info["contrato"]; rfin = info["reservado_fin"]
        inicio_dev = date.fromordinal(c.fecha_fin.toordinal() + 1)
        dias = dias_inclusivos(inicio_dev, rfin)
        if dias <= 0:
            continue
        clave = ClavePlaza(prop.id_plaza, prop.direccion_codigo, prop.clausula)
        devol_cierre[clave] += dias
        registrada = devol_mov.get(prop.propuesta_id, 0)
        res.devoluciones_cierre.append(dict(
            propuesta_id=prop.propuesta_id, idrh=prop.idrh, id_plaza=prop.id_plaza,
            direccion=prop.direccion_codigo, clausula=prop.clausula,
            contrato_periodo=c.num_periodo, contrato_fin=str(c.fecha_fin),
            reservado_hasta=str(rfin), dias_devueltos=dias,
            devolucion_registrada=registrada,
            devolucion_pendiente=max(0, dias - registrada),
        ))

    # 2ter) auditoría del control: contratos prioritarios con inicio o alta
    # posteriores al corte (mecanizados tras el 02/07, no en el control inicial).
    # Los que NO enlacen con una propuesta que compute son un posible consumo
    # no capturado por el control.
    # cubierto = existe alguna propuesta VIVA (APROBADA) enlazada al contrato,
    # ya sea posterior (computa) o pre-corte (ya en la base). El descuadre real
    # es un contrato posterior SIN propuesta viva que lo respalde.
    props_presentes = {p.propuesta_id for p in propuestas}
    cubiertos = set()
    for enl in enlaces:
        if enl.propuesta.estado in config.estados_vivos:
            for c0 in enl.contratos:
                cubiertos.add((c0.idrh, c0.num_periodo))
    for c in contratos:
        if c.clausula not in prioritarias or config.es_laboral(c.id_plaza):
            continue
        inicio_post = c.fecha_inicio is not None and c.fecha_inicio > fecha_corte
        if not inicio_post:      # el control es sobre inicio posterior al corte
            continue
        cubierto = (c.idrh, c.num_periodo) in cubiertos
        if cubierto:
            incidencia = ""
        elif c.propuesta_ref and c.propuesta_ref not in props_presentes:
            incidencia = f"referencia propuesta {c.propuesta_ref} no está en el export"
        else:
            incidencia = "sin propuesta localizada (posible consumo no capturado)"
        info = (info_contratos or {}).get((c.idrh, c.num_periodo), {})
        alta = info.get("alta_congelada") or c.alta   # congelada si hay registro
        res.contratos_post_corte.append(dict(
            idrh=c.idrh, num_periodo=c.num_periodo, id_plaza=c.id_plaza,
            clausula=c.clausula, inicio_plaza=str(c.fecha_inicio or ""),
            fin_plaza=str(c.fecha_fin or ""), alta=str(alta or ""),
            primera_aparicion=str(info.get("primera_aparicion") or ""),
            nuevo_en_importacion=bool(info.get("nuevo")),
            propuesta_ref=c.propuesta_ref,
            alta_posterior_corte=(alta is not None and alta >= fecha_corte),
            enlazado_a_propuesta=cubierto,
            incidencia=incidencia,
        ))

    # 3) saldo actual de Propuestas agregado a id_plaza
    sa_agg = defaultdict(int)
    for sa in saldo_actual:
        sa_agg[ClavePlaza(sa.id_plaza, sa.direccion_codigo, sa.clausula)] += sa.bolsa_dias_restante

    # 4) construir filas de detalle (todas las claves prioritarias del corte +
    #    cualquier clave prioritaria que aparezca por consumo/ajuste)
    claves = set(k for k in saldo_inicial if k.clausula in prioritarias)
    for d in (consumo, ajuste, reserva_pend, devolucion, devol_cierre):
        claves |= {k for k in d if k.clausula in prioritarias}

    for clave in sorted(claves, key=lambda k: (k.direccion_codigo, k.id_plaza, k.clausula)):
        si = saldo_inicial.get(clave)
        base = si.saldo_base_02_07 if si else 0
        post = si.saldo_postcontrol if si else 0
        fila = FilaDetalle(
            id_plaza=clave.id_plaza,
            direccion_codigo=clave.direccion_codigo,
            direccion_nombre=si.direccion_nombre if si else "",
            descripcion_categoria=si.descripcion_categoria if si else "",
            clausula=clave.clausula,
            saldo_base=base,
            control_inicial_neto=(post - base) if si else 0,
            saldo_postcontrol=post,
            consumo_posterior=consumo.get(clave, 0),
            devolucion_posterior=devolucion.get(clave, 0),
            devolucion_cierre=devol_cierre.get(clave, 0),
            ajuste_peoplenet=ajuste.get(clave, 0),
            reserva_pendiente=reserva_pend.get(clave, 0),
            laboral=config.es_laboral(clave.id_plaza),
        )
        fila.saldo_calculado = (
            fila.saldo_postcontrol
            - fila.consumo_posterior
            + fila.devolucion_posterior
            + fila.devolucion_cierre
            + fila.ajuste_peoplenet
        )
        if clave in sa_agg:
            fila.saldo_actual_propuestas = sa_agg[clave]
            fila.diferencia = fila.saldo_calculado - sa_agg[clave]
        if si is None:
            fila.nota = "plaza/cláusula no presente en el corte inicial"
        elif fila.laboral and (fila.consumo_posterior or fila.reserva_pendiente):
            fila.nota = "plaza laboral con actividad (descuadre)"
        res.detalle.append(fila)

    # 5) resumen por dirección + cláusula
    por_dir = defaultdict(lambda: FilaDetalle("", "", "", "", ""))
    agg_dir: dict[tuple, dict] = {}
    for f in res.detalle:
        k = (f.direccion_codigo, f.clausula)
        a = agg_dir.setdefault(k, dict(
            direccion_codigo=f.direccion_codigo, direccion_nombre=f.direccion_nombre,
            clausula=f.clausula, saldo_postcontrol=0, consumo_posterior=0,
            devolucion_posterior=0, devolucion_cierre=0, ajuste_peoplenet=0,
            reserva_pendiente=0,
            saldo_calculado=0, saldo_actual_propuestas=0, diferencia=0))
        a["saldo_postcontrol"] += f.saldo_postcontrol
        a["consumo_posterior"] += f.consumo_posterior
        a["devolucion_posterior"] += f.devolucion_posterior
        a["devolucion_cierre"] += f.devolucion_cierre
        a["ajuste_peoplenet"] += f.ajuste_peoplenet
        a["reserva_pendiente"] += f.reserva_pendiente
        a["saldo_calculado"] += f.saldo_calculado
        a["saldo_actual_propuestas"] += f.saldo_actual_propuestas or 0
        a["diferencia"] += f.diferencia or 0
    res.resumen_direccion = sorted(
        agg_dir.values(), key=lambda x: (x["direccion_codigo"], x["clausula"])
    )

    # 6) totales por cláusula
    bolsa_por_clausula = {b.clausula: b for b in bolsa_peoplenet}
    agg_cl: dict[str, dict] = {}
    for f in res.detalle:
        a = agg_cl.setdefault(f.clausula, dict(
            clausula=f.clausula, saldo_postcontrol=0, consumo_posterior=0,
            devolucion_posterior=0, devolucion_cierre=0, ajuste_peoplenet=0,
            reserva_pendiente=0,
            saldo_calculado=0, saldo_actual_propuestas=0))
        a["saldo_postcontrol"] += f.saldo_postcontrol
        a["consumo_posterior"] += f.consumo_posterior
        a["devolucion_posterior"] += f.devolucion_posterior
        a["devolucion_cierre"] += f.devolucion_cierre
        a["ajuste_peoplenet"] += f.ajuste_peoplenet
        a["reserva_pendiente"] += f.reserva_pendiente
        a["saldo_calculado"] += f.saldo_calculado
        a["saldo_actual_propuestas"] += f.saldo_actual_propuestas or 0
    res.totales_clausula = [agg_cl[c] for c in sorted(agg_cl)]

    # 7) semáforo de riesgo por cláusula
    for cl in prioritarias:
        b = bolsa_por_clausula.get(cl)
        disp_oficial = b.disponible if b else None
        reserva_sin_contrato = sum(
            f.reserva_pendiente for f in res.detalle if f.clausula == cl
        )
        saldo_calc = agg_cl.get(cl, {}).get("saldo_calculado", 0)
        saldo_prop = agg_cl.get(cl, {}).get("saldo_actual_propuestas", 0)
        disp_tras = (disp_oficial - reserva_sin_contrato) if disp_oficial is not None else None
        estado = "SIN DATOS"
        if disp_tras is not None:
            if disp_tras < 0:
                estado = "ROJO"
            elif disp_tras < max(1, int(0.05 * (disp_oficial or 1))):
                estado = "AMBAR"
            else:
                estado = "VERDE"
        usados = b.dias_usados if b else None
        comprometido_total = (
            usados + reserva_sin_contrato if usados is not None else None)
        res.semaforo.append(dict(
            clausula=cl,
            bolsa_oficial_contratacion=(b.dias_contratacion if b else None),
            bolsa_oficial_usados=usados,
            disponible_peoplenet=disp_oficial,
            reserva_pendiente_sin_contrato=reserva_sin_contrato,
            comprometido_total=comprometido_total,       # usados (contratos) + reservas
            disponible_tras_compromisos=disp_tras,        # = contratación − comprometido_total
            saldo_calculado_recarga=saldo_calc,           # distribución por plaza (recarga)
            saldo_actual_propuestas=saldo_prop,
            estado=estado,
        ))

    # 8) validación cruzada esperado vs registrado
    from .validacion import valida_movimientos
    res.validacion = valida_movimientos(
        propuestas, movimientos, res.detalle_propuestas, fecha_limite, config
    )

    # 9) control PeopleNet: 'Días Usados' vs días comprometidos por contrato.
    # Sumamos cada contrato hasta su fin REAL (tope fecha_limite, dentro del año)
    # y lo comparamos con el 'dias_usados' oficial de la Bolsa. Deben coincidir:
    # si no, o faltan contratos en el export o el 'usados' de PeopleNet descuadra.
    anio_inicio = date(fecha_limite.year, 1, 1)
    comprometido: dict[str, int] = defaultdict(int)
    for c in contratos:
        if not c.fecha_inicio:
            continue
        ini = max(c.fecha_inicio, anio_inicio)
        fin = min(c.fecha_fin or fecha_limite, fecha_limite)
        comprometido[c.clausula] += max(0, dias_inclusivos(ini, fin))
    for b in bolsa_peoplenet:
        comp = comprometido.get(b.clausula, 0)
        usados = b.dias_usados
        dif = comp - usados
        base = max(abs(comp), abs(usados), 1)
        pct = round(100 * (1 - abs(dif) / base), 1)
        res.usados_vs_contratos.append(dict(
            clausula=b.clausula,
            comprometido_contratos=comp,
            dias_usados_peoplenet=usados,
            diferencia=dif,
            coincidencia_pct=pct,
            estado="OK" if abs(dif) <= max(50, 0.02 * base) else "REVISAR",
        ))

    # 10) modo ANCLADO A PEOPLENET (paralelo al saldo del corte):
    #   disponible = Contratación − Usados_real(contratos, a fin real) − Pendiente(reservas sin contrato)
    # El 'usados_real' ya incorpora los cierres (contrato a fin real), así que no
    # necesita la 'devolución por cierre'. La Contratación (bolsa anual, por
    # cláusula) se reparte a plaza/dirección con el reparto del corte (postcontrol
    # + usados a fecha de corte) y se escala para cuadrar por cláusula. El control
    # relevante es por DIRECCIÓN (que su global quede ≥ 0; una plaza puede ir en
    # negativo mientras la dirección sume positivo).
    _ancla_a_peoplenet(res, contratos, bolsa_peoplenet, fecha_corte,
                       fecha_limite, prioritarias)
    return res


def _ancla_a_peoplenet(res, contratos, bolsa_peoplenet, fecha_corte,
                       fecha_limite, prioritarias):
    anio_inicio = date(fecha_limite.year, 1, 1)

    def _reparte_2026(c, hasta_alta=None):
        """Reparte los días 2026 del contrato (a fin real) por división (GFH)."""
        if c.fecha_inicio is None:
            return {}
        if hasta_alta is not None and (c.alta is None or c.alta > hasta_alta):
            return {}
        ini = max(c.fecha_inicio, anio_inicio)
        fin = min(c.fecha_fin or fecha_limite, fecha_limite)
        if dias_inclusivos(ini, fin) <= 0:
            return {}
        reparto, sin_tramo = reparte_dias(ini, fin, c.tramos)
        if sin_tramo > 0:
            # días sin tramo GFH (p.ej. la cola de un contrato abierto que
            # contamos hasta 31/12 pero cuyos tramos no llegan tan lejos):
            # se atribuyen al GFH vigente = el tramo que empieza más tarde.
            fb = ""
            if c.tramos:
                ult = max(c.tramos, key=lambda t: (t.fecha_inicio or date.min))
                fb = ult.division or ""
            reparto[fb] = reparto.get(fb, 0) + sin_tramo
        return reparto

    usados_now: dict[ClavePlaza, int] = defaultdict(int)
    usados_cut: dict[ClavePlaza, int] = defaultdict(int)
    for c in contratos:
        if c.clausula not in prioritarias:
            continue
        for div, dias in _reparte_2026(c).items():
            usados_now[ClavePlaza(c.id_plaza, div, c.clausula)] += dias
        for div, dias in _reparte_2026(c, fecha_corte).items():
            usados_cut[ClavePlaza(c.id_plaza, div, c.clausula)] += dias

    # postcontrol y pendiente por clave, desde el detalle ya calculado
    post: dict[ClavePlaza, int] = defaultdict(int)
    pend: dict[ClavePlaza, int] = defaultdict(int)
    nombre_dir: dict[str, str] = {}
    for f in res.detalle:
        k = ClavePlaza(f.id_plaza, f.direccion_codigo, f.clausula)
        post[k] += f.saldo_postcontrol
        pend[k] += f.reserva_pendiente
        nombre_dir[f.direccion_codigo] = f.direccion_nombre

    contratacion = {b.clausula: b.dias_contratacion for b in bolsa_peoplenet}
    claves = set(usados_now) | set(post) | set(pend)

    # peso de reparto por clave = max(0, postcontrol) + usados a fecha de corte
    peso = {k: max(0, post[k]) + usados_cut.get(k, 0) for k in claves}
    peso_clau: dict[str, int] = defaultdict(int)
    for k, w in peso.items():
        peso_clau[k.clausula] += w

    agg_dir: dict[tuple, dict] = {}
    for k in sorted(claves, key=lambda x: (x.direccion_codigo, x.id_plaza)):
        if k.clausula not in prioritarias:
            continue
        contro = contratacion.get(k.clausula, 0)
        w = peso.get(k, 0)
        wc = peso_clau.get(k.clausula, 0)
        contro_k = (contro * w / wc) if wc else 0
        u = usados_now.get(k, 0)
        p = pend.get(k, 0)
        disp = round(contro_k - u - p)
        res.anclado_plaza.append(dict(
            id_plaza=k.id_plaza, direccion=k.direccion_codigo, clausula=k.clausula,
            contratacion_plaza=round(contro_k), usados_real=u, pendiente=p,
            disponible=disp))
        a = agg_dir.setdefault((k.direccion_codigo, k.clausula), dict(
            direccion=k.direccion_codigo, direccion_nombre=nombre_dir.get(k.direccion_codigo, ""),
            clausula=k.clausula, contratacion=0, usados_real=0, pendiente=0, disponible=0))
        a["contratacion"] += round(contro_k)
        a["usados_real"] += u
        a["pendiente"] += p
        a["disponible"] += disp
    for a in agg_dir.values():
        a["estado"] = "ROJO" if a["disponible"] < 0 else "VERDE"
    res.anclado_direccion = sorted(
        agg_dir.values(), key=lambda x: (x["clausula"], x["direccion"]))
