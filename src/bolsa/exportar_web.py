"""Informe HTML autocontenido (local) para explorar la conciliación.

Genera un único fichero `.html` con los datos embebidos (JSON) y una pequeña
interfaz en JS puro (sin dependencias, funciona sin internet). Tres vistas:
- Por Dirección + Cláusula: cascada del saldo y drill-down a propuestas.
- Por DNI: propuestas, contratos y devoluciones (calculado vs registrado).
- Por Propuesta: detalle y estado de la devolución (¿ya registrada?).

Contiene DNI/NIE -> es un fichero LOCAL, no se publica.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .motor import ResultadoConciliacion


def _datos(res: ResultadoConciliacion) -> dict:
    dps = res.detalle_propuestas
    relevantes = [d for d in dps if d.computa or d.movimiento_importe
                  or d.devolucion_registrada]

    def prop(d):
        return dict(
            propuesta_id=d.propuesta_id, idrh=d.idrh_efectivo, id_plaza=d.id_plaza,
            idrh_de_contrato=bool(d.idrh_efectivo and not d.idrh),
            dir_prop=d.direccion_declarada, dir_real=d.direccion_efectiva,
            clau_prop=d.clausula_declarada, clau_real=d.clausula_efectiva,
            inicio=str(d.fecha_inicio or ""), reserva_fin=str(d.reserva_fin or ""),
            efectivo_fin=str(d.efectivo_fin or ""),
            consumo_bruto=d.consumo_bruto, consumo_neto=d.consumo_neto,
            devol_prevista=d.devolucion_prevista,
            devol_registrada=d.devolucion_registrada,
            devol_pendiente=d.devolucion_pendiente,
            mov_importe=d.movimiento_importe,
            enlazada=d.enlazada, enlace_directo=d.enlace_directo,
            contrato_cerrado=d.contrato_cerrado, computa=d.computa,
            sub_estado=d.sub_estado, motivo=d.motivo_no_computa,
        )

    def fila(f):
        return dict(
            id_plaza=f.id_plaza, categoria=f.descripcion_categoria,
            direccion=f.direccion_codigo, direccion_nombre=f.direccion_nombre,
            clausula=f.clausula, saldo_base=f.saldo_base,
            control=f.control_inicial_neto, postcontrol=f.saldo_postcontrol,
            consumo=f.consumo_posterior, devolucion=f.devolucion_posterior,
            devol_cierre=f.devolucion_cierre, ajuste=f.ajuste_peoplenet,
            reserva=f.reserva_pendiente, saldo_calc=f.saldo_calculado,
            saldo_prop=f.saldo_actual_propuestas, diferencia=f.diferencia,
        )

    return dict(
        semaforo=res.semaforo,
        totales=res.totales_clausula,
        direcciones=res.resumen_direccion,
        detalle=[fila(f) for f in res.detalle],
        propuestas=[prop(d) for d in relevantes],
        cierres=res.devoluciones_cierre,
    )


_HTML = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conciliación de bolsas — informe</title>
<style>
:root{--bg:#f5f6f8;--card:#fff;--ink:#1e293b;--mut:#64748b;--line:#e2e8f0;
--blue:#305496;--green:#16a34a;--red:#dc2626;--amber:#d97706;}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 system-ui,Segoe UI,Arial;background:var(--bg);color:var(--ink)}
header{background:var(--blue);color:#fff;padding:14px 20px}
header h1{margin:0;font-size:18px}header .sub{opacity:.85;font-size:12px}
nav{display:flex;gap:4px;background:#26406e;padding:0 12px}
nav button{background:none;border:0;color:#cbd5e1;padding:10px 14px;cursor:pointer;font-size:14px;border-bottom:3px solid transparent}
nav button.on{color:#fff;border-color:#fff;font-weight:600}
main{padding:18px;max-width:1180px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}
h2{font-size:15px;margin:0 0 10px}h3{font-size:13px;color:var(--mut);margin:14px 0 6px;text-transform:uppercase;letter-spacing:.04em}
select,input{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:14px;background:#fff}
input{width:260px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child,.l{text-align:left}
th{color:var(--mut);font-weight:600;background:#fafbfc;position:sticky;top:0}
.scroll{overflow:auto;max-height:60vh;border:1px solid var(--line);border-radius:8px}
.tag{display:inline-block;padding:1px 8px;border-radius:20px;font-size:11px;font-weight:600}
.g{background:#dcfce7;color:#166534}.r{background:#fee2e2;color:#991b1b}.a{background:#fef3c7;color:#92400e}.n{background:#e2e8f0;color:#475569}
.pos{color:var(--green)}.neg{color:var(--red)}
.wf{display:flex;flex-direction:column;gap:6px;margin:8px 0}
.wf .row{display:grid;grid-template-columns:190px 1fr 110px;align-items:center;gap:10px}
.wf .bar{height:16px;border-radius:4px;background:var(--blue);opacity:.85}
.wf .add .bar{background:var(--green)}.wf .sub .bar{background:var(--red)}
.wf .tot{font-weight:700}.wf .tot .bar{background:#334155}
.kpis{display:flex;gap:12px;flex-wrap:wrap}
.kpi{flex:1;min-width:150px;background:#fafbfc;border:1px solid var(--line);border-radius:8px;padding:10px}
.kpi .v{font-size:22px;font-weight:700}.kpi .k{font-size:11px;color:var(--mut);text-transform:uppercase}
.muted{color:var(--mut)}.hint{color:var(--mut);font-size:12px;margin:2px 0 10px}
.leg{color:var(--mut);font-size:12px;margin:8px 0 0;line-height:1.9}
.tag[title]{cursor:help}
.ast{color:var(--amber);font-weight:700;cursor:help;margin-left:1px}
.legend{font-size:12px;color:var(--mut)}.legend b{color:var(--ink)}
.empty{color:var(--mut);padding:18px;text-align:center}
</style></head><body>
<header><h1>Conciliación de bolsas de días — N91c · S9b1a</h1>
<div class="sub">Informe local · <span id="fecha"></span> · <b>calculado</b> = teórico del corte · <b>registrado</b> = movimiento hecho en PeopleNet/Propuestas</div></header>
<nav id="nav"></nav><main id="app"></main>
<script>
const DATA = __DATA__;
const eur = n => {
  if(n==null||n==="") return "";
  const x = Math.round(Number(n));
  if(!isFinite(x)) return "";
  const s = Math.abs(x).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (x<0?"-":"")+s;   // agrupa siempre cada 3 dígitos (también 1.234)
};
const el = (h)=>{const d=document.createElement("div");d.innerHTML=h;return d.firstElementChild;};
const clauSel = (id)=>`<select id="${id}"><option value="N91c">N91c (refuerzos)</option><option value="S9b1a">S9b1a (sustituciones)</option></select>`;
function tag(txt,cls,title){return `<span class="tag ${cls}"${title?` title="${title}"`:""}>${txt}</span>`}
const ENL_T={directo:"Enlazada al contrato por su comentario en PeopleNet (\"Solicitud contratacion N\"): referencia explícita.",
  heuristico:"Sin referencia explícita en el contrato; enlace deducido por coincidencia de DNI/NIE + fechas + plaza.",
  sincontrato:"No se encontró contrato: la propuesta reserva días pero aún no está mecanizada en PeopleNet."};
function enlTag(p){return !p.enlazada?tag("sin contrato","a",ENL_T.sincontrato)
  :(p.enlace_directo?tag("directo","g",ENL_T.directo):tag("heurístico","n",ENL_T.heuristico));}
const DNI_C_T="DNI tomado del contrato: la propuesta se exportó sin IDRH (aún no asignado). El enlace al contrato aporta el DNI.";
const dniCell=p=>p.idrh?(p.idrh_de_contrato?`${p.idrh}<span class="ast" title="${DNI_C_T}">*</span>`:p.idrh):"";
const LEG_ENL=`<p class="leg"><b>Enlace:</b> `
  +tag("directo","g",ENL_T.directo)+` propuesta↔contrato por el comentario del contrato · `
  +tag("heurístico","n",ENL_T.heuristico)+` deducido por DNI/NIE + fechas + plaza (sin referencia explícita) · `
  +tag("sin contrato","a",ENL_T.sincontrato)+` reserva sin contrato mecanizado. `
  +`<span class="ast">*</span> DNI tomado del contrato (la propuesta se exportó sin IDRH).</p>`;
function siNo(b){return b?tag("sí","g"):tag("no","n")}

// ---- vista semáforo ----
function vSemaforo(){
  let h=`<div class="card"><h2>Semáforo de compromiso</h2>
   <p class="hint">Margen = Contratación − (Usados por contratos + Reservas sin contrato). Positivo = no hay sobre-compromiso.</p>
   <table><tr><th class="l">Cláusula</th><th>Contratación</th><th>Usados (contratos)</th><th>Reservas sin contrato</th><th>Comprometido total</th><th>Margen</th><th>Estado</th></tr>`;
  for(const s of DATA.semaforo){const est=s.estado, cls=est==="ROJO"?"r":est==="AMBAR"?"a":"g";
   h+=`<tr><td class="l"><b>${s.clausula}</b></td><td>${eur(s.bolsa_oficial_contratacion)}</td><td>${eur(s.bolsa_oficial_usados)}</td><td>${eur(s.reserva_pendiente_sin_contrato)}</td><td>${eur(s.comprometido_total)}</td><td><b>${eur(s.disponible_tras_compromisos)}</b></td><td>${tag(est,cls)}</td></tr>`;}
  h+=`</table></div>`;
  h+=`<div class="card"><h2>Totales por cláusula</h2><table><tr><th class="l">Cláusula</th><th>Postcontrol</th><th>Consumo</th><th>Devolución</th><th>Devol. cierre</th><th>Ajuste</th><th>Reserva</th><th>Saldo calculado</th><th>Saldo Propuestas</th></tr>`;
  for(const t of DATA.totales){h+=`<tr><td class="l"><b>${t.clausula}</b></td><td>${eur(t.saldo_postcontrol)}</td><td>${eur(t.consumo_posterior)}</td><td>${eur(t.devolucion_posterior)}</td><td>${eur(t.devolucion_cierre)}</td><td>${eur(t.ajuste_peoplenet)}</td><td>${eur(t.reserva_pendiente)}</td><td><b>${eur(t.saldo_calculado)}</b></td><td>${eur(t.saldo_actual_propuestas)}</td></tr>`}
  h+=`</table></div>`;
  return h;
}

// ---- vista dirección ----
function vDireccion(){
  const dirs=[...new Set(DATA.direcciones.map(d=>d.direccion_codigo))];
  let h=`<div class="card"><h2>Por Dirección y Cláusula</h2>
   <div class="hint">Responde: «¿por qué tenía tantos días y ahora me quedan tan pocos?»</div>
   <div style="display:flex;gap:10px;flex-wrap:wrap">
    <select id="dir">${dirs.map(d=>`<option>${d}</option>`).join("")}</select>${clauSel("clau")}</div>
   <div id="dirOut"></div></div>`;
  return h;
}
function renderDir(){
  const dir=document.getElementById("dir").value, clau=document.getElementById("clau").value;
  const r=DATA.direcciones.find(x=>x.direccion_codigo===dir&&x.clausula===clau);
  const out=document.getElementById("dirOut");
  if(!r){out.innerHTML=`<p class="empty">Sin datos para ${dir} · ${clau}</p>`;return;}
  const steps=[["Saldo postcontrol (02/07)",r.saldo_postcontrol,"tot"],
    ["− Consumo posterior",-r.consumo_posterior,"sub"],
    ["+ Devolución",r.devolucion_posterior,"add"],
    ["+ Devolución por cierre",r.devolucion_cierre,"add"],
    ["± Ajuste PeopleNet",r.ajuste_peoplenet,r.ajuste_peoplenet<0?"sub":"add"],
    ["= Saldo calculado (a recargar)",r.saldo_calculado,"tot"]];
  const max=Math.max(...steps.map(s=>Math.abs(s[1])),1);
  let wf=`<div class="wf">`;
  for(const [lab,val,cls] of steps){wf+=`<div class="row ${cls}"><div class="l">${lab}</div><div><div class="bar" style="width:${Math.max(2,100*Math.abs(val)/max)}%"></div></div><div>${eur(val)}</div></div>`}
  wf+=`</div>`;
  const dif=r.diferencia||0;
  let k=`<div class="kpis">
    <div class="kpi"><div class="k">Saldo calculado</div><div class="v">${eur(r.saldo_calculado)}</div></div>
    <div class="kpi"><div class="k">Saldo actual en Propuestas</div><div class="v">${eur(r.saldo_actual_propuestas)}</div></div>
    <div class="kpi"><div class="k">Diferencia (recargar)</div><div class="v ${dif<0?'neg':'pos'}">${eur(dif)}</div></div>
    <div class="kpi"><div class="k">Reserva sin contrato</div><div class="v">${eur(r.reserva_pendiente)}</div></div></div>`;
  // plazas
  const plz=DATA.detalle.filter(f=>f.direccion===dir&&f.clausula===clau&&(f.saldo_calc||f.consumo||f.devol_cierre||f.reserva));
  let tp=`<h3>Plazas de ${dir} · ${clau}</h3><div class="scroll"><table><tr><th class="l">Plaza</th><th class="l">Categoría</th><th>Postcontrol</th><th>Consumo</th><th>Devol.</th><th>D.cierre</th><th>Ajuste</th><th>Reserva</th><th>Calculado</th><th>Propuestas</th><th>Dif.</th></tr>`;
  for(const f of plz){tp+=`<tr><td class="l">${f.id_plaza}</td><td class="l">${f.categoria||""}</td><td>${eur(f.postcontrol)}</td><td>${eur(f.consumo)}</td><td>${eur(f.devolucion)}</td><td>${eur(f.devol_cierre)}</td><td>${eur(f.ajuste)}</td><td>${eur(f.reserva)}</td><td><b>${eur(f.saldo_calc)}</b></td><td>${eur(f.saldo_prop)}</td><td class="${(f.diferencia||0)<0?'neg':'pos'}">${eur(f.diferencia)}</td></tr>`}
  tp+=`</table></div>`;
  // propuestas que mueven
  const pr=DATA.propuestas.filter(p=>p.computa&&(p.clau_real===clau)&&(p.dir_prop===dir||(p.dir_real||"").includes(dir)));
  let tpr=`<h3>Movimientos (propuestas que computan) — ${pr.length}</h3><div class="scroll"><table><tr><th class="l">Propuesta</th><th class="l">DNI</th><th class="l">Plaza</th><th class="l">Cláu. prop→real</th><th>Inicio</th><th>Fin comp.</th><th>Consumo</th><th>Devol. prev.</th><th>Devol. reg.</th><th>Devol. pend.</th><th class="l">Enlace</th></tr>`;
  for(const p of pr){tpr+=filaProp(p)}
  tpr+=`</table></div>`+LEG_ENL;
  out.innerHTML=`<h3>Cascada del saldo</h3>${wf}${k}${tp}${tpr}`;
}
function filaProp(p){
  const cd=p.clau_prop!==p.clau_real?`${p.clau_prop}→<b>${p.clau_real}</b>`:p.clau_real;
  const enl=enlTag(p);
  const dp=p.devol_pendiente>0?`<span class="neg">${eur(p.devol_pendiente)}</span>`:eur(p.devol_pendiente);
  return `<tr><td class="l">${p.propuesta_id}</td><td class="l">${dniCell(p)}</td><td class="l">${p.id_plaza}</td><td class="l">${cd}</td><td>${p.inicio}</td><td>${p.efectivo_fin}</td><td>${eur(p.consumo_neto)}</td><td>${eur(p.devol_prevista)}</td><td>${eur(p.devol_registrada)}</td><td>${dp}</td><td class="l">${enl}</td></tr>`;
}

// ---- vista DNI ----
function vDni(){
  return `<div class="card"><h2>Por DNI / NIE</h2>
   <div class="hint">Responde: «¿me devolvieron los días de este DNI?» · «esta propuesta hasta el 31/12 que cerró antes, ¿me sumaron días?»</div>
   <input id="dni" placeholder="Escribe un DNI/NIE y pulsa Enter" autocomplete="off">
   <p class="legend">Devol. <b>prevista</b> = calculada (teórica) · <b>registrada</b> = ya hecha en movimientos · <b>pendiente</b> = falta hacerla en PeopleNet.</p>
   <div id="dniOut"><p class="empty">Introduce un DNI/NIE.</p></div></div>`;
}
function renderDni(){
  const q=(document.getElementById("dni").value||"").trim().toUpperCase();
  const out=document.getElementById("dniOut");
  if(!q){out.innerHTML=`<p class="empty">Introduce un DNI/NIE.</p>`;return;}
  const ps=DATA.propuestas.filter(p=>(p.idrh||"").toUpperCase()===q);
  const cs=DATA.cierres.filter(c=>(c.idrh||"").toUpperCase()===q);
  if(!ps.length&&!cs.length){out.innerHTML=`<p class="empty">Sin actividad relevante para ${q} (posterior al corte).</p>`;return;}
  let h=`<h3>Propuestas / contratos de ${q} — ${ps.length}</h3><div class="scroll"><table><tr><th class="l">Propuesta</th><th class="l">Plaza</th><th class="l">Dir.</th><th class="l">Cláu. prop→real</th><th>Inicio</th><th>Fin reserv.</th><th>Fin comp.</th><th>Consumo</th><th>Devol. prev.</th><th>Devol. reg.</th><th>Devol. pend.</th><th class="l">Enlace</th></tr>`;
  for(const p of ps){const cd=p.clau_prop!==p.clau_real?`${p.clau_prop}→<b>${p.clau_real}</b>`:p.clau_real;
    const enl=enlTag(p);
    const dp=p.devol_pendiente>0?`<span class="neg">${eur(p.devol_pendiente)}</span>`:eur(p.devol_pendiente);
    h+=`<tr><td class="l">${p.propuesta_id}</td><td class="l">${p.id_plaza}</td><td class="l">${p.dir_real||p.dir_prop}</td><td class="l">${cd}</td><td>${p.inicio}</td><td>${p.reserva_fin}</td><td>${p.efectivo_fin}</td><td>${eur(p.consumo_neto)}</td><td>${eur(p.devol_prevista)}</td><td>${eur(p.devol_registrada)}</td><td>${dp}</td><td class="l">${enl}</td></tr>`}
  h+=`</table></div>`+LEG_ENL;
  if(cs.length){h+=`<h3>Devoluciones por cierre de contrato (contrato terminó antes de 31/12)</h3><div class="scroll"><table><tr><th class="l">Propuesta</th><th class="l">Plaza</th><th class="l">Cláu.</th><th>Nº periodo</th><th>Cierre</th><th>Reservado hasta</th><th>Días a devolver (calc.)</th><th>Ya registrado</th><th>Pendiente</th></tr>`;
    for(const c of cs){const pend=c.devolucion_pendiente>0;
      h+=`<tr><td class="l">${c.propuesta_id}</td><td class="l">${c.id_plaza}</td><td class="l">${c.clausula}</td><td>${c.contrato_periodo}</td><td>${c.contrato_fin}</td><td>${c.reservado_hasta}</td><td><b>${eur(c.dias_devueltos)}</b></td><td>${eur(c.devolucion_registrada)}</td><td>${pend?tag(eur(c.devolucion_pendiente)+" pend.","a"):tag("hecho","g")}</td></tr>`}
    h+=`</table></div>`;}
  out.innerHTML=h;
}

// ---- vista propuesta ----
function vProp(){
  return `<div class="card"><h2>Por Propuesta — ¿ya hicieron el movimiento?</h2>
   <input id="pid" placeholder="Nº de propuesta y Enter" autocomplete="off">
   <div id="propOut"><p class="empty">Introduce un nº de propuesta.</p></div></div>`;
}
function renderProp(){
  const q=(document.getElementById("pid").value||"").trim();
  const out=document.getElementById("propOut");
  const p=DATA.propuestas.find(x=>String(x.propuesta_id)===q);
  if(!p){out.innerHTML=`<p class="empty">No encontrada (o sin actividad posterior al corte): ${q}</p>`;return;}
  const cierre=DATA.cierres.find(c=>String(c.propuesta_id)===q);
  const estadoDev = p.devol_pendiente>0 ? tag("DEVOLUCIÓN PENDIENTE de registrar","a") :
    (p.devol_prevista>0? tag("devolución ya registrada","g") : tag("sin devolución","n"));
  let h=`<div class="kpis" style="margin-top:10px">
    <div class="kpi"><div class="k">Cláusula prop → real</div><div class="v" style="font-size:16px">${p.clau_prop}${p.clau_prop!==p.clau_real?" → "+p.clau_real:""}</div></div>
    <div class="kpi"><div class="k">Consumo neto</div><div class="v">${eur(p.consumo_neto)}</div></div>
    <div class="kpi"><div class="k">Devol. prevista</div><div class="v">${eur(p.devol_prevista)}</div></div>
    <div class="kpi"><div class="k">Devol. registrada</div><div class="v">${eur(p.devol_registrada)}</div></div>
    <div class="kpi"><div class="k">Devol. pendiente</div><div class="v ${p.devol_pendiente>0?'neg':''}">${eur(p.devol_pendiente)}</div></div></div>
   <p style="margin-top:12px">Estado de la devolución: ${estadoDev}</p>
   <table style="margin-top:8px">
    <tr><th class="l">DNI</th><td class="l">${dniCell(p)}</td><th class="l">Plaza</th><td class="l">${p.id_plaza}</td></tr>
    <tr><th class="l">Dirección prop → real</th><td class="l">${p.dir_prop} ${p.dir_real&&p.dir_real!==p.dir_prop?"→ "+p.dir_real:""}</td><th class="l">Enlace</th><td class="l">${p.enlazada?(p.enlace_directo?"directo (comentario)":"heurístico"):"sin contrato"}</td></tr>
    <tr><th class="l">Inicio</th><td class="l">${p.inicio}</td><th class="l">Fin reservado / computable</th><td class="l">${p.reserva_fin} / ${p.efectivo_fin}</td></tr>
    <tr><th class="l">¿Computa?</th><td class="l">${p.computa?"sí":"no — "+p.motivo}</td><th class="l">Σ movimientos reales</th><td class="l">${eur(p.mov_importe)}</td></tr></table>`;
  if(cierre){h+=`<h3>Devolución por cierre</h3><p>El contrato (periodo ${cierre.contrato_periodo}) cerró el <b>${cierre.contrato_fin}</b>, estaba reservado hasta ${cierre.reservado_hasta} → <b>${eur(cierre.dias_devueltos)}</b> días a devolver; registrados ${eur(cierre.devolucion_registrada)}, pendientes ${eur(cierre.devolucion_pendiente)}.</p>`}
  out.innerHTML=h;
}

const VIEWS=[["Semáforo",vSemaforo],["Por Dirección",vDireccion],["Por DNI",vDni],["Por Propuesta",vProp]];
let cur=0;
function draw(){
  document.getElementById("nav").innerHTML=VIEWS.map((v,i)=>`<button class="${i===cur?'on':''}" data-i="${i}">${v[0]}</button>`).join("");
  document.getElementById("app").innerHTML=VIEWS[cur][1]();
  document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{cur=+b.dataset.i;draw()});
  if(cur===1){["dir","clau"].forEach(id=>document.getElementById(id).onchange=renderDir);renderDir();}
  if(cur===2){const i=document.getElementById("dni");i.onkeydown=e=>{if(e.key==="Enter")renderDni()};i.focus();}
  if(cur===3){const i=document.getElementById("pid");i.onkeydown=e=>{if(e.key==="Enter")renderProp()};i.focus();}
}
document.getElementById("fecha").textContent=DATA.fecha||"";
draw();
</script></body></html>"""


def exporta_informe(res: ResultadoConciliacion, ruta, fecha: str = "") -> Path:
    datos = _datos(res)
    datos["fecha"] = fecha
    html = _HTML.replace("__DATA__", json.dumps(datos, ensure_ascii=False))
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_text(html, encoding="utf-8")
    return Path(ruta)
