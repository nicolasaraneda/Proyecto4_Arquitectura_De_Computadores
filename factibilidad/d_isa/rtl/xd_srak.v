// xd_srak.v: desplazamiento aritmético a la derecha restringido, rd = rs1 >>> k.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es la alternativa barata al paso de media exponencial: con un k cableado no
// tiene lógica propia (son cables) y el paso se escribe con dos instrucciones,
// `srak t, dev, k` y `add S, S, t`, usando el sumador que la ALU ya tiene.
// Combinacional, sin estado. Modelo de referencia: ref/xd.py, función srak.
//
// KB elige cuántos valores de k se implementan, igual que en xd_ema.v:
//   KB = 0   un solo k, cableado (parámetro K0)
//   KB = 2   k entre 4 y 7     KB = 3   k entre 0 y 7     KB = 5   k entre 0 y 31
//
// MUTA_XD_SRAK es una mutación de prueba (tools/tb_modulos.sh): el
// desplazamiento pasa a ser lógico. Solo se activa desde la línea de comandos.

module xd_srak #(
  parameter integer KB = 0,
  parameter integer K0 = 5
) (
  input  wire [31:0] a_i,     // rs1
  input  wire [4:0]  k_i,     // funct7[4:0]
  output wire [31:0] r_o
);

  wire signed [31:0] d  = a_i;
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

`ifdef MUTA_XD_SRAK
  assign r_o = (KB == 0) ? ($unsigned(d) >> K0) : (sh & 32'h7FFFFFFF);
`else
  assign r_o = sh;
`endif

  wire _unused = &{1'b0, k_i, d4};

endmodule
