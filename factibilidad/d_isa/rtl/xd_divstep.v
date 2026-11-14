// xd_divstep.v: un paso de división con restauración, cociente de 8 bits.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Combinacional, sin estado. rs1 = {R, Q} con R en los 24 bits altos y Q en
// los 8 bajos, y el divisor es D = rs2[23:0]. El paso desplaza {R, Q} un bit a
// la izquierda y, si el R nuevo es mayor o igual que D, le resta D y pone un 1
// en el bit bajo. Partiendo de rs1 = N con N < 256 * D, después de 8 pasos
// Q = N div D y R = N mod D.
// Modelo de referencia: ref/xd.py, funciones divstep y dividir.
//
// MUTA_XD_DIVSTEP es una mutación de prueba (tools/tb_modulos.sh): compara con
// mayor estricto en vez de mayor o igual. Solo se activa desde la línea de
// comandos.

module xd_divstep (
  input  wire [31:0] a_i,     // rs1: {resto parcial, cociente parcial}
  input  wire [31:0] b_i,     // rs2: divisor en los bits 23:0
  output wire [31:0] r_o
);

  wire [24:0] r  = a_i[31:7];                          // R desplazado, 25 bits
  wire [25:0] t  = {1'b0, r} - {2'b0, b_i[23:0]};
`ifdef MUTA_XD_DIVSTEP
  wire        ge = ~t[25] & (t[24:0] != 25'b0);
`else
  wire        ge = ~t[25];                             // r >= D
`endif

  assign r_o = ge ? {t[23:0], a_i[6:0], 1'b1} : {a_i[30:0], 1'b0};

  wire _unused = &{1'b0, b_i[31:24], t[24]};

endmodule
