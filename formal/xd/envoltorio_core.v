// envoltorio_core.v: el core barrel con y sin la extensión, con los mismos
// puertos, para la prueba de equivalencia de tools/xd/formal.sh.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El mismo archivo se lee dos veces. Sin definiciones instancia el core sin la
// extensión (lado de referencia). Con -DLADO_XD=m instancia el core con el
// subconjunto m. Con -DSIN_CUSTOM0, en los dos lados, una palabra de custom-0
// que sale de la memoria se reemplaza por un nop (addi x0, x0, 0) antes de
// entrar al core: así se compara el comportamiento con programas que no usan
// el opcode de la extensión. Con -DCORE_P1 el lado de referencia es el core
// tal como quedó verificado en el paquete P1, que no tenía el parámetro Xd.
//
// El banco de registros es una caja negra en los dos lados
// (regfile_caja.v): el script convierte sus puertos en puertos del
// envoltorio, de modo que lo que el banco entrega es una entrada libre, la
// misma para los dos, y lo que el core le pide se compara.

module w_core (
  input  wire        clk_i,
  input  wire        rst_ni,
  output wire [1:0]  hilo_x_o,
  output wire        instr_req_o,
  output wire [31:0] instr_addr_o,
  input  wire [31:0] instr_rdata_i,
  output wire        data_req_o,
  output wire        data_we_o,
  output wire [3:0]  data_be_o,
  output wire [31:0] data_addr_o,
  output wire [31:0] data_wdata_o,
  input  wire [31:0] data_rdata_i
);
`ifdef SIN_CUSTOM0
  wire [31:0] instr = (instr_rdata_i[6:0] == 7'b0001011) ? 32'h0000_0013 : instr_rdata_i;
`else
  wire [31:0] instr = instr_rdata_i;
`endif

`ifdef LADO_XD
  espino_barrel_core #(.BootAddr(32'h0000_0000), .PcW(11), .Xd(`LADO_XD)) u (
`elsif CORE_P1
  espino_barrel_core #(.BootAddr(32'h0000_0000), .PcW(11)) u (
`else
  espino_barrel_core #(.BootAddr(32'h0000_0000), .PcW(11), .Xd(3'b000)) u (
`endif
    .clk_i(clk_i), .rst_ni(rst_ni), .hilo_x_o(hilo_x_o),
    .instr_req_o(instr_req_o), .instr_addr_o(instr_addr_o), .instr_rdata_i(instr),
    .data_req_o(data_req_o), .data_we_o(data_we_o), .data_be_o(data_be_o),
    .data_addr_o(data_addr_o), .data_wdata_o(data_wdata_o), .data_rdata_i(data_rdata_i));
endmodule
