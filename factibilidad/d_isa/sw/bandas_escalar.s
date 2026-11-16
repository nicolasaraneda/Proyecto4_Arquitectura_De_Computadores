# bandas_escalar.s: kernel de cuatro bandas con las instrucciones de RV32E.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El kernel evalúa cuatro estrategias en papel con el mismo precio p. Cada
# una tiene su media m_i y su banda b_i:
#     entrar_i = p < m_i - b_i          salir_i = p > m_i
#     pos_i    = (pos_i | entrar_i) & ~salir_i
# y entrega un bit por estrategia: resultado = pos_0 + 2 pos_1 + 4 pos_2 + 8 pos_3.
# Es la misma regla de sw/trade.s, cuatro veces. Modelo: tools/kernel_bandas.py.
#
# Esta es la versión de referencia, sin instrucciones nuevas: 6 instrucciones
# por banda y 6 para juntar los cuatro bits, 30 en total. La versión con
# carriles es bandas_carriles.s. Las mide tools/medir_kernel.sh.
#
# Registros: x10 a x13 las medias, x3, x4, x14 y x15 las posiciones, x5 el
# precio, x6 y x7 temporales, x8 el resultado, x1 el contador.

.equ RES,   0x7F8
.equ MARCA, 0x7FC
.equ N,     256
.equ M0, 100
.equ M1, 160
.equ M2, 60
.equ M3, 200
.equ MENOS_B0, -2             # las bandas, con signo menos (2, 40, 70 y 16)
.equ MENOS_B1, -40
.equ MENOS_B2, -70            # mayor que la media: esta estrategia nunca entra
.equ MENOS_B3, -16

_start:
    li   x1, N
    li   x5, 0
    li   x10, M0
    li   x11, M1
    li   x12, M2
    li   x13, M3
    li   x3, 0
    li   x4, 0
    li   x14, 0
    li   x15, 0
    sw   x0, MARCA(x0)
lazo:
    addi x5, x5, 37
    andi x5, x5, 255

# --- kernel: 30 instrucciones -------------------------------------------------
    addi x6, x10, MENOS_B0          # umbral = m - b (si queda negativo, slt da 0)
    slt  x6, x5, x6            # entrar = p < umbral
    slt  x7, x10, x5           # salir = m < p
    or   x3, x3, x6
    xori x7, x7, 1
    and  x3, x3, x7            # pos = (pos | entrar) & ~salir

    addi x6, x11, MENOS_B1
    slt  x6, x5, x6
    slt  x7, x11, x5
    or   x4, x4, x6
    xori x7, x7, 1
    and  x4, x4, x7

    addi x6, x12, MENOS_B2
    slt  x6, x5, x6
    slt  x7, x12, x5
    or   x14, x14, x6
    xori x7, x7, 1
    and  x14, x14, x7

    addi x6, x13, MENOS_B3
    slt  x6, x5, x6
    slt  x7, x13, x5
    or   x15, x15, x6
    xori x7, x7, 1
    and  x15, x15, x7

    add  x8, x15, x15          # juntar los cuatro bits: ((p3 * 2 + p2) * 2 + p1) * 2 + p0
    add  x8, x8, x14
    add  x8, x8, x8
    add  x8, x8, x4
    add  x8, x8, x8
    add  x8, x8, x3
# -----------------------------------------------------------------------------

    sw   x8, RES(x0)
    addi x1, x1, -1
    bnez x1, lazo
    sw   x0, MARCA(x0)
fin:
    j    fin

.org 0x800
