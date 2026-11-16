# Mediciones de la edición ASIC: procedencia

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Estos archivos son copias, sin cambios, de las salidas guardadas de la pieza G de la factibilidad (rama `factibilidad-fondo`, commit `b556e1c`, carpeta `factibilidad/g_asic/mediciones/`, salidas del 14/11). Se traen solo las mediciones; el flujo (LibreLane 3.0.16 en Docker, PDK GF180MCU `gf180mcuD`, biblioteca de 7 pistas a 5 V) no se corrió en P7 y no se trae al repositorio.

| Archivo | Copia de | Qué contiene |
|---|---|---|
| `corridas.md` | `mediciones/corridas.md` | Las diez corridas del barrido de período (base y segmentado, 40 a 22 ns): área, celdas, holguras, DRC, LVS, antenas |
| `cierre.txt` | `mediciones/cierre.txt` | Qué corrida cierra con los criterios del Proyecto 3 |
| `potencia_base_t40.md` | `mediciones/potencia/base_t40/tabla.md` | Potencia con actividad real (OpenSTA, VCD del netlist final ejecutando `sw/trade.s` a 0,1 ms), energía por decisión, en las tres esquinas |
| `potencia_seg_t40.md` | `mediciones/potencia/seg_t40/tabla.md` | Lo mismo para el segmentado |

Cómo se regeneran (necesita Docker, la imagen de LibreLane y el PDK, varios GB; 2 horas el barrido):

```
git worktree add ../factibilidad origin/factibilidad-fondo
make -C ../factibilidad/factibilidad/g_asic barrido recolectar cierre potencia
```

Lo que calcula P7 a partir de estas tablas (`tools/p7/tablas.py`, `make p7-rapido`, salida en `docs/mediciones/p7/asic.txt`):

- Ops/s del kernel con la definición de P7 (8 operaciones útiles por tick) y los ciclos del kernel medidos en la FPGA, a 25 MHz y a la frecuencia máxima con cierre demostrado.
- Ops/W: MOPS del kernel y Ppeak divididos por la potencia de la ventana de cálculo (promedio de los ticks 20 y 23 de la tabla de potencia), esquina típica.
- Energía por decisión: la de la tabla (ronda 3 calculada por el flujo, rondas 2 y 1 estimadas sumando potencia de sondeo) y el costo marginal de decidir por operación útil.

La factibilidad usaba 6 operaciones útiles por tick, una definición provisoria. P7 fija 8 (`docs/codiseno.md`, sección 3), por eso los MOPS/W de `asic.txt` son distintos de los de `potencia_*.md`.
