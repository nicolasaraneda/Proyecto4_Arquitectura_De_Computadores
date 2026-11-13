// envoltorios.v: mismos puertos para el módulo original y para el modificado.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Los usa formal/base_sin_cambios/equiv.sh para probar que, con Pipeline = 0,
// las etapas IF e ID del Espino son lógicamente equivalentes a las del
// repositorio base. Cada envoltorio instancia la etapa con los puertos que
// tenía el módulo original. Los puertos nuevos quedan sin conectar (salidas)
// o en cero (entradas), y los parámetros nuevos en su valor de core base.
// El mismo archivo se lee dos veces: con -DORIGINAL instancia el módulo del
// repositorio base, que no tiene esos puertos ni esos parámetros.

module w_if (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        pc_set_i,
  input  wire [31:0] pc_target_i,
  input  wire        stall_i,
  output wire        instr_req_o,
  output wire [31:0] instr_addr_o,
  output wire [31:0] pc_id_o,
  output wire        instr_valid_id_o
);
`ifdef ORIGINAL
  espino_if_stage #(.BootAddr(32'h0000_0000)) u (
`else
  espino_if_stage #(.BootAddr(32'h0000_0000), .PcW(32), .Pipeline(0)) u (
`endif
    .clk_i(clk_i), .rst_ni(rst_ni), .pc_set_i(pc_set_i), .pc_target_i(pc_target_i), .stall_i(stall_i),
    .instr_req_o(instr_req_o), .instr_addr_o(instr_addr_o), .pc_id_o(pc_id_o),
    .instr_valid_id_o(instr_valid_id_o));
endmodule

module w_id (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        instr_valid_i,
  input  wire [31:0] instr_rdata_i,
  input  wire [31:0] pc_id_i,
  input  wire        stall_i,
  output wire [3:0]  rf_raddr_a_o,
  output wire [3:0]  rf_raddr_b_o,
  input  wire [31:0] rf_rdata_a_i,
  input  wire [31:0] rf_rdata_b_i,
  output wire [3:0]  rf_waddr_o,
  output wire [31:0] rf_wdata_o,
  output wire        rf_we_o,
  output wire        lsu_req_o,
  output wire        lsu_we_o,
  output wire [1:0]  lsu_type_o,
  output wire        lsu_sign_o,
  output wire [31:0] lsu_addr_o,
  output wire [31:0] lsu_wdata_o,
  input  wire [31:0] lsu_rdata_i,
  output wire        branch_taken_o,
  output wire        jump_o,
  output wire [31:0] pc_target_o,
  output wire        rf_ready_o,
  output wire        illegal_insn_o
);
`ifdef ORIGINAL
  espino_id_stage u (
`else
  espino_id_stage #(.Pipeline(0), .PcW(32)) u (
    .instr_next_i(32'b0), .rf_rd_en_o(), .instr_ex_o(),
`endif
    .clk_i(clk_i), .rst_ni(rst_ni), .instr_valid_i(instr_valid_i), .instr_rdata_i(instr_rdata_i),
    .pc_id_i(pc_id_i), .stall_i(stall_i),
    .rf_raddr_a_o(rf_raddr_a_o), .rf_raddr_b_o(rf_raddr_b_o),
    .rf_rdata_a_i(rf_rdata_a_i), .rf_rdata_b_i(rf_rdata_b_i),
    .rf_waddr_o(rf_waddr_o), .rf_wdata_o(rf_wdata_o), .rf_we_o(rf_we_o),
    .lsu_req_o(lsu_req_o), .lsu_we_o(lsu_we_o), .lsu_type_o(lsu_type_o), .lsu_sign_o(lsu_sign_o),
    .lsu_addr_o(lsu_addr_o), .lsu_wdata_o(lsu_wdata_o), .lsu_rdata_i(lsu_rdata_i),
    .branch_taken_o(branch_taken_o), .jump_o(jump_o), .pc_target_o(pc_target_o),
    .rf_ready_o(rf_ready_o), .illegal_insn_o(illegal_insn_o));
endmodule
