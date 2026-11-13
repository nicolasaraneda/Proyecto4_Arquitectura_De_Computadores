#!/usr/bin/env python3
"""gen_mv2x2.py: genera el producto 2x2 de coeficientes fijos (kal2_fijo.v).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Recibe los parámetros del modelo de dos estados (o directamente phi, k1 y k2),
cuantiza los coeficientes y escribe un módulo combinacional en que cada
producto por una constante es una suma de copias desplazadas de la entrada
(dígitos con signo canónicos). No hay multiplicadores: los desplazamientos son
cables. La semántica exacta está en ref/mv2x2.py.

Dos formas, que calculan lo mismo bit a bit:

  directa      cuatro productos por constante, uno por coeficiente de G.
  factorizada  aprovecha que G = [k1; k2] [1, -phi] + diag(0, phi): calcula la
               innovación e = d - phi u una sola vez. Son tres productos por
               constante (phi, k1 y k2) en vez de cuatro. Sus coeficientes
               quedan con 2C bits de fracción, con C los bits de phi, k1 y k2.

Uso, desde la raíz del repositorio:
    python3 tools/gen_mv2x2.py -o build/mv2x2/kal2_fijo.v
    python3 tools/gen_mv2x2.py --forma directa --s 8 -o build/mv2x2/directa.v
    python3 tools/gen_mv2x2.py --k1 0.03125 --k2 0.5 --phi 0.875 --c 5 -o ...
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ref"))
import mv2x2  # noqa: E402

ENCABEZADO = """\
// {nombre}.v: producto 2x2 en punto fijo con coeficientes fijos.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// ARCHIVO GENERADO por tools/gen_mv2x2.py. No se edita a mano.
//   {comando}
//
// Un paso del estimador de dos estados (nivel m y transitoria u):
//   d  = (precio << 8) - m
//   dm = (g00 d + g01 u) >>> {s}
//   un = (g10 d + g11 u) >>> {s}
//   estado_o = {{saturar(un), saturar(m + dm)}}
// con G x 2^{s} = [{g00} {g01}; {g10} {g11}]  (forma {forma}, {terminos} términos).
// Cada producto es una suma de copias desplazadas de la entrada. La referencia
// bit a bit es ref/mv2x2.py y la especificación está en docs/producto_2x2.md.
"""


class Nodo:
    """Una señal con signo: nombre, rango de valores y si representa el negativo."""

    def __init__(self, nombre, lo, hi, negado=False):
        self.nombre, self.lo, self.hi, self.negado = nombre, lo, hi, negado

    @property
    def ancho(self):
        return max(self.lo.bit_length() if self.lo >= 0 else (-self.lo - 1).bit_length(),
                   self.hi.bit_length() if self.hi >= 0 else (-self.hi - 1).bit_length()) + 1


class Circuito:
    """Arma el camino de datos como sumas de dos operandos con el ancho justo."""

    def __init__(self):
        self.lineas, self.n, self.sumadores, self.bits = [], 0, 0, 0

    def cable(self, lo, hi, expr, comentario="", negado=False):
        self.n += 1
        nodo = Nodo(f"t{self.n}", lo, hi, negado)
        self.lineas.append(f"  wire signed [{nodo.ancho - 1}:0] {nodo.nombre} = {expr};"
                           + (f"   // {comentario}" if comentario else ""))
        return nodo

    def desplazar(self, a, k):
        """a * 2^k: son solo cables."""
        if k == 0:
            return a
        return Nodo(f"({a.nombre} <<< {k})", a.lo << k, a.hi << k, a.negado)

    def sumar(self, a, b, comentario=""):
        """Valor real de a más valor real de b (cada uno puede venir negado)."""
        self.sumadores += 1
        if a.negado == b.negado:
            nodo = self.cable(a.lo + b.lo, a.hi + b.hi, f"{a.nombre} + {b.nombre}", comentario, a.negado)
        elif b.negado:
            nodo = self.cable(a.lo - b.hi, a.hi - b.lo, f"{a.nombre} - {b.nombre}", comentario)
        else:
            nodo = self.cable(b.lo - a.hi, b.hi - a.lo, f"{b.nombre} - {a.nombre}", comentario)
        self.bits += nodo.ancho
        return nodo

    def por_constante(self, x, n, etiqueta):
        """n * x por el método de Horner sobre los dígitos con signo canónicos."""
        if n == 0:
            return None
        digitos = sorted(mv2x2.csd(abs(n)), key=lambda sk: -sk[1])
        acc, k_ant = x, digitos[0][1]                      # el dígito más alto de |n| siempre es +1
        for signo, k in digitos[1:]:
            termino = Nodo(x.nombre, x.lo, x.hi, x.negado != (signo < 0))
            acc = self.sumar(self.desplazar(acc, k_ant - k), termino)
            k_ant = k
        acc = self.desplazar(acc, k_ant)
        if len(digitos) > 1:
            self.lineas[-1] += f"   // {etiqueta}" if "//" not in self.lineas[-1] else ""
        return Nodo(acc.nombre, acc.lo, acc.hi, acc.negado != (n < 0))


def generar(nombre, forma, gi, s, c=None, enteros=None, comando="", saturar=True):
    cto = Circuito()
    u = Nodo("u", -32768, 32767)
    d = Nodo("d", -65535, 65280)
    if forma == "directa":
        filas = []
        for i in (0, 1):
            a = cto.por_constante(d, gi[i][0], f"{gi[i][0]} d")
            b = cto.por_constante(u, gi[i][1], f"{gi[i][1]} u")
            filas.append(cto.sumar(a, b, f"acumulador {i}") if a and b else (a or b))
        acc0, acc1 = filas
    else:
        phi_i, k1_i, k2_i = enteros
        pu = cto.por_constante(u, phi_i, f"{phi_i} u")
        e = cto.sumar(cto.desplazar(d, c), Nodo(pu.nombre, pu.lo, pu.hi, not pu.negado), "innovación e = d - phi u")
        acc0 = cto.por_constante(e, k1_i, f"acumulador 0 = {k1_i} e")
        acc1 = cto.sumar(cto.desplazar(pu, c), cto.por_constante(e, k2_i, f"{k2_i} e"), "acumulador 1")
    for acc in (acc0, acc1):
        if acc is None or acc.negado:
            raise SystemExit("coeficientes no soportados: una fila de la matriz quedó en cero o negada")
    w0, w1 = acc0.ancho - s, acc1.ancho - s
    if w0 < 2 or w1 < 17:
        raise SystemExit("coeficientes demasiado chicos para esta cantidad de bits de fracción")

    terminos = (sum(len(mv2x2.csd(x)) for x in enteros) if forma == "factorizada" else mv2x2.terminos_csd(gi))
    v = [ENCABEZADO.format(nombre=nombre, comando=comando, s=s, forma=forma,
                           g00=gi[0][0], g01=gi[0][1], g10=gi[1][0], g11=gi[1][1], terminos=terminos)]
    v.append(f"""//
// Camino de datos: {cto.sumadores + 2} sumadores de dos operandos ({cto.bits + 17 + w0 + 1} bits en total).

module {nombre} (
  input  wire [31:0] estado_i,   // {{u[15:0], m[15:0]}}: u con signo Q7.8, m sin signo Q8.8
  input  wire [7:0]  precio_i,
  output wire [31:0] estado_o
);

  wire        [15:0] m = estado_i[15:0];
  wire signed [15:0] u = estado_i[31:16];
  wire signed [16:0] d = $signed({{1'b0, precio_i, 8'b0}}) - $signed({{1'b0, m}});

""")
    v.append("\n".join(cto.lineas) + "\n")
    v.append(f"""
  wire signed [{w0 - 1}:0] dm = {acc0.nombre} >>> {s};
  wire signed [{w1 - 1}:0] un = {acc1.nombre} >>> {s};
  wire signed [{max(w0, 17)}:0] ms = $signed({{1'b0, m}}) + dm;   // m' = m + dm
""")
    wm = max(w0, 17) + 1
    if saturar:
        v.append(f"""
  // m' saturado a [0, 65535] y u' saturado a [-32768, 32767]
  wire [15:0] m_o = ms[{wm - 1}] ? 16'h0000 : (|ms[{wm - 2}:16] ? 16'hFFFF : ms[15:0]);
  wire u_cabe = (un[{w1 - 1}:15] == {{{w1 - 15}{{1'b0}}}}) | (un[{w1 - 1}:15] == {{{w1 - 15}{{1'b1}}}});
  wire [15:0] u_o = u_cabe ? un[15:0] : {{un[{w1 - 1}], {{15{{~un[{w1 - 1}]}}}}}};
""")
    else:
        v.append("""
  // Sin saturación: los carriles dan la vuelta (solo para medir cuánto cuesta saturar)
  wire [15:0] m_o = ms[15:0];
  wire [15:0] u_o = un[15:0];
""")
    v.append("""
  assign estado_o = {u_o, m_o};

endmodule
""")
    return "".join(v), cto.sumadores + 2, cto.bits + 17 + w0 + 1


def resolver(a):
    """Devuelve (forma, gi, s, c, enteros) a partir de los argumentos."""
    if a.k1 is not None:
        phi, k1, k2 = a.phi, a.k1, a.k2
    else:
        phi = a.phi
        k1, k2 = mv2x2.ganancia_estacionaria(a.phi, a.q_m, a.q_u, a.r)
    if a.forma == "directa":
        return "directa", mv2x2.cuantizar(mv2x2.matriz(phi, k1, k2), a.s), a.s, None, None
    c = a.c
    phi_i, k1_i, k2_i = (int(round(x * (1 << c))) for x in (phi, k1, k2))
    gi = [[k1_i << c, -k1_i * phi_i], [k2_i << c, phi_i * ((1 << c) - k2_i)]]
    return "factorizada", gi, 2 * c, c, (phi_i, k1_i, k2_i)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera el producto 2x2 de coeficientes fijos")
    ap.add_argument("--forma", choices=("factorizada", "directa"), default="factorizada")
    ap.add_argument("--phi", type=float, default=mv2x2.EJEMPLO["phi"])
    ap.add_argument("--q-m", type=float, default=mv2x2.EJEMPLO["q_m"])
    ap.add_argument("--q-u", type=float, default=mv2x2.EJEMPLO["q_u"])
    ap.add_argument("--r", type=float, default=mv2x2.EJEMPLO["r"])
    ap.add_argument("--k1", type=float, help="fijar las ganancias a mano (con --k2)")
    ap.add_argument("--k2", type=float)
    ap.add_argument("--s", type=int, default=8, help="forma directa: bits de fracción de G")
    ap.add_argument("--c", type=int, default=6, help="forma factorizada: bits de fracción de phi, k1 y k2")
    ap.add_argument("--nombre", default="kal2_fijo")
    ap.add_argument("--sin-saturar", action="store_true", help="carriles sin saturación (solo para medir su costo)")
    ap.add_argument("--matriz", action="store_true", help="solo imprimir 'g00 g01 g10 g11 s'")
    ap.add_argument("-o", "--salida")
    a = ap.parse_args(argv)
    if (a.k1 is None) != (a.k2 is None):
        ap.error("--k1 y --k2 van juntos")

    forma, gi, s, c, enteros = resolver(a)
    if a.matriz:
        print(gi[0][0], gi[0][1], gi[1][0], gi[1][1], s)
        return 0
    comando = "python3 tools/gen_mv2x2.py " + " ".join(argv if argv is not None else sys.argv[1:])
    texto, sumadores, bits = generar(a.nombre, forma, gi, s, c, enteros, comando, not a.sin_saturar)
    print(f"{a.nombre}: forma {forma}, G x 2^{s} = {gi}, {sumadores} sumadores, {bits} bits de suma", file=sys.stderr)
    if a.salida:
        os.makedirs(os.path.dirname(a.salida) or ".", exist_ok=True)
        with open(a.salida, "w", newline="\n") as f:
            f.write(texto)
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
