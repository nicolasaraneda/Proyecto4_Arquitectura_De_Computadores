# bandas_carriles.s: kernel de cuatro bandas con los carriles de 4 x 8 bits.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El mismo kernel de bandas_escalar.s, con las cuatro estrategias empaquetadas
# en un registro (un carril de 8 bits cada una): 8 instrucciones en vez de 30.
# La posición de cada estrategia es una máscara por carril (0xFF adentro, 0x00
# afuera), que es lo que entrega pcmpltu8. Por eso se puede combinar con or,
# xori y and de RV32E, y pmovmsk8 la pasa a un bit por carril al final.
#
# Las instrucciones nuevas se pasan a .word con tools/xd_word.py --pre.
# Necesita el core con -DXD_SIMD=28 (saturadas, pbcast8 y pmovmsk8).
#
# Registros: x10 las cuatro medias, x11 las cuatro bandas, x4 las cuatro
# posiciones, x5 el precio, x6, x7 y x9 temporales, x8 el resultado.

.equ RES,   0x7F8
.equ MARCA, 0x7FC
.equ N,     256
.equ MEDIAS, 0xC83CA064        # carriles 3 a 0: 200, 60, 160, 100
.equ BANDAS, 0x10462802        # carriles 3 a 0: 16, 70, 40, 2 (la de 70 satura el umbral en 0)

_start:
    li   x1, N
    li   x5, 0
    li   x10, MEDIAS
    li   x11, BANDAS
    li   x4, 0
    sw   x0, MARCA(x0)
lazo:
    addi x5, x5, 37
    andi x5, x5, 255

# --- kernel: 8 instrucciones --------------------------------------------------
    pbcast8  x6, x5            # el precio en los cuatro carriles
    psubus8  x7, x10, x11      # umbral = m - b, con piso en 0
    pcmpltu8 x7, x6, x7        # entrar = p < umbral (0xFF o 0x00 por carril)
    pcmpltu8 x9, x10, x6       # salir = m < p
    or       x4, x4, x7
    xori     x9, x9, -1
    and      x4, x4, x9        # pos = (pos | entrar) & ~salir
    pmovmsk8 x8, x4            # un bit por carril
# -----------------------------------------------------------------------------

    sw   x8, RES(x0)
    addi x1, x1, -1
    bnez x1, lazo
    sw   x0, MARCA(x0)
fin:
    j    fin

.org 0x800
