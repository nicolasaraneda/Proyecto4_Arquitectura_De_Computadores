#!/usr/bin/env python3
"""variante.py: arma sw/c1.s con fallas puestas a propósito, para las pruebas de degradación de R3
(criterio 6 de la puerta) y del vigilante.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

No cambia ninguna línea del programa: solo inserta instrucciones en las marcas "#@HILOk", que
están justo después de que el hilo k ve el precio del tick. Los datos del programa tienen
dirección fija (.org), así que las inserciones no mueven ninguna palabra compartida. Quedan 30
palabras libres entre el código y los datos: caben hasta tres fallas juntas.

Fallas (K es el hilo, N el tick contado desde 1 como lo cuenta el hilo 0; se juntan con "+"):
  cuelga:K:N         el hilo K (1, 2 o 3) entra en un lazo infinito al ver el precio del tick N.
                     Desde ese tick la política no llega: el hilo 0 sostiene un tick y pasa a
                     modo seguro (banda 40)
  atraso:K:N:V       el hilo K (1 o 2) da V vueltas de 8 ciclos antes de trabajar el tick N.
                     Con V sobre unas 60 la política del tick N llega después del plazo (dato
                     viejo): el hilo 0 sostiene ese tick y en el siguiente vuelve a usarla. Si el
                     atraso dura más que un período, el hilo se salta un precio, los que esperan
                     su dato de ese tick no avanzan más y el hilo 0 pasa a modo seguro.
                     No se ofrece en el hilo 3: ese hilo lee D_ORD (el byte del tick anterior)
                     apenas ve el precio, sin esperar a nadie; atrasarlo ahí no es un dato que
                     llega tarde sino un hilo roto, y eso lo cubre cuelga:3
  cuelga:0:N         el hilo 0 entra en un lazo infinito al recibir el precio del tick N, antes de
                     decidir: deja de escribir DECISION. Es la falla dura que ve el vigilante

Qué espera la referencia (ref/c1/c1.py): --faltas imprime los argumentos para tools/c1/caso.py
(--faltas con los ticks en que la política no llega nunca y --tardias con los que llega después
del plazo), suponiendo que cada atraso vence el plazo. Si no fuera así, la corrida lo delata:
los bytes difieren de la referencia.

Uso: tools/c1/variante.py FALLAS [-i sw/c1.s] -o salida.s
     tools/c1/variante.py FALLAS --faltas NTICKS [--periodo-ns P]   # argumentos para caso.py
"""
import argparse
import sys

# registro que trae D_PUB en la marca y un temporal libre ahí, por hilo
REG = {1: ("x14", "x15"), 2: ("x14", "x15"), 3: ("x13", "x12")}
MARGEN = 100             # ciclos: un atraso a menos de esto del período ya cuenta como precio saltado


def leer(texto):
    fallas = []
    for parte in texto.split("+"):
        campos = parte.split(":")
        tipo, nums = campos[0], [int(c) for c in campos[1:]]
        if tipo == "cuelga" and len(nums) == 2 and nums[0] in (0, 1, 2, 3) and nums[1] >= 1:
            fallas.append((tipo, nums))
        elif tipo == "atraso" and len(nums) == 3 and nums[0] in (1, 2) and nums[1] >= 1 and 1 <= nums[2] <= 2000:
            fallas.append((tipo, nums))
        else:
            raise SystemExit(f"falla mal escrita: {parte}")
    return fallas


def armar(fuente, fallas):
    marcas = {f"#@HILO{k}": [] for k in range(4)}
    for i, (tipo, n) in enumerate(fallas):
        k, tick = n[0], n[1]
        if k == 0:
            # x3 trae el tick anterior << 8; x15 está libre en ese punto
            marcas["#@HILO0"] += [f"    li   x15, {256 * (tick - 1)}", f"    bne  x3, x15, v{i}_s",
                                  f"v{i}_c:", f"    j    v{i}_c", f"v{i}_s:"]
            continue
        pub, tmp = REG[k]
        codigo = [f"    li   {tmp}, {256 * tick}", f"    sub  {tmp}, {pub}, {tmp}", f"    sltiu {tmp}, {tmp}, 256"]
        if tipo == "cuelga":
            codigo += [f"v{i}_c:", f"    bnez {tmp}, v{i}_c"]
        else:
            codigo += [f"    beqz {tmp}, v{i}_s", f"    li   {tmp}, {n[2]}", f"v{i}_l:", f"    addi {tmp}, {tmp}, -1",
                       f"    bnez {tmp}, v{i}_l", f"v{i}_s:"]
        marcas[f"#@HILO{k}"] += codigo
    salida, vistas = [], set()
    for linea in fuente.splitlines():
        salida.append(linea)
        m = linea.strip()
        if m in marcas:
            vistas.add(m)
            salida += marcas[m]
    faltan = set(marcas) - vistas
    if faltan:
        raise SystemExit(f"el programa no tiene las marcas {sorted(faltan)}")
    return "\n".join(salida) + "\n"


def faltas(fallas, nticks, periodo_ns=100000):
    """Argumentos para caso.py: ticks en que la política no llega nunca y ticks en que llega tarde."""
    ciclos = periodo_ns // 40
    nunca, tarde, desde = [], [], nticks + 1
    for tipo, n in fallas:
        if n[0] == 0:
            continue
        if tipo == "cuelga" or 8 * n[2] > ciclos - MARGEN:
            desde = min(desde, n[1])
        else:
            tarde.append(n[1])
    tarde = [t for t in tarde if t < desde]
    if desde <= nticks:
        nunca.append(f"{desde}-{nticks}")
    return (["--faltas", ",".join(nunca)] if nunca else []) + (["--tardias", ",".join(map(str, tarde))] if tarde else [])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Variantes de sw/c1.s con fallas")
    ap.add_argument("fallas")
    ap.add_argument("-i", "--entrada", default="sw/c1.s")
    ap.add_argument("-o", "--salida")
    ap.add_argument("--faltas", type=int, metavar="NTICKS", help="imprime los argumentos para tools/c1/caso.py y termina")
    ap.add_argument("--periodo-ns", type=int, default=100000)
    a = ap.parse_args(argv)
    fallas = leer(a.fallas)
    if a.faltas:
        print(" ".join(faltas(fallas, a.faltas, a.periodo_ns)))
        return 0
    with open(a.entrada, encoding="utf-8") as f:
        texto = armar(f.read(), fallas)
    if a.salida:
        with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
