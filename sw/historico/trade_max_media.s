# trade_max_media.s: el programa de R0 hasta el 17/11 (max_media), guardado como historico.
# Lo usan el estudio de co-diseno (tools/p7), la prueba de la extension (tools/xd) y la
# reproduccion de bitstreams/r0_base_max_media.bin. El programa de R0 es sw/trade.s (T133).
#
# Texto original:
# trade.s: programa de inversion para el Pochoco SoC (Espino Core, RV32E).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Variante: solo software. Referencia bit a bit: ref/trader.py (MaxMedia).
#
# Algoritmo: max_media (decision T50), la regla base de reversion a la media
# con el umbral de entrada en 3 unidades en vez de 4:
#   S   = 32 * media exponencial del precio, con alfa = 1/32
#   dev = 32 p - S                desviacion del precio respecto a la media
#   si dev < -96   -> entrar      (precio mas de 3 unidades bajo la media)
#   si dev > 0     -> salir       (precio recupero la media)
#   si no          -> mantener la posicion anterior
#   DECISION = "comprar 63" si se quiere estar adentro, "vender 63" si no.
#   S = S + ((32 p - S) >> 5)     actualizacion de la media
#
# La maestra recorta cada orden a lo que alcanza con la caja o con las
# acciones, asi que repetir "comprar 63" o "vender 63" no paga comisiones de
# mas. Por eso el programa no lleva contabilidad: solo decide si quiere estar
# adentro o afuera.
#
# Ciclo principal:
#   1. esperar   sondea STATUS[0] hasta que haya un precio nuevo
#   2. leer      lee PRICE (la lectura baja la bandera)
#   3. predecir  dev = 32 p - S
#   4. decidir   actualiza la posicion y arma el byte, sin saltos
#   5. escribir  un solo store a DECISION, con la decision definitiva
#   6. estado    actualiza la media S (despues del store, para que la
#                decision salga lo antes posible)
#
# Operaciones que Espino no tiene:
#   - 32 p: cinco sumas (duplicar cinco veces).
#   - (32 p - S) >> 5: como desplazar un negativo no se puede hacer con el
#     truco de abajo, se usa la identidad
#         (32 p - S) >> 5  =  p - ceil(S / 32)  =  p - ((S + 31) >> 5)
#     donde S + 31 nunca es negativo.
#   - x >> 5 con x >= 0: se multiplica por 8 (tres sumas), se guarda la
#     palabra en memoria y se lee su segundo byte con lbu. Eso es x * 8 / 256.
#     Funciona porque (S + 31) * 8 < 65536: S nunca pasa de 255 * 32 = 8160.
#   - Las comparaciones dan 0 o 1 con slti y la posicion se actualiza con
#     or y and: no hay saltos que dependan del precio. El unico salto que
#     depende de algo externo es el del sondeo.
#
# Registros:
#   x2  base del esclavo SPI (0x8001_0000)
#   x3  S, la media por 32 (13 bits: entre 32 y 8160)
#   x4  pos: 0 afuera, 1 adentro
#   x5  p, el ultimo precio (1 a 255)
#   x6  32 p, y despues dev (con signo, entre -8128 y 8128)
#   x7  temporal
#   x8  byte de decision
#   x9  temporal
#
# Memoria: una sola palabra de trabajo, TMP, en la ultima palabra de la RAM.
# El .org del final rellena el .hex hasta las 512 palabras, para que la
# simulacion y la placa partan con la misma memoria.

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo, bit 1: CS activo
.equ OFF_PRICE,     4          # precio recibido (1 a 255)
.equ OFF_DECISION,  8          # byte que la maestra lee en la proxima transaccion

.equ UMBRAL_COMPRA, -96        # entra si dev < -(3 * 32). La regla base usaba -128
.equ UMBRAL_VENTA,  1          # sale si dev >= 1, o sea dev > 0 * 32
.equ VENDER_63,     0xBF       # accion 10, cantidad 63
.equ COMPRAR_MENOS_VENDER, -64 # 0x7F - 0xBF: lo que se suma para pasar a "comprar 63"

.equ TMP,           0x7FC      # palabra de trabajo (ultima de la RAM)
.equ TMP_BYTE1,     0x7FD      # su segundo byte: bits 15:8

_start:
    li   x2, SPI_BASE
    li   x4, 0                 # pos = 0: afuera

# --- Primer precio: la media parte en ese precio (S = 32 p) ------------------
primero:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, primero
    lw   x5, OFF_PRICE(x2)
    add  x6, x5, x5            # 2 p
    add  x6, x6, x6            # 4 p
    add  x6, x6, x6            # 8 p
    add  x6, x6, x6            # 16 p
    add  x6, x6, x6            # 32 p
    mv   x3, x6                # S = 32 p, asi dev = 0 y no se opera
    j    decidir

# --- 1. Esperar el precio -----------------------------------------------------
esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar

# --- 2. Leer ------------------------------------------------------------------
    lw   x5, OFF_PRICE(x2)

# --- 3. Predecir: dev = 32 p - S ---------------------------------------------
    add  x6, x5, x5            # 2 p
    add  x6, x6, x6            # 4 p
    add  x6, x6, x6            # 8 p
    add  x6, x6, x6            # 16 p
    add  x6, x6, x6            # 32 p
decidir:
    sub  x6, x6, x3            # dev = 32 p - S

# --- 4. Decidir, sin saltos ---------------------------------------------------
    slti x7, x6, UMBRAL_COMPRA # 1 si hay que entrar
    slti x9, x6, UMBRAL_VENTA  # 0 si hay que salir
    or   x4, x4, x7            # pos = (pos | entrar) & no_salir
    and  x4, x4, x9
    sub  x7, x0, x4            # 0 si pos = 0, 0xFFFFFFFF si pos = 1
    andi x7, x7, COMPRAR_MENOS_VENDER   # 0 o -64
    addi x8, x7, VENDER_63     # 0xBF (vender 63) o 0x7F (comprar 63)

# --- 5. Escribir la decision (una sola vez por tick) -------------------------
    sw   x8, OFF_DECISION(x2)

# --- 6. Actualizar la media: S = S + p - ((S + 31) >> 5) ---------------------
    addi x7, x3, 31            # S + 31
    add  x7, x7, x7            # por 2
    add  x7, x7, x7            # por 4
    add  x7, x7, x7            # por 8
    sw   x7, TMP(x0)
    lbu  x7, TMP_BYTE1(x0)     # ((S + 31) * 8) >> 8 = (S + 31) >> 5
    add  x3, x3, x5
    sub  x3, x3, x7
    j    esperar

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
