# Procedimiento operativo para futuras cargas

La conciliación **siempre se recalcula desde el corte inicial 02/07/2026**. Las
cargas periódicas son exportaciones **completas**: se sustituyen enteras, no se
acumulan.

## Cada vez que haya nuevos ficheros periódicos

1. **Copiar** los 5 ficheros a `data/periodicas/` conservando el patrón de
   nombre (`PropuestasContratacion_<fecha>.csv`, `Bolsa_de_dias_<fecha>.xlsx`,
   `Contratos_PeopleNet_<fecha>.ods`, `MovimientosBolsa_<fecha>.csv`,
   `SaldoActualPropuestas_<fecha>.csv`). La CLI toma el **más reciente** por
   patrón. Los del corte inicial (`data/inicial/`) **no se tocan nunca**.

2. **Comprobar el mapeo** (`config/mapeo_columnas.yaml`) si la exportación pudo
   cambiar de columnas. No hace falta tocar código.

3. **Registrar equivalencias NIE/DNI** nuevas en
   `config/equivalencias_nie_dni.csv` (`idrh_a;idrh_b;motivo;fecha_alta;usuario`).
   Quedan auditadas en la pestaña `A8b`.

4. **Ejecutar**:
   ```bash
   PYTHONPATH=src python -m bolsa.cli
   ```

5. **Revisar** en `salidas/conciliacion_<fecha>.xlsx`:
   - `4_Semaforo`: que ninguna cláusula quede en **ROJO** (disponible tras
     compromisos < 0). Ámbar = margen < 5 %.
   - `1_Detalle` y `2_Resumen_Direccion`: diferencias cálculo vs Propuestas.
   - Pestañas `A1`–`A9`: reservas, mecanizadas sin contrato, cláusula distinta,
     contratos sin propuesta, cierres/devoluciones, movimientos, auditoría del
     corte, importaciones/equivalencias y excepciones.

6. **Recargar Propuestas** con `salidas/recarga_propuestas_<fecha>.xlsx`
   (incluye filas a 0 para permitir consumos futuros).

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

Deben pasar las 22 pruebas (fechas, casos críticos e integración) antes de
publicar resultados.
