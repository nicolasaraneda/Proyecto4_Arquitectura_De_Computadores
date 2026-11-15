// regfile_abstracto.v: banco de registros sin contenido, para la prueba formal.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Reemplaza a espino_barrel_regfile en tools/barrel/formal.sh. Entrega cualquier
// valor en cada ciclo: las propiedades de formal/propiedades.vh no dependen
// de lo que haya en los registros, así que valen para cualquier contenido.

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
  (* anyseq *) wire [31:0] f_a;
  (* anyseq *) wire [31:0] f_b;
  assign rdata_a_o = f_a;
  assign rdata_b_o = f_b;
  wire _unused = &{1'b0, clk_i, raddr_a_i, raddr_b_i, waddr_i, wdata_i, we_i};
endmodule
