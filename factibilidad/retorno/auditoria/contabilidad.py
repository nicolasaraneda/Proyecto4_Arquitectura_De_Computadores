#!/usr/bin/env python3
"""contabilidad.py: comprobación independiente de la contabilidad del arnés de retorno.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Compara cuatro contabilidades con los mismos flujos de órdenes, tick por tick:

  propia     escrita aquí desde las reglas de mercado del enunciado (sección
             2.4), sin mirar el evaluador del arnés;
  market     ref/market.py;
  arnes      el comando `mercado` de build/retorno (cuenta_ejecutar, en C);
  testbench  la tarea `ejecutar` copiada textual de tb/tb_proyecto_4.sv a un
             banco de pruebas mínimo y simulada con Icarus. Es la contabilidad
             oficial, con la aritmética de SystemVerilog.

Los flujos son casos de borde escritos a mano (caja justa, precio 1 y 255,
cantidad 0, acción 11, ventas sin acciones, caja menor que la comisión,
primer y único tick) y flujos al azar con distintas cajas y comisiones.

    python3 auditoria/contabilidad.py            (desde factibilidad/retorno)

Necesita iverilog y vvp en el PATH y build/retorno compilado.
"""
import os
import random
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(RETORNO))
BUILD = os.path.join(RETORNO, "build", "auditoria")
TB = os.path.join(RAIZ, "tb", "tb_proyecto_4.sv")
ARNES = os.path.join(RETORNO, "build", "retorno")

sys.path.insert(0, os.path.join(RAIZ, "ref"))
import market        # noqa: E402


# ---- Contabilidad propia, desde el enunciado -------------------------------------
# Enunciado 2.4: una compra de q acciones cuesta q*p + C; si la caja no alcanza
# se compra el máximo posible. Una venta entrega q*p - C y no puede superar las
# acciones que se tienen. No hay deuda. W = caja + acciones * p.
# Enunciado 2.3: acción 00 mantener, 01 comprar, 10 vender, 11 se trata como
# mantener; cantidad en los 6 bits bajos.

class Propia:
    def __init__(self, caja0, comision):
        self.caja, self.acc, self.com = caja0, 0, comision
        self.ordenes, self.w, self.maximo, self.caida = 0, caja0, caja0, 0

    def tick(self, byte, p):
        accion, q = byte >> 6, byte & 0x3F
        if accion == 0b01:
            # lo máximo que se puede pagar dejando la comisión: sin deuda
            alcanza = 0 if self.caja < self.com else (self.caja - self.com) // p
            q = min(q, alcanza)
            if q >= 1:
                self.caja -= q * p + self.com
                self.acc += q
                self.ordenes += 1
        elif accion == 0b10:
            q = min(q, self.acc)
            # la venta no puede dejar la caja negativa (comisión mayor que lo que entra)
            if q >= 1 and self.caja + q * p - self.com >= 0:
                self.caja += q * p - self.com
                self.acc -= q
                self.ordenes += 1
        self.w = self.caja + self.acc * p
        self.maximo = max(self.maximo, self.w)
        self.caida = max(self.caida, self.maximo - self.w)
        return (self.caja, self.acc, self.w, self.ordenes, self.caida)


# ---- Flujos -------------------------------------------------------------------------

def casos_de_borde():
    """Lista de (nombre, caja0, comision, [(precio, byte), ...])."""
    C, V, M, X = 0x40, 0x80, 0x00, 0xC0
    casos = []
    # caja justa: alcanza exacto para q acciones, y un peso menos
    for q, p in [(1, 1), (1, 255), (7, 13), (39, 255), (63, 1), (63, 158), (63, 255)]:
        casos.append((f"caja justa para {q} a {p}", q * p + 5, 5, [(p, C | q), (p, V | 63)]))
        casos.append((f"falta 1 para {q} a {p}", q * p + 4, 5, [(p, C | q), (p, V | 63)]))
        casos.append((f"sobra 1 para {q} a {p}", q * p + 6, 5, [(p, C | q), (p, C | 63), (p, V | 63)]))
    # cantidad 0 en compra y en venta, con y sin acciones
    casos.append(("cantidad 0", 10000, 5, [(100, C | 0), (100, V | 0), (100, C | 5), (100, V | 0), (100, C | 0)]))
    # acción 11 con todas las cantidades: nunca opera
    casos.append(("accion 11", 10000, 5, [(100, C | 10)] + [(100 + (q % 7), X | q) for q in range(64)]))
    # venta sin acciones y venta de más de lo que hay
    casos.append(("venta sin acciones", 10000, 5, [(50, V | 63), (50, V | 1), (50, C | 3), (60, V | 63), (60, V | 63)]))
    # caja menor que la comisión: (caja - C) / p es negativo en el testbench
    for caja in (0, 1, 3, 4, 5, 6):
        casos.append((f"caja {caja} con comision 5", caja, 5, [(p, C | 63) for p in (1, 2, 3, 255)]))
    # venta que no cubre la comisión: caja 0, una acción, precio menor que la comisión
    casos.append(("venta que no cubre la comision", 6, 5,
                  [(1, C | 63), (1, V | 63), (3, V | 63), (4, V | 63), (5, V | 63), (5, V | 63)]))
    casos.append(("venta que no cubre la comision 50", 60, 50,
                  [(2, C | 63), (2, V | 63), (9, V | 63), (10, V | 63), (10, V | 63)]))
    # precio 1 y 255 con todas las cantidades
    for p in (1, 255):
        casos.append((f"precio {p}, todas las cantidades", 10000, 5,
                      [(p, C | q) for q in range(64)] + [(p, V | q) for q in range(64)]))
    # comisión 0 y comisión 50, caja 1000 y 100 000
    for caja, com in [(1000, 0), (1000, 50), (100000, 0), (100000, 50), (100000, 5)]:
        casos.append((f"caja {caja}, comision {com}", caja, com,
                      [(1, C | 63)] * 5 + [(255, V | 63)] * 5 + [(255, C | 63)] * 5 + [(1, V | 63)] * 5))
    # un solo tick (primer tick igual a último tick) con cada acción
    for b in (M, C | 63, V | 63, X | 63):
        casos.append((f"un solo tick, byte {b:02x}", 10000, 5, [(158, b)]))
    # todos los bytes posibles sobre una cuenta con caja y acciones
    casos.append(("los 256 bytes", 10000, 5, [(100, C | 40)] + [(97 + (b % 11), b) for b in range(256)]))
    return casos


def flujos_al_azar(cuantos, rng):
    practica = market.leer_serie(os.path.join(RAIZ, "tb", "practica.csv"))
    flujos = []
    for k in range(cuantos):
        caja = rng.choice([6, 10, 100, 1000, 10000, 10000, 10000, 100000, rng.randint(0, 100000)])
        com = rng.choice([0, 1, 5, 5, 5, 50, rng.randint(0, 50)])
        n = rng.choice([1, 2, 3, 50, 500, 2000, rng.randint(1, 3000)])
        forma = k % 6
        if forma == 0:                       # precios uniformes
            precios = [rng.randint(1, 255) for _ in range(n)]
        elif forma == 1:                     # paseo con rebote
            p, precios = rng.randint(1, 255), []
            for _ in range(n):
                p = min(255, max(1, p + rng.choice([-3, -2, -1, 0, 0, 1, 2, 3])))
                precios.append(p)
        elif forma == 2:                     # pegada al precio 1
            precios = [rng.choice([1, 1, 1, 2, 3]) for _ in range(n)]
        elif forma == 3:                     # pegada al precio 255
            precios = [rng.choice([255, 255, 254, 253]) for _ in range(n)]
        elif forma == 4:                     # un tramo de la serie de práctica
            i = rng.randrange(len(practica) - n)
            precios = practica[i:i + n]
        else:                                # salta entre los extremos
            precios = [rng.choice([1, 255, rng.randint(1, 255)]) for _ in range(n)]
        estilo = rng.randrange(4)
        if estilo == 0:                      # cualquier byte
            bytes_ = [rng.randrange(256) for _ in range(n)]
        elif estilo == 1:                    # posición objetivo, como la regla base
            bytes_, dentro = [], False
            for _ in range(n):
                if rng.random() < 0.05:
                    dentro = not dentro
                bytes_.append(0x7F if dentro else 0xBF)
        elif estilo == 2:                    # órdenes chicas y frecuentes
            bytes_ = [rng.choice([0x40, 0x80]) | rng.randint(0, 12) for _ in range(n)]
        else:                                # mezcla con muchas mantener y acción 11
            bytes_ = [rng.choice([0x00, 0x00, 0xC0 | rng.randrange(64), 0x40 | rng.randrange(64),
                                  0x80 | rng.randrange(64)]) for _ in range(n)]
        flujos.append((f"azar {k}", caja, com, list(zip(precios, bytes_))))
    return flujos


# ---- Las otras tres contabilidades ---------------------------------------------------

def con_market(flujos):
    filas = []
    for _, caja, com, ticks in flujos:
        m = market.Mercado(caja, com)
        for p, b in ticks:
            m.ejecutar(b, p)
            filas.append((m.caja, m.acciones, m.w, m.ordenes, m.max_dd))
    return filas


def con_arnes(flujos):
    lineas = []
    for _, caja, com, ticks in flujos:
        lineas.append(f"R {caja} {com}")
        lineas += [f"{p} {b}" for p, b in ticks]
    r = subprocess.run([ARNES, "mercado"], input="\n".join(lineas) + "\n", capture_output=True, text=True, check=True)
    return [tuple(int(x) for x in linea.split()) for linea in r.stdout.splitlines()]


def tarea_del_testbench():
    """Las líneas de la tarea `ejecutar`, textuales, y su posición en el archivo."""
    with open(TB) as f:
        lineas = f.read().split("\n")
    ini = next(i for i, x in enumerate(lineas) if "task automatic ejecutar" in x)
    fin = next(i for i in range(ini, len(lineas)) if "endtask" in lineas[i])
    return lineas[ini:fin + 1], ini + 1, fin + 1


def con_testbench(flujos):
    os.makedirs(BUILD, exist_ok=True)
    tarea, ini, fin = tarea_del_testbench()
    entrada = os.path.join(BUILD, "flujos.txt")
    salida = os.path.join(BUILD, "flujos_tb.txt")
    with open(entrada, "w") as f:
        for _, caja, com, ticks in flujos:
            f.write(f"0 {caja} {com}\n")
            for p, b in ticks:
                f.write(f"1 {p} {b}\n")
    banco = f"""// Banco minimo generado por auditoria/contabilidad.py. La tarea `ejecutar`
// es copia textual de tb/tb_proyecto_4.sv, lineas {ini} a {fin}.
`timescale 1ns/1ps
module tb_ejecutar;
  int COMISION = 5;
  int caja, acciones, w, peak, max_dd, ordenes;

{chr(10).join(tarea)}

  int fd, fo, r, tipo, a, b;
  initial begin
    fd = $fopen("{entrada}", "r");
    fo = $fopen("{salida}", "w");
    while ($fscanf(fd, "%d %d %d\\n", tipo, a, b) == 3) begin
      if (tipo == 0) begin
        caja = a; COMISION = b; acciones = 0; w = a; peak = a; max_dd = 0; ordenes = 0;
      end else begin
        ejecutar(b[7:0], a);
        $fdisplay(fo, "%0d %0d %0d %0d %0d", caja, acciones, w, ordenes, max_dd);
      end
    end
    $fclose(fd); $fclose(fo);
    $finish;
  end
endmodule
"""
    fuente = os.path.join(BUILD, "tb_ejecutar.sv")
    with open(fuente, "w") as f:
        f.write(banco)
    binario = os.path.join(BUILD, "tb_ejecutar.vvp")
    subprocess.run(["iverilog", "-g2012", "-s", "tb_ejecutar", "-o", binario, fuente], check=True)
    subprocess.run(["vvp", "-n", binario], check=True, capture_output=True)
    with open(salida) as f:
        return [tuple(int(x) for x in linea.split()) for linea in f], ini, fin


def main():
    rng = random.Random(20261114)
    borde = casos_de_borde()
    azar = flujos_al_azar(600, rng)
    flujos = borde + azar
    propia, ordenes_borde, ordenes_total = [], 0, 0
    for k, (_, caja, com, ticks) in enumerate(flujos):
        c = Propia(caja, com)
        for p, b in ticks:
            propia.append(c.tick(b, p))
        ordenes_total += c.ordenes
        if k < len(borde):
            ordenes_borde += c.ordenes
    otras = {"ref/market.py": con_market(flujos), "arnes (comando mercado)": con_arnes(flujos)}
    tb, ini, fin = con_testbench(flujos)
    otras[f"testbench (tarea ejecutar, lineas {ini} a {fin}, Icarus)"] = tb

    nticks = len(propia)
    print("Auditoria de la contabilidad: cuatro implementaciones con los mismos flujos")
    print(f"Flujos: {len(borde)} casos de borde y {len(azar)} al azar, {nticks} ticks y {ordenes_total} ordenes ejecutadas "
          f"en total ({ordenes_borde} en los casos de borde).")
    print("Columnas comparadas en cada tick: caja, acciones, patrimonio, ordenes ejecutadas y perdida maxima.")
    mal = 0
    for nombre, filas in otras.items():
        if len(filas) != nticks:
            print(f"FAIL  propia contra {nombre}: {len(filas)} filas en vez de {nticks}")
            mal += 1
            continue
        dif = [i for i in range(nticks) if filas[i] != propia[i]]
        print(f"{'PASS' if not dif else 'FAIL'}  propia contra {nombre}: {nticks} ticks, {len(dif)} filas distintas")
        for i in dif[:5]:
            print(f"      tick {i}: propia {propia[i]}  otra {filas[i]}")
        mal += bool(dif)

    # Casos de borde, con el resultado que dan las cuatro (para leerlos)
    print("\nCasos de borde (caja inicial, comision; por tick: precio, byte -> caja, acciones, ordenes):")
    i = 0
    for nombre, caja, com, ticks in borde:
        if len(ticks) <= 6:
            pasos = "  ".join(f"p={p} {b:02x}->{propia[i + j][0]},{propia[i + j][1]},{propia[i + j][3]}" for j, (p, b) in enumerate(ticks))
            print(f"  {nombre:36s} caja {caja:6d} com {com:2d} | {pasos}")
        else:
            ult = propia[i + len(ticks) - 1]
            print(f"  {nombre:36s} caja {caja:6d} com {com:2d} | {len(ticks)} ticks, final: caja {ult[0]}, acciones {ult[1]}, "
                  f"patrimonio {ult[2]}, ordenes {ult[3]}")
        i += len(ticks)
    cajas_neg = sum(1 for f in propia if f[0] < 0)
    acc_neg = sum(1 for f in propia if f[1] < 0)
    print(f"\nCaja negativa en {cajas_neg} ticks y acciones negativas en {acc_neg} ticks (debe ser 0 y 0: no hay deuda ni venta en corto).")
    mal += cajas_neg + acc_neg
    print("PASS: la contabilidad del arnes es la del testbench" if not mal else "FAIL")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
