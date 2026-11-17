# Bitácora: campañas largas del 16 y 17/11

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Punto 2 de la lista del 16/11. Rama `campanas-noche`. Todo corrió por la cola global de la máquina, de a un trabajo por vez.

## Qué se corrió

| Campaña | Resultado | Archivo |
|---------|-----------|---------|
| Barrel contra el Espino base con la máscara exacta de R1 | 50,8 millones de instrucciones (23,9 millones lineales, 91,48 % distintas; 26,9 millones en lazos), cero diferencias | `docs/mediciones/noche/barrel_r1_50m.txt` |
| Gemelo de R0, 100 series de 20 000 ticks por familia a los tres períodos | 90 millones de ticks, todos los bytes iguales a `ref/trader.py` | `docs/mediciones/noche/gemelo_series_r0_20k.txt` |
| Gemelo de R1, lo mismo | 90 millones de ticks, todos iguales a `ref/fondo.py` | `docs/mediciones/noche/gemelo_series_r1_20k.txt` |
| Exhaustiva de R0 | Cobertura 4 144 770 de 4 144 770; gemelo y RTL (24 series largas, 19,1 millones de ticks, y 300 de la esquina) iguales a la referencia | `docs/mediciones/noche/exhaustivo_r0.txt`, `docs/verificacion_exhaustiva.md` |
| Exhaustiva de R1 | Supervisor y gestor 1 al 100 %, gestor 2 al 86,24 %, gestor 3 al 99,70 %; gemelo y RTL iguales a la referencia | `docs/mediciones/noche/exhaustivo_r1.txt` |

## Errores encontrados (todos de las herramientas de prueba, ninguno del diseño)

1. **Arreglo de 20 000 precios del testbench oficial.** Con series más largas, Verilator plegaba los índices y mandaba otros precios: la primera corrida del RTL de R0 no valía. La copia del testbench que arman `r0.py` y `r1.py` dimensiona el arreglo con `NTICKS` y comprueba que no cambia ninguna otra línea (5 o 6, según si el oficial ya apunta a `sw/trade.hex`; la primera versión exigía 6 y rechazó todas las series).
2. **Búfer de 4 MB por línea del gemelo en modo lote.** Cortaba las series largas: 314 diferencias falsas en R1. Las series largas van con `--serie`.
3. **Memoria.** La cobertura juntaba con `pool.map` los mapas de bits de todas las series: 8 GB en R0 y 30,6 GB en R1, que dejaron la máquina sin memoria (la corrida se detuvo a mano antes de que WSL se cayera). Ahora se acumulan a medida que llega cada serie (`imap_unordered`), y la cola detiene cualquier trabajo si la memoria disponible baja de 3 GB.
4. **El patrimonio de 32 bits.** En las dos series de precios bajos el testbench y el gemelo desbordan la contabilidad (la referencia en Python no). Se comparan los bytes de decisión, que es lo que se verifica.

## Qué falta

Nada de este punto. La votación de R1 no es exhaustiva (4 de 8 juegos de votos aparecen con estas series); está cubierta por los controles de `make check-fondo`.
