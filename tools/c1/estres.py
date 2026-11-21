#!/usr/bin/env python3
"""estres.py: matriz de estrés de R3 contra ref/c1/c1.py (criterio 7 de la puerta de simulación).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Usa los mismos casos que tools/estres.py corre con R0 y tools/fondo/estres.py con R1 y R2 (SCLK
de 100 kHz a 1 MHz, tiempos de CS_n distintos, el reset terminando con la maestra a mitad de una
transacción, rondas seguidas sin reset y series pegadas en 1 y en 255), con tb/c1/tb_c1.sv y el
hardware de R3. Diferencias:

  - R3 responde en hasta 907 ciclos (el plazo vencido con un hilo colgado). Los casos que dejan
    menos de 1000 ciclos entre transacciones son exploración y no cuentan para la puerta: SCLK
    de 100 kHz con período de 0,1 ms (237 ciclos) y el período de 40 us (762 ciclos). El período
    de 50 us (1012 ciclos) sí cuenta.
  - Se agregan SCLK de 100 kHz y de 200 kHz con período de 1 ms, que es donde una maestra así
    de lenta puede operar.

La serie de los casos se arma con ventanas de la serie Meta normalizadas de a una, como en R1 y
R2. Las series pegadas en 1 y las familias sin normalizar bajan de 100: R3 pasa a modo seguro
(banda 40), que es lo que la referencia espera.

Cada caso exige: todos los bytes que lee la maestra iguales a los de la referencia, MISO sin X,
ningún precio sin leer ni sin respuesta, una sola escritura en DECISION por tick, ninguna
violación del protocolo de memoria compartida, peor caso dentro del presupuesto del caso, y que
el vigilante no se dispare ni llegue a contar más de un precio pendiente.

Uso: python3 tools/c1/estres.py SIM CARPETA   (lo llama tools/c1/estres.sh; make c1-estres)
"""
import multiprocessing
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(RAIZ, "tools", "c1"), os.path.join(RAIZ, "tools"), os.path.join(RAIZ, "tools", "fondo"),
                os.path.join(RAIZ, "ref", "cotas"), os.path.join(RAIZ, "ref", "c1"), os.path.join(RAIZ, "ref")]
import comun               # noqa: E402
import market              # noqa: E402
import series              # noqa: E402
import trader              # noqa: E402
import c1 as R             # noqa: E402
import tablas as TB        # noqa: E402
import caso as CASO        # noqa: E402
import importlib.util      # noqa: E402

# tools/estres.py (la matriz de R0), por su ruta: en esta carpeta hay otro estres.py
_spec = importlib.util.spec_from_file_location("estres_base", os.path.join(RAIZ, "tools", "estres.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

MINIMO = 1000              # ciclos entre transacciones bajo los cuales el caso es exploración
TABLA = "sw/c1_tabla.hex"


def presupuesto(c):
    dur = c["CS_SETUP_NS"] + 15 * c["SCLK_MEDIO_NS"] + c["CS_HOLD_NS"]
    per = min(c.get(k, c["PERIODO_NS"]) for k in ("PERIODO_NS", "PERIODO2_NS", "PERIODO3_NS"))
    return (per - dur) // base.CLK_NS


def serie_estres():
    """14 000 ticks: siete ventanas de 2000 de la serie Meta, cada una normalizada entre 100 y 255
    (las mismas de tools/fondo/estres.py)."""
    meta = market.leer_serie(os.path.join(RAIZ, "data", "practica_meta.csv"))
    out = []
    for ini in (2775, 10000, 16900, 14000, 6000, 12000, 18000):
        out += comun.normalizar(meta[ini:ini + 2000])
    return out


def casos(practica):
    c = base.casos_estres(practica, minimos=(40000, 50000))
    p = practica[:1000]
    c.append(base.base("sclk_100k_periodo_1ms", p, SCLK_MEDIO_NS=5000, CS_SETUP_NS=15000, PERIODO_NS=1000000))
    c.append(base.base("sclk_200k_periodo_1ms", p, SCLK_MEDIO_NS=2500, CS_SETUP_NS=7500, PERIODO_NS=1000000))
    for caso in c:
        if presupuesto(caso) < MINIMO:
            caso["explora"] = True
    return c


def correr(arg):
    sim, prog, plus, d, caso = arg
    nombre = caso["nombre"]
    csv = f"{d}/{nombre}.csv"
    series.escribir_csv(csv, caso["precios"])
    args = [sim, f"+PROGRAMA={prog}", f"+TABLA={TABLA}", *plus, f"+SERIE={csv}",
            f"+SALIDA={d}/{nombre}.out.csv"] + [f"+{k}={v}" for k, v in caso.items() if k.isupper()]
    out = subprocess.run(args, capture_output=True, text=True, cwd=RAIZ).stdout
    linea = [l for l in out.splitlines() if l.startswith("RESUMEN")]
    explora = caso.get("explora", False)
    if not linea:
        return nombre, False, "sin RESUMEN: " + out[-300:], 0, explora
    r = {k: int(v) for k, v in (kv.split("=") for kv in linea[0].split()[1:])}
    leidos = [int(l.split(",")[2], 16) for l in open(os.path.join(RAIZ, f"{d}/{nombre}.out.csv")).read().split("\n")[1:] if l]
    perd = base.perdidos(caso)
    ref = R.C1(TB.leer_hex(os.path.join(RAIZ, TABLA)))
    esperado = trader.decisiones(caso["precios"], ref, perd)
    distintos = sum(a != b for a, b in zip(leidos, esperado)) + abs(len(leidos) - len(esperado))
    ok = (distintos == 0 and r["bits_x"] == 0 and r["precios_perdidos"] == 0 and r["sin_respuesta"] == 0
          and r["respuestas"] == caso["NTICKS"] - perd and r["peor_caso"] < r["presupuesto"]
          and r["violaciones"] == 0 and r["dec_distinto_de_1"] == 0 and r["tel_mas_de_1"] == 0
          and r["vig_boot"] == 0 and r["vig_max"] <= 1)
    prom = r["suma_ciclos"] / max(r["respuestas"], 1)
    det = (f"perdidos en reset {perd}, respuestas {r['respuestas']}, bytes distintos {distintos}, "
           f"X {r['bits_x']}, sin leer {r['precios_perdidos']}, sin respuesta {r['sin_respuesta']}, "
           f"violaciones {r['violaciones']}, vigilante {r['vig_boot']} (max {r['vig_max']}), modo seguro {ref.seguro}, "
           f"ciclos prom {prom:.1f} peor {r['peor_caso']} de {r['presupuesto']}")
    return nombre, ok, det, r["peor_caso"], explora


def main(argv):
    sim, d = argv[1:3]
    os.chdir(RAIZ)
    os.makedirs(d, exist_ok=True)
    sb = CASO.ensamblar("sw/c1.s", f"{d}/programa.hex")
    plus = CASO.plusargs(sb)
    lista = casos(serie_estres())
    with multiprocessing.get_context("fork").Pool(int(os.environ.get("JOBS", "6"))) as pool:
        res = pool.map(correr, [(sim, f"{d}/programa.hex", plus, d, c) for c in lista])
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
