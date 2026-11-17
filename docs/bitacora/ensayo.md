# Bitácora: ensayo general (punto 6 de la lista de trabajo del 16 al 17/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Objetivo: un comando `make ensayo` que corra las tres rondas para cada peldaño con una serie nueva y muestre lo que vería la maestra, patrimonio incluido. Rama `ensayo`.

- `tools/ensayo.py`: una serie nueva por ronda (familia `modelo` de `ref/series.py`, semilla 20261130, que no se usó para elegir nada), y para cada peldaño una copia del testbench oficial por el RTL con Verilator, como `tools/equiv.sh`: solo cambian programa, serie, período, largo y nombre de `decisiones.csv` (el script cuenta las líneas cambiadas). Muestra lo que imprime el testbench y exige `decisiones.csv` idéntico a la referencia del peldaño (`ref/trader.py` para R0, `ref/fondo.py` para R1 y R2).
- R2 se simula con el vigilante en el SoC; en una ronda sana no dispara, así que se comporta como R1.
- Resultado (`docs/mediciones/ensayo.txt`): 9 de 9 corridas con 4/4 y decisiones iguales a su referencia, en 290 s. Patrimonio por ronda: 9 656, 10 014 y 8 125, igual en los tres peldaños; comprar y mantener 10 310, 5 123 y 8 197. Peor caso de respuesta: 44 ciclos en R0; 391, 435 y 443 en R1 y R2.
- Lo que se ve: en estas tres series el fondo decide igual que `max_media` (como en la práctica a 0,1 ms), y la suerte de la serie pesa más que la regla: dos de las tres rondas terminan bajo la caja inicial.
- Qué no hace: rondas seguidas sin reset (están en la matriz de estrés, `make fondo-estres`) ni el relevo de R2 (`make vig-relevo`).
