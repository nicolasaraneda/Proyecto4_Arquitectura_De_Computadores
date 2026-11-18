# fondo_votos.s: el programa de R1 y R2 hasta el 17/11 (el fondo de cuatro hilos que vota),
# guardado como historico para el estudio de co-diseno (tools/p7). Su tabla es
# sw/historico/fondo_votos_tabla.hex. El programa de R1 y R2 es sw/fondo.s (T133).
#
# Texto original:
# =============================================================================
# fondo.s: el fondo en un chip. Un supervisor y tres gestores, uno por hilo del
# Espino barrel (docs/fondo.md).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre en el Espino barrel compilado con -DESPINO_XD_EMAD, -DESPINO_XD_DEVK y
# -DESPINO_TABLA (la tabla de parámetros en su BRAM, docs/tabla_vigilante.md).
# Referencia byte a byte: ref/fondo.py (make fondo-equiv).
#
#   hilo 0   supervisor: sondea el SPI, lee el precio, lo publica, calcula
#            max_media por su cuenta, recoge los votos, combina y escribe
#            DECISION una vez por tick. Es el único hilo que toca el SPI.
#   hilo 1   gestor max_media: entra 3 bajo la media, sale al recuperarla
#   hilo 2   gestor base:      entra 4 bajo la media, sale al recuperarla
#   hilo 3   gestor activo:    entra 2 bajo la media, sale medio punto arriba
#
# Los tres gestores ejecutan la misma rutina, cada uno con sus registros. Lo
# único que cambia entre ellos son dos umbrales, que salen de la tabla de
# parámetros, y la dirección de su bloque de memoria.
#
# Protocolo de memoria compartida (cada palabra tiene un solo hilo que la
# escribe):
#
#   PUB    la escribe el supervisor, una vez por tick. Número de tick en los
#          bits 31:8 y precio en los bits 7:0, con un solo store.
#   DES_k  la escribe el gestor k antes que EST_k. Su puntaje en papel, en
#          treintaidosavos de unidad de precio.
#   EST_k  la escribe el gestor k, una vez por tick y al final. Es su voto:
#          el número del tick que acaba de procesar en los bits 31:8 y su
#          posición (0 afuera, 1 adentro) en el bit 0.
#
#   Supervisor                          Gestor k
#   ----------                          --------
#   lee PRICE                           sondea PUB hasta que cambie
#   PUB = tick * 256 + precio  ------>  puntaje en papel y regla de reversión
#   calcula su propia max_media         DES_k = puntaje
#   lee EST_1, EST_2 y EST_3   <------  EST_k = tick * 256 + posición
#   hasta que los tres traigan          actualiza su media y vuelve a sondear
#   este tick, o venza el plazo
#   ajusta pesos (cada VENTANA ticks)
#   vota, escribe DECISION y un registro de telemetría
#
# Voto viejo: EST_k - tick * 256 vale 0 o 1 (la posición) si el gestor ya
# publicó este tick. Con cualquier otro tick la resta, sin signo, es 2 o más.
#
# Degradación: el supervisor no espera a nadie más de PLAZO vueltas de su lazo
# de lectura (48 ciclos por vuelta). Vencido el plazo, en el lugar de cada voto
# viejo usa la posición de su propia max_media. Si no llegó ninguno decide
# solo, y lo que escribe es exactamente lo que escribiría sw/trade.s. La
# decisión nunca depende de que otro hilo esté vivo. Con algún voto ausente no
# se ajustan los pesos, porque DES_k solo se lee después de ver EST_k al día.
#
# Aritmética: la de sw/trade.s (docs/trade_s.md) con las dos instrucciones de
# la extensión (docs/extension_isa.md). devk da 32 p - S en una instrucción y
# emad actualiza la media en otra. La media se guarda por 32.
#
# Las líneas que empiezan con "#@" son marcas para tools/fondo/variante.py,
# que arma desde este mismo archivo los programas con fallas puestas a
# propósito (un gestor colgado, un voto que no llega, un voto atrasado). Para
# el ensamblador son comentarios. En un gestor x1 queda libre después de leer
# sus umbrales: lo usan solo esas variantes.
#
# Registros del supervisor (hilo 0):
#   x1   base de la tabla de parámetros desde que se publica el precio hasta
#        el voto; después, temporal
#   x2   base del esclavo SPI
#   x3   número de tick por 256
#   x4   S0, la media por 32 de su max_media
#   x5, x6, x7   voto de cada gestor; temporales de la frontera
#   x8   precio
#   x9   temporal
#   x10, x11, x12   pesos vigentes (copia de W1, W2, W3)
#   x13  ticks que faltan para la frontera de ventana
#   x14  vueltas que quedan del plazo
#   x15  pos0, la posición de su max_media
#
# Registros de cada gestor (hilos 1, 2 y 3):
#   x2   dirección de su bloque: DES en 0, EST en 4
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
#   x14  32 p del tick anterior
#   x15  temporal
# fondo_votos.s: el programa de R1 y R2 hasta el 17/11 (el fondo de cuatro hilos que vota),
# guardado como historico para el estudio de co-diseno (tools/p7). Su tabla es
# sw/historico/fondo_votos_tabla.hex. El programa de R1 y R2 es sw/fondo.s (T133).
#
# Texto original:
# =============================================================================

.extension xd

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8

.equ PER_BASE,      0x80000000 # periférico de la placa
.equ PER_DIGITOS,   0          # dos dígitos de 7 segmentos
.equ PER_LEDS,      4          # cuatro LED

.equ K,             5          # alfa = 1/32. El hardware solo tiene k = 5
.equ COMPRAR_63,    0x7F
.equ VENDER_MENOS_COMPRAR, 64  # 0xBF - 0x7F
.equ DIGITOS_ADENTRO, 0x63     # los 7 segmentos muestran 63 o 00
.equ BIT_PAR,       256        # bit 0 del número de tick, dentro de x3
.equ BIT_LATIDO,    0x40000    # bit 10 del número de tick, dentro de x3

# --- Tabla de parámetros (solo lectura, en su propia BRAM) ---------------------
# El programa no trae ninguna constante del algoritmo en sus instrucciones:
# todas salen de aquí. Son valores de 16 bits que se leen con lw y llegan con
# extensión de signo. El orden es el de PARAMETROS en ref/fondo.py, y el
# contenido es sw/fondo_tabla.hex (python3 ref/fondo.py --tabla-hex).
.equ TAB_BASE,      0x80020000
.equ T_S_ENTRA,     0          # supervisor, max_media: entra si dev < este valor
.equ T_S_SALE,      4          #                         sale si dev >= este valor
.equ T_G1_ENTRA,    8          # gestor 1
.equ T_G1_SALE,     12
.equ T_G2_ENTRA,    16         # gestor 2
.equ T_G2_SALE,     20
.equ T_G3_ENTRA,    24         # gestor 3
.equ T_G3_SALE,     28
.equ T_W1_INI,      32         # pesos iniciales, en dieciseisavos
.equ T_W2_INI,      36
.equ T_W3_INI,      40
.equ T_W1_MAX,      44         # tope de cada peso
.equ T_W1_MIN,      56         # piso de cada peso
.equ T_VENTANA,     68         # ticks entre ajustes de los pesos
.equ T_UMBRAL,      72         # compra si los pesos adentro suman esto o más
.equ T_PLAZO,       76         # vueltas del lazo de lectura de votos (1 o más)

# --- Estado compartido (parte en cero) ----------------------------------------
.equ PUB,           0x7C0      # supervisor: tick * 256 + precio
.equ W1,            0x7C4      # supervisor: pesos vigentes
.equ W2,            0x7C8
.equ W3,            0x7CC
.equ REF1,          0x7D0      # supervisor: puntaje de cada gestor al empezar la ventana
.equ REF2,          0x7D4
.equ REF3,          0x7D8
.equ G1,            0x7DC      # bloque del gestor 1
.equ G2,            0x7E4      # bloque del gestor 2
.equ G3,            0x7EC      # bloque del gestor 3
.equ OFF_DES,       0          # puntaje en papel
.equ OFF_EST,       4          # voto: tick * 256 + posición
.equ DES1,          0x7DC
.equ EST1,          0x7E0
.equ DES2,          0x7E4
.equ EST2,          0x7E8
.equ DES3,          0x7EC
.equ EST3,          0x7F0

# --- Tabla de arranque: el hilo t parte en la dirección 4 t -------------------
    j    supervisor
    j    hilo1
    j    hilo2
    j    hilo3

# fondo_votos.s: el programa de R1 y R2 hasta el 17/11 (el fondo de cuatro hilos que vota),
# guardado como historico para el estudio de co-diseno (tools/p7). Su tabla es
# sw/historico/fondo_votos_tabla.hex. El programa de R1 y R2 es sw/fondo.s (T133).
#
# Texto original:
# =============================================================================
# Hilo 0: supervisor
# fondo_votos.s: el programa de R1 y R2 hasta el 17/11 (el fondo de cuatro hilos que vota),
# guardado como historico para el estudio de co-diseno (tools/p7). Su tabla es
# sw/historico/fondo_votos_tabla.hex. El programa de R1 y R2 es sw/fondo.s (T133).
#
# Texto original:
# =============================================================================
supervisor:
    li   x2, SPI_BASE
    li   x3, 0                 # todavía no hay ningún tick
    li   x15, 0                # pos0 = 0: afuera
    li   x1, TAB_BASE
    lw   x10, T_W1_INI(x1)     # los pesos parten en el prior de la tabla
    sw   x10, W1(x0)
    lw   x11, T_W2_INI(x1)
    sw   x11, W2(x0)
    lw   x12, T_W3_INI(x1)
    sw   x12, W3(x0)
    lw   x13, T_VENTANA(x1)

# Primer precio: la media del supervisor parte en ese precio
s_primero:
    lw   x9, OFF_STATUS(x2)
    andi x9, x9, 1
    beqz x9, s_primero
    lw   x8, OFF_PRICE(x2)
    devk x4, x8, x0, K         # S0 = 32 p
    j    s_publica

# --- 1. Esperar el precio (único hilo que toca el SPI) ------------------------
s_espera:
    lw   x9, OFF_STATUS(x2)
    andi x9, x9, 1
    beqz x9, s_espera
    lw   x8, OFF_PRICE(x2)

# --- 2. Publicar el precio con su número de tick, en un solo store ------------
s_publica:
#@SUPERVISOR
    addi x3, x3, 256
    add  x9, x3, x8
    sw   x9, PUB(x0)
# --- 3. max_media propia, mientras los gestores calculan ----------------------
    li   x1, TAB_BASE          # base de la tabla, hasta el voto
    devk x9, x8, x4, K         # dev = 32 p - S0
    lw   x5, T_S_ENTRA(x1)
    slt  x5, x9, x5            # 1 si hay que entrar
    lw   x6, T_S_SALE(x1)
    slt  x6, x9, x6            # 0 si hay que salir
    or   x15, x15, x5
    and  x15, x15, x6          # pos0 = (pos0 | entrar) & no_salir
    emad x4, x9, x4, K         # S0 = S0 + (dev >>> 5)
    addi x13, x13, -1          # un tick menos para la frontera de ventana
    lw   x14, T_PLAZO(x1)

# --- 4. Recoger los votos, con plazo ------------------------------------------
# Cada resta da 0 o 1 si el voto es de este tick, y 2 o más (sin signo) si es
# viejo. Si las tres son menores que 2, su "or" también.
s_votos:
    lw   x5, EST1(x0)
    sub  x5, x5, x3
    lw   x6, EST2(x0)
    sub  x6, x6, x3
    lw   x7, EST3(x0)
    sub  x7, x7, x3
    or   x9, x5, x6
    or   x9, x9, x7
    sltiu x9, x9, 2
    bnez x9, s_todos           # llegaron los tres
    addi x14, x14, -1
    bnez x14, s_votos
# Venció el plazo: cada voto viejo se reemplaza por la max_media propia
s_plazo:
    sltiu x9, x5, 2
    bnez x9, d_2
    mv   x5, x15
d_2:
    sltiu x9, x6, 2
    bnez x9, d_3
    mv   x6, x15
d_3:
    sltiu x9, x7, 2
    bnez x9, d_4
    mv   x7, x15
d_4:
    bnez x13, s_voto
    lw   x13, T_VENTANA(x1)    # era tick de frontera: sin los tres votos no se ajusta
    j    s_voto

# --- 5. Reparto: cada VENTANA ticks se ajustan los pesos ----------------------
s_todos:
    beqz x13, frontera

# --- 6. Voto ponderado y DECISION (una sola escritura por tick) ---------------
s_voto:
    sub  x5, x0, x5            # 0 o 0xFFFFFFFF
    and  x5, x5, x10           # peso del gestor 1 si su voto es adentro
    sub  x6, x0, x6
    and  x6, x6, x11
    sub  x7, x0, x7
    and  x7, x7, x12
    add  x9, x5, x6
    add  x9, x9, x7            # F: pesos de los votos adentro
    lw   x1, T_UMBRAL(x1)
    slt  x9, x9, x1            # 1 si no hay mayoría
    sub  x9, x0, x9            # 0 si se compra, 0xFFFFFFFF si se vende
    andi x1, x9, VENDER_MENOS_COMPRAR
    addi x1, x1, COMPRAR_63    # 0x7F (comprar 63) o 0xBF (vender 63)
    sw   x1, OFF_DECISION(x2)

# --- 7. Telemetría: un store por tick, después de decidir ---------------------
# Ticks pares: los 7 segmentos muestran la posición objetivo, 63 o 00.
# Ticks impares: LED 0 es el latido (bit 10 del número de tick) y los LED 1, 2
# y 3 son los votos de los gestores 1, 2 y 3 tal como entraron a la suma.
    andi x1, x3, BIT_PAR
    bnez x1, t_leds
    xori x9, x9, -1
    andi x9, x9, DIGITOS_ADENTRO
    li   x1, PER_BASE
    sw   x9, PER_DIGITOS(x1)
    j    s_espera
t_leds:
    sltu x5, x0, x5            # 1 si el voto fue adentro (y su peso no es cero)
    sltu x6, x0, x6
    sltu x7, x0, x7
    add  x5, x5, x5            # LED 1
    add  x6, x6, x6
    add  x6, x6, x6            # LED 2
    add  x7, x7, x7
    add  x7, x7, x7
    add  x7, x7, x7            # LED 3
    or   x5, x5, x6
    or   x5, x5, x7
    li   x1, BIT_LATIDO
    and  x1, x1, x3
    sltu x1, x0, x1            # LED 0
    or   x5, x5, x1
    li   x1, PER_BASE
    sw   x5, PER_LEDS(x1)
    j    s_espera

# --- Frontera de ventana: pesos aprendidos alrededor del prior ----------------
# g_k = lo que ganó el gestor k en la ventana (DES_k - REF_k). Se pasa 1/16
# del que menos ganó al que más ganó si la ventaja supera 1/32 del precio
# (los puntajes están en treintaidosavos: ventaja > p) y los topes lo permiten.
# Solo se llega aquí con los tres votos al día, así que los tres DES_k son de
# este tick. Usa como temporales los registros de los votos y de los pesos (x1
# no se toca: sigue siendo la base de la tabla). Al
# terminar se recargan los pesos y se repite la lectura de votos, que pasa de
# inmediato porque ningún gestor vuelve a publicar hasta que cambie PUB.
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
    li   x10, 0                # y el desplazamiento del peso de ese gestor
    mv   x11, x5               # la peor ganancia hasta ahora
    li   x12, 0
    bge  x9, x6, f_1
    mv   x9, x6
    li   x10, 4
f_1:
    bge  x6, x11, f_2
    mv   x11, x6
    li   x12, 4
f_2:
    bge  x9, x7, f_3
    mv   x9, x7
    li   x10, 8
f_3:
    bge  x7, x11, f_4
    mv   x11, x7
    li   x12, 8
f_4:
    sub  x9, x9, x11           # ventaja del mejor sobre el peor
    bge  x8, x9, f_fin         # ventaja <= p: no supera el margen
    lw   x5, W1(x10)           # peso del mejor
    add  x6, x1, x10
    lw   x6, T_W1_MAX(x6)
    bge  x5, x6, f_fin         # ya está en su tope
    lw   x7, W1(x12)           # peso del peor
    add  x6, x1, x12
    lw   x6, T_W1_MIN(x6)
    bge  x6, x7, f_fin         # ya está en su piso
    addi x5, x5, 1
    sw   x5, W1(x10)
    addi x7, x7, -1
    sw   x7, W1(x12)
f_fin:
    lw   x10, W1(x0)
    lw   x11, W2(x0)
    lw   x12, W3(x0)
    lw   x13, T_VENTANA(x1)
    j    s_votos

# fondo_votos.s: el programa de R1 y R2 hasta el 17/11 (el fondo de cuatro hilos que vota),
# guardado como historico para el estudio de co-diseno (tools/p7). Su tabla es
# sw/historico/fondo_votos_tabla.hex. El programa de R1 y R2 es sw/fondo.s (T133).
#
# Texto original:
# =============================================================================
# Hilos 1, 2 y 3: gestores en papel
# fondo_votos.s: el programa de R1 y R2 hasta el 17/11 (el fondo de cuatro hilos que vota),
# guardado como historico para el estudio de co-diseno (tools/p7). Su tabla es
# sw/historico/fondo_votos_tabla.hex. El programa de R1 y R2 es sw/fondo.s (T133).
#
# Texto original:
# =============================================================================
hilo1:
    li   x2, G1
    li   x1, TAB_BASE
    lw   x10, T_G1_ENTRA(x1)
    lw   x11, T_G1_SALE(x1)
    j    gestor
hilo2:
    li   x2, G2
    li   x1, TAB_BASE
    lw   x10, T_G2_ENTRA(x1)
    lw   x11, T_G2_SALE(x1)
    j    gestor
hilo3:
    li   x2, G3
    li   x1, TAB_BASE
    lw   x10, T_G3_ENTRA(x1)
    lw   x11, T_G3_SALE(x1)
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
    devk x6, x8, x0, K         # 32 p
    mv   x14, x6
    mv   x3, x6                # S = 32 p
    j    g_decidir

# 1. Esperar el tick siguiente: PUB cambia en cada tick
g_espera:
    lw   x7, PUB(x0)
    beq  x7, x5, g_espera
    mv   x5, x7
    andi x8, x7, 255           # precio
    devk x6, x8, x0, K         # 32 p

# 2. Puntaje en papel, sin productos: suma 32 veces el cambio de precio si
#    tenía la acción, y resta 2 cuando se ejecuta un cambio de posición
    sub  x15, x6, x14          # 32 (p - p anterior)
    mv   x14, x6
    sub  x7, x0, x12           # 0 o 0xFFFFFFFF según la posición ejecutada
    and  x15, x15, x7
    add  x13, x13, x15
    xor  x7, x12, x4           # 1 si la orden del tick anterior cambia la posición
    add  x7, x7, x7
    sub  x13, x13, x7          # la comisión
    mv   x12, x4               # la orden ya se ejecutó

# 3. Regla de reversión, sin saltos (igual que sw/trade.s)
g_decidir:
    sub  x6, x6, x3            # dev = 32 p - S
    slt  x7, x6, x10           # 1 si hay que entrar
    slt  x9, x6, x11           # 0 si hay que salir
    or   x4, x4, x7
    and  x4, x4, x9            # pos = (pos | entrar) & no_salir

# 4. Publicar: primero el puntaje, al final el voto con su número de tick
#@ANTES_DE_PUBLICAR
    sw   x13, OFF_DES(x2)
    sub  x7, x5, x8            # tick * 256
    add  x7, x7, x4
#@VOTO
    sw   x7, OFF_EST(x2)
#@DESPUES_DEL_VOTO

# 5. Actualizar la media: S = S + (dev >>> 5)
    emad x3, x6, x3, K
    j    g_espera

# La memoria de datos parte en cero: el programa no toma ningún valor inicial
# de su imagen. Los parámetros están en la BRAM de la tabla.
.org 0x800
