# =============================================================================
# mix_clase7.s: programa con el mix de instrucciones de la clase 7.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La clase 7 (Métricas de Desempeño) calcula el CPI de Espino con un mix de
# ejemplo: da 2,35 para el Espino base (2 ciclos por instrucción, 3 los loads
# y 3 los saltos tomados) y estima 1,5 para un pipeline de 3 etapas (1 ciclo,
# 2 los loads y 3 los saltos tomados). Esas dos cifras fijan el mix:
#     2 + loads + tomados     = 2,35
#     1 + loads + 2 * tomados = 1,5
# de donde loads = 20 % y saltos tomados = 15 %. El 65 % restante son
# instrucciones que cuestan lo mismo en los dos casos (ALU, stores y saltos
# no tomados).
#
# El lazo de este programa tiene 20 instrucciones con ese mix exacto:
#     4 loads, 3 saltos tomados (jal, jalr y j) y 13 de las otras
#     (9 de ALU, 2 stores y 2 saltos no tomados).
# Se usa para medir el CPI del base y del segmentado con el mismo programa y
# compararlo con la estimación de la clase (make medir-espino).
# =============================================================================

_start:
    la    x8, datos
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

datos:
    .word 0x00000011, 0, 0x00001234
.org 0x800
