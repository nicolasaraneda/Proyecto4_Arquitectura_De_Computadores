// regfile_caja.v: el banco de registros del barrel como caja negra, para la
// prueba de equivalencia de tools/xd/formal.sh.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.

(* blackbox *)
module espino_barrel_regfile (
  input  wire        clk_i,
  input  wire [5:0]  raddr_a_i,
  output wire [31:0] rdata_a_o,
  input  wire [5:0]  raddr_b_i,
  output wire [31:0] rdata_b_o,
  input  wire [5:0]  waddr_i,
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
endmodule
