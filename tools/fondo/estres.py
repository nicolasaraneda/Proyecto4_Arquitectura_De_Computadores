#!/usr/bin/env python3
"""estres.py: matriz de estrés del fondo en un chip contra ref/fondo.py
(criterio 7 de la puerta de simulación).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Usa los mismos casos que tools/estres.py corre con R0 (SCLK de 100 kHz a
1 MHz, tiempos de CS_n distintos, el reset terminando con la maestra a mitad
de una transacción, rondas seguidas sin reset y series pegadas en 1 y en 255),
con tb/fondo/tb_fondo.sv y el hardware de R1 o de R2. Dos diferencias:

  - El fondo responde en 220 a 480 ciclos y R0 en menos de 50. Los casos que
    dejan menos de 600 ciclos entre transacciones (SCLK de 100 kHz con período
    de 0,1 ms, y los períodos de 11,5 y 13,5 us) no caben: se corren igual y
    se informan como exploración, sin contar para la puerta.
  - Se agregan SCLK de 100 kHz y de 200 kHz con período de 1 ms, que es donde
    una maestra así de lenta puede operar.

Cada caso exige: todos los bytes que lee la maestra iguales a los de
ref/fondo.py, MISO sin X, ningún precio sin leer ni sin respuesta, una sola
escritura en DECISION por tick, a lo más un store de telemetría, ninguna
violación del protocolo, ningún plazo vencido, peor caso dentro del
presupuesto del caso y, en R2, que el vigilante no se dispare ni llegue a
contar más de un precio pendiente.

Uso: HW=r1 python3 tools/fondo/estres.py SIM PROGRAMA.hex TABLA.hex PLUSARGS CARPETA
     (lo llama tools/fondo/estres.sh; make fondo-estres)
"""
import multiprocessing
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import estres as base      # noqa: E402
import fondo               # noqa: E402
import series              # noqa: E402
import trader              # noqa: E402

MINIMO = 600               # ciclos entre transacciones bajo los cuales el caso es exploración


def presupuesto(c):
    dur = c["CS_SETUP_NS"] + 15 * c["SCLK_MEDIO_NS"] + c["CS_HOLD_NS"]
    per = min(c.get(k, c["PERIODO_NS"]) for k in ("PERIODO_NS", "PERIODO2_NS", "PERIODO3_NS"))
    return (per - dur) // base.CLK_NS


def casos(practica):
    c = base.casos_estres(practica)
    p = practica[:1000]
    c.append(base.base("sclk_100k_periodo_1ms", p, SCLK_MEDIO_NS=5000, CS_SETUP_NS=15000, PERIODO_NS=1000000))
    c.append(base.base("sclk_200k_periodo_1ms", p, SCLK_MEDIO_NS=2500, CS_SETUP_NS=7500, PERIODO_NS=1000000))
    for caso in c:
        if presupuesto(caso) < MINIMO:
            caso["explora"] = True
    return c


def correr(arg):
    sim, prog, tabla, plus, d, caso = arg
    nombre = caso["nombre"]
    csv = f"{d}/{nombre}.csv"
    series.escribir_csv(csv, caso["precios"])
    args = [sim, f"+PROGRAMA={prog}", f"+TABLA={tabla}", *plus.split(), f"+SERIE={csv}",
            f"+SALIDA={d}/{nombre}.out.csv"] + [f"+{k}={v}" for k, v in caso.items() if k.isupper()]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    linea = [l for l in out.splitlines() if l.startswith("RESUMEN")]
    explora = caso.get("explora", False)
    if not linea:
        return nombre, False, "sin RESUMEN: " + out[-300:], 0, explora
    r = {k: int(v) for k, v in (kv.split("=") for kv in linea[0].split()[1:])}
    leidos = [int(l.split(",")[2], 16) for l in open(f"{d}/{nombre}.out.csv").read().split("\n")[1:] if l]
    perd = base.perdidos(caso)
    esperado = trader.decisiones(caso["precios"], fondo.Fondo(), perd)
    distintos = sum(a != b for a, b in zip(leidos, esperado)) + abs(len(leidos) - len(esperado))
    ok = (distintos == 0 and r["bits_x"] == 0 and r["precios_perdidos"] == 0 and r["sin_respuesta"] == 0
          and r["respuestas"] == caso["NTICKS"] - perd and r["peor_caso"] < r["presupuesto"]
          and r["violaciones"] == 0 and r["dec_distinto_de_1"] == 0 and r["tel_mas_de_1"] == 0
          and r["ticks_plazo"] == 0 and r["vig_boot"] == 0 and r["vig_max"] <= 1)
    prom = r["suma_ciclos"] / max(r["respuestas"], 1)
    det = (f"perdidos en reset {perd}, respuestas {r['respuestas']}, bytes distintos {distintos}, "
           f"X {r['bits_x']}, sin leer {r['precios_perdidos']}, sin respuesta {r['sin_respuesta']}, "
           f"plazo {r['ticks_plazo']}, violaciones {r['violaciones']}, vigilante {r['vig_boot']} (max {r['vig_max']}), "
           f"ciclos prom {prom:.1f} peor {r['peor_caso']} de {r['presupuesto']}")
    return nombre, ok, det, r["peor_caso"], explora


def main(argv):
    sim, prog, tabla, plus, d = argv[1:6]
    os.makedirs(d, exist_ok=True)
    lista = casos(series.practica())
    with multiprocessing.Pool(int(os.environ.get("JOBS", "6"))) as pool:
        res = pool.map(correr, [(sim, prog, tabla, plus, d, c) for c in lista])
    puerta = [r for r in res if not r[4]]
    explora = [r for r in res if r[4]]
    for nombre, ok, det, _, _ in puerta:
        print(f"{'PASS' if ok else 'FAIL'} {nombre}: {det}")
    print()
    print("Exploracion (no cuenta para la puerta): casos fuera del rango pedido o que dejan menos de "
          f"{MINIMO} ciclos entre transacciones")
    for nombre, ok, det, _, _ in explora:
        print(f"  {'funciona' if ok else 'no funciona'} {nombre}: {det}")
    print()
    n = sum(1 for r in puerta if r[1])
    peor = max(r[3] for r in puerta)
    print(f"{'PASS' if n == len(puerta) else 'FAIL'}: {n} de {len(puerta)} casos de la matriz pasan. "
          f"Peor caso de la respuesta en la matriz: {peor} ciclos")
    return 0 if n == len(puerta) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
