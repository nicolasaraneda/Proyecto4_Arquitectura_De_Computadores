# =============================================================================
# fondo.s: un fondo de estrategias con un gestor por hilo, para el Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Prototipo de factibilidad (factibilidad/b_fondo_hilos/README.md). Corre en el
# barrel de 4 hilos de factibilidad/a_barrel/. Referencia byte a byte: la
# configuración fondo_min de factibilidad/retorno/r4b_fondo/fondo.c
#     fondo:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8
#
#   hilo 0   supervisor: sondea el SPI, lee el precio, lo publica, espera a los
#            tres gestores, reparte (pesos), vota, escribe DECISION y lleva el
#            espejo de la cuenta real.
#   hilo 1   gestor max_media: entra 3 bajo la media, sale al recuperarla
#   hilo 2   gestor base:      entra 4 bajo la media, sale al recuperarla
#   hilo 3   gestor activo:    entra 2 bajo la media, sale medio punto arriba
#
# Los tres gestores ejecutan la misma rutina (gestor), cada uno con sus
# registros. Lo único que cambia entre ellos son dos umbrales y la dirección
# de su bloque de memoria, que se cargan en la entrada de cada hilo.
#
# Protocolo entre hilos (cada palabra tiene un solo hilo que la escribe):
#
#   PUB    la escribe el supervisor. Lleva el número de tick en los bits 31:8
#          y el precio en los bits 7:0. Se escribe con un solo store, así que
#          el precio y su número de tick aparecen juntos.
#   EST_k  la escribe el gestor k. Lleva el número de tick que acaba de
#          procesar en los bits 31:8 y su posición (0 afuera, 1 adentro) en el
#          bit 0. Es lo último que publica en el tick.
#   DES_k  la escribe el gestor k antes que EST_k. Es su desempeño en papel
#          (puntaje por acción, en dieciseisavos de unidad de precio).
#
#   Supervisor                          Gestor k
#   ----------                          --------
#   lee PRICE                           sondea PUB hasta que cambie
#   PUB = tick * 256 + precio  ------>  calcula puntaje y posición
#   espera EST_1, EST_2, EST_3  <-----  DES_k = puntaje; EST_k = tick * 256 + pos
#   (cada una con su número de tick)    actualiza su media y vuelve a sondear
#   ajusta pesos (cada 512 ticks)
#   vota y escribe DECISION
#   espejo de la cuenta real
#
# El supervisor no publica el tick n+1 hasta haber visto los tres EST_k del
# tick n, así que ningún gestor puede saltarse un precio ni procesar dos veces
# el mismo, demore lo que demore. La decisión no depende de cuántos ciclos
# tarda cada hilo.
#
# Las líneas que empiezan con "#@" son marcas para tools/variante.py, que
# arma las variantes de medición a partir de este mismo archivo (espejo de la
# cuenta antes de decidir, un gestor atrasado a propósito y supervisor que
# usa lo publicado en el tick anterior). Para el ensamblador son comentarios.
#
# Aritmética de cada gestor: la de sw/trade.s (docs/trade_s.md). La media se
# guarda por 32, 32 p son cinco sumas y el desplazamiento a la derecha se hace
# con la memoria (palabra TMP propia de cada gestor).
#
# Registros del supervisor (hilo 0):
#   x1   temporal
#   x2   base del esclavo SPI
#   x3   número de tick por 256
#   x4   byte escrito en DECISION
#   x5, x6, x7   posición de cada gestor; temporales del espejo y de la frontera
#   x8   precio
#   x9   temporal
#   x10, x11, x12   pesos vigentes (copia de W1, W2, W3)
#   x13  ticks que faltan para la frontera de ventana
#   x14  constante 2 (y cociente dentro del espejo)
#   x15  byte del tick anterior, que es el que la maestra ejecuta con este precio
#
# Registros de cada gestor (hilos 1, 2 y 3):
#   x2   dirección de su bloque: DES en 0, EST en 4, TMP en 8
#   x3   S, la media por 32
#   x4   pos: 0 afuera, 1 adentro
#   x5   última palabra PUB procesada
#   x6   32 p, y después dev
#   x7, x9   temporales
#   x8   precio
#   x10  umbral de entrada: entra si dev < x10
#   x11  umbral de salida: sale si dev >= x11
#   x12  posición ya ejecutada en papel
#   x13  puntaje por acción
#   x14  16 p del tick anterior
#   x15  temporal
# =============================================================================

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8

# --- Constantes del fondo -----------------------------------------------------
.equ G1_ENTRA,      -96        # max_media: entra si dev < -3 * 32
.equ G1_SALE,       1          #            sale si dev > 0
.equ G2_ENTRA,      -128       # base: entra si dev < -4 * 32
.equ G2_SALE,       1
.equ G3_ENTRA,      -64        # activo: entra si dev < -2 * 32
.equ G3_SALE,       17         #         sale si dev > 16

.equ W1_INI,        6          # pesos iniciales (el prior), en dieciseisavos
.equ W2_INI,        5
.equ W3_INI,        5
.equ W1_MAX,        10         # prior + 4
.equ W2_MAX,        9
.equ W3_MAX,        9
.equ W1_MIN,        2          # prior - 4, nunca menos que 0
.equ W2_MIN,        1
.equ W3_MIN,        1
.equ VENTANA,       512        # ticks entre ajustes de los pesos
.equ UMBRAL_VOTO,   8          # compra si los pesos adentro suman 8/16 o más

.equ CAJA_INI,      10000
.equ COMISION_NEG,  -5
.equ COMPRAR_63,    0x7F
.equ VENDER_MENOS_COMPRAR, 64  # 0xBF - 0x7F
.equ MASCARA_ACCION, 0xC0
.equ ACCION_COMPRAR, 0x40
.equ ACCION_VENDER,  0x80

# --- Memoria de datos (final de la RAM) ---------------------------------------
.equ PUB,           0x7A0      # supervisor: tick * 256 + precio
.equ CAJA,          0x7A4      # supervisor: espejo de la caja
.equ ACC,           0x7A8      # supervisor: espejo de las acciones
.equ W1,            0x7AC      # supervisor: pesos vigentes
.equ W2,            0x7B0
.equ W3,            0x7B4
.equ OFF_WMAX,      12         # tope de cada peso: 12 bytes después del peso
.equ OFF_WMIN,      24         # piso de cada peso: 24 bytes después del peso
.equ REF1,          0x7D0      # supervisor: puntaje de cada gestor al empezar la ventana
.equ REF2,          0x7D4
.equ REF3,          0x7D8
.equ G1,            0x7DC      # bloque del gestor 1
.equ G2,            0x7E8      # bloque del gestor 2
.equ G3,            0x7F4      # bloque del gestor 3
.equ OFF_DES,       0          # desempeño en papel
.equ OFF_EST,       4          # tick * 256 + posición
.equ OFF_TMP,       8          # palabra de trabajo del desplazamiento
.equ OFF_TMP1,      9          # su segundo byte
.equ DES1,          0x7DC
.equ EST1,          0x7E0
.equ DES2,          0x7E8
.equ EST2,          0x7EC
.equ DES3,          0x7F4
.equ EST3,          0x7F8

# --- Tabla de arranque: el hilo t parte en la dirección 4 t -------------------
    j    supervisor
    j    hilo1
    j    hilo2
    j    hilo3

# =============================================================================
# Hilo 0: supervisor
# =============================================================================
supervisor:
    li   x2, SPI_BASE
    li   x3, 0                 # todavía no hay ningún tick
    li   x4, 0                 # DECISION parte en 0x00: mantener
    li   x13, VENTANA
    li   x14, 2
    lw   x10, W1(x0)
    lw   x11, W2(x0)
    lw   x12, W3(x0)

# --- 1. Esperar el precio (único hilo que toca el SPI) ------------------------
s_espera:
    lw   x9, OFF_STATUS(x2)
    andi x9, x9, 1
    beqz x9, s_espera
    lw   x8, OFF_PRICE(x2)

# --- 2. Publicar el precio con su número de tick, en un solo store ------------
#@PUB_INICIO
    addi x3, x3, 256
    add  x9, x3, x8
    sw   x9, PUB(x0)
#@PUB_FIN
    mv   x15, x4               # byte del tick anterior, para el espejo
    addi x13, x13, -1          # un tick menos para la frontera de ventana
#@ESPEJO_ANTES

# --- 3. Esperar a los tres gestores -------------------------------------------
# EST_k - tick * 256 vale 0 o 1 (la posición) si el gestor ya publicó este
# tick. Si todavía tiene el tick anterior da -256 o -255, que sin signo es
# mayor que 2.
s_g1:
    lw   x5, EST1(x0)
    sub  x5, x5, x3
    bgeu x5, x14, s_g1
s_g2:
    lw   x6, EST2(x0)
    sub  x6, x6, x3
    bgeu x6, x14, s_g2
s_g3:
    lw   x7, EST3(x0)
    sub  x7, x7, x3
    bgeu x7, x14, s_g3

# --- 4. Reparto: cada VENTANA ticks se ajustan los pesos ----------------------
    beqz x13, frontera
#@PUB_DESPUES

# --- 5. Voto ponderado y DECISION (una sola escritura por tick) ---------------
    sub  x5, x0, x5            # 0 o 0xFFFFFFFF
    and  x5, x5, x10           # peso del gestor 1 si está adentro
    sub  x6, x0, x6
    and  x6, x6, x11
    sub  x7, x0, x7
    and  x7, x7, x12
    add  x5, x5, x6
    add  x5, x5, x7            # F: pesos de los gestores que están adentro
    slti x5, x5, UMBRAL_VOTO   # 1 si no hay mayoría
    sub  x5, x0, x5
    andi x5, x5, VENDER_MENOS_COMPRAR
    addi x4, x5, COMPRAR_63    # 0x7F (comprar 63) o 0xBF (vender 63)
    sw   x4, OFF_DECISION(x2)

# --- 6. Espejo de la cuenta real ----------------------------------------------
# La maestra ejecuta al precio de este tick (x8) el byte que leyó, que es el
# del tick anterior (x15). Mismas reglas que tb/tb_proyecto_4.sv. Este
# programa solo escribe 0x00, 0x7F y 0xBF: la compra se resuelve para
# "comprar 63" y la venta para cualquier cantidad.
#@ESPEJO_INICIO
espejo:
    andi x9, x15, MASCARA_ACCION
    addi x1, x0, ACCION_VENDER
    beq  x9, x1, e_venta
    addi x1, x0, ACCION_COMPRAR
    bne  x9, x1, e_fin         # 00 y 11: mantener

# Compra: q = min(63, (caja - 5) / p). El cociente sale de 6 restas de prueba
# contra 32 p, 16 p, ..., p, y el resto es la caja que queda.
    lw   x1, CAJA(x0)
    addi x1, x1, COMISION_NEG  # lo que hay para comprar
    blt  x1, x8, e_fin         # no alcanza para una acción
    add  x5, x8, x8            # 2 p
    add  x6, x5, x5            # 4 p
    add  x7, x6, x6            # 8 p
    add  x9, x7, x7            # 16 p
    add  x15, x9, x9           # 32 p
    li   x14, 0                # cociente
    bltu x1, x15, e_c16
    sub  x1, x1, x15
    addi x14, x14, 32
e_c16:
    bltu x1, x9, e_c8
    sub  x1, x1, x9
    addi x14, x14, 16
e_c8:
    bltu x1, x7, e_c4
    sub  x1, x1, x7
    addi x14, x14, 8
e_c4:
    bltu x1, x6, e_c2
    sub  x1, x1, x6
    addi x14, x14, 4
e_c2:
    bltu x1, x5, e_c1
    sub  x1, x1, x5
    addi x14, x14, 2
e_c1:
    bltu x1, x8, e_c0
    sub  x1, x1, x8
    addi x14, x14, 1
e_c0:
    sw   x1, CAJA(x0)          # caja = caja - 5 - q p
    lw   x5, ACC(x0)
    add  x5, x5, x14
    sw   x5, ACC(x0)           # acciones = acciones + q
    li   x14, 2                # se repone la constante
    j    e_fin

# Venta: q = min(cantidad pedida, acciones). El producto q p se arma sumando
# p * 2^i por cada bit de q (6 pasos).
e_venta:
    lw   x7, ACC(x0)
    andi x5, x15, 63           # cantidad pedida
    bgeu x7, x5, e_v1
    mv   x5, x7                # no se vende más de lo que se tiene
e_v1:
    beqz x5, e_fin             # nada que vender
    mv   x9, x8                # p * 2^i
    li   x6, 0                 # producto
    andi x1, x5, 1
    beqz x1, e_p1
    add  x6, x6, x9
e_p1:
    add  x9, x9, x9
    andi x1, x5, 2
    beqz x1, e_p2
    add  x6, x6, x9
e_p2:
    add  x9, x9, x9
    andi x1, x5, 4
    beqz x1, e_p3
    add  x6, x6, x9
e_p3:
    add  x9, x9, x9
    andi x1, x5, 8
    beqz x1, e_p4
    add  x6, x6, x9
e_p4:
    add  x9, x9, x9
    andi x1, x5, 16
    beqz x1, e_p5
    add  x6, x6, x9
e_p5:
    add  x9, x9, x9
    andi x1, x5, 32
    beqz x1, e_p6
    add  x6, x6, x9
e_p6:
    lw   x1, CAJA(x0)
    add  x1, x1, x6
    addi x1, x1, COMISION_NEG  # caja + q p - 5
    bltz x1, e_fin             # no alcanza para la comisión: no se ejecuta
    sw   x1, CAJA(x0)
    sub  x7, x7, x5
    sw   x7, ACC(x0)
e_fin:
#@ESPEJO_FIN
    j    s_espera

# --- Frontera de ventana: pesos aprendidos alrededor del prior ----------------
# g_k = lo que ganó el gestor k en la ventana (DES_k - REF_k). Se pasa 1/16
# del que menos ganó al que más ganó si la ventaja supera 1/32 del precio
# (16 * 2 * ventaja > 16 p) y ningún peso se aleja más de 4/16 de su prior.
# Usa como temporales los registros de las posiciones, de los pesos y del
# contador: al terminar se vuelven a cargar y se repite la espera, que pasa de
# inmediato porque los tres EST_k ya son de este tick.
frontera:
    lw   x5, DES1(x0)
    lw   x9, REF1(x0)
    sw   x5, REF1(x0)
    sub  x5, x5, x9            # g1
    lw   x6, DES2(x0)
    lw   x9, REF2(x0)
    sw   x6, REF2(x0)
    sub  x6, x6, x9            # g2
    lw   x7, DES3(x0)
    lw   x9, REF3(x0)
    sw   x7, REF3(x0)
    sub  x7, x7, x9            # g3
    mv   x9, x5                # la mejor ganancia hasta ahora
    li   x10, W1               # y la dirección del peso de ese gestor
    mv   x11, x5               # la peor ganancia hasta ahora
    li   x12, W1
    bge  x9, x6, f_1
    mv   x9, x6
    li   x10, W2
f_1:
    bge  x6, x11, f_2
    mv   x11, x6
    li   x12, W2
f_2:
    bge  x9, x7, f_3
    mv   x9, x7
    li   x10, W3
f_3:
    bge  x7, x11, f_4
    mv   x11, x7
    li   x12, W3
f_4:
    sub  x9, x9, x11           # ventaja del mejor sobre el peor
    add  x9, x9, x9
    bge  x8, x9, f_fin         # 2 * ventaja <= p: no supera el margen
    lw   x5, 0(x10)            # peso del mejor
    lw   x6, OFF_WMAX(x10)
    bge  x5, x6, f_fin         # ya está en su tope
    lw   x7, 0(x12)            # peso del peor
    lw   x6, OFF_WMIN(x12)
    bge  x6, x7, f_fin         # ya está en su piso
    addi x5, x5, 1
    sw   x5, 0(x10)
    addi x7, x7, -1
    sw   x7, 0(x12)
f_fin:
    lw   x10, W1(x0)
    lw   x11, W2(x0)
    lw   x12, W3(x0)
    li   x13, VENTANA
    j    s_g1

# =============================================================================
# Hilos 1, 2 y 3: gestores en papel
# =============================================================================
hilo1:
    li   x2, G1
    li   x10, G1_ENTRA
    li   x11, G1_SALE
    j    gestor
hilo2:
    li   x2, G2
    li   x10, G2_ENTRA
    li   x11, G2_SALE
    j    gestor
hilo3:
    li   x2, G3
    li   x10, G3_ENTRA
    li   x11, G3_SALE
    j    gestor

# --- Rutina común (reentrante: solo usa registros y el bloque de x2) ----------
gestor:
    li   x4, 0                 # afuera
    li   x12, 0                # sin posición ejecutada
    li   x13, 0                # puntaje 0

# Primer precio: la media parte en ese precio y no hay cambio de precio
g_primero:
    lw   x5, PUB(x0)
    beqz x5, g_primero
    andi x8, x5, 255           # precio
    add  x6, x8, x8            # 2 p
    add  x6, x6, x6            # 4 p
    add  x6, x6, x6            # 8 p
    add  x6, x6, x6            # 16 p
    mv   x14, x6
    add  x6, x6, x6            # 32 p
    mv   x3, x6                # S = 32 p
    j    g_decidir

# 1. Esperar el tick siguiente: PUB cambia en cada tick
g_espera:
    lw   x7, PUB(x0)
    beq  x7, x5, g_espera
    mv   x5, x7
    andi x8, x7, 255           # precio
    add  x6, x8, x8            # 2 p
    add  x6, x6, x6            # 4 p
    add  x6, x6, x6            # 8 p
    add  x6, x6, x6            # 16 p

# 2. Puntaje en papel, sin productos: suma 16 veces el cambio de precio si
#    tenía la acción, y resta 1 cuando se ejecuta un cambio de posición
    sub  x15, x6, x14          # 16 (p - p anterior)
    mv   x14, x6
    add  x6, x6, x6            # 32 p
    sub  x7, x0, x12           # 0 o 0xFFFFFFFF según la posición ejecutada
    and  x15, x15, x7
    add  x13, x13, x15
    xor  x7, x12, x4           # 1 si la orden del tick anterior cambia la posición
    sub  x13, x13, x7          # la comisión
    mv   x12, x4               # la orden ya se ejecutó

# 3. Regla de reversión, sin saltos (igual que sw/trade.s)
g_decidir:
    sub  x6, x6, x3            # dev = 32 p - S
    slt  x7, x6, x10           # 1 si hay que entrar
    slt  x9, x6, x11           # 0 si hay que salir
    or   x4, x4, x7
    and  x4, x4, x9            # pos = (pos | entrar) & no_salir

# 4. Publicar: primero el desempeño, al final el tick con la posición
#@RETARDO_ANTES
    sw   x13, OFF_DES(x2)
    sub  x7, x5, x8            # tick * 256
    add  x7, x7, x4
    sw   x7, OFF_EST(x2)
#@RETARDO

# 5. Actualizar la media: S = S + p - ((S + 31) >> 5)
    addi x7, x3, 31
    add  x7, x7, x7
    add  x7, x7, x7
    add  x7, x7, x7
    sw   x7, OFF_TMP(x2)
    lbu  x7, OFF_TMP1(x2)      # ((S + 31) * 8) >> 8
    add  x3, x3, x8
    sub  x3, x3, x7
    j    g_espera

# =============================================================================
# Datos iniciales. El resto de la memoria queda en cero.
# =============================================================================
.org 0x7A0
    .word 0                    # PUB
    .word CAJA_INI             # CAJA
    .word 0                    # ACC
    .word W1_INI, W2_INI, W3_INI
    .word W1_MAX, W2_MAX, W3_MAX
    .word W1_MIN, W2_MIN, W3_MIN
    .word 0, 0, 0              # REF1, REF2, REF3
    .word 0, 0, 0              # gestor 1: DES, EST, TMP
    .word 0, 0, 0              # gestor 2
    .word 0, 0, 0              # gestor 3
.org 0x800
