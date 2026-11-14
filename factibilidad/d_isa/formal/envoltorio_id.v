// envoltorio_id.v: la etapa ID del Espino con sus parámetros fijos, para comparar
// la del repositorio con la copia que lleva la extensión de la ISA.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Lo usa tools/core_sin_cambios.sh con los pases equiv_* de Yosys, el mismo
// método de formal/base_sin_cambios del repositorio. El archivo se lee dos
// veces, una con la etapa ID del repositorio (rtl/) y otra con la de la copia
// (factibilidad/d_isa/core). Las definiciones PIPE y PCW fijan el core: 0 y 32
// para el Espino base, 1 y 11 para el segmentado.
//
// Con SANEAR = 1 una instrucción de custom-0 (opcode 0001011) se reemplaza por
// un nop antes de entrar a la etapa, en los dos lados. Así se compara el
// comportamiento con todas las demás instrucciones cuando la copia tiene la
// extensión encendida: lo que se prueba es que agregar la extensión no cambia
// ninguna instrucción de RV32E.

module w_id (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        instr_valid_i,
  input  wire [31:0] instr_rdata_i,
  input  wire [31:0] instr_next_i,
  input  wire [31:0] pc_id_i,
  input  wire        stall_i,
  output wire [3:0]  rf_raddr_a_o,
  output wire [3:0]  rf_raddr_b_o,
  output wire        rf_rd_en_o,
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
  output wire [31:0] instr_ex_o,
  output wire        illegal_insn_o
);

  localparam [31:0] NOP = 32'h0000_0013;       // addi x0, x0, 0
  wire [31:0] instr  = (`SANEAR != 0 && instr_rdata_i[6:0] == 7'h0b) ? NOP : instr_rdata_i;
  wire [31:0] instrn = (`SANEAR != 0 && instr_next_i[6:0]  == 7'h0b) ? NOP : instr_next_i;

  espino_id_stage #(.Pipeline(`PIPE), .PcW(`PCW)) u (
    .clk_i(clk_i), .rst_ni(rst_ni), .instr_valid_i(instr_valid_i),
    .instr_rdata_i(instr), .instr_next_i(instrn), .pc_id_i(pc_id_i), .stall_i(stall_i),
    .rf_raddr_a_o(rf_raddr_a_o), .rf_raddr_b_o(rf_raddr_b_o), .rf_rd_en_o(rf_rd_en_o),
    .rf_rdata_a_i(rf_rdata_a_i), .rf_rdata_b_i(rf_rdata_b_i),
    .rf_waddr_o(rf_waddr_o), .rf_wdata_o(rf_wdata_o), .rf_we_o(rf_we_o),
    .lsu_req_o(lsu_req_o), .lsu_we_o(lsu_we_o), .lsu_type_o(lsu_type_o), .lsu_sign_o(lsu_sign_o),
    .lsu_addr_o(lsu_addr_o), .lsu_wdata_o(lsu_wdata_o), .lsu_rdata_i(lsu_rdata_i),
    .branch_taken_o(branch_taken_o), .jump_o(jump_o), .pc_target_o(pc_target_o),
    .rf_ready_o(rf_ready_o), .instr_ex_o(instr_ex_o), .illegal_insn_o(illegal_insn_o));

endmodule
