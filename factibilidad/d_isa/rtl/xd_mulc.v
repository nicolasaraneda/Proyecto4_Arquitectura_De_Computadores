// xd_mulc.v: producto combinacional angosto, sin signo.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// rd = rs1[AW-1:0] * rs2[BW-1:0], extendido con ceros. Un solo ciclo, sin
// estado. El iCE40 HX1K no tiene bloques multiplicadores, así que son BW
// sumas condicionales en lógica. Modelo de referencia: ref/xd.py, función
// mulc.
//
// MUTA_XD_MULC es una mutación de prueba (tools/tb_modulos.sh): pierde el bit
// más alto del multiplicador. Solo se activa desde la línea de comandos.

module xd_mulc #(
  parameter integer AW = 16,   // bits del multiplicando (acciones)
  parameter integer BW = 8     // bits del multiplicador (precio)
) (
  input  wire [31:0] a_i,      // rs1
  input  wire [31:0] b_i,      // rs2
  output wire [31:0] r_o
);

`ifdef MUTA_XD_MULC
  wire [AW+BW-1:0] p = a_i[AW-1:0] * {1'b0, b_i[BW-2:0]};
`else
  wire [AW+BW-1:0] p = a_i[AW-1:0] * b_i[BW-1:0];
`endif
  assign r_o = {{(32-AW-BW){1'b0}}, p};

  wire _unused = &{1'b0, a_i, b_i};

endmodule
