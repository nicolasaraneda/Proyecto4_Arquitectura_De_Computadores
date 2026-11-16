# cuelgue_supervisor.s: el hilo supervisor deja de responder y los otros tres
# hilos siguen trabajando. Prueba del vigilante sobre el barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es sw/cuelgue.s del estudio del respaldo por reconfiguración llevado a
# cuatro hilos. El hilo 0 hace de supervisor: responde con el byte DEC a los
# primeros K precios y después se queda en un lazo sin leer precios ni
# escribir DECISION. Los hilos 1, 2 y 3 hacen de estrategias: cada uno cuenta
# sin parar y guarda su cuenta en la memoria (CNT + 4 t), antes y después de
# que el supervisor se cuelgue.
#
# Lo que tiene que pasar: el vigilante mira solo las escrituras en DECISION,
# así que dispara N + 1 precios después de la última respuesta aunque tres de
# los cuatro hilos sigan vivos y escribiendo en la memoria. Si el vigilante
# tomara cualquier escritura al bus como señal de vida, no dispararía nunca.
#
# K y DEC se cambian al ensamblar (-D K=20 -D DEC=0x7F).

.equ PER_BASE,      0x80000000
.equ OFF_DIGITOS,   0
.equ OFF_LEDS,      4
.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8
.equ CNT,           0x700      # cuentas de los hilos 1, 2 y 3
.equ K,             20
.equ DEC,           0x7F       # comprar 63

# Tabla de arranque del barrel
    j    supervisor
    j    estrategia1
    j    estrategia2
    j    estrategia3

supervisor:
    li   x2, SPI_BASE
    li   x3, PER_BASE
    li   x10, K
    li   x8, DEC
    li   x7, 1
    sw   x7, OFF_LEDS(x3)      # LED 1 encendido: corre la imagen principal
    sw   x10, OFF_DIGITOS(x3)
esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar
    lw   x5, OFF_PRICE(x2)
    sw   x8, OFF_DECISION(x2)
    addi x10, x10, -1
    sw   x10, OFF_DIGITOS(x3)
    bnez x10, esperar
colgado:
    j    colgado

estrategia1:
    li   x1, CNT
    addi x1, x1, 4
    j    contar
estrategia2:
    li   x1, CNT
    addi x1, x1, 8
    j    contar
estrategia3:
    li   x1, CNT
    addi x1, x1, 12
contar:
    li   x2, 0
cuenta:
    addi x2, x2, 1
    sw   x2, 0(x1)
    j    cuenta

# Relleno con ceros hasta las 512 palabras de la memoria
.org 0x800
