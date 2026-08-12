# Procedimiento operativo para futuras cargas

La conciliación **siempre se recalcula desde el corte inicial 02/07/2026**. Las
cargas periódicas son exportaciones **completas**: se sustituyen enteras, no se
acumulan.

## Cada vez que haya nuevos ficheros periódicos

1. **Copiar** los ficheros a `data/periodicas/` conservando el patrón de
   nombre. La CLI toma el **más reciente** por patrón. Los del corte inicial
   (`data/inicial/`) **no se tocan nunca**.
   - **Imprescindibles:** `PropuestasContratacion_<fecha>.csv`,
     `Bolsa_de_dias_<fecha>.xlsx` (o `Bolsa_PeopleNet_...`),
     `Contratos_PeopleNet_<fecha>.xlsx` (o `.ods`).
   - **Opcionales** (ya no entran en el cálculo anclado; solo informe/auditoría):
     `MovimientosBolsa_<fecha>.csv`, `SaldoActualPropuestas_<fecha>.csv`.
     La CLI todavía los pide; si usas `exportar_consultas.ps1` se generan igual.

2. **Comprobar el mapeo** (`config/mapeo_columnas.yaml`) si la exportación pudo
   cambiar de columnas. No hace falta tocar código.
   - El export de **Contratos** debe incluir `Inicio GFH`, `Fin GFH`, `id. GFH1`
     (tramos GFH) para que la dirección real se reparta bien.
   - El **maestro de Divisiones** va en `data/maestros/Divisiones_Plazas_GFHs.xlsx`.
     Actualízalo si se dan de alta nuevos GFH/plazas (si falta un `(plaza,GFH)`,
     esos días se marcan como excepción “sin división”).

3. **Registrar equivalencias NIE/DNI** nuevas en
   `config/equivalencias_nie_dni.csv` (`idrh_a;idrh_b;motivo;fecha_alta;usuario`).
   Quedan auditadas en la pestaña `A8b`.
   - **Equivalencias de plaza** (cuando contrato y propuesta usan códigos
     distintos para la misma categoría, p.ej. `E071A2`/`E073A2`) en
     `config/equivalencias_plazas.csv`. Solo enlaza los pares declarados; no
     enlaza plazas no relacionadas. Los enlaces así se marcan en `A9`.

3bis. **Política de reserva** (`parametros.yaml → sub_estados_reserva_firme`):
   una propuesta **enlazada a contrato consume siempre** (mecanizada); una
   propuesta **sin contrato** solo reserva si su `sub_estado` está en esa lista.
   Endurece o relaja según qué aprobaciones consideres un compromiso firme. El
   desglose está en `A2b_Reserva_por_subestado`.

4. **Ejecutar**:
   ```bash
   PYTHONPATH=src python -m bolsa.cli
   ```

> **Registro de contratos** (`data/estado/registro_contratos.csv`, no se
> versiona): en cada ejecución congela el **alta** de cada contrato la 1ª vez
> que aparece y marca los **contratos nuevos** de esa importación (columna en
> `A4b`). La primera ejecución marca todo como nuevo; a partir de la 2ª, solo
> los realmente nuevos. Consérvalo entre cargas.

5. **Revisar** en `salidas/conciliacion_<fecha>.xlsx`:
   - `4_Semaforo`: que ninguna cláusula quede en **ROJO** (disponible tras
     compromisos < 0). Ámbar = margen < 5 %.
   - `1_Detalle` y `2_Resumen_Direccion`: diferencias cálculo vs Propuestas.
   - Pestañas `A1`–`A9`: reservas, mecanizadas sin contrato, cláusula distinta,
     contratos sin propuesta, cierres/devoluciones, movimientos, auditoría del
     corte, importaciones/equivalencias y excepciones.
   - `A12_Coherencia_enlace_directo`: enlaces por comentario cuyo contrato **no
     corresponde** con la propuesta en DNI, fecha de inicio o plaza. Casos:
     `NIE↔DNI` (probable mismo — registrar equivalencia), `L↔E` (misma
     categoría laboral/estatutaria), `DISTINTO`/`FECHA distinta` (revisar
     posible error). En el informe web salen con `⚠` y su desglose.
   - `A13_Usados_vs_Contratos`: que el `Días Usados` de PeopleNet cuadre con la
     suma de contratos a fin real (diagnóstico; ~0,3 % de residuo en S9b1a es
     normal). Si se dispara, faltan contratos o hay descuadre.
   - `B1_Anclado_PeopleNet_Direccion`: **control por dirección** del modo
     anclado (verde si su global ≥ 0). `B2` desglosa por plaza; `B3_Sin_GFH`
     lista contratos cuyo GFH falta en el maestro (DNI + GFH a añadir).

6. **Recargar Propuestas.** Dos opciones (ver
   [`metodologia_y_conteo.md`](metodologia_y_conteo.md)):
   - `recarga_propuestas_<fecha>.xlsx` — **modo actual** (desde el corte).
   - `recarga_anclada_PeopleNet_<fecha>.xlsx` — **modo anclado** (`Contratación
     − Usados_real − Pendiente`, gasto real de PeopleNet). El recomendado si
     quieres el disponible alineado con PeopleNet.

7. **Consultar** `salidas/informe_<fecha>.html` (informe web local): un único
   fichero que se abre en el navegador (doble clic), sin internet ni servidor.
   Cuatro vistas para atender preguntas al vuelo:
   - **Semáforo** y totales por cláusula.
   - **Por Dirección**: cascada del saldo (postcontrol − consumo + devoluciones
     ± ajuste = calculado) — «¿por qué me quedan tan pocos días?».
   - **Por DNI/NIE**: propuestas, contratos y devoluciones del DNI, con
     devolución *prevista* (calculada), *registrada* y *pendiente*.
   - **Por Propuesta**: estado de la devolución — «¿ya hicieron el movimiento?».
   > Las búsquedas «Por DNI» y «Por Propuesta» incluyen también las
   > `APROBADA/MECANIZADA` **vigentes** (fin ≥ corte) aunque **no computen**
   > (p.ej. autorizadas antes del 02/07, ya en la base): salen atenuadas con la
   > etiqueta *no computa* y su motivo, para poder localizarlas sin que alteren
   > los totales. El histórico ya terminado (anterior al corte) no se incluye.
   > Contiene DNI/NIE: es un fichero **local**, no se publica ni se versiona
   > (está en `salidas/`, ignorada por git).

## Controles antes de dar por buena una carga

- `avisos_corte` vacío (el corte cuadra) — es una prueba automática.
- `movimiento_id` sin duplicados (dedup automático + prueba).
- Revisar **excepciones** (`A9`): sin IDRH, sin contrato, cláusula distinta,
  devolución prevista no registrada. Resolver o justificar cada una.
- Ninguna devolución debe aplicarse dos veces: el `saldo_calculado` usa el
  consumo **neto**; los movimientos solo verifican.

## Qué NO hacer

- No usar `SaldoActualPropuestas` como base de cálculo (solo comparación).
- No suponer una devolución aplicada si no aparece en `MovimientosBolsa`
  (se muestra como *pendiente*, diferenciada).
- No asumir relación 1:1 contrato↔propuesta.
- No aplicar consumos/devoluciones a plazas laborales (`L…`).

## Pruebas

```bash
python -m pytest -q
```

Deben pasar las 64 pruebas (fechas, casos críticos, integración, modo anclado)
antes de
publicar resultados.
