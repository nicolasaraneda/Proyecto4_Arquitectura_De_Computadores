# bandas_vacio.s: el lazo de prueba del kernel de cuatro bandas, sin kernel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mide el costo del lazo solo (generar el precio, guardar el resultado y
# contar), para restarlo de bandas_escalar.s y bandas_carriles.s. Lo corre
# tools/medir_kernel.sh con tb/tb_xd_kernel.sv: el testbench cuenta ciclos e
# instrucciones entre las dos escrituras a MARCA y anota cada escritura a RES.

.equ RES,   0x7F8              # resultado de cada vuelta
.equ MARCA, 0x7FC              # inicio y fin de la medición
.equ N,     256                # vueltas: el precio recorre los 256 valores

_start:
    li   x1, N
    li   x5, 0
    sw   x0, MARCA(x0)
lazo:
    addi x5, x5, 37            # precio siguiente: recorre 0 a 255
    andi x5, x5, 255
    mv   x8, x5                # sin kernel: el resultado es el precio
    sw   x8, RES(x0)
    addi x1, x1, -1
    bnez x1, lazo
    sw   x0, MARCA(x0)
fin:
    j    fin

.org 0x800
