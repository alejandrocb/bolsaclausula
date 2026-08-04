# Conciliación de bolsas de días (N91c / S9b1a)

Aplicativo que **recalcula y concilia** la bolsa de días de contratación
estatutaria de una Gerencia de Servicios Sanitarios entre **PeopleNet** y el
aplicativo de **Propuestas de contratación**, de forma **reproducible desde el
corte inicial validado del 02/07/2026**.

Cláusulas prioritarias:
- **N91c** — exceso o acumulación de tareas / refuerzos.
- **S9b1a** — sustituciones por IT, vacaciones, permisos, etc.

El resto de cláusulas (`N91a`, `N91b`, `S9b1b`, `S9b1c`…) se tratan como no
computables/descuadres. El **personal laboral** (plazas cuyo `id_plaza`
empieza por `L`) conserva su saldo inicial histórico pero **no recibe nuevos
consumos, devoluciones ni ajustes**.

> **Prioridad absoluta:** trazabilidad, reproducibilidad desde el 02/07/2026 y
> evitar que una misma propuesta, movimiento o devolución afecte dos veces al
> saldo.

---

## Instalación

```bash
pip install -r requirements.txt      # solo openpyxl (+ pytest para pruebas)
```

No requiere pandas. La lectura de ODS se hace con la librería estándar.

## Datos (no versionados)

Los ficheros fuente contienen **datos personales (DNI/NIE en `idrh`)** y por
eso están excluidos de git (`.gitignore`). Colócalos así:

```
data/
  inicial/     carga_inicial_bolsas_2026-07-02_auditoria.csv
               carga_inicial_bolsas_2026-07-02_post_control.csv
               carga_postcontrol_diario_2026-06-30_a_2026-07-02.csv
  periodicas/  PropuestasContratacion_<fecha>.csv
               Bolsa_de_dias_<fecha>.xlsx
               Contratos_PeopleNet_<fecha>.xlsx   (o .ods; se autodetecta)
               MovimientosBolsa_<fecha>.csv
               SaldoActualPropuestas_<fecha>.csv
  maestros/    Divisiones_Plazas_GFHs.xlsx        (ID Plaza, ID GFH → División)
```

## Ejecución

```bash
python -m bolsa.cli --inicial data/inicial --periodicas data/periodicas --salida salidas
# o, si no está instalado como paquete:
PYTHONPATH=src python -m bolsa.cli
```

Genera en `salidas/`:
- **`conciliacion_<fecha>.xlsx`** — detalle, resumen por dirección, totales,
  semáforo y 11 pestañas de auditoría.
- **`recarga_propuestas_<fecha>.xlsx`** — fichero de recarga completa
  (ID Plaza, categoría, dirección, cláusula, saldo para cargar; incluye 0).

## Pruebas

```bash
python -m pytest -q        # 43 pruebas
```

Cubren: conteo inclusivo y topes de fecha; enlace propuesta↔contrato; los
**10 casos críticos** (ver `tests/test_casos_criticos.py`); y la validación
cruzada esperado vs registrado (`tests/test_validacion.py`).

En **Windows** puedes usar `run.bat` (crea el entorno, instala e ejecuta de una
vez).

---

## Reglas implementadas

| # | Regla | Dónde |
|---|-------|-------|
| 1 | Días inclusivos `fin − inicio + 1` (incluye findes/festivos, jornada completa) | `fechas.dias_inclusivos` |
| 2 | Base aritmética = solo el corte 02/07 (los 3 CSV). SaldoActual **no** es base | `motor.conciliar`, `cargas.inicial` |
| 3 | `saldo = postcontrol − consumo + devolución ± ajuste_cláusula` | `motor.conciliar` |
| 4 | Propuestas autorizadas tras el corte consumen aunque no haya contrato | `motor.computa_propuesta` |
| 5 | La **cláusula y la dirección reales del contrato** mandan sobre la propuesta; la dirección se resuelve por `(GFH, ID Plaza)` y se reparte por tramos GFH | `enlace`, `motor.reparte_dias`, maestro Divisiones |
| 6 | Abiertas/contratos abiertos reservan solo hasta 31/12/2026 | `fechas.fin_computable` |
| 7 | Contrato cerrado: fin = min(fin propuesta, fin contrato, 31/12/2026) | `fechas.fin_computable` |
| 8 | Devolución **prevista / registrada / pendiente** diferenciadas | `motor` + `MovimientosBolsa` |
| 9 | Un contrato puede tener varias propuestas sucesivas (no 1:1) | `enlace.enlaza_propuesta` |
| 10 | Enlace: **directo por comentario del contrato** ("Solicitud contratacion N") y, si no, heurístico IDRH/NIE + fechas + plaza (con equivalencias de plaza) | `enlace`, `cargas.propuesta_de_comentario` |
| 11 | Contrato N91c/S9b1a sin propuesta = excepción | `enlace.contratos_sin_propuesta` |
| 12 | Saldo negativo admisible por plaza; validación crítica a nivel Dirección+cláusula | `motor` (resumen) |
| 13 | Exportaciones completas y solapadas: dedup por id, histórico, recálculo total | `importaciones` |

---

## Diagnóstico de la situación (corte 02/07/2026 → datos 30/07/2026)

- **El corte inicial cuadra al 100 %**: en las 458 filas se cumple
  `saldo = base − nuevos + recuperados` (0 descuadres aritméticos).
- **311 propuestas** posteriores al corte consumen saldo; de ellas **113 no
  tienen contrato PeopleNet localizado** (reserva/compromiso pendiente).
- **34 contratos** prioritarios PeopleNet **sin propuesta** localizada.
- **9 contratos** cerraron antes del fin reservado → devolución prevista.
- **1.161 propuestas** sobre **plazas laborales** (no consumen; se listan como
  excepción). En el propio corte hay un descuadre histórico: `L134E/DGSG/S9b1a`.
- **144 excepciones** que requieren comprobación (sin IDRH, sin contrato,
  cláusula distinta, devolución no registrada).
- **Validación cruzada** (esperado vs `MovimientosBolsa`): 0 movimientos
  anómalos y 9 propuestas con diferencia, **todas explicadas** por el recorte a
  31/12/2026 (lo registrado coincide con el periodo completo de la propuesta).
  Pestañas `A10_Esperado_vs_Registrado` y `A11_Movimientos_anomalos`.
- **Dirección real (GFH):** el contrato manda también sobre la dirección; se
  resuelve por `(GFH, ID Plaza)` con el maestro de Divisiones y se **reparte por
  tramos** cuando el GFH cambia durante el contrato. En este corte, 0 propuestas
  posteriores cambian de dirección respecto a la propuesta (solo 38 de 4.474
  contratos abarcan >1 división), así que **no altera las cifras**, pero queda
  cubierto para cuando haya movilidad. Pestaña `A3b_Direccion_distinta`. La
  división `FORM` (formación) no está en el corte y se marca como fila nueva.

### Semáforo (control de sobre-compromiso)

`PeopleNet usados` cuenta los **días completos comprometidos de los contratos**
(hasta su fin o 31/12). PeopleNet **no conoce las propuestas**: lo único que
añade compromiso y PeopleNet no ve son las **propuestas sin contrato** (reservas).
El `sub_estado = MECANIZADA` no es fiable (se pone a mano, a veces en falso); lo
que decide si algo está ejecutado en PeopleNet es la **presencia de contrato**.

```
Contratación − ( Usados[contratos] + Reservas[sin contrato] ) = Margen tras compromisos
```

| Cláusula | Contratación | Usados | Reservas | Comprometido | **Margen** | Estado |
|----------|-------------:|-------:|---------:|-------------:|-----------:|:------:|
| **N91c** | 127.686 | 111.784 | 4.159 | 115.943 | **11.743** | 🟢 |
| **S9b1a**| 240.069 | 189.306 | 4.947 | 194.253 | **45.816** | 🟢 |

Mientras el margen sea positivo no hay sobre-compromiso. El `saldo de recarga`
(distribución por plaza) es **otra contabilidad** y no debe restarse contra el
global de PeopleNet.

### Diferencias cálculo vs Propuestas (para recargar)

| Cláusula | Saldo calculado | Saldo actual Propuestas | Diferencia |
|----------|----------------:|------------------------:|-----------:|
| **N91c** | 8.774 | 10.680 | −1.906 |
| **S9b1a**| 37.158 | 45.935 | −8.777 |

Propuestas muestra **más** saldo que el recalculado: refleja reservas/consumos
posteriores al corte aún **no mecanizados** en Propuestas. El detalle plaza a
plaza está en la pestaña `1_Detalle` y las causas en las pestañas de auditoría.

> Estas cifras se recalculan en cada ejecución; son el estado con los ficheros
> del 30/07/2026.

---

## Documentación

- [`docs/modelo_datos.md`](docs/modelo_datos.md) — modelo de datos, granularidad y diagrama de conciliación.
- [`docs/formato_cargas.md`](docs/formato_cargas.md) — formato y columnas de cada fichero.
- [`docs/procedimiento_operativo.md`](docs/procedimiento_operativo.md) — procedimiento para futuras cargas.

## Estructura del proyecto

```
config/       parametros.yaml, mapeo_columnas.yaml, equivalencias_nie_dni.csv
src/bolsa/    config, fechas, modelo, cargas/, equivalencias, enlace, motor, exportar, importaciones, cli
tests/        pruebas de fechas, casos críticos e integración
docs/         modelo de datos, formatos, procedimiento
```
