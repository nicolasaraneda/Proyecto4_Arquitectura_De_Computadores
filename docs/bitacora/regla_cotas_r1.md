# Bitácora: la regla de cotas en R1 y R2 (opción F-a, decisión T133)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `regla-cotas-r1`, desde `0acda61` (R0 ya con la regla nueva). El hardware de R1 y R2 no cambia: el programa y la tabla entran por `icebram` en los moldes guardados.

## 17/11, noche

- Plan: `sw/fondo.s` nuevo (hilo 0 con la regla y los umbrales leídos de la tabla en cada tick, hilos 1 a 3 en un lazo de espera), `ref/fondo.py` como modelo exacto, y adaptar el testbench del fondo y las pruebas de la puerta, que estaban hechas para el fondo que vota.
