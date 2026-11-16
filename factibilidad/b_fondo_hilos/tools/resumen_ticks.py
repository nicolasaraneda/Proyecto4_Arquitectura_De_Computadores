#!/usr/bin/env python3
"""resumen_ticks.py: tablas de las mediciones por tick que escribe tb/tb_fondo.sv.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    resumen_ticks.py completo TICKS.csv PERIODO_NS    todas las tablas de una corrida
    resumen_ticks.py linea ETIQUETA TICKS.csv         una fila, para comparar variantes
    resumen_ticks.py fases TICKS_0.csv TICKS_1.csv... peor caso por fase del sondeo

Convenciones (ver el encabezado de tb/tb_fondo.sv):
  - una ventana va de un byte_done al siguiente; la última de cada corrida se
    descarta porque queda incompleta;
  - trabajo de un hilo en un tick = instrucciones fuera de los lazos de espera
    más una vuelta de cada lazo (la que encuentra lo que esperaba): 3 del
    sondeo del SPI y 9 de la espera a los tres gestores en el supervisor, y 2
    del sondeo de PUB en cada gestor.
"""
import csv
import sys

VUELTA = {0: 12, 1: 2, 2: 2, 3: 2}
PRESUPUESTO = {"ronda 1 (10 ms)": 249762, "ronda 2 (1 ms)": 24762, "ronda 3 (0,1 ms)": 2262}


def leer(ruta):
    with open(ruta, encoding="ascii") as f:
        filas = list(csv.DictReader(f))
    salida = []
    for fila in filas[:-1]:
        salida.append({k: (int(v, 16) if k == "decision" else int(v)) for k, v in fila.items()})
    return salida


def est(v):
    if not v:
        return "{:>8} {:>10} {:>8}".format("-", "-", "-")
    return "{:>8d} {:>10.2f} {:>8d}".format(min(v), sum(v) / len(v), max(v))


def trabajo(fila, t):
    return fila[f"trab{t}"] + VUELTA[t]


def completo(ruta, periodo_ns):
    f = leer(ruta)
    n = len(f)
    turno = f[0]["ic0"]
    ciclos_tick = periodo_ns // 40
    presupuesto = (periodo_ns - 9500) // 40
    frontera = [x for x in f if x["ic_frontera"] > 0]
    comun = [x for x in f[1:] if x["ic_frontera"] == 0]
    cab = "{:<44} {:>7} {:>8} {:>10} {:>8}".format("", "ticks", "minimo", "promedio", "maximo")

    print(f"Ticks medidos: {n} (se descarta la ultima ventana de la corrida, que queda incompleta)")
    print(f"Ciclos por tick: {ciclos_tick}. Turno de cada hilo: {turno} instrucciones por tick (una cada 4 ciclos).")
    sin_respuesta = sum(1 for x in f if x["escrituras"] != 1)
    print(f"Ticks con una sola escritura de DECISION: {n - sin_respuesta} de {n}")
    print()
    print("1. Respuesta: ciclos desde byte_done hasta la escritura de DECISION")
    print()
    print("  " + cab)
    for nombre, g in (("todos los ticks", f), ("primer precio", f[:1]), ("tick comun", comun), ("tick con frontera de ventana", frontera)):
        print("  {:<44} {:>7} {}".format(nombre, len(g), est([x["r_ciclos"] for x in g])))
    r = [x["r_ciclos"] for x in f]
    print(f"  En tiempo, a 40 ns por ciclo: promedio {sum(r) / n * 0.04:.2f} us, peor caso {max(r) * 0.04:.2f} us")
    print(f"  Instrucciones del supervisor hasta DECISION (contando sus vueltas de espera): {est([x['r_ic0'] for x in f]).strip()}")
    print()
    print("2. Hitos del protocolo dentro del tick, en ciclos desde byte_done (ticks comunes)")
    print()
    print("  " + cab)
    for nombre, k in (("el supervisor publica PUB", "c_pub"), ("el gestor 1 publica EST_1", "c_est1"),
                      ("el gestor 2 publica EST_2", "c_est2"), ("el gestor 3 publica EST_3", "c_est3"),
                      ("el supervisor escribe DECISION", "r_ciclos")):
        print("  {:<44} {:>7} {}".format(nombre, len(comun), est([x[k] for x in comun])))
    print("  Tramos:")
    tramos = (("llega el precio -> PUB (sondeo del SPI y publicacion)", lambda x: x["c_pub"]),
              ("PUB -> ultimo EST (los tres gestores, en paralelo)", lambda x: max(x["c_est1"], x["c_est2"], x["c_est3"]) - x["c_pub"]),
              ("ultimo EST -> DECISION (espera, voto y store)", lambda x: x["r_ciclos"] - max(x["c_est1"], x["c_est2"], x["c_est3"])))
    for nombre, fn in tramos:
        print("  {:<52} {}".format(nombre, est([fn(x) for x in comun])))
    print()
    print("3. Instrucciones por tick de cada hilo (trabajo, sin las vueltas de espera que no encuentran nada)")
    print()
    print("  " + cab)
    nombres = ("hilo 0, supervisor", "hilo 1, gestor max_media", "hilo 2, gestor base", "hilo 3, gestor activo")
    for t in range(4):
        print("  {:<44} {:>7} {}".format(nombres[t], n, est([trabajo(x, t) for x in f])))
    print("  Del supervisor:")
    orden = [x for x in f if x["ic_espejo"] >= 20]
    sin_orden = [x for x in comun if x["ic_espejo"] < 20]
    for nombre, g in (("tick comun sin orden que ejecutar", sin_orden), ("tick en que el espejo ejecuta una orden", orden),
                      ("tick con frontera de ventana", frontera)):
        print("    {:<42} {:>7} {}".format(nombre, len(g), est([trabajo(x, 0) for x in g])))
    print("    {:<42} {:>7} {}".format("de ellas, en el espejo de la cuenta", n, est([x["ic_espejo"] for x in f])))
    print("    {:<42} {:>7} {}".format("de ellas, en la frontera (cuando la hay)", len(frontera), est([x["ic_frontera"] for x in frontera])))
    print("  Instrucciones gastadas en lazos de espera, por tick:")
    print("    {:<42} {:>7} {}".format("supervisor sondeando el SPI", n, est([x["ic_spi"] for x in f])))
    print("    {:<42} {:>7} {}".format("supervisor esperando a los gestores", n, est([x["ic_ges"] for x in f])))
    for t in (1, 2, 3):
        print("    {:<42} {:>7} {}".format(f"gestor {t} sondeando PUB", n, est([x[f'ic{t}'] - x[f'trab{t}'] for x in f])))
    total = sum(trabajo(x, t) for x in f for t in range(4))
    print(f"  Trabajo de los cuatro hilos: {total / n:.2f} instrucciones por tick de {4 * turno} turnos ({100.0 * total / n / (4 * turno):.2f} % de ocupacion).")
    print(f"  CPI por hilo 4,000 y agregado 1,000 por construccion (una instruccion por ciclo, por turnos). Contando solo el trabajo:")
    print(f"  {ciclos_tick * n / total:.1f} ciclos por instruccion util a este periodo.")
    print()
    print("4. Tick completo: ultimo ciclo en que cada hilo hace trabajo, en ciclos desde byte_done")
    print()
    print("  " + cab)
    for t in range(4):
        print("  {:<44} {:>7} {}".format(nombres[t], n, est([x[f"fin{t}"] for x in f])))
    peor_fin = max(max(x[f"fin{t}"] for t in range(4)) for x in f)
    print(f"  El hilo que termina ultimo deja {ciclos_tick - peor_fin} ciclos libres antes del byte_done siguiente en el peor tick.")
    print()
    print("5. Contra el presupuesto del testbench (peor caso de esta corrida; el barrido de la fase va aparte)")
    print()
    peor = max(r)
    print(f"  Presupuesto a este periodo: {presupuesto} ciclos. Peor caso: {peor} ciclos ({100.0 * peor / presupuesto:.2f} %). Margen: {presupuesto - peor} ciclos.")
    return 0


def linea(etiqueta, ruta):
    f = leer(ruta)
    n = len(f)
    r = [x["r_ciclos"] for x in f]
    comun = [x["r_ciclos"] for x in f[1:] if x["ic_frontera"] == 0]
    fin0 = [x["fin0"] for x in f]
    t0 = [trabajo(x, 0) for x in f]
    ge = [x["ic_ges"] for x in f]
    print("  {:<26} {:>6} {:>9.2f} {:>9.2f} {:>6d} {:>9.2f} {:>6d} {:>9.2f} {:>9.2f}".format(
        etiqueta, n, sum(r) / n, sum(comun) / max(1, len(comun)), max(r), sum(fin0) / n, max(fin0), sum(t0) / n, sum(ge) / n))
    return 0


CABECERA_LINEA = "  {:<26} {:>6} {:>9} {:>9} {:>6} {:>9} {:>6} {:>9} {:>9}".format(
    "variante", "ticks", "resp.", "resp.", "resp.", "fin sup.", "fin", "trabajo", "espera a")
CABECERA_LINEA2 = "  {:<26} {:>6} {:>9} {:>9} {:>6} {:>9} {:>6} {:>9} {:>9}".format(
    "", "", "promedio", "t. comun", "peor", "promedio", "peor", "superv.", "gestores")


def fases(rutas):
    peores, medias = [], []
    t_pub, t_ges, t_dec, total = [], [], [], 0
    for ruta in rutas:
        f = leer(ruta)
        r = [x["r_ciclos"] for x in f]
        peores.append(max(r))
        medias.append(sum(r) / len(r))
        comunes = [x["r_ciclos"] for x in f[1:] if x["ic_frontera"] == 0]
        print("  fase {:>2}: ticks {:>5}, respuesta promedio {:>7.2f}, peor tick comun {:>4d}, peor caso {:>4d}".format(
            len(peores) - 1, len(f), medias[-1], max(comunes), max(r)))
        for x in f[1:]:
            ultimo = max(x["c_est1"], x["c_est2"], x["c_est3"])
            t_pub.append(x["c_pub"])
            t_ges.append(ultimo - x["c_pub"])
            t_dec.append(x["r_ciclos"] - ultimo)
        total += len(f)
    print(f"  Peor caso entre las {len(rutas)} fases: {max(peores)} ciclos, en {total} ticks. Promedio de los promedios: {sum(medias) / len(medias):.2f}.")
    print(f"  Maximo de cada tramo por separado: llegada a PUB {max(t_pub)} (minimo {min(t_pub)}), PUB a ultimo EST {max(t_ges)},")
    print(f"  ultimo EST a DECISION {max(t_dec)} (con frontera de ventana). Suma de los tres maximos: {max(t_pub) + max(t_ges) + max(t_dec)} ciclos.")
    print("  Es una cota de lo observado, no una cota demostrada: los tres maximos no se dieron en el mismo tick.")
    for nombre, p in PRESUPUESTO.items():
        print(f"    {nombre:<18} presupuesto {p:>7}: usa {100.0 * max(peores) / p:>6.3f} %, margen {p - max(peores)} ciclos ({(p - max(peores)) // 4} instrucciones por hilo)")
    return 0


def main():
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == "completo":
        return completo(a[1], int(a[2]))
    if len(a) == 3 and a[0] == "linea":
        return linea(a[1], a[2])
    if len(a) == 1 and a[0] == "cabecera":
        print(CABECERA_LINEA)
        print(CABECERA_LINEA2)
        return 0
    if len(a) >= 2 and a[0] == "fases":
        return fases(a[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
