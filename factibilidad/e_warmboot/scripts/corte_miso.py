#!/usr/bin/env python3
"""corte_miso.py: qué byte lee la maestra si el pin MISO se suelta o vuelve a mitad de una transacción.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Durante la reconfiguración el pin MISO queda en alta impedancia. La maestra
lee entonces el nivel que imponga la resistencia más fuerte de la línea:

    tirón = 1   el pull-up interno del iCE40 (lo documentado para un pin sin
                configurar), si la maestra no tiene una resistencia a tierra
    tirón = 0   una resistencia a tierra en la maestra, más fuerte que el pull-up

El byte se transmite con el bit 7 primero. Si el cambio cae dentro de una
transacción, la maestra lee una mezcla. Este script recorre todos los casos:

    salida    el SoC principal deja de manejar el pin después de k bits
              (k = 0 a 8): los primeros k bits son los de DECISION y el resto
              vale el tirón
    vuelta    el SoC de respaldo empieza a manejar el pin después de k bits:
              los primeros k bits valen el tirón y el resto vale 0, porque el
              respaldo arranca en reset con MISO en 0 y con DECISION = 0x00

y clasifica el byte resultante con el formato del enunciado: bits [7:6]
acción (00 mantener, 01 comprar, 10 vender, 11 se trata como mantener) y bits
[5:0] cantidad. Una orden con cantidad 0 no se ejecuta.

Para la salida se recorren los 256 valores de DECISION. El resultado se
compara con la orden que el programa había escrito:

    igual        la maestra lee el mismo byte
    inocuo       lee mantener, o una orden que no se ejecuta (cantidad 0)
    menor        misma acción, cantidad menor
    mayor        misma acción, cantidad mayor
    ajena        una acción que el programa no pidió

    python3 scripts/corte_miso.py
"""


def accion(b):
    a, q = b >> 6, b & 63
    if a == 1 and q:
        return "comprar", q
    if a == 2 and q:
        return "vender", q
    return "mantener", 0


def texto(b):
    a, q = accion(b)
    return "0x%02X %s" % (b, a if a == "mantener" else "%s %d" % (a, q))


def salida(dec, k, tiron):
    """Los primeros k bits (desde el 7) son de dec; el resto vale el tirón."""
    resto = 8 - k
    alto = (dec >> resto) << resto
    return alto | (((1 << resto) - 1) if tiron else 0)


def vuelta(k, tiron):
    """Los primeros k bits valen el tirón; el resto vale 0."""
    return (((1 << k) - 1) << (8 - k)) if tiron else 0


def clasificar(dec, leido):
    a0, q0 = accion(dec)
    a1, q1 = accion(leido)
    if leido == dec:
        return "igual"
    if a1 == "mantener":
        return "inocuo"
    if a1 != a0:
        return "ajena"
    if q1 == q0:
        return "igual"
    return "menor" if q1 < q0 else "mayor"


def main():
    print("Byte que lee la maestra si el pin MISO cambia a mitad de una transacción")
    print("Comando: python3 factibilidad/e_warmboot/scripts/corte_miso.py")
    print()
    print("1. Transacción completa con el pin suelto")
    for tiron in (1, 0):
        print("   tirón = %d: %s" % (tiron, texto(0xFF if tiron else 0x00)))
    print()

    print("2. Vuelta: el respaldo empieza a manejar el pin después de k bits")
    for tiron in (1, 0):
        vistos = [vuelta(k, tiron) for k in range(9)]
        print("   tirón = %d: %s" % (tiron, ", ".join(texto(b) for b in sorted(set(vistos)))))
        ejecutan = [b for b in vistos if accion(b)[0] != "mantener"]
        print("      órdenes que se ejecutarían: %d de 9 casos" % len(ejecutan))
    print()

    print("3. Salida: el principal suelta el pin después de k bits (256 valores de DECISION por 9 cortes)")
    for tiron in (1, 0):
        cuenta = {}
        ejemplos = {}
        for dec in range(256):
            for k in range(9):
                c = clasificar(dec, salida(dec, k, tiron))
                cuenta[c] = cuenta.get(c, 0) + 1
                ejemplos.setdefault(c, (dec, k, salida(dec, k, tiron)))
        print("   tirón = %d:" % tiron)
        for c in ("igual", "inocuo", "menor", "mayor", "ajena"):
            if c in cuenta:
                d, k, l = ejemplos[c]
                print("      %-7s %4d casos   (ejemplo: DECISION %s, corte tras %d bits, lee %s)" %
                      (c, cuenta[c], texto(d), k, texto(l)))
    print()

    print("4. Salida, solo los bytes que escribe el programa de la regla base y los de un programa que mantiene")
    casos = [(0x7F, "comprar 63"), (0xBF, "vender 63"), (0x00, "mantener (0x00)"), (0xC0, "mantener (0xC0)")]
    for tiron in (1, 0):
        print("   tirón = %d:" % tiron)
        for dec, nombre in casos:
            partes = []
            for k in range(9):
                l = salida(dec, k, tiron)
                partes.append("%s[%s]" % (texto(l), clasificar(dec, l)))
            distintos = []
            for p in partes:
                if p not in distintos:
                    distintos.append(p)
            print("      DECISION = %-16s -> %s" % (nombre, "; ".join(distintos)))
    print()
    print("Conclusión:")
    print("- Con el pin suelto durante toda la transacción la maestra lee 0xFF o 0x00: mantener.")
    print("- En la vuelta ningún caso ejecuta una orden, con cualquiera de los dos tirones.")
    print("- En la salida, los bytes de la regla base (comprar 63 y vender 63) dan la misma orden,")
    print("  una menor o mantener. Con tirón = 1 hay 77 casos de 2304 con una orden ajena: todos")
    print("  parten de un mantener con el bit 7 en 0 (0x00 a 0x3F, corte tras el primer bit) o de")
    print("  una orden de cantidad 0 (0x40 y 0x80). Un programa que escriba mantener como 0xC0 no")
    print("  tiene ningún caso con orden ajena.")
    print("- El vigilante sube BOOT solo con CS_n en alto. La salida cae dentro de una transacción")
    print("  solo si el pin tarda en soltarse más que lo que falta para el tick siguiente. Ese")
    print("  retardo no está documentado y hay que medirlo en la placa.")


if __name__ == "__main__":
    main()
