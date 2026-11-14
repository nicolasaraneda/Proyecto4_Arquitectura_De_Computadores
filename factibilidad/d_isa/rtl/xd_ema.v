// xd_ema.v: paso de media exponencial, rd = rs2 + ((rs1 - rs2) >>> k).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Versión autónoma: tiene su propio restador y su propio sumador. rs1 es la
// muestra y rs2 el estado (la media), los dos en la misma escala. La resta y
// la suma dan la vuelta en 32 bits y el desplazamiento es aritmético:
// equivale a `sub t, rs1, rs2; srai t, t, k; add rd, rs2, t`. Con rs2 = x0 es
// un desplazamiento aritmético de rs1. Combinacional, sin estado.
// Modelo de referencia: ref/xd.py, función ema.
//
// KB elige cuántos valores de k se implementan, que es lo que fija el costo:
//   KB = 0   un solo k, cableado (parámetro K0). k_i no se usa.
//   KB = 2   k entre 4 y 7: se decodifican k_i[1:0] y se supone k_i[4:2] = 001.
//   KB = 3   k entre 0 y 7: se decodifican k_i[2:0] y se supone k_i[4:3] = 00.
//   KB = 5   k entre 0 y 31: desplazador aritmético completo.
//
// MUTA_XD_EMA es una mutación de prueba (tools/tb_modulos.sh): el
// desplazamiento pasa a ser lógico. Solo se activa desde la línea de comandos.

module xd_ema #(
  parameter integer KB = 0,
  parameter integer K0 = 5
) (
  input  wire [31:0] a_i,     // rs1: la muestra, en la misma escala que el estado
  input  wire [31:0] b_i,     // rs2: el estado (la media)
  input  wire [4:0]  k_i,     // funct7[4:0]
  output wire [31:0] r_o
);

  wire signed [31:0] d = a_i - b_i;
  wire signed [31:0] d4 = d >>> 4;
  reg  signed [31:0] sh;

  always @* begin
    case (KB)
      0:       sh = d >>> K0;
      2:       sh = d4 >>> k_i[1:0];
      3:       sh = d >>> k_i[2:0];
      default: sh = d >>> k_i;
    endcase
  end

`ifdef MUTA_XD_EMA
  assign r_o = b_i + (KB == 0 ? ($unsigned(d) >> K0) : $unsigned(sh));
`else
  assign r_o = b_i + sh;
`endif

  wire _unused = &{1'b0, k_i, d4};

endmodule
