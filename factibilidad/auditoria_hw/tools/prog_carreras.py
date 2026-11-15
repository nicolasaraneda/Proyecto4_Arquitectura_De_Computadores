#!/usr/bin/env python3
"""prog_carreras.py: variantes de sw/fondo.s para la búsqueda de carreras y las mutaciones del protocolo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee factibilidad/b_fondo_hilos/sw/fondo.s (no lo modifica) y escribe una copia
con lo que se pida. Dos tipos de cambio, que se pueden combinar:

Retardos (--retardos D): cada hilo demora una cantidad distinta en cada tick,
según lo que lea de los cuatro interruptores de la placa (0x8000_0008), que el
testbench mueve al azar. No cambian ningún valor que el programa calcule: solo
usan registros que están libres en ese punto.
  - cada gestor, antes de publicar: sw vueltas (0 a 15) de un lazo de dos
    instrucciones, más una instrucción si otra lectura de los interruptores
    tiene el bit 0 en 1. Entre 6 y 37 instrucciones (24 a 148 ciclos).
  - cada gestor, después de publicar: sw * 2^D vueltas y la instrucción de
    paridad con el bit 1. Con D = 4 son hasta 240 vueltas (1920 ciclos), o sea
    que el gestor puede seguir ocupado cuando llega el precio siguiente si el
    período es corto.
  - el supervisor, entre publicar y esperar a los gestores: sw vueltas y la
    instrucción de paridad con el bit 2. Así unas veces llega a leer EST_k
    antes que el gestor publique y otras después.
Con D negativo no hay retardo después de publicar.

Mutaciones del protocolo (--mutacion NOMBRE): un error puesto a propósito.
  sin_esperar_g3   el supervisor lee EST_3 una sola vez y no comprueba su
                   número de tick: si el gestor 3 no ha publicado, vota con su
                   posición del tick anterior
  sin_esperar_g2   lo mismo con EST_2. Con el gestor 3 atrasado (la variante
                   atraso_800 de la pieza) no se nota, porque el gestor 2
                   sigue publicando a tiempo: hace falta atrasar al gestor 2
  pub_dos_stores   el supervisor publica primero el número de tick y después
                   el precio, en dos escrituras: un gestor puede ver el tick
                   nuevo con precio 0
  g1_sin_sello     el supervisor toma el bit de posición de EST_1 sin mirar su
                   número de tick
  des_despues      el gestor publica EST_k antes que DES_k
  est_tick_viejo   el gestor sella EST_k con el tick que procesó antes y no
                   con el que acaba de procesar (se cuelga la espera)

Cuelgue (--cuelgue T): el gestor del hilo 3 se queda en un lazo sin fin cuando
le llega el tick número T, antes de publicar. Sirve para ver qué hace el resto
del fondo, y el vigilante, cuando un hilo de estrategia deja de responder.

Uso:
    prog_carreras.py FONDO.s -o SALIDA.s [--retardos D] [--mutacion NOMBRE] [--cuelgue T]
    prog_carreras.py --lista
"""
import argparse
import sys

PERIF = "0x80000000"
OFF_BTN = 8


def lazo(prefijo, base, cnt, doblar, bit):
    """Bloque de retardo: usa los registros base y cnt, que deben estar libres."""
    b = [
        f"# Auditoría: retardo según los interruptores ({prefijo})",
        f"    li   {base}, {PERIF}",
        f"    lw   {cnt}, {OFF_BTN}({base})",
    ]
    b += [f"    add  {cnt}, {cnt}, {cnt}"] * doblar
    b += [
        f"    beqz {cnt}, {prefijo}_fin",
        f"{prefijo}_lazo:",
        f"    addi {cnt}, {cnt}, -1",
        f"    bnez {cnt}, {prefijo}_lazo",
        f"{prefijo}_fin:",
        f"    lw   {cnt}, {OFF_BTN}({base})",
        f"    andi {cnt}, {cnt}, {bit}",
        f"    beqz {cnt}, {prefijo}_par",
        f"    addi {cnt}, {cnt}, 0",
        f"{prefijo}_par:",
    ]
    return b


def insertar(lineas, marca, bloque):
    i = lineas.index(marca)
    return lineas[:i + 1] + bloque + lineas[i + 1:]


def reemplazar(lineas, viejo, nuevo):
    """Reemplaza un tramo de líneas consecutivas. Tiene que aparecer una sola vez."""
    n = len(viejo)
    donde = [i for i in range(len(lineas) - n + 1) if [s.split("#")[0].split() for s in lineas[i:i + n]] == [s.split() for s in viejo]]
    if len(donde) != 1:
        raise SystemExit(f"prog_carreras.py: el tramo {viejo[0].strip()!r}... aparece {len(donde)} veces")
    i = donde[0]
    return lineas[:i] + nuevo + lineas[i + n:]


MUTACIONES = {
    "sin_esperar_g3": (
        "el supervisor no comprueba el número de tick de EST_3",
        ["s_g3:", "    lw   x7, EST3(x0)", "    sub  x7, x7, x3", "    bgeu x7, x14, s_g3"],
        ["s_g3:", "    lw   x7, EST3(x0)", "    andi x7, x7, 1             # MUTACION: sin comprobar el tick", "    addi x0, x0, 0"]),
    "sin_esperar_g2": (
        "el supervisor no comprueba el número de tick de EST_2",
        ["s_g2:", "    lw   x6, EST2(x0)", "    sub  x6, x6, x3", "    bgeu x6, x14, s_g2"],
        ["s_g2:", "    lw   x6, EST2(x0)", "    andi x6, x6, 1             # MUTACION: sin comprobar el tick", "    addi x0, x0, 0"]),
    "pub_dos_stores": (
        "PUB se escribe en dos stores: primero el tick y después el precio",
        ["    addi x3, x3, 256", "    add  x9, x3, x8", "    sw   x9, PUB(x0)"],
        ["    addi x3, x3, 256", "    sw   x3, PUB(x0)           # MUTACION: el tick solo", "    add  x9, x3, x8", "    sw   x9, PUB(x0)"]),
    "g1_sin_sello": (
        "el supervisor toma la posición de EST_1 sin mirar su número de tick",
        ["s_g1:", "    lw   x5, EST1(x0)", "    sub  x5, x5, x3", "    bgeu x5, x14, s_g1"],
        ["s_g1:", "    lw   x5, EST1(x0)", "    andi x5, x5, 1             # MUTACION: sin comprobar el tick", "    addi x0, x0, 0"]),
    "des_despues": (
        "el gestor publica EST_k antes que DES_k",
        ["    sw   x13, OFF_DES(x2)", "    sub  x7, x5, x8", "    add  x7, x7, x4", "    sw   x7, OFF_EST(x2)"],
        ["    sub  x7, x5, x8", "    add  x7, x7, x4", "    sw   x7, OFF_EST(x2)", "    sw   x13, OFF_DES(x2)       # MUTACION: después que EST"]),
    "est_tick_viejo": (
        "el gestor sella EST_k con el tick anterior",
        ["    sub  x7, x5, x8", "    add  x7, x7, x4", "    sw   x7, OFF_EST(x2)"],
        ["    sub  x7, x5, x8", "    addi x7, x7, -256          # MUTACION: tick anterior", "    add  x7, x7, x4", "    sw   x7, OFF_EST(x2)"]),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("programa", nargs="?")
    ap.add_argument("-o", "--salida")
    ap.add_argument("--retardos", type=int, default=None, metavar="D")
    ap.add_argument("--mutacion", default=None)
    ap.add_argument("--cuelgue", type=int, default=None, metavar="T")
    ap.add_argument("--lista", action="store_true")
    args = ap.parse_args()
    if args.lista:
        for n, (desc, _, _) in MUTACIONES.items():
            print(f"{n}|{desc}")
        return 0
    if not args.programa or not args.salida:
        ap.error("faltan el programa y -o")
    with open(args.programa, encoding="utf-8") as f:
        lineas = f.read().split("\n")
    if args.mutacion:
        if args.mutacion not in MUTACIONES:
            raise SystemExit(f"mutación desconocida: {args.mutacion}")
        _, viejo, nuevo = MUTACIONES[args.mutacion]
        lineas = reemplazar(lineas, viejo, nuevo)
    if args.cuelgue is not None:
        lineas = insertar(lineas, "#@RETARDO_ANTES", [
            f"# Auditoría: el gestor del hilo 3 se cuelga al llegar el tick {args.cuelgue}",
            "    li   x7, G3",
            "    bne  x2, x7, cg_fin",
            f"    li   x7, {args.cuelgue * 256}",
            "    bltu x5, x7, cg_fin        # x5 = tick * 256 + precio",
            "cg_cuelgue:",
            "    j    cg_cuelgue",
            "cg_fin:",
        ])
    if args.retardos is not None:
        # En el gestor x7 y x9 están libres en las dos marcas. En el supervisor
        # x1 y x9 son temporales libres entre publicar y esperar.
        lineas = insertar(lineas, "#@RETARDO_ANTES", lazo("ca", "x7", "x9", 0, 1))
        if args.retardos >= 0:
            lineas = insertar(lineas, "#@RETARDO", lazo("cd", "x7", "x9", args.retardos, 2))
        lineas = insertar(lineas, "#@ESPEJO_ANTES", lazo("cs", "x1", "x9", 0, 4))
    with open(args.salida, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
