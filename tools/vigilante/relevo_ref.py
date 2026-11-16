#!/usr/bin/env python3
"""
relevo_ref.py: resultado esperado del relevo, byte por byte, y comparación con
lo que midió tb/vigilante/tb_relevo.sv.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El relevo tiene cuatro tramos. Las transacciones de la maestra se cuentan
desde 0 y la transacción n empieza en t(n) = inicio + n * periodo.

  1. Fondo sano. La imagen 0 no ve los primeros `perd` precios, que llegan
     durante su reset de encendido (trader.ticks_perdidos). Desde ahí la
     maestra lee los bytes de ref/fondo.py.
  2. Falla. La variante cuelgue_sup:N cuelga al supervisor al recibir el
     precio N del programa, que es la transacción nf = perd + N - 1. El byte
     que se lee en nf todavía es bueno (responde al precio nf - 1). Desde ahí
     nadie escribe DECISION y el esclavo repite ese byte.
  3. Disparo y reconfiguración. El vigilante cuenta precios sin respuesta: el
     de nf es el primero y el de nb = nf + VigN es el número VigN + 1. BOOT
     sube cuando termina la transacción nb: CS_n sube, pasa por los dos
     registros del sincronizador y el vigilante lo registra, tres flancos de
     reloj en total. Desde ahí y durante T_RECONF el pin MISO está suelto y la
     maestra lee unos.
  4. Respaldo. La imagen 1 parte de cero: su reset dura 4095 ciclos y después
     corre max_media sin historia. No ve los precios que llegan durante el
     reset y la maestra lee 0x00 hasta su primera decisión.

Detalle de los tiempos (reloj de 40 ns con flancos de subida en 20 + 40 k, como
en el testbench):

  - t_boot = P + 80, donde P es el primer flanco de subida que ve CS_n en
    alto. En P se carga el primer registro del sincronizador, en P + 40 el
    segundo (cs_active baja) y en P + 80 el vigilante sube BOOT.
  - La fase 2 empieza en t2, el primer flanco de bajada con
    t - t_boot >= T_RECONF. El primer flanco de subida de la imagen 1 es
    t2 + 20 y su contador de reset se llena en R = t2 + 20 + 40 * 4094.
  - La imagen 1 recibe la transacción n si el primer flanco de subida de
    SCLK, que ocurre en t(n) + 1500, se muestrea en R + 80 o después. Un
    flanco muestreado en R + 40 se detecta en el mismo ciclo en que el esclavo
    detecta la bajada de CS_n (los dos sincronizadores salen juntos del
    reset) y ese ciclo solo reinicia la cuenta de bits: el byte queda con 7
    bits y se descarta. Esta regla es más fina que la de
    trader.ticks_perdidos, que suma un margen fijo de 160 ns; las dos
    coinciden salvo en una ventana de 120 ns.
  - Cada bit se lee en t(n) + 1500 + 1000 i. Vale 1 si a esa hora el pin está
    suelto. Una transacción que queda a caballo del final de la
    reconfiguración se lee con unos al principio y ceros al final, porque la
    imagen 1 está en reset y su MISO vale 0.

Cuando un cambio de la maestra coincide con un flanco de subida del reloj
(pasa con INICIO_NS = 4000, el del testbench oficial), Verilator muestrea el
valor nuevo. Eso es una propiedad del simulador y no del diseño: por eso
relevo.sh repite un caso con INICIO_NS = 4010, donde no hay coincidencias.

Uso:
  relevo_ref.py --resumen tb.log --sim salida.csv --serie tb/practica.csv
                --falla 100 [--vig-n 4] [--nombre caso] [--breve]
  --falla 0 es la corrida sana: BOOT no debe subir nunca.
Imprime una línea PASS o FAIL por comprobación y termina con error si hay
algún FAIL. Con --breve imprime una sola línea.
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ref"))
import fondo      # noqa: E402
import market     # noqa: E402
import trader     # noqa: E402

CLK = 40                 # período del reloj en ns
FASE_CLK = 20            # los flancos de subida están en 20 + 40 k
POR_CICLOS = 4095        # reset de encendido de pochoco_soc (PorBits = 12)
T_PRIMER_SCLK = 1500     # de la bajada de CS_n al primer flanco de subida de SCLK
T_BIT = 1000             # período de SCLK
DUR_TX = 9500            # duración de la transacción


def flanco_subida(t):
    """Primer flanco de subida del reloj en t o después."""
    k = -(-(t - FASE_CLK) // CLK)
    return FASE_CLK + CLK * max(k, 0)


def flanco_bajada(t):
    """Primer flanco de bajada del reloj en t o después."""
    return CLK * -(-t // CLK)


class Esperado:
    """Todo lo que se puede predecir de una corrida a partir de sus parámetros."""

    def __init__(self, precios, periodo, inicio, falla, vig_n, t_reconf):
        self.precios = precios
        n = len(precios)
        self.perd = trader.ticks_perdidos(periodo, inicio_ns=inicio)
        sano = trader.decisiones(precios, fondo.Fondo(), self.perd)
        self.sano = sano
        self.falla = falla
        if falla == 0:
            self.bytes = list(sano)
            return

        def t(k):
            return inicio + k * periodo

        self.nf = self.perd + falla - 1
        self.nb = self.nf + vig_n
        if self.nb >= n:
            raise SystemExit("la corrida es demasiado corta: el vigilante no alcanza a disparar")
        self.t_cs = t(self.nb) + DUR_TX                    # CS_n sube
        self.t_boot = flanco_subida(self.t_cs) + 2 * CLK
        if self.t_boot + FASE_CLK >= t(self.nb + 1):
            raise SystemExit("el período es tan corto que BOOT sube dentro de la transacción siguiente")
        self.t2 = flanco_bajada(self.t_boot + t_reconf)
        self.t_rst = self.t2 + FASE_CLK + CLK * (POR_CICLOS - 1)
        # Primera transacción que recibe la imagen 1
        n1 = self.nb + 1
        while n1 < n and flanco_subida(t(n1) + T_PRIMER_SCLK) < self.t_rst + 2 * CLK:
            n1 += 1
        self.n1 = n1 if n1 < n else None
        mm = trader.decisiones(precios[n1:], trader.Oficial(), 0) if n1 < n else []

        self.bytes, self.clase = [], []
        for k in range(n):
            if k <= self.nf:
                b, c = sano[k], "fondo"
            elif k <= self.nb:
                b, c = sano[self.nf], "repetido"
            else:
                tras = k > n1
                dato = mm[k - n1] if tras else market.MANTENER
                b, unos = 0, 0
                for i in range(8):
                    suelto = t(k) + T_PRIMER_SCLK + T_BIT * i < self.t2
                    unos += suelto
                    bit = 1 if suelto else (dato >> (7 - i)) & 1
                    b = (b << 1) | bit
                c = "suelto" if unos == 8 else "cortado" if unos else "respaldo" if tras else "reset"
            self.bytes.append(b)
            self.clase.append(c)


def leer_resumen(ruta):
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        if linea.startswith("RESUMEN "):
            return {c.split("=")[0]: int(c.split("=")[1]) for c in linea.split()[1:]}
    raise SystemExit(f"{ruta}: la simulación no llegó al resumen")


def es_orden(b):
    """El byte hace que la maestra intente comprar o vender algo."""
    return (b >> 6) in (1, 2) and (b & 63) > 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Resultado esperado del relevo y comparación con la simulación")
    ap.add_argument("--resumen", required=True, help="salida del testbench, con la línea RESUMEN")
    ap.add_argument("--sim", required=True, help="CSV del testbench")
    ap.add_argument("--serie", default="tb/practica.csv")
    ap.add_argument("--falla", type=int, required=True, help="N de cuelgue_sup:N, o 0 para la corrida sana")
    ap.add_argument("--vig-n", type=int, default=4)
    ap.add_argument("--nombre", default="relevo")
    ap.add_argument("--breve", action="store_true")
    a = ap.parse_args(argv)

    r = leer_resumen(a.resumen)
    filas = list(csv.DictReader(open(a.sim, encoding="utf-8")))
    nticks, periodo, inicio = r["ticks"], r["periodo_ns"], r["inicio_ns"]
    if len(filas) != nticks:
        raise SystemExit(f"{a.sim}: {len(filas)} filas y la simulación dice {nticks} ticks")
    precios = market.leer_serie(a.serie, nticks)
    sim = [int(f["decision"], 16) for f in filas]
    e = Esperado(precios, periodo, inicio, a.falla, a.vig_n, r["t_reconf_ns"])

    lineas, fallas = [], 0

    def comprobar(ok, texto):
        nonlocal fallas
        fallas += 0 if ok else 1
        lineas.append(f"{'PASS' if ok else 'FAIL'} {a.nombre}: {texto}")

    def igual(nombre, obtenido, esperado, texto):
        comprobar(obtenido == esperado, texto if obtenido == esperado
                  else f"{nombre}: la simulación dio {obtenido} y se esperaba {esperado}")

    difs = [k for k in range(nticks) if sim[k] != e.bytes[k]]
    w_sim = market.simular(precios, sim).w
    comprobar(r["bits_x"] == 0, f"MISO sin X ni Z en los {nticks * 8} bits leídos" if r["bits_x"] == 0
              else f"{r['bits_x']} bits de MISO indefinidos")
    igual("primer precio de la imagen 0", r["primer_precio0"], e.perd,
          f"la imagen 0 no ve {e.perd} de los primeros precios (reset de encendido) y recibe desde la transacción {e.perd}")

    if a.falla == 0:
        igual("t_boot", r["t_boot"], -1, f"BOOT no sube en {nticks} ticks")
        comprobar(r["vig_max"] <= 1, f"la cuenta del vigilante nunca pasa de {r['vig_max']}")
        igual("escrituras", r["escrituras0"], r["recibidos0"],
              f"una escritura en DECISION por cada uno de los {r['recibidos0']} precios recibidos")
        igual("fase final", int(filas[-1]["fase_fin"]), 0, "la imagen 1 nunca recibe reloj")
        comprobar(not difs, f"los {nticks} bytes coinciden con ref/fondo.py" if not difs
                  else f"{len(difs)} bytes distintos de ref/fondo.py, el primero en el tick {difs[0]}")
        resumen = f"sana, {nticks} ticks, BOOT no sube, cuenta máxima {r['vig_max']}, {len(difs)} diferencias"
        detalle = [f"  patrimonio final: {w_sim}"]
    else:
        ult = e.nf - 1 if a.falla > 1 else -1
        igual("última escritura de la imagen 0", r["ultima_escritura0"], ult,
              f"cuelgue_sup:{a.falla}: la última escritura de la imagen 0 responde al precio de la transacción {ult} "
              f"y el precio de la {e.nf} queda sin respuesta" if ult >= 0 else
              f"cuelgue_sup:{a.falla}: la imagen 0 no escribe nunca y el precio de la transacción {e.nf} queda sin respuesta")
        igual("transacción del disparo", r["tick_boot"], e.nb,
              f"BOOT sube al terminar la transacción {e.nb} = {e.nf} + {a.vig_n}: es el precio número {a.vig_n + 1} "
              f"sin respuesta ({e.nf} a {e.nb})")
        igual("precios sin respuesta", (r["vig_max"], r["precios_tras_ultima"]), (a.vig_n + 1, a.vig_n + 1),
              f"el vigilante cuenta {a.vig_n + 1} precios sin escritura y ninguno más")
        igual("t_boot", r["t_boot"], e.t_boot,
              f"BOOT sube en t = {e.t_boot} ns, {e.t_boot - e.t_cs} ns después de que CS_n sube y "
              f"{(e.t_boot - (inicio + e.nf * periodo + DUR_TX - 1000)) / 1000:.2f} us después del último bit del "
              f"precio que cuelga al supervisor")
        igual("CS_n, transacción en curso y S1 S0 al disparar",
              (r["cs_n_al_boot"], r["en_tx_al_boot"], r["s1s0"]), (1, 0, 1),
              "BOOT sube con CS_n en alto, sin transacción en curso, y pide la imagen 01")
        igual("comienzo de la fase 2", r["t_fase2"], e.t2,
              f"la imagen 1 recibe reloj desde t = {e.t2} ns ({(e.t2 - e.t_boot) / 1e6:.3f} ms después de BOOT)")
        igual("fin del reset de la imagen 1", r["t_rst1"], e.t_rst,
              f"el reset de la imagen 1 termina en t = {e.t_rst} ns, {POR_CICLOS} ciclos después")
        n1 = e.n1 if e.n1 is not None else -1
        igual("primer precio de la imagen 1", (r["primer_precio1"], r["primera_escritura1"]), (n1, n1),
              f"la imagen 1 recibe su primer precio en la transacción {n1} y lo responde en {r['resp1']} ciclos")
        cuenta = {c: e.clase.count(c) for c in ("suelto", "cortado", "reset", "respaldo")}
        sueltos = [k for k in range(nticks) if k > e.nb and e.clase[k] == "suelto"]
        cortados = [(k, e.bytes[k]) for k in range(nticks) if k > e.nb and e.clase[k] == "cortado"]
        ff_sim = sum(1 for k in sueltos if sim[k] == 0xFF)
        igual("ticks con 0xFF", ff_sim, cuenta["suelto"],
              f"la maestra lee 0xFF en {cuenta['suelto']} ticks" +
              (f" (transacciones {sueltos[0]} a {sueltos[-1]})" if sueltos else ""))
        corte = [k for k in range(e.nf + 1, nticks) if e.clase[k] != "respaldo"]
        ordenes = [k for k in corte if k > e.nb and es_orden(sim[k])]
        comprobar(not ordenes, "ningún byte leído con el pin suelto, cortado o con la imagen 1 en reset es una orden"
                  if not ordenes else f"la maestra recibe una orden espuria en el tick {ordenes[0]}")
        comprobar(not difs, f"los {nticks} bytes coinciden con el esperado" if not difs
                  else f"{len(difs)} bytes distintos del esperado, el primero en el tick {difs[0]} "
                       f"(simulación {sim[difs[0]]:02x}, esperado {e.bytes[difs[0]]:02x})")
        sin_decision = (n1 - e.nf) if n1 >= 0 else None
        resumen = (f"cuelgue_sup:{a.falla}, T = {periodo} ns, T_RECONF = {r['t_reconf_ns']} ns: BOOT en la transacción "
                   f"{e.nb}, {cuenta['suelto']} ticks con 0xFF, "
                   f"cortados {' '.join(f'{b:02x}' for _, b in cortados) or 'ninguno'}, "
                   f"{cuenta['reset']} con 0x00, primer precio del respaldo en {n1}, {len(difs)} diferencias")
        detalle = [
            f"  bytes del fondo sano: transacciones 0 a {e.nf}; byte repetido ({e.bytes[e.nf]:02x}): {e.nf + 1} a {e.nb}",
            f"  pin suelto, byte 0xFF: {cuenta['suelto']} ticks; transacciones cortadas por el fin de la reconfiguración: "
            + (", ".join(f"{k} (byte {b:02x})" for k, b in cortados) or "ninguna"),
            f"  imagen 1 en reset o sin decisión todavía, byte 0x00 en {cuenta['reset']} transacciones; "
            f"bytes de max_media desde la transacción {n1 + 1 if n1 >= 0 else '-'}: {cuenta['respaldo']}",
            f"  ticks sin decisión nueva, desde el precio colgado hasta el primero que responde la imagen 1: "
            f"{sin_decision if sin_decision is not None else 'no vuelve en esta corrida'} "
            f"(precios {e.nf} a {n1 - 1}; {a.vig_n + 1} los gasta el vigilante en contar)",
            f"  patrimonio final: {w_sim} con el relevo; {market.simular(precios, e.sano).w} el fondo sano en los mismos "
            f"{nticks} ticks; {trader.correr(precios, perdidos=e.perd).w} max_media sola",
        ]

    if a.breve:
        print(f"{'PASS' if fallas == 0 else 'FAIL'} {a.nombre}: {resumen}")
        if fallas:
            print("\n".join("  " + x for x in lineas if x.startswith("FAIL")))
    else:
        print("\n".join(lineas + detalle))
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
