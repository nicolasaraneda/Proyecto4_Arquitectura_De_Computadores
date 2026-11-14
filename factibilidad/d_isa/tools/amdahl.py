#!/usr/bin/env python3
"""amdahl.py: speedup predicho con la ley de Amdahl contra el medido.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee las mediciones ya guardadas en mediciones/ (ticks_xd.txt de
tools/medir_xd.sh, costo_integrado.txt de tools/costo_integrado.sh y
kernel_bandas.txt de tools/medir_kernel.sh) y escribe:

  1. El perfil del tick de sw/trade.s por bloque, en el Espino base y en el
     segmentado, con el modelo de costo que tb/tb_cpi.sv comprueba.
  2. Para cada versión con instrucciones nuevas, el speedup que predice
     Amdahl generalizado, S = 1 / ((1 - f) + f / F), y el medido.
  3. La escalera de la clase 7 aplicada al kernel "actualizar el estimador y
     decidir": instrucciones y ciclos por decisión, decisiones por segundo,
     speedup y costo en celdas.
  4. La predicción para un tick que evalúe cuatro bandas (no hay programa
     completo: es una estimación a partir del kernel medido).

    python3 tools/amdahl.py > mediciones/amdahl.txt
"""
import os
import re
import sys

AQUI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
F_MHZ = 25.0

# Bloques del lazo principal de sw/trade.s (docs/trade_s.md, sección 6):
# nombre, instrucciones, loads, saltos tomados, ¿dentro de la respuesta?
BLOQUES = [
    ("sondeo que detecta el precio", 3, 1, 0, True),
    ("leer PRICE", 1, 1, 0, True),
    ("predecir: 32 p y dev", 6, 0, 0, True),
    ("decidir y armar el byte", 7, 0, 0, True),
    ("escribir DECISION", 1, 0, 0, True),
    ("actualizar la media", 8, 1, 0, False),
    ("volver al sondeo", 1, 0, 1, False),
]
# Qué reemplaza cada versión: bloque -> instrucciones nuevas (todas de ALU, sin loads)
VERSIONES = [
    ("trade_srak", "srak + add", {"actualizar la media": 2}),
    ("trade_emad", "emad", {"actualizar la media": 1}),
    ("trade_ema", "ema", {"actualizar la media": 1}),
    ("trade_media", "devk + emad", {"predecir: 32 p y dev": 1, "actualizar la media": 1}),
]
COSTO = {"trade_srak": "srak_k5", "trade_emad": "emad_k5", "trade_ema": "emaalu_k5", "trade_media": "media_k5"}


def ciclos(core, instr, loads=0, saltos=0):
    """Modelo de costo: 2 ciclos por instrucción en el base y 1 en el
    segmentado, más 1 por load y 1 por salto tomado."""
    return (2 if core == "base" else 1) * instr + loads + saltos


def leer_ticks():
    """mediciones/ticks_xd.txt -> {(core, programa): dict de columnas}."""
    datos = {}
    with open(os.path.join(AQUI, "mediciones", "ticks_xd.txt"), encoding="utf-8") as f:
        for linea in f:
            c = linea.split()
            if len(c) >= 12 and c[0] in ("base", "segmentado") and c[1].startswith("trade_"):
                # las definiciones pueden tener espacios: las columnas numéricas se cuentan desde el final
                nums = c[-9:-1] if c[-1] == "coincide" else c[-10:-2]
                ic_r, resp, resp_pc, ic_t, t_mn, tick, t_pc, cpi = (float(x) for x in nums)
                datos[(c[0], c[1])] = dict(ic_resp=ic_r, resp=resp, resp_pc=resp_pc, ic_tick=ic_t,
                                           tick_min=t_mn, tick=tick, tick_pc=t_pc, cpi=cpi,
                                           equiv="4/4,igual" in linea)
    return datos


def leer_costo():
    """mediciones/costo_integrado.txt -> {variante: (celdas, agrega, fmin, cierran)}."""
    costo = {}
    with open(os.path.join(AQUI, "mediciones", "costo_integrado.txt"), encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"^(\w+)\s+(\d+)\s+([+-]\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+ de \d+)", linea)
            if m:
                costo[m.group(1)] = (int(m.group(2)), int(m.group(3)), float(m.group(7)), m.group(10))
    return costo


def leer_kernel():
    """mediciones/kernel_bandas.txt -> {(core, versión): (instr, ciclos)} del kernel solo."""
    k = {}
    with open(os.path.join(AQUI, "mediciones", "kernel_bandas.txt"), encoding="utf-8") as f:
        for linea in f:
            c = linea.split()
            if len(c) == 5 and c[0] in ("base", "segmentado") and c[1] in ("escalar", "carriles"):
                k[(c[0], c[1])] = (float(c[2]), float(c[3]))
    return k


def amdahl(f, F):
    return 1.0 / ((1.0 - f) + f / F)


def main():
    ticks, costo, kernel = leer_ticks(), leer_costo(), leer_kernel()
    print("Amdahl: speedup predicho contra medido, y la escalera de la clase 7")
    print("Generado por factibilidad/d_isa/tools/amdahl.py (make amdahl) a partir de mediciones/ticks_xd.txt,")
    print("mediciones/costo_integrado.txt y mediciones/kernel_bandas.txt. No editar a mano.")

    # --- 1. Perfil ------------------------------------------------------------------
    print("\n== 1. Perfil del tick de sw/trade.s por bloque ==")
    print("Instrucciones contadas en el fuente. Ciclos con el modelo de costo que tb/tb_cpi.sv comprueba contra")
    print("el RTL (2 por instrucción en el base y 1 en el segmentado, más 1 por load y 1 por salto tomado).\n")
    print(f"{'bloque':<30} {'instr':>5} {'base':>6} {'% base':>7} {'segm.':>6} {'% segm.':>8}")
    tot = {"base": sum(ciclos("base", i, l, s) for _, i, l, s, _ in BLOQUES),
           "segmentado": sum(ciclos("segmentado", i, l, s) for _, i, l, s, _ in BLOQUES)}
    for nombre, i, l, s, _ in BLOQUES:
        cb, cs = ciclos("base", i, l, s), ciclos("segmentado", i, l, s)
        print(f"{nombre:<30} {i:>5} {cb:>6} {100 * cb / tot['base']:>6.1f}% {cs:>6} {100 * cs / tot['segmentado']:>7.1f}%")
    print(f"{'total sin la espera':<30} {sum(b[1] for b in BLOQUES):>5} {tot['base']:>6} {'':>7} {tot['segmentado']:>6}")
    for core in ("base", "segmentado"):
        t = ticks[(core, "trade_sw")]
        print(f"Medido en el {core}: tick completo {t['tick']:.2f} ciclos en promedio (mínimo {t['tick_min']:.0f}, "
              f"peor caso {t['tick_pc']:.0f}); la diferencia con el total es la espera del sondeo.")

    # --- 2. Amdahl ------------------------------------------------------------------
    print("\n== 2. Speedup de cada versión: Amdahl contra lo medido ==")
    print("f es la fracción del tiempo medido (promedio, con la espera) que ocupan los bloques reemplazados y F cuánto")
    print("se aceleran esos bloques. S predicho = 1 / ((1 - f) + f / F). S medido = ciclos de trade_sw / ciclos de la versión.")
    print("Dos ventanas: el tick completo y la respuesta (de byte_done a DECISION), que es la que mide el testbench oficial.\n")
    print(f"{'core':<11} {'versión':<13} {'ventana':<10} {'antes':>6} {'f':>6} {'F':>6} {'S pred.':>8} {'después':>8} {'S medido':>9} {'dif.':>6}")
    for core in ("base", "segmentado"):
        sw = ticks[(core, "trade_sw")]
        for prog, nombre, cambios in VERSIONES:
            v = ticks[(core, prog)]
            for ventana, clave in (("tick", "tick"), ("respuesta", "resp")):
                viejo = nuevo = 0
                for bn, i, l, s, en_resp in BLOQUES:
                    if bn in cambios and (ventana == "tick" or en_resp):
                        viejo += ciclos(core, i, l, s)
                        nuevo += ciclos(core, cambios[bn])
                antes, despues = sw[clave], v[clave]
                if viejo:
                    f, F = viejo / antes, viejo / nuevo
                    pred = amdahl(f, F)
                    ftxt, Ftxt = f"{f:.3f}", f"{F:.2f}"
                else:
                    pred, ftxt, Ftxt = 1.0, "0", "-"
                med = antes / despues
                print(f"{core:<11} {nombre:<13} {ventana:<10} {antes:>6.2f} {ftxt:>6} {Ftxt:>6} {pred:>8.3f} {despues:>8.2f} {med:>9.3f} {med - pred:>+6.3f}")
        print()
    print("La diferencia entre lo predicho y lo medido en el base (medio ciclo de 63) es la espera del sondeo: una vuelta")
    print("del lazo de sondeo dura 8 ciclos en el base y la fase en que llega el precio cambia con el largo del tick.")
    print("Las versiones que solo cambian la actualización de la media no mejoran la respuesta: ese bloque se ejecuta")
    print("después de escribir DECISION.")

    # --- 3. Escalera ----------------------------------------------------------------
    print("\n== 3. Escalera de la clase 7 sobre el kernel 'actualizar el estimador y decidir' ==")
    print("Una operación útil es una decisión (un tick completo). MOPS = 25 MHz / ciclos por decisión, con el promedio medido.")
    print("Costo: celdas que agrega la variante al SoC segmentado (10 semillas, mediciones/costo_integrado.txt).\n")
    print(f"{'peldaño':<44} {'instr/dec.':>10} {'ciclos/dec.':>11} {'CPI':>6} {'MOPS':>6} {'speedup':>8}  costo")
    ref = ticks[("base", "trade_sw")]["tick"]
    filas = [("0. Espino base, solo software", "base", "trade_sw", "referencia (1083 celdas en docs/estado.md)"),
             ("1. Extensión de la ISA: emad", "base", "trade_emad", "no medido en el base"),
             ("1. Extensión de la ISA: devk + emad", "base", "trade_media", "no medido en el base"),
             ("2. Pipeline de 3 etapas, solo software", "segmentado", "trade_sw", None),
             ("2+1. Pipeline + srak", "segmentado", "trade_srak", "srak_k5"),
             ("2+1. Pipeline + emad", "segmentado", "trade_emad", "emad_k5"),
             ("2+1. Pipeline + ema (resta de la ALU)", "segmentado", "trade_ema", "emaalu_k5"),
             ("2+1. Pipeline + devk + emad", "segmentado", "trade_media", "media_k5")]
    for nombre, core, prog, c in filas:
        t = ticks[(core, prog)]
        if c is None:
            ctxt = f"{costo['ref'][0]} celdas (copia sin instrucciones nuevas)"
        elif c in costo:
            ctxt = f"{costo[c][1]:+d} celdas ({costo[c][0]}), fmax mínima {costo[c][2]:.1f} MHz, cierran {costo[c][3]}"
        else:
            ctxt = c
        print(f"{nombre:<44} {t['ic_tick']:>10.2f} {t['tick']:>11.2f} {t['cpi']:>6.3f} {F_MHZ / t['tick']:>6.3f} {ref / t['tick']:>8.2f}  {ctxt}")
    print("\nLo que la clase estimó sin simular: pipeline de 3 etapas con CPI 1,5 en su mix (aquí el tick mide el CPI de la")
    print("columna, con la espera del sondeo incluida) y los pasos siguientes con CPI ideal. Aquí cada fila está medida.")
    print("Las instrucciones por decisión incluyen las vueltas de sondeo que caben en la espera, por eso no son enteras.")

    # --- 4. Cuatro bandas -----------------------------------------------------------
    print("\n== 4. Carriles: kernel de cuatro bandas ==")
    print("Medido (mediciones/kernel_bandas.txt): el kernel solo, en la copia del core con -DXD_SIMD=28.\n")
    print(f"{'core':<11} {'versión':<10} {'instr':>6} {'ciclos':>7} {'instr/op':>9} {'ciclos/op':>10} {'MOPS':>7} {'speedup':>8}")
    for core in ("base", "segmentado"):
        esc = kernel[(core, "escalar")]
        for ver in ("escalar", "carriles"):
            i, c = kernel[(core, ver)]
            print(f"{core:<11} {ver:<10} {i:>6.0f} {c:>7.0f} {i / 4:>9.2f} {c / 4:>10.2f} {4 * F_MHZ / c:>7.2f} {esc[1] / c:>8.2f}")
    b = costo.get("simd_bandas"); a = costo.get("simdalu_bandas")
    if b and a:
        print(f"\nCosto de los carriles que usa el kernel: {b[1]:+d} celdas como unidad aparte (fmax mínima {b[2]:.1f} MHz) y "
              f"{a[1]:+d} celdas\ncompartiendo el sumador de la ALU (fmax mínima {a[2]:.1f} MHz, sin pmovmsk8).")
    print("\nPredicción para un tick completo que evalúe cuatro bandas (ESTIMADO: ese programa no existe).")
    print("Se arma con el perfil de la sección 1: al tick de trade.s se le quitan las 4 instrucciones que evalúan la")
    print("banda única (2 slti, or y and) y se le agrega el kernel medido. El resto del tick no cambia.\n")
    print(f"{'core':<11} {'tick escalar':>12} {'f':>6} {'F':>6} {'S pred.':>8} {'tick carriles':>14}   con devk + emad además")
    for core in ("base", "segmentado"):
        espera = ticks[(core, "trade_sw")]["tick"] - sum(ciclos(core, i, l, s) for _, i, l, s, _ in BLOQUES)
        t_sw = ticks[(core, "trade_sw")]["tick"] - ciclos(core, 4)
        ke, kc = kernel[(core, "escalar")][1], kernel[(core, "carriles")][1]
        t_esc = t_sw + ke
        f, F = ke / t_esc, ke / kc
        t_car = t_esc - ke + kc
        # además devk + emad: predecir 6 -> 1 y actualizar 8 -> 1
        ahorro = (ciclos(core, 6) - ciclos(core, 1)) + (ciclos(core, 8, 1) - ciclos(core, 1))
        print(f"{core:<11} {t_esc:>12.1f} {f:>6.3f} {F:>6.2f} {amdahl(f, F):>8.3f} {t_car:>14.1f}   "
              f"{t_car - ahorro:.1f} ciclos, S = {t_esc / (t_car - ahorro):.2f} (espera del sondeo supuesta igual: {espera:.1f} ciclos)")
    print("\nNinguno de estos speedups cambia el resultado de la competencia: el peor caso de la respuesta de trade.s sin")
    print("ninguna instrucción nueva usa menos del 2 % del presupuesto de la ronda más rápida (2262 ciclos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
