#!/usr/bin/env python3
"""variante.py: arma las variantes de medición de sw/fondo.s a partir del mismo archivo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

sw/fondo.s trae marcas (líneas que empiezan con "#@"). Este script mueve o
inserta texto en esas marcas y escribe el programa resultante. No cambia
ninguna otra línea, así que cada variante difiere del programa base solo en
lo que dice su nombre.

  espejo_antes        El espejo de la cuenta real se calcula antes de esperar
                      a los gestores, en paralelo con ellos, en vez de después
                      de escribir DECISION. Es lo que haría falta si el reparto
                      necesitara el patrimonio (posiciones parciales).
  retardo_antes:N:H   El gestor del hilo H (1, 2 o 3) da N vueltas de un lazo
                      vacío (2 N instrucciones, 8 N ciclos) antes de publicar.
  retardo_despues:N:H Lo mismo, pero después de publicar: se atrasa para el
                      tick siguiente.
  anterior            El supervisor no espera el resultado del tick en curso:
                      toma lo que los gestores publicaron en el tick anterior
                      (comprueba que sea de ese tick), publica el precio nuevo
                      y decide. Su referencia es fondo_min_ant (df=1).
  vuelta              El contador de ticks del supervisor parte 16 ticks antes
                      de dar la vuelta (24 bits), para ejercitar ese caso sin
                      simular 16,7 millones de ticks.

Uso:
    python3 tools/variante.py sw/fondo.s espejo_antes -o build/sw/fondo_espejo_antes.s
"""
import argparse
import sys

BASE_GESTOR = {1: "G1", 2: "G2", 3: "G3"}


def cortar(lineas, inicio, fin):
    """Saca las líneas entre dos marcas (sin las marcas) y las devuelve aparte."""
    a, b = lineas.index(inicio), lineas.index(fin)
    if not a < b:
        raise SystemExit(f"las marcas {inicio} y {fin} están en el orden equivocado")
    return lineas[:a + 1] + lineas[b:], lineas[a + 1:b]


def insertar(lineas, marca, bloque):
    i = lineas.index(marca)
    return lineas[:i + 1] + bloque + lineas[i + 1:]


def retardo(vueltas, hilo, prefijo):
    return [
        f"# Retardo puesto a propósito: el gestor del hilo {hilo} da {vueltas} vueltas vacías",
        f"    li   x7, {BASE_GESTOR[hilo]}",
        f"    bne  x2, x7, {prefijo}_fin",
        f"    li   x7, {vueltas}",
        f"{prefijo}_lazo:",
        "    addi x7, x7, -1",
        f"    bnez x7, {prefijo}_lazo",
        f"{prefijo}_fin:",
    ]


def aplicar(lineas, variante):
    nombre, _, resto = variante.partition(":")
    if nombre == "base":
        return lineas
    if nombre == "espejo_antes":
        lineas, bloque = cortar(lineas, "#@ESPEJO_INICIO", "#@ESPEJO_FIN")
        return insertar(lineas, "#@ESPEJO_ANTES", bloque)
    if nombre == "anterior":
        lineas, bloque = cortar(lineas, "#@PUB_INICIO", "#@PUB_FIN")
        return insertar(lineas, "#@PUB_DESPUES", bloque)
    if nombre == "vuelta":
        i = next(k for k, s in enumerate(lineas) if s.startswith("    li   x3, 0 "))
        lineas = list(lineas)
        lineas[i] = "    li   x3, -4096             # variante: el contador de ticks da la vuelta en el tick 16"
        return lineas
    if nombre in ("retardo_antes", "retardo_despues"):
        partes = resto.split(":")
        vueltas = int(partes[0])
        hilo = int(partes[1]) if len(partes) > 1 else 3
        if hilo not in BASE_GESTOR or vueltas < 1:
            raise SystemExit("retardo: N debe ser positivo y H debe ser 1, 2 o 3")
        marca = "#@RETARDO_ANTES" if nombre == "retardo_antes" else "#@RETARDO"
        return insertar(lineas, marca, retardo(vueltas, hilo, "ra" if nombre == "retardo_antes" else "rd"))
    raise SystemExit(f"variante desconocida: {variante}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("programa")
    ap.add_argument("variantes", nargs="+", help="una o más variantes, se aplican en orden")
    ap.add_argument("-o", "--salida", required=True)
    args = ap.parse_args()
    with open(args.programa, encoding="utf-8") as f:
        lineas = f.read().split("\n")
    for v in args.variantes:
        lineas = aplicar(lineas, v)
    with open(args.salida, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
