# Formato de carga de cada fichero

Los nombres de columna se mapean en `config/mapeo_columnas.yaml`. Si una
exportación cambia nombres/orden, se ajusta **ahí**, sin tocar el código.

## Iniciales inmutables (corte 02/07/2026) — CSV, delimitador `;`

### 1. `*_auditoria.csv` (detalle completo — base aritmética)
`periodo; id_plaza; descripcion_categoria; direccion_id; direccion_codigo;
direccion_nombre; clausula; saldo; categoria_ids_maestro; saldo_base_02_07;
nuevos_control; recuperados_control; origen_ajustes`
- `saldo = saldo_base_02_07 − nuevos_control + recuperados_control` (verificado).
- `categoria_ids_maestro`: lista de `categoria_id` agregados (`65,169,175`).

### 2. `*_post_control.csv` (solo saldo final, verificación cruzada)
`periodo; id_plaza; descripcion_categoria; direccion_id; direccion_codigo;
direccion_nombre; clausula; saldo`

### 3. `*_postcontrol_diario_*.csv` (diario 30/06→02/07, trazabilidad)
`fecha_registro; hoja_origen; fila_origen; propuesta_id; direccion_codigo;
categoria_texto; id_plaza; clausula; dias_nuevos; dias_recuperados;
saldo_direccion_reportado; clasificacion`
- `fila_origen` enlaza con `origen_ajustes` del auditoría.
- `clasificacion`: `contract_peoplenet`, `group_contratacion`,
  `manual_return_assumption`.

## Periódicos

### 4. `Bolsa_de_dias_*.xlsx` — hoja `Export` (bolsa global por cláusula)
Cabecera en la fila 2: `Año | Id. Tipo Nom. Cláusula. | Días contratación |
Días Usados | Comentario`. `disponible = Días contratación − Días Usados`.

### 5. `PropuestasContratacion_*.csv` — delimitador `|`, fecha `YYYY-MM-DD HH:MM:SS`
Columnas usadas: `propuesta_id, categoria_codigo, direccion_codigo, clausula,
estado, sub_estado, fecha_autorizacion, fecha_inicio_contrato,
fecha_fin_contrato, idrh, propuesta_original_id, propuesta_sustituta_id`.
- Estados: `APROBADA` (vivo), `ANULADA/DENEGADA/CANCELADA/DEVUELTA_AL_GESTOR`.
- Sub_estado `MECANIZADA` = mecanizada; otros = reserva pendiente de mecanizar.
- `idrh` puede ser DNI o NIE (`X…`).

### 6. `Contratos_PeopleNet_*.xlsx` (o `.ods`) — tabla/hoja `Query`, fecha `DD/MM/YYYY`
`ID RH | Núm. periodo | Inicio Plaza | Fin Plaza | Id. Cláusula |
Motivo inicio | ID Plaza | Descripción Plaza | Inicio GFH | Fin GFH |
id. GFH1 | Nombre GFH`.
- **Un `(ID RH, Núm. periodo)` = 1 contrato**; puede tener **varias filas**, una
  por **tramo GFH** (con su `Inicio GFH`/`Fin GFH`). El cargador las agrupa.
- `Fin Plaza` vacío = contrato **abierto**; `Fin GFH` vacío = tramo abierto.
- El formato real puede ser XLSX o ODS: **se autodetecta** por contenido.
- **El contrato manda** sobre cláusula y dirección (regla 5).

### Maestro `Divisiones_Plazas_GFHs.xlsx` — hoja `Hoja1`
`ID Plaza | DG | ID GFH | División asignada | Nivel`.
- Traduce **`(ID Plaza, ID GFH) → División asignada`** (la dirección real). Es
  función (una división por combinación). Va en `data/maestros/`.
- No contiene datos personales.

### 7. `MovimientosBolsa_*.csv` — delimitador `|`, fecha `YYYY-MM-DD HH:MM:SS`
`movimiento_id | bolsa_dias_id | propuesta_id | fecha_movimiento |
tipo_movimiento | importe_movimiento | … | categoria_codigo | direccion_codigo |
… | clausula`.
- `movimiento_id` **único** (dedup obligatorio).
- Signo: `NUEVA_SOLICITUD` (+ consume); `DEVOLUCION_SOLICITUD`,
  `ANULACION_SOLICITUD` (− devuelve).

### 8. `SaldoActualPropuestas_*.csv` — delimitador `|`
`fecha_corte | anio | bolsa_dias_id | direccion_id | direccion_codigo |
direccion_nombre | categoria_id | categoria_codigo | categoria_descripcion |
clausula | bolsa_dias_inicial | bolsa_dias_restante`.
- Nivel `categoria_id`; se agrega a `id_plaza` para comparar. **No** es base.

## Notas de inconsistencias detectadas
- Tres delimitadores (`;` iniciales, `|` periódicos) y dos formatos de fecha.
- `direccion_nombre` puede venir vacío en alguna fila del corte (p.ej. `E102A2`).
- Cláusulas fuera de alcance en contratos: `N91a`, `N91b`, `S9b1b`, `S9b1c`.
- Propuestas prioritarias sin `idrh` (no enlazables) y sobre plazas `L`.
