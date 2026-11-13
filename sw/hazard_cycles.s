# =============================================================================
# hazard_cycles.s: lectura de un periférico cuyo valor depende del ciclo,
# seguida de uso inmediato.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Adaptado del sw/hazard_cycles.s de nuestro Proyecto 3. Allá el valor que
# cambiaba en cada ciclo era el contador CYCLES. El SoC del Proyecto 4 no
# tiene ese registro, así que aquí el testbench (tb/core_trace_tb.v con
# -DSWITCH_CONTADOR) conecta un contador a los interruptores y el programa lee
# BTN: el valor leído depende del ciclo en que se hace la lectura.
#
# Va aparte de hazard_test.s y hazard_review.s porque el ciclo de cada lectura
# cambia por diseño entre el Espino base (2 ciclos por instrucción) y el
# segmentado (1 ciclo). Las escrituras al banco de registros NO son
# comparables entre los dos, pero el resultado de cada comprobación sí: todas
# comparan el valor usado en la instrucción inmediata con el mismo valor usado
# una instrucción más tarde, cuando ya se lee del banco. Si el adelantamiento
# o la detención por carga fallan, los dos difieren.
#
# Lo que se compara entre el base y el segmentado son las salidas: DISP = 5 y
# LEDS = F en los dos (make riesgos).
# =============================================================================

.equ PERIPH_HI, 0x80000
.equ SPI_HI,    0x80010
.equ OFF_DISP,  0
.equ OFF_LEDS,  4
.equ OFF_BTN,   8
.equ TOTAL,     5

_start:
    lui   x2, PERIPH_HI
    lui   x9, SPI_HI
    la    x8, datos
    addi  x14, x0, 0

    # 1: lectura copiada en la instrucción inmediata y en la siguiente
    lw    x3, OFF_BTN(x2)
    addi  x4, x3, 0              # uso inmediato del dato del periférico
    addi  x5, x3, 0              # uso tardío: ya sale del banco
    bne   x4, x5, k1
    addi  x14, x14, 1
k1:
    # 2: dos lecturas seguidas, la segunda usada de inmediato como rs1
    lw    x3, OFF_BTN(x2)
    lw    x4, OFF_BTN(x2)
    sub   x5, x4, x3             # inmediato
    sub   x6, x4, x3             # tardío
    bne   x5, x6, k2
    addi  x14, x14, 1
k2:
    # 3: como operando de un salto, de inmediato. Cada camino confirma más
    #    tarde que el salto se decidió con el valor correcto.
    lw    x3, OFF_BTN(x2)
    beq   x3, x0, k3_cero
    beq   x3, x0, k3             # tardío: aquí x3 no puede ser cero
    addi  x14, x14, 1
    jal   x0, k3
k3_cero:
    bne   x3, x0, k3             # tardío: aquí x3 tiene que ser cero
    addi  x14, x14, 1
k3:
    # 4: como dato de un store, de inmediato
    lw    x3, OFF_BTN(x2)
    sw    x3, 0(x8)
    lw    x4, 0(x8)
    bne   x4, x3, k4
    addi  x14, x14, 1
k4:
    # 5: BTN y STATUS del esclavo SPI alternados, los dos usados de inmediato
    lw    x3, OFF_BTN(x2)
    lw    x4, 0(x9)              # STATUS vale 0 con el bus SPI quieto
    add   x5, x3, x4             # inmediato
    add   x6, x3, x4             # tardío
    bne   x5, x6, k5
    addi  x14, x14, 1
k5:
    sw    x14, OFF_DISP(x2)
    addi  x13, x0, TOTAL
    addi  x5, x14, 0
    bne   x14, x13, k_leds
    addi  x5, x0, 0xF
k_leds:
    sw    x5, OFF_LEDS(x2)
k_fin:
    j     k_fin

datos:
