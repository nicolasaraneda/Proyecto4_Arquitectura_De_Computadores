# Bitácora: caída de la frecuencia mínima del segmentado entre P1 y P7

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Script: `tools/p7/caida_segmentado.sh` (`make p7-caida-seg`, unos 3 minutos con 24 núcleos). Todas las cifras de esta bitácora están en `docs/mediciones/p7/caida_segmentado.txt`.

## Pregunta

El SoC con el core segmentado (`-DESPINO_SEGMENTADO`, `sw/trade.hex`) medía en P1 una frecuencia máxima mínima de 51,59 MHz en 10 semillas (`docs/mediciones/barrel/recursos.txt`, 993 celdas). En P7 midió 45,34 MHz de mínima y 47,20 de mediana (`docs/mediciones/p7/recursos.txt`, 990 celdas). El RTL del core no cambió entre las dos mediciones. Se quería saber si la caída viene de lógica nueva en el SoC, del programa en la BRAM, de una diferencia de método entre los scripts o de la variación propia de la herramienta.

## Método

1. Se ejecutó el mismo comando, `DEFS=-DESPINO_SEGMENTADO HEX=sw/trade.hex tools/medir_variante.sh ETIQUETA N`, con el script del commit actual sobre `rtl/`, `sw/trade.hex` y `goboard.pcf` de cada commit, extraídos con `git archive`. Así la única variable es el contenido del commit.
2. Se sintetizó el segmentado en cada commit que cambió `rtl/`, `sw/trade.hex`, `goboard.pcf` o `tools/medir_variante.sh` desde la medición de P1 (`e118269`) y se comparó el conteo de celdas por tipo y una huella de la netlist (tipo, parámetros y conexiones de cada celda, sin atributos).
3. Se corrió nextpnr con las semillas 1 a 40 en cuatro commits: el de P1 (`e118269`), el anterior al salto (`05b3b7e`), el del salto (`c293cf4`) y el actual.
4. Para separar el efecto de la síntesis, se sintetizaron las fuentes del commit actual leyendo los archivos de `rtl/` en diez órdenes distintos (40 semillas cada uno). El orden 0 es el de `medir_variante.sh` y reproduce el commit actual semilla a semilla, lo que confirma que el nombre de los archivos no influye.
5. Se comprobó con `equiv_make`, `equiv_simple` y `equiv_induct` de Yosys que el SoC segmentado de P1 y el actual son equivalentes, con la memoria del SoC y las BRAM del banco de registros cortadas en sus puertos. Como control negativo, una copia del SoC actual con la selección de la tabla activa tiene que dar distinta, y da distinta.

## Resultados

- Con el mismo script se reproducen los dos valores: P1 da 51,59 de mínima y 53,48 de mediana en las semillas 1 a 10; el commit actual da 45,34 y 47,20. La diferencia no viene del método ni de la exclusión de `rtl/00_*`.
- La netlist cambia en dos commits. En `7bdc62b` (extensión de la ISA, que solo toca código del barrel) pasa de 801 a 802 LUT4, pero la frecuencia no cambia: el commit anterior al salto tiene esa misma netlist y su mediana en 40 semillas es 53,45 MHz, contra 53,63 en P1 (p = 0,91 con Mann-Whitney). En `c293cf4` (tabla de parámetros y vigilante en `pochoco_soc.v` y tres salidas nuevas en el esclavo SPI) pasa a 798 LUT4 con los mismos 98 SB_CARRY, 586 flip-flops y 12 BRAM. Desde ahí la netlist es idéntica hasta el commit actual.
- `sw/trade.hex` es el mismo en todos los commits.
- La equivalencia formal da EQUIVALENTES en P1 contra el actual y en el anterior al salto contra el salto (2971 celdas `$equiv` probadas, ninguna sin probar). Con `Tabla = 0` y `Vigilante = 0` el SoC no tiene lógica nueva: `tab_sel` vale cero, la entrada nueva del multiplexor de lectura nunca se elige y las salidas nuevas del esclavo SPI no se usan.
- En 40 semillas las distribuciones antes y después del salto no se solapan: ninguna semilla del salto supera la mínima de la anterior (U = 1600 de 1600, p = 1,4e-14). Mediana 53,45 MHz antes y 47,88 MHz después; mínima 51,37 y 44,82. No es ruido de colocación de una semilla: la netlist nueva es más lenta en promedio.
- Las mismas fuentes leídas en otro orden dan cuatro netlists distintas (de 798 a 805 LUT4) con medianas de 47,88 a 53,59 MHz y mínimas de 43,89 a 50,55 MHz. El rango abarca los dos extremos: el orden 5 (mediana 53,59) queda donde estaba P1 (53,63) y el orden 0 es el actual.
- La ruta crítica es la misma ruta del RTL antes y después: sale del banco de registros, pasa por la ALU y llega al habilitador de `pc_target` (o de un registro de periféricos). Cambia su implementación: en P1 el promedio sobre las 40 semillas es 34,5 pasos de lógica (LUT y acarreo) con 10,36 ns de ruteo; en el actual son 16,1 pasos con 13,45 ns de ruteo, y el período total sube de 18,67 a 20,76 ns.

## Conclusión

La caída de 51,59 a 45,34 MHz no se debe a un cambio de lógica, del programa ni del método de medición. La causa es que el commit `c293cf4` cambió el texto de `pochoco_soc.v` y del esclavo SPI sin cambiar su función; Yosys numera distinto las señales internas y ABC entrega otra netlist equivalente, de 798 LUT4 en vez de 802, que nextpnr coloca y rutea peor en casi todas las semillas. Que este efecto es propio de la síntesis lo muestra el experimento del orden de lectura: con exactamente el mismo RTL, la mediana del segmentado varía entre 47,88 y 53,59 MHz.

Consecuencia para la tabla de co-diseño: la frecuencia de una variante medida con una sola síntesis tiene una incertidumbre de unos 6 MHz en la mediana, independiente de la cantidad de semillas de nextpnr. Diferencias de ese orden entre variantes no se deben atribuir al diseño. En los cuatro commits el segmentado cierra a 25 MHz en 40 de 40 semillas; en el commit actual la peor semilla necesita 22,31 ns de los 40 disponibles.
