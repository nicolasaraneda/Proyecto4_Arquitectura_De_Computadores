#!/usr/bin/env python3
"""controles.py: controles negativos de las pruebas de R3. Cada uno es sw/c1.s o su tabla con un
error puesto a propósito, corrido con la misma comparación que usan las demás pruebas
(tools/c1/caso.py) contra la referencia sin el error. Todos tienen que fallar.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Tres clases de error:
  tabla      una celda o una fila de la tabla cambiada (la referencia usa la tabla buena)
  parámetro  el programa generado con un parámetro distinto (plazo, comisión, caja, mínimo válido,
             largo de la ronda)
  programa   una línea de sw/c1.s cambiada o agregada: la histéresis, el tick en que se activa la
             tabla, el largo de un tramo, la regla del dato viejo (con un dato atrasado), una
             segunda escritura en DECISION, un hilo que escribe la palabra de otro, un store a la
             tabla y un hilo que no es el 0 leyendo el SPI

Cada control corre con tres series: las dos de las pruebas de degradación (la hecha a mano y la
ventana de la serie Meta con motor) y un triángulo que recorre de a un precio todo el rango entre
100 y 255, para que un umbral corrido en uno se note. Está detectado si falla en alguna.

Uso: python3 tools/c1/controles.py CARPETA   (imprime una línea por corrida; lo llama controles.sh)
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path[:0] = [os.path.join(RAIZ, "tools", "c1"), os.path.join(RAIZ, "ref"), os.path.join(RAIZ, "ref", "c1")]
import degradacion    # noqa: E402
import variante       # noqa: E402
import tablas as TB   # noqa: E402

NT = degradacion.NT


def tabla_con(d, nombre, cambio):
    T = list(TB.leer_hex("sw/c1_tabla.hex"))
    cambio(T)
    ruta = f"{d}/{nombre}.tabla.hex"
    with open(ruta, "w", newline="\n") as f:
        f.write("".join(f"{v & 0xFFFF:04x}\n" for v in T))
    return ruta


def cada(T, ini, n, f):
    for i in range(ini, ini + n):
        T[i] = f(T[i])


def programa_con(d, nombre, viejo, nuevo, veces=1):
    s = open("sw/c1.s", encoding="utf-8").read()
    if s.count(viejo) != veces:
        raise SystemExit(f"FAIL: el control {nombre} esperaba {veces} veces '{viejo.strip()}' y hay {s.count(viejo)}")
    ruta = f"{d}/{nombre}.s"
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(s.replace(viejo, nuevo))
    return ruta


def main():
    d = sys.argv[1]
    os.chdir(RAIZ)
    os.makedirs(d, exist_ok=True)
    casos = []      # nombre, argumentos extra, descripción

    def tabla(nombre, cambio, desc):
        casos.append((nombre, ["--tabla", tabla_con(d, nombre, cambio), "--tabla-ref", "sw/c1_tabla.hex"], desc))

    def bajo(v):
        return (v & 0xFF00) | min(255, (v & 0xFF) + 1)

    tabla("tabla_entrada", lambda T: cada(T, TB.T_FASE_A, 128, lambda v: (v & 0xFF00) | max(0, (v & 0xFF) - 1)),
          "tabla: el umbral de entrada de la fase A un precio más abajo en todas las celdas")
    tabla("tabla_salida", lambda T: cada(T, TB.T_FASE_A, 128, lambda v: (min(255, (v >> 8) + 80) << 8) | (v & 0xFF)),
          "tabla: el umbral de salida de la fase A 80 precios más arriba (tope 255)")
    tabla("tabla_motor", lambda T: cada(T, TB.T_MOTOR, 192, bajo), "tabla: el nivel de compra del motor un precio más arriba en todas las celdas")
    tabla("tabla_n64", lambda T: cada(T, TB.T_N64, 7, lambda v: v + 6), "tabla: los siete umbrales de la clase de v^2 corridos")
    tabla("tabla_cuad", lambda T: cada(T, TB.T_CUAD64 + 1, 1, lambda v: v + 64), "tabla: 64 d^2 mal para d = 1")
    tabla("tabla_banda_compra", lambda T: cada(T, TB.T_BANDA_COMPRA, 1, lambda v: v + 1), "tabla: la banda 40 compra un precio más arriba")
    tabla("tabla_banda_venta", lambda T: cada(T, TB.T_BANDA_VENTA, 1, lambda v: v - 1), "tabla: la banda 40 vende un precio más abajo")
    tabla("tabla_apagada", lambda T: cada(T, TB.T_POLITICA, 1, lambda v: 0), "tabla: la política apagada (la referencia la espera encendida)")

    for nombre, opcion, desc in (("par_plazo", ["--plazo", "8"], "parámetro: plazo de 8 vueltas, la política no alcanza a llegar"),
                                 ("par_comision", ["--comision", "4"], "parámetro: las cuentas emuladas con comisión 4"),
                                 ("par_caja", ["--caja", "9999"], "parámetro: las cuentas emuladas parten con caja 9999"),
                                 ("par_p_min", ["--p-min", "101"], "parámetro: precio mínimo válido 101 (el 100 dispara el modo seguro)"),
                                 ("par_n_ronda", ["--n-ronda", "2000"], "parámetro: ronda supuesta de 2000 ticks"),
                                 ("par_m", ["--m", "400"], "parámetro: candado con D >= 400")):
        subprocess.run([sys.executable, "tools/c1/generar.py", *opcion, "-o", f"{d}/{nombre}"], check=True, stdout=subprocess.DEVNULL)
        casos.append((nombre, ["--asm", f"{d}/{nombre}/c1.s"], desc))

    def prog(nombre, viejo, nuevo, desc, extra=(), veces=1):
        casos.append((nombre, ["--asm", programa_con(d, nombre, viejo, nuevo, veces)] + list(extra), desc))

    prog("prog_histeresis", ".equ HISTERESIS,    64", ".equ HISTERESIS,    64\n.equ CONTROL, 1", "(sin cambio: comprueba que el control en blanco pasa)")
    prog("prog_hist_63", "    addi x14, x13, -64\n", "    addi x14, x13, -40\n", "programa: histéresis de la clase de 40 ticks en vez de 64")
    prog("prog_t_min", "D_CMIN:     .word 389", "D_CMIN:     .word 300", "programa: la tabla se activa en el tick 301")
    prog("prog_largo_a", ".equ LARGO_A,       1250", ".equ LARGO_A,       1000", "programa: tramos de la fase A de 1000 ticks")
    prog("prog_largo_m", ".equ LARGO_M,       2500", ".equ LARGO_M,       500", "programa: tramos del motor de 500 ticks")
    prog("prog_dos_decisiones", "    sw   x6, OFF_DECISION(x2)\n", "    sw   x6, OFF_DECISION(x2)\n    sw   x6, OFF_DECISION(x2)\n",
         "programa: el hilo 0 escribe DECISION dos veces por tick")
    prog("prog_dos_escritores", "#@HILO2\n", "#@HILO2\n    sw   x14, D_REGA(x0)\n", "programa: el hilo 2 escribe una palabra del hilo 1")
    prog("prog_store_tabla", "#@HILO2\n", "#@HILO2\n    sw   x14, T_POLITICA(x1)\n", "programa: el hilo 2 hace un store a la tabla")
    prog("prog_spi_hilo1", "#@HILO1\n", "#@HILO1\n    li   x15, SPI_BASE\n    lw   x15, OFF_STATUS(x15)\n", "programa: el hilo 1 lee el SPI")
    prog("prog_clon", "    sw   x10, D_QC(x0)", "    sw   x0, D_QC(x0)", "programa: el clon nunca recibe órdenes")
    prog("prog_candado", "D_M:        .word 100 ", "D_M:        .word 5000", "programa: el candado no llega nunca (M 5000)")
    # la regla del dato viejo solo se ve con un dato atrasado: se corre con la falla tarde2 del motor
    casos_deg = {l.split("|")[0]: l.split("|")[1] for l in open(f"{d}/deg/casos.txt")}
    tm = int(casos_deg["tarde2_motor"].split("--tardias ")[1])
    fuente = open("sw/c1.s", encoding="utf-8").read()
    viejo = "    addi x14, x14, -63\n"
    if fuente.count(viejo) != 1:
        raise SystemExit("FAIL: el control prog_dato_viejo no encuentra la regla")
    with open(f"{d}/prog_dato_viejo.s", "w", encoding="utf-8", newline="\n") as f:
        f.write(variante.armar(fuente.replace(viejo, "    addi x14, x14, -62\n"), variante.leer(f"atraso:2:{tm}:150")))
    casos.append(("prog_dato_viejo", ["--asm", f"{d}/prog_dato_viejo.s", "--tardias", str(tm)],
                  "programa: con el dato atrasado no sostiene la orden completa (la regla compara con 62)"))

    # triángulo: 180 sube a 255, baja a 100 y vuelve, de a un precio cada dos ticks
    tri, p, paso = [], 180, 1
    while len(tri) < NT:
        tri += [p, p]
        if p + paso > 255 or p + paso < 100:
            paso = -paso
        p += paso
    import series
    series.escribir_csv(f"{d}/deg/triangulo.csv", tri[:NT])
    for nombre, extra, desc in casos:
        for serie in ("mano", "motor", "triangulo"):
            print(f"{nombre}|{serie}|--serie {d}/deg/{serie}.csv --nticks {NT} --inicio-ns 200000 {' '.join(extra)}|{desc}")


if __name__ == "__main__":
    main()
