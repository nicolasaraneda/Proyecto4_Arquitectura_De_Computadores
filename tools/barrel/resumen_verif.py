#!/usr/bin/env python3
"""resumen_verif.py: junta los resultados de las corridas de tools/verif.sh.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 resumen_verif.py CARPETA corridas.txt [CLAVES_UNICAS [PUERTA [XD]]]

corridas.txt tiene una línea "GRUPO SEMILLA HILO" por corrida y el log de cada
una está en CARPETA/GRUPO/GRUPO_sSEMILLA_hHILO.log. Lee de cada log las líneas
"HILO t: ..." y "PASS verif: ..." de tb/tb_verif.sv y escribe, por grupo, las
corridas que pasan y el conteo exacto de instrucciones comparadas por hilo.
Termina con código 1 si alguna corrida que debía pasar no pasa, o si alguna
del grupo de control (N) pasa.

CLAVES_UNICAS es la cantidad de instrucciones distintas de la campaña lineal
(grupos L, M, P y Q) contadas sobre toda la campaña, que calcula
tools/barrel/verif.sh. Con PUERTA = 1 se exige además el criterio 5 de la
puerta de simulación: al menos 5 millones de instrucciones en la campaña
lineal y más de 90 % de ellas distintas.

XD es la máscara de la extensión de la ISA en custom-0 con que se compiló el
barrel (0 sin extensión). Con un valor distinto de 0 se suman además las
líneas "XD t: ..." del testbench: cuántas instrucciones emad, devk y mulstep
se compararon contra la especificación y cuántas palabras de custom-0 sin
efecto. Se exige que cada instrucción presente se haya ejecutado.
"""
import re
import sys
from collections import defaultdict

TITULOS = {
    "A": "A. Un hilo con el programa (tools/prog_aleatorio.py del repositorio, 300 instrucciones al azar, con SPI y\n"
         "   perifericos, precio nuevo cada 97 instrucciones) y los otros tres en un lazo vacio. Referencia: Espino\n"
         "   base solo. Si el programa sale de la memoria (jalr con una base cualquiera) la comparacion de esa\n"
         "   corrida termina ahi. Estos programas llegan a un punto fijo: despues de un par de vueltas repiten valores.",
    "W": "W. Los programas del grupo A con el barrel compilado con contador de programa de 32 bits: se compara\n"
         "   tambien lo que el programa hace fuera de la memoria.",
    "U": "U. Un hilo con el programa (tools/barrel/prog_hilos.py --modo uno: 300 instrucciones al azar que no se quedan\n"
         "   quietas, precio nuevo cada 97 instrucciones) y los otros tres en un lazo vacio.",
    "H": "H. sw/hazard_test.s y sw/hazard_review.s (sin modificar) en un hilo, los otros tres en un lazo vacio.\n"
         "   Los dos programas terminan en un lazo vacio, que se cuenta aparte.",
    "B": "B. Cuatro hilos a la vez, programas aleatorios distintos, zonas de datos separadas, los cuatro con accesos\n"
         "   al SPI (bus quieto) y a los perifericos. Referencia: cada hilo contra un Espino base que corre solo.",
    "C": "C. Cuatro hilos a la vez; uno solo accede al SPI y recibe un precio nuevo cada 29 instrucciones.",
    "T": "T. Un hilo corre sw/trade.s (sin modificar) con un precio nuevo cada 61 instrucciones y los otros tres\n"
         "   corren programas aleatorios.",
    "D": "D. Cuatro hilos a la vez sobre la MISMA zona de datos, y con saltos que pueden caer en el codigo de otro\n"
         "   hilo. Referencia: cuatro Espino base por turnos, con las escrituras de cada uno copiadas a la memoria\n"
         "   de los demas. Si un hilo sale de la memoria la corrida termina ahi.",
    "N": "N. Control: los programas del grupo D con la referencia del grupo B. Tienen que fallar.",
    "J": "J. Informativo: programas como los del grupo B pero con el jalr libre del generador del repositorio (un\n"
         "   salto puede caer en un jalr sin su auipc), contra la referencia de hilos aislados. No cuenta como falla.",
    "K": "K. Los mismos programas del grupo J con la referencia de memoria compartida. Tienen que pasar todos.",
    "L": "L. Campana lineal. Cuatro hilos a la vez, cada programa se ejecuta una sola vez (prog_hilos.py --lineal),\n"
         "   zonas de datos separadas, los cuatro con accesos al SPI (bus quieto) y a los perifericos.",
    "M": "M. Campana lineal. Cuatro hilos a la vez; uno solo accede al SPI y recibe un precio nuevo cada 11 instrucciones.",
    "P": "P. Campana lineal. Cuatro hilos a la vez sobre la MISMA zona de datos, con saltos que pueden caer en el\n"
         "   codigo de otro hilo. Referencia: cuatro Espino base por turnos con las escrituras copiadas entre ellos.",
    "Q": "Q. Campana lineal. Un hilo con un cuerpo de 300 instrucciones (precio nuevo cada 31) y los otros tres en\n"
         "   un lazo vacio.",
}
LINEAL = "LMPQ"
REFERENCIA = ["el Espino base", "el Espino base con la especificacion de la extension"]
META_INSTR = 5_000_000
META_DIST = 0.90
CAMPOS = ["instr", "rf", "stores", "loads", "saltos", "mmio", "spi", "bandera", "lazo", "dist"]
RE_HILO = re.compile(r"^HILO (\d): (\d+) instrucciones comparadas \((\d+) escrituras de registro, (\d+) stores, (\d+) loads, "
                     r"(\d+) saltos, (\d+) accesos a SPI y perifericos, de ellos (\d+) al SPI, (\d+) lecturas de STATUS con precio nuevo, "
                     r"(\d+) de lazo vacio, (\d+) distintas")
RE_XD = re.compile(r"^XD (\d): (\d+) emad, (\d+) devk, (\d+) mulstep, (\d+) palabras de custom-0 sin efecto")
RE_PASS = re.compile(r"^PASS verif: (\d+) instrucciones.*memoria final: (\d+) palabras iguales y (\d+) sin comparar.*"
                     r"testbench: (\d+); ciclos del barrel: (\d+)")


def miles(n):
    return f"{n:,}".replace(",", " ")


def main():
    carpeta, lista = sys.argv[1], sys.argv[2]
    unicas = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    puerta = len(sys.argv) > 4 and sys.argv[4] == "1"
    xd = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    xd_lin, xd_lazos = [0, 0, 0, 0], [0, 0, 0, 0]     # emad, devk, mulstep y custom-0 sin efecto
    lin_hilo = [0, 0, 0, 0]              # campaña lineal: instrucciones de programa, por hilo
    lin_dist = lin_corridas = lin_rf = lin_loads = lin_stores = lin_saltos = lin_mmio = lin_spi = 0
    lin_precios = lin_bandera = lin_ocioso = lin_fuera = 0
    grupos = defaultdict(list)
    for linea in open(lista):
        g, s, t = linea.split()
        grupos[g].append((s, t))

    mal = 0
    total_hilo = [0, 0, 0, 0]            # instrucciones de programa, por hilo
    total_ocioso = [0, 0, 0, 0]          # instrucciones de lazo vacío, por hilo
    total_spi = total_mmio = total_stores = total_loads = total_rf = total_saltos = 0
    total_w = [0, 0, 0, 0]               # grupo W: contador de programa de 32 bits
    total_dist = [0, 0, 0, 0]            # instrucciones distintas (contador de programa y datos), por hilo
    total_precios = total_bandera = 0
    for g in "AWUHBCTDNJK" + LINEAL:
        if g not in grupos:
            continue
        corridas = grupos[g]
        pasan, fallas, fuera = 0, [], 0
        hilo = [defaultdict(int) for _ in range(4)]       # hilos con programa
        ocioso = [0, 0, 0, 0]
        mem_ok = mem_vuelo = precios = ciclos = 0
        for s, t in corridas:
            ruta = f"{carpeta}/{g}/{g}_s{s}_h{t}.log"
            try:
                texto = open(ruta).read()
            except OSError:
                texto = ""
            m = None
            filas = []
            xd_corrida = [0, 0, 0, 0]
            for linea in texto.splitlines():
                mx = RE_XD.match(linea)
                if mx:
                    for k in range(4):
                        xd_corrida[k] += int(mx.group(2 + k))
                mh = RE_HILO.match(linea)
                if mh:
                    filas.append([int(x) for x in mh.groups()])
                    if "FUERA" in linea:
                        fuera += 1
                m = RE_PASS.match(linea) or m
            if m is None or len(filas) != 4:
                primera = next((x for x in texto.splitlines() if x.startswith("FAIL")), "sin linea FAIL ni PASS")
                fallas.append((s, t, primera))
                continue
            pasan += 1
            if g not in "WK":
                for k in range(4):
                    (xd_lin if g in LINEAL else xd_lazos)[k] += xd_corrida[k]
            mem_ok += int(m.group(2)); mem_vuelo += int(m.group(3)); precios += int(m.group(4)); ciclos += int(m.group(5))
            for f in filas:
                h = f[0]
                # Las instrucciones de lazo vacío (jal x0 a sí mismo) se cuentan
                # aparte: son las de los hilos ociosos y las del lazo final de
                # un programa que termina. También son saltos, así que se
                # descuentan de esa columna.
                ocioso[h] += f[9]
                f[1] -= f[9]
                f[5] -= f[9]
                if f[9]:
                    f[10] -= 1          # el lazo vacío cuenta como una instrucción distinta
                for k, c in enumerate(CAMPOS):
                    hilo[h][c] += f[1 + k]

        print(TITULOS[g])
        if g in "NJ":
            if g == "N":
                print(f"   Corridas: {len(corridas)}. Fallan (lo esperado): {len(fallas)}. Pasan: {pasan}.")
                if pasan:
                    mal += 1
                    print("   FAIL: un programa de memoria compartida pasa con la referencia de hilos aislados")
            else:
                print(f"   Corridas: {len(corridas)}. Difieren de la referencia de hilos aislados: {len(fallas)}. Pasan: {pasan}.")
            causas = defaultdict(int)
            for _, _, f in fallas:
                mm = re.search(r"\(([^)]*)\)\s*$", f)
                causas[mm.group(1) if mm else f] += 1
            for c, n in sorted(causas.items(), key=lambda x: -x[1]):
                print(f"     {n} por: {c}")
            print()
            continue
        print(f"   Corridas: {len(corridas)}. Pasan: {pasan}. Fallan: {len(fallas)}. Programas que salieron de la memoria: {fuera}.")
        for s, t, f in fallas[:5]:
            print(f"   FAIL semilla {s} hilo {t}: {f}")
        mal += len(fallas)
        print("   hilo   instrucciones    distintas   escr. registro     stores      loads     saltos   SPI y perif.   solo SPI   STATUS con precio")
        for h in range(4):
            d = hilo[h]
            print(f"   {h}      {miles(d['instr']):>13}   {miles(d['dist']):>10}   {miles(d['rf']):>14}   {miles(d['stores']):>8}   {miles(d['loads']):>8}   "
                  f"{miles(d['saltos']):>8}   {miles(d['mmio']):>12}   {miles(d['spi']):>8}   {miles(d['bandera']):>17}")
            if g in "WK":
                if g == "W":
                    total_w[h] += d["instr"]
                continue
            if g in LINEAL:
                lin_hilo[h] += d["instr"]; lin_dist += d["dist"]; lin_ocioso += ocioso[h]
                lin_rf += d["rf"]; lin_loads += d["loads"]; lin_stores += d["stores"]; lin_saltos += d["saltos"]
                lin_mmio += d["mmio"]; lin_spi += d["spi"]; lin_bandera += d["bandera"]
                continue
            total_bandera += d["bandera"]
            total_hilo[h] += d["instr"]
            total_dist[h] += d["dist"]
            total_ocioso[h] += ocioso[h]
            total_spi += d["spi"]; total_mmio += d["mmio"]; total_stores += d["stores"]; total_loads += d["loads"]
            total_rf += d["rf"]; total_saltos += d["saltos"]
        suma = sum(hilo[h]["instr"] for h in range(4))
        print(f"   total  {miles(suma):>13}   {miles(sum(hilo[h]['dist'] for h in range(4))):>10}")
        if sum(ocioso):
            print(f"   Ademas, instrucciones de lazo vacio (jal x0 a si mismo: hilos ociosos y lazo final), tambien comparadas: "
                  f"{miles(ocioso[0])}, {miles(ocioso[1])}, {miles(ocioso[2])} y {miles(ocioso[3])}.")
        if g in LINEAL:
            lin_precios += precios; lin_corridas += pasan; lin_fuera += fuera
        elif g not in "WK":
            total_precios += precios
        print(f"   Memoria al final: {miles(mem_ok)} palabras iguales y {miles(mem_vuelo)} sin comparar por stores en vuelo. "
              f"Precios nuevos puestos por el testbench: {miles(precios)}. Ciclos del barrel: {miles(ciclos)}.")
        print()

    if sum(lin_hilo):
        lin = sum(lin_hilo)
        print("CAMPANA LINEAL (grupos L, M, P y Q): instrucciones de programa comparadas una por una, con el barrel tal")
        print("como se sintetiza (contador de programa de 11 bits), sin contar los lazos vacios:")
        for h in range(4):
            print(f"   hilo {h}: {miles(lin_hilo[h]):>11}")
        print(f"   total:  {miles(lin):>11}   en {miles(lin_corridas)} corridas, cada una con un programa distinto")
        print(f"   Distintas dentro de su corrida: {miles(lin_dist)} ({100 * lin_dist / lin:.2f} %).")
        print(f"   Distintas en toda la campana:   {miles(unicas)} ({100 * unicas / lin:.2f} %).")
        print("   (distinta: no hay otra instruccion comparada, en ninguna corrida de la campana, con el mismo hilo, contador")
        print("    de programa, instruccion, valor escrito al banco, acceso al bus y palabra de memoria escrita)")
        print(f"   De ellas: {miles(lin_rf)} escriben un registro, {miles(lin_loads)} son loads, {miles(lin_stores)} son stores, "
              f"{miles(lin_saltos)} son saltos, {miles(lin_mmio)} acceden al SPI o a los perifericos ({miles(lin_spi)} al SPI).")
        print(f"   Precios nuevos puestos por el testbench: {miles(lin_precios)}. Lecturas de STATUS con la bandera de precio nuevo: {miles(lin_bandera)}.")
        print(f"   Programas que salieron de la memoria: {lin_fuera}. Instrucciones de lazo vacio comparadas aparte: {miles(lin_ocioso)}.")
        if xd:
            print(f"   Extension de la ISA, comparadas contra la especificacion: {miles(xd_lin[0])} emad, {miles(xd_lin[1])} devk y "
                  f"{miles(xd_lin[2])} mulstep. Palabras de custom-0 que no son una instruccion y no hicieron nada: {miles(xd_lin[3])}.")
            if any((xd >> k) & 1 and xd_lin[k] == 0 for k in range(3)):
                mal += 1
                print("   FAIL: una instruccion de la extension presente en el core no se ejecuto nunca")
        if puerta:
            ok = lin >= META_INSTR and unicas > META_DIST * lin
            print(f"   Criterio 5 de la puerta (al menos {miles(META_INSTR)} instrucciones y mas de {100 * META_DIST:.0f} % distintas): "
                  f"{'PASS' if ok else 'FAIL'}")
            if not ok:
                mal += 1
        print()
    if not sum(total_hilo):
        print("RESULTADO: PASS, cero diferencias entre cada hilo del barrel y " + REFERENCIA[xd != 0] if mal == 0
              else f"RESULTADO: FAIL ({mal} problemas)")
        sys.exit(0 if mal == 0 else 1)
    print("CAMPANA DE LAZOS: instrucciones de programa comparadas una por una, por hilo, con el barrel tal como se sintetiza")
    print("(contador de programa de 11 bits; sin contar los lazos vacios ni los grupos W, J y K):")
    for h in range(4):
        print(f"   hilo {h}: {miles(total_hilo[h]):>11}   de ellas distintas: {miles(total_dist[h]):>10}")
    print(f"   total:  {miles(sum(total_hilo)):>11}   de ellas distintas: {miles(sum(total_dist)):>10}")
    print("   (distinta: el mismo contador de programa con otro valor escrito u otro acceso al bus dentro de la corrida;")
    print("    mide cuanto de lo comparado no es repeticion de la misma vuelta del programa)")
    print(f"   De ellas: {miles(total_rf)} escriben un registro, {miles(total_loads)} son loads, {miles(total_stores)} son stores, "
          f"{miles(total_saltos)} son saltos, {miles(total_mmio)} acceden al SPI o a los perifericos ({miles(total_spi)} al SPI).")
    print(f"   Precios nuevos puestos por el testbench: {miles(total_precios)}. Lecturas de STATUS con la bandera de precio nuevo: {miles(total_bandera)}.")
    print(f"   Instrucciones de lazo vacio comparadas aparte: {miles(sum(total_ocioso))}.")
    if xd:
        print(f"   Extension de la ISA, comparadas contra la especificacion: {miles(xd_lazos[0])} emad, {miles(xd_lazos[1])} devk y "
              f"{miles(xd_lazos[2])} mulstep. Palabras de custom-0 que no son una instruccion y no hicieron nada: {miles(xd_lazos[3])}.")
        if any((xd >> k) & 1 and xd_lazos[k] == 0 for k in range(3)):
            mal += 1
            print("   FAIL: una instruccion de la extension presente en el core no se ejecuto nunca")
    if sum(total_w):
        print(f"Ademas, con el contador de programa de 32 bits (grupo W): {miles(total_w[0])}, {miles(total_w[1])}, "
              f"{miles(total_w[2])} y {miles(total_w[3])} por hilo, {miles(sum(total_w))} en total.")
    print()
    if mal == 0:
        print("RESULTADO: PASS, cero diferencias entre cada hilo del barrel y " + REFERENCIA[xd != 0])
    else:
        print(f"RESULTADO: FAIL ({mal} corridas con problemas)")
    sys.exit(0 if mal == 0 else 1)


if __name__ == "__main__":
    main()
