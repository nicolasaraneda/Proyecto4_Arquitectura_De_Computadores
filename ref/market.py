#!/usr/bin/env python3
"""market.py: mercado de la maestra, porte exacto de tb/tb_proyecto_4.sv.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Este módulo no decide nada: recibe la lista de bytes que la maestra lee en cada
tick y lleva la contabilidad oficial. La tarea `ejecutar` del testbench está
portada línea a línea, incluida la división entera de SystemVerilog, que trunca
hacia cero (la de Python redondea hacia abajo).

El archivo que escribe `escribir_csv` tiene el mismo formato que el
`decisiones.csv` del testbench, byte a byte. Con eso la equivalencia se
comprueba con `cmp`.

Uso como programa, para validar este mercado contra el testbench:

    python3 ref/market.py validar decisiones.csv

Toma la columna `decision` del archivo del testbench, rehace la contabilidad y
exige que caja, acciones y patrimonio coincidan en todas las filas.

Y para hacer la contabilidad de un archivo que solo trae los bytes leídos por
la maestra ("tick,precio,decision", como el de tb/tb_bitstream.sv):

    python3 ref/market.py contabilizar bytes.csv -o decisiones.csv
"""
import sys

CAJA0 = 10000
COMISION = 5

MANTENER = 0x00
COMPRAR_63 = 0x40 | 63      # "quiero estar adentro": la maestra compra lo que alcance
VENDER_63 = 0x80 | 63       # "quiero estar afuera": la maestra vende lo que haya

ENCABEZADO = "tick,precio,decision,caja,acciones,patrimonio"


def div_sv(a, b):
    """División entera de SystemVerilog: trunca hacia cero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def leer_serie(ruta, nticks=None):
    """Lee un CSV "tick,price" y devuelve la lista de precios."""
    with open(ruta) as f:
        next(f)
        precios = [int(linea.split(",")[1]) for linea in f if linea.strip()]
    return precios if nticks is None else precios[:nticks]


class Mercado:
    """Estado de la contabilidad oficial. `ejecutar` es la tarea del testbench."""

    def __init__(self, caja0=CAJA0, comision=COMISION):
        self.caja0 = caja0
        self.comision = comision
        self.caja = caja0
        self.acciones = 0
        self.w = caja0
        self.peak = caja0
        self.max_dd = 0
        self.ordenes = 0

    def ejecutar(self, decision, p):
        q = decision & 63
        accion = (decision >> 6) & 3
        if accion == 1:                                   # comprar lo que alcance
            tope = div_sv(self.caja - self.comision, p)
            if q > tope:
                q = tope
            if q > 0:
                self.caja -= q * p + self.comision
                self.acciones += q
                self.ordenes += 1
        elif accion == 2:                                 # vender lo que se tenga
            if q > self.acciones:
                q = self.acciones
            if q > 0 and self.caja + q * p >= self.comision:
                self.caja += q * p - self.comision
                self.acciones -= q
                self.ordenes += 1
        self.w = self.caja + self.acciones * p            # 00 y 11: mantener
        if self.w > self.peak:
            self.peak = self.w
        if self.peak - self.w > self.max_dd:
            self.max_dd = self.peak - self.w

    @property
    def comisiones(self):
        return self.ordenes * self.comision


def simular(precios, decisiones, caja0=CAJA0, comision=COMISION, filas=None):
    """Ejecuta decisiones[n] al precio precios[n]. Devuelve el Mercado final.

    Si `filas` es una lista, agrega una tupla por tick con las columnas de
    decisiones.csv.
    """
    m = Mercado(caja0, comision)
    for n, (p, d) in enumerate(zip(precios, decisiones)):
        m.ejecutar(d, p)
        if filas is not None:
            filas.append((n, p, d, m.caja, m.acciones, m.w))
    return m


def comprar_y_mantener(precios, caja0=CAJA0, comision=COMISION):
    """Referencia del testbench: compra todo en el tick 0 y no vende."""
    q = div_sv(caja0 - comision, precios[0])
    return caja0 - comision - q * precios[0] + q * precios[-1]


def formatear_csv(filas):
    lineas = [ENCABEZADO]
    lineas += ["%d,%d,%02x,%d,%d,%d" % fila for fila in filas]
    return "\n".join(lineas) + "\n"


def escribir_csv(ruta, filas):
    with open(ruta, "w", newline="\n") as f:
        f.write(formatear_csv(filas))


def leer_csv(ruta):
    """Lee un decisiones.csv. Devuelve tuplas (tick, precio, decision, caja, acciones, patrimonio)."""
    filas = []
    with open(ruta) as f:
        encabezado = f.readline().strip()
        if encabezado != ENCABEZADO:
            raise ValueError(f"{ruta}: encabezado inesperado: {encabezado!r}")
        for linea in f:
            if not linea.strip():
                continue
            c = linea.strip().split(",")
            filas.append((int(c[0]), int(c[1]), int(c[2], 16), int(c[3]), int(c[4]), int(c[5])))
    return filas


def validar(ruta, caja0=CAJA0, comision=COMISION):
    """Rehace la contabilidad de un decisiones.csv del testbench. Devuelve las diferencias."""
    filas_tb = leer_csv(ruta)
    filas = []
    m = simular([f[1] for f in filas_tb], [f[2] for f in filas_tb], caja0, comision, filas)
    diferencias = [(a, b) for a, b in zip(filas_tb, filas) if a != b]
    return len(filas_tb), diferencias, m


def main(argv):
    if len(argv) >= 3 and argv[1] == "validar":
        n, diferencias, m = validar(argv[2])
        print(f"{argv[2]}: {n} filas, {len(diferencias)} diferencias con ref/market.py")
        print(f"patrimonio final {m.w}, {m.ordenes} ordenes, comisiones {m.comisiones}, perdida maxima {m.max_dd}")
        for tb, ref in diferencias[:5]:
            print(f"  testbench {tb}\n  market.py {ref}")
        return 1 if diferencias else 0
    if len(argv) == 5 and argv[1] == "contabilizar" and argv[3] == "-o":
        with open(argv[2]) as f:
            next(f)
            datos = [linea.strip().split(",") for linea in f if linea.strip()]
        filas = []
        m = simular([int(c[1]) for c in datos], [int(c[2], 16) for c in datos], filas=filas)
        escribir_csv(argv[4], filas)
        print(f"{argv[4]}: {len(filas)} filas, patrimonio final {m.w}, {m.ordenes} ordenes")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
