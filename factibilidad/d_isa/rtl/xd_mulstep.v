// xd_mulstep.v: un paso de multiplicación, rd = (rs1 << 1) + (rs1[31] ? rs2 : 0).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Combinacional, sin estado: el multiplicador y el acumulador viajan juntos en
// rs1, así que no hay registros ocultos que guardar por hilo. El multiplicador
// de n bits se carga en los n bits altos de rs1, con el resto en cero. En
// cada paso sale por arriba su bit más significativo y, si vale 1, se suma el
// multiplicando rs2 al acumulador, que crece desde abajo. Después de n pasos
// rd = multiplicador * rs2, siempre que rs2 < 2^(32 - n).
// Modelo de referencia: ref/xd.py, funciones mulstep y multiplicar.
//
// MUTA_XD_MULSTEP es una mutación de prueba (tools/tb_modulos.sh): mira el bit
// 30 en vez del 31. Solo se activa desde la línea de comandos.

module xd_mulstep (
  input  wire [31:0] a_i,     // rs1: {multiplicador que queda, acumulador}
  input  wire [31:0] b_i,     // rs2: multiplicando
  output wire [31:0] r_o
);

`ifdef MUTA_XD_MULSTEP
  assign r_o = {a_i[30:0], 1'b0} + (a_i[30] ? b_i : 32'b0);
`else
  assign r_o = {a_i[30:0], 1'b0} + (a_i[31] ? b_i : 32'b0);
`endif

endmodule
