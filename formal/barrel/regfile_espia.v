// regfile_espia.v: banco de registros que devuelve lo que vio en sus puertos.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Reemplaza a espino_barrel_regfile en la tarea "operandos" de
// tools/barrel/formal.sh. No guarda registros. Igual que la BRAM, entrega en el
// ciclo siguiente lo que corresponde a las direcciones del flanco anterior,
// pero en vez del contenido entrega las direcciones mismas:
//   rdata_a_o[5:0]    dirección {hilo, registro} que se leyó por el puerto A
//   rdata_a_o[13:8]   dirección {hilo, registro} que se presentó para escribir
//   rdata_a_o[14]     si esa escritura estaba habilitada
//   rdata_b_o[5:0]    dirección que se leyó por el puerto B
// El resto de los bits queda libre. Con eso las propiedades P10 y P11 de
// formal/propiedades.vh comprueban, desde dentro del core, qué contexto y qué
// registro llegan de verdad al banco.

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
  reg [5:0] ra_q, rb_q, wa_q;
  reg       we_q;
  always @(posedge clk_i) begin
    ra_q <= raddr_a_i;
    rb_q <= raddr_b_i;
    wa_q <= waddr_i;
    we_q <= we_i;
  end
  assign rdata_a_o = {f_a[31:15], we_q, wa_q, f_a[7:6], ra_q};
  assign rdata_b_o = {f_b[31:6], rb_q};
  wire _unused = &{1'b0, wdata_i, f_a[14:8], f_a[5:0], f_b[5:0]};
endmodule
