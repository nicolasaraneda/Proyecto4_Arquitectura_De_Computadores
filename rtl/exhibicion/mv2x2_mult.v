// mv2x2_mult.v: producto 2x2 en punto fijo con multiplicadores reales.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Versión para la edición ASIC. Calcula lo mismo que kal2_fijo.v, pero los
// cuatro coeficientes de la matriz son entradas: se pueden cambiar mientras
// el programa corre. Cuesta cuatro multiplicadores de 17 x CW bits.
//
//   d  = (precio << 8) - m
//   dm = (g00 d + g01 u) >>> S
//   un = (g10 d + g11 u) >>> S
//   estado_o = {saturar(un), saturar(m + dm)}
//
// La referencia bit a bit es ref/mv2x2.py y la especificación está en
// docs/producto_2x2.md. Este módulo no forma parte del SoC de competencia:
// vive en rtl/exhibicion/ y no entra en la lista de fuentes del testbench.

module mv2x2_mult #(
  parameter CW = 14,             // ancho de cada coeficiente, con signo
  parameter S  = 12              // bits de fracción de los coeficientes
) (
  input  wire [31:0]          estado_i,   // {u[15:0], m[15:0]}: u con signo Q7.8, m sin signo Q8.8
  input  wire [7:0]           precio_i,
  input  wire signed [CW-1:0] g00_i,
  input  wire signed [CW-1:0] g01_i,
  input  wire signed [CW-1:0] g10_i,
  input  wire signed [CW-1:0] g11_i,
  output wire [31:0]          estado_o
);

  localparam W = 17 + CW + 1;    // ancho de los acumuladores

  wire        [15:0] m = estado_i[15:0];
  wire signed [15:0] u = estado_i[31:16];
  wire signed [16:0] d = $signed({1'b0, precio_i, 8'b0}) - $signed({1'b0, m});

  wire signed [W-1:0] acc0 = g00_i * d + g01_i * u;
  wire signed [W-1:0] acc1 = g10_i * d + g11_i * u;

  wire signed [W-S-1:0] dm = acc0 >>> S;
  wire signed [W-S-1:0] un = acc1 >>> S;

  // m' = m + dm, saturado a [0, 65535]
  wire signed [W-S:0] ms = $signed({1'b0, m}) + dm;
  wire [15:0] m_o = ms[W-S] ? 16'h0000 : (|ms[W-S-1:16] ? 16'hFFFF : ms[15:0]);

  // u' = un, saturado a [-32768, 32767]
  wire u_cabe = (un[W-S-1:15] == {(W-S-15){1'b0}}) | (un[W-S-1:15] == {(W-S-15){1'b1}});
  wire [15:0] u_o = u_cabe ? un[15:0] : {un[W-S-1], {15{~un[W-S-1]}}};

  assign estado_o = {u_o, m_o};

endmodule
