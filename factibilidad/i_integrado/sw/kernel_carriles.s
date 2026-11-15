# kernel_carriles.s: tres hilos de estrategia que usan los carriles de 4 x 8
# bits y emad sin parar, para correr junto a la regla base en el hilo 0.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Igual que kernel_media.s, para la variante con los carriles en el sumador de
# la ALU (-DXD_SIMDALU=12, que reemplaza espino_alu por xd_alu). Es el caso
# más delicado de la integración: la ALU corta el acarreo cada 8 bits cuando
# la instrucción que está en X es de carriles, y en el ciclo siguiente la usa
# una instrucción de RV32E de otro hilo. Cada vuelta:
#
#     x1 = x1 + 37                          el "precio", RV32E
#     x3 = pbcast8(x1)                      el precio en los cuatro carriles
#     x4 = psubus8(x2, x3)                  max(media - precio, 0) por carril
#     x7 = pcmpltu8(x3, x2)                 0xFF donde precio < media
#     x9 = paddus8(x4, x7)                  suma saturada
#     x9 = padd8(x9, x3)
#     x9 = psub8(x9, x2)
#     x1 = emad(x9, x1, 5)                  x1 + (x9 >>> 5)
#     S  = S + x9
#
# x2 son cuatro "medias", distintas en cada hilo. El modelo está en
# tools/modelo_kernel.py.

.equ KRES, 0x6C0

# Tabla de arranque del barrel
    j    _start
    j    kernel1
    j    kernel2
    j    kernel3

kernel1:
    li   x1, 0x00000011
    li   x2, 0xC83CA064
    li   x5, KRES
    j    kernel
kernel2:
    li   x1, 0x000000A7
    li   x2, 0x10462802
    li   x5, KRES
    addi x5, x5, 8
    j    kernel
kernel3:
    li   x1, 0x0000005C
    li   x2, 0xFF80017F
    li   x5, KRES
    addi x5, x5, 16
kernel:
    li   x6, 0                 # S
    li   x8, 0                 # n
vuelta:
    addi     x1, x1, 37
    pbcast8  x3, x1
    psubus8  x4, x2, x3
    pcmpltu8 x7, x3, x2
    paddus8  x9, x4, x7
    padd8    x9, x9, x3
    psub8    x9, x9, x2
    emad     x1, x9, x1, 5
    add      x6, x6, x9
    addi     x8, x8, 1
    sw       x6, 0(x5)
    sw       x8, 4(x5)
    j        vuelta

