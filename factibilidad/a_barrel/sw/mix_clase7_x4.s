# =============================================================================
# mix_clase7_x4.s: el mix de instrucciones de la clase 7 en los cuatro hilos.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es sw/mix_clase7.s adaptado al Espino barrel (factibilidad/a_barrel). El
# lazo de 20 instrucciones es el mismo, copiado sin cambios: 4 loads, 3 saltos
# tomados (jal, jalr y j) y 13 de las otras (9 de ALU, 2 stores y 2 saltos no
# tomados), que es el mix con que la clase 7 calcula CPI 2,35 para el Espino
# base. Lo que cambia:
#   - La tabla de arranque: el hilo t parte en la dirección 4 t.
#   - Cada hilo recibe en x8 su propia zona de datos. Los cuatro ejecutan el
#     mismo código (es reentrante: cada hilo tiene su banco de registros).
# =============================================================================

# --- Tabla de arranque ----------------------------------------------------------
    j    hilo0
    j    hilo1
    j    hilo2
    j    hilo3

hilo0:
    la    x8, datos0
    j     _start
hilo1:
    la    x8, datos1
    j     _start
hilo2:
    la    x8, datos2
    j     _start
hilo3:
    la    x8, datos3
    j     _start

_start:
    addi  x5, x0, 0
    addi  x6, x0, 1
    addi  x9, x0, 0
lazo:
    lw    x1, 0(x8)              # load 1
    add   x2, x1, x5             # ALU, usa el dato recién cargado
    addi  x5, x5, 1              # ALU
    sw    x2, 4(x8)              # store 1
    lw    x3, 4(x8)              # load 2
    xor   x4, x3, x2             # ALU: da 0
    bne   x4, x0, error          # salto no tomado 1
    lbu   x7, 8(x8)              # load 3
    andi  x7, x7, 15             # ALU
    beq   x6, x0, error          # salto no tomado 2
    jal   x1, subrutina          # salto tomado 1
    or    x9, x9, x7             # ALU
    sub   x10, x5, x9            # ALU
    sh    x10, 8(x8)             # store 2
    lh    x11, 8(x8)             # load 4
    slt   x12, x11, x5           # ALU
    sltu  x13, x9, x5            # ALU
    j     lazo                   # salto tomado 3
subrutina:
    addi  x9, x7, 3              # ALU
    jalr  x0, 0(x1)              # salto tomado 2
error:
    j     error

datos0:
    .word 0x00000011, 0, 0x00001234
datos1:
    .word 0x00000022, 0, 0x00002345
datos2:
    .word 0x00000033, 0, 0x00003456
datos3:
    .word 0x00000044, 0, 0x00004567
.org 0x800
