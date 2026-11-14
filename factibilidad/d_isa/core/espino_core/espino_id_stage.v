// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Course: Arquitectura de Computadores (2026)
//
// Authors:
// - Nicolás Villegas <navillegas@miuandes.cl>
//
// Modificado para el Proyecto 4 por Nicolás Araneda, Vicente Calderón y
// Santiago Muñoz (docs/espino_segmentado.md). El diseño viene del core con
// lectura anticipada (EarlyRead) de nuestro Proyecto 3.
//   - Pipeline = 0: el módulo original. Cada instrucción espera un ciclo
//     (ops_valid_q) mientras el banco de registros lee sus operandos.
//   - Pipeline != 0: pipeline de 3 etapas. La instrucción llega por
//     instr_next_i antes del flanco en que entra a ejecución. En ese flanco
//     se registran su decodificación y sus operandos (el banco lee con las
//     direcciones de instr_next_i), así que no hay ciclo de espera.
//   - PcW: bits del contador de programa que se implementan.
//   - MUTA_LOADUSE: mutación de prueba, solo desde la línea de comandos.
//
// Copia para el estudio de factibilidad de la extensión de la ISA
// (factibilidad/d_isa). Cambios respecto a rtl/espino_core/espino_id_stage.v:
//   - Las definiciones XD_EMA, XD_SRAK, XD_SIMD, XD_MULSTEP, XD_DIVSTEP y
//     XD_MULC, que se pasan por la línea de comandos, eligen qué instrucciones
//     de custom-0 se incluyen. Sin ninguna, el módulo es el original.
//   - XD_EMAALU (junto con XD_EMA) y XD_MULSTEPALU son las integraciones que
//     comparten la ALU: el paso de media exponencial usa la resta de la ALU, y
//     mulstep usa su sumador con el operando A desplazado un bit (selección 3
//     del multiplexor del operando A) y el operando B anulado si rs1[31] = 0.
//   - XD_EMAD y XD_DEVK (con el conjunto de k como valor: 0, 2, 3 o 5)
//     agregan emad y devk, que también usan el sumador de la ALU con el
//     operando A desplazado. El operando sale de xd_opa.
//   - XD_SIMDALU (máscara: 4 saturadas, 8 pbcast8) pone los carriles en el
//     sumador de la ALU: se instancia xd_alu en vez de espino_alu y el
//     decodificador entrega lane_op.
//   - Se instancia xd_unit con los operandos que entrega el banco de
//     registros y su resultado entra al multiplexor de escritura. En el
//     pipeline la marca is_xd se registra junto con el resto de la
//     decodificación.

module espino_id_stage #(
  parameter integer Pipeline = 0,
  parameter integer PcW      = 32
) (
  input  wire        clk_i,
  input  wire        rst_ni,

  input  wire        instr_valid_i,
  input  wire [31:0] instr_rdata_i,   // instrucción en ejecución (Pipeline = 0)
  input  wire [31:0] instr_next_i,    // instrucción que entra en el próximo flanco (Pipeline != 0)
  input  wire [31:0] pc_id_i,
  input  wire        stall_i,

  // Register file
  output wire [3:0]  rf_raddr_a_o,
  output wire [3:0]  rf_raddr_b_o,
  output wire        rf_rd_en_o,
  input  wire [31:0] rf_rdata_a_i,
  input  wire [31:0] rf_rdata_b_i,
  output wire [3:0]  rf_waddr_o,
  output reg  [31:0] rf_wdata_o,
  output wire        rf_we_o,

  // LSU control
  output wire        lsu_req_o,
  output wire        lsu_we_o,
  output wire [1:0]  lsu_type_o,
  output wire        lsu_sign_o,
  output wire [31:0] lsu_addr_o,
  output wire [31:0] lsu_wdata_o,
  input  wire [31:0] lsu_rdata_i,

  // Control transfer
  output wire        branch_taken_o,
  output wire        jump_o,
  output wire [31:0] pc_target_o,

  // Sync-read handshake to controller
  output wire        rf_ready_o,

  // Instrucción en ejecución. Solo la miran los testbenches.
  output wire [31:0] instr_ex_o,

  output wire        illegal_insn_o
);

  localparam [1:0] OP_A_PC   = 2'd1;
  localparam [1:0] OP_A_ZERO = 2'd2;
  localparam [1:0] OP_A_XD   = 2'd3;   // operando A desplazado (xd_opa): mulstep, emad y devk
  localparam       OP_B_IMM  = 1'b1;
  localparam [1:0] WD_LSU    = 2'd1;
  localparam [1:0] WD_PC4    = 2'd2;

  // Extensión en custom-0: qué se incluye (ver rtl/xd_unit.v)
`ifdef XD_EMA
  localparam integer XdEmaKb = `XD_EMA;
`else
  localparam integer XdEmaKb = -1;
`endif
`ifdef XD_SRAK
  localparam integer XdSrakKb = `XD_SRAK;
`else
  localparam integer XdSrakKb = -1;
`endif
`ifdef XD_SIMD
  localparam integer XdSimd = `XD_SIMD;
`else
  localparam integer XdSimd = -1;
`endif
`ifdef XD_MULSTEP
  localparam integer XdMulstep = 1;
`else
  localparam integer XdMulstep = 0;
`endif
`ifdef XD_DIVSTEP
  localparam integer XdDivstep = 1;
`else
  localparam integer XdDivstep = 0;
`endif
`ifdef XD_MULC
  localparam integer XdMulcAw = `XD_MULC;
`else
  localparam integer XdMulcAw = 0;
`endif
`ifdef XD_EMAALU
  localparam integer XdEmaAlu = 1;
`else
  localparam integer XdEmaAlu = 0;
`endif
`ifdef XD_MULSTEPALU
  localparam integer XdMulAlu = 1;
`else
  localparam integer XdMulAlu = 0;
`endif
`ifdef XD_EMAD
  localparam integer XdEmadKb = `XD_EMAD;
`else
  localparam integer XdEmadKb = -1;
`endif
`ifdef XD_DEVK
  localparam integer XdDevkKb = `XD_DEVK;
`else
  localparam integer XdDevkKb = -1;
`endif
`ifdef XD_SIMDALU
  localparam integer XdLanes = `XD_SIMDALU;
`else
  localparam integer XdLanes = -1;
`endif
  localparam integer XdBcastAlu = (XdLanes >= 0 && (XdLanes & 8) != 0) ? 1 : 0;
  localparam integer XdOpa = (XdMulAlu != 0 || XdEmadKb >= 0 || XdDevkKb >= 0 || XdBcastAlu != 0) ? 1 : 0;
  localparam [7:0] XdF3 = {4'b0,
                           (XdSrakKb >= 0) ? 1'b1 : 1'b0,
                           (XdMulstep != 0 || XdDivstep != 0 || XdMulcAw != 0) ? 1'b1 : 1'b0,
                           (XdSimd >= 0) ? 1'b1 : 1'b0,
                           (XdEmaKb >= 0) ? 1'b1 : 1'b0};

  wire advance = ~stall_i;

  // Instrucción que se decodifica y cuyos registros se piden al banco
  wire [31:0] dec_instr = (Pipeline != 0) ? instr_next_i : instr_rdata_i;

  // Register addresses
  assign rf_raddr_a_o = dec_instr[18:15];
  assign rf_raddr_b_o = dec_instr[23:20];

  // Decode
  wire [3:0]  alu_operator_d;
  wire [1:0]  alu_op_a_sel_d;
  wire        alu_op_b_sel_d;
  wire [31:0] imm_operand_d, imm_target_d;
  wire        rf_we_dec_d;
  wire [1:0]  rf_wd_sel_d;
  wire        is_branch_d, is_jal_d, is_jalr_d;
  wire        lsu_req_dec_d, lsu_we_dec_d;
  wire [1:0]  lsu_type_dec_d;
  wire        lsu_sign_dec_d;
  wire        is_xd_d;
  wire [2:0]  lane_op_d;

  espino_decoder #(.XdF3(XdF3), .XdEmaAlu(XdEmaAlu), .XdMulAlu(XdMulAlu),
                   .XdEmad(XdEmadKb >= 0), .XdDevk(XdDevkKb >= 0), .XdLanes(XdLanes)) u_decoder (
    .instr_i        (dec_instr),
    .illegal_insn_o (illegal_insn_o),
    .alu_operator_o (alu_operator_d),
    .alu_op_a_sel_o (alu_op_a_sel_d),
    .alu_op_b_sel_o (alu_op_b_sel_d),
    .imm_operand_o  (imm_operand_d),
    .imm_target_o   (imm_target_d),
    .rf_we_o        (rf_we_dec_d),
    .rf_wd_sel_o    (rf_wd_sel_d),
    .is_branch_o    (is_branch_d),
    .is_jal_o       (is_jal_d),
    .is_jalr_o      (is_jalr_d),
    .lsu_req_o      (lsu_req_dec_d),
    .lsu_we_o       (lsu_we_dec_d),
    .lsu_type_o     (lsu_type_dec_d),
    .lsu_sign_o     (lsu_sign_dec_d),
    .is_xd_o        (is_xd_d),
    .lane_op_o      (lane_op_d)
  );

  // Señales de decodificación que usa la ejecución
  wire [3:0]  alu_operator;
  wire [1:0]  alu_op_a_sel;
  wire        alu_op_b_sel;
  wire [31:0] imm_operand, imm_target;
  wire        rf_we_dec;
  wire [1:0]  rf_wd_sel;
  wire        is_branch, is_jal, is_jalr;
  wire        lsu_req_dec, lsu_we_dec;
  wire [1:0]  lsu_type_dec;
  wire        lsu_sign_dec;
  wire        is_xd;
  wire [2:0]  lane_op;

  generate
    if (Pipeline != 0) begin : g_pipe
      // ---- Pipeline de 3 etapas ----
      // El banco lee con las direcciones de la instrucción que viene y la
      // decodificación se registra en el mismo flanco en que esa instrucción
      // entra a ejecución. Nada de esto avanza mientras una carga espera su
      // dato: el banco conserva los operandos de la carga (la LSU los
      // necesita para alinear el dato) y la lectura de la instrucción
      // siguiente coincide con el flanco en que la carga escribe su registro.
      reg  [31:0]    instr_q;
      reg  [3:0]     alu_operator_q;
      reg  [1:0]     alu_op_a_sel_q;
      reg            alu_op_b_sel_q;
      reg  [31:0]    imm_operand_q;
      reg  [PcW-1:0] imm_target_q;
      reg            rf_we_dec_q;
      reg  [1:0]     rf_wd_sel_q;
      reg            is_branch_q, is_jal_q, is_jalr_q;
      reg            lsu_req_dec_q, lsu_we_dec_q;
      reg  [1:0]     lsu_type_dec_q;
      reg            lsu_sign_dec_q;
      reg            is_xd_q;
      reg  [2:0]     lane_op_q;

      // Sin reset: todo lo que usa estos registros está condicionado a
      // instr_valid_i, que vale 0 hasta que entra la primera instrucción.
      always @(posedge clk_i) begin
        if (advance) begin
          instr_q        <= instr_next_i;
          alu_operator_q <= alu_operator_d;
          alu_op_a_sel_q <= alu_op_a_sel_d;
          alu_op_b_sel_q <= alu_op_b_sel_d;
          imm_operand_q  <= imm_operand_d;
          imm_target_q   <= imm_target_d[PcW-1:0];
          rf_we_dec_q    <= rf_we_dec_d;
          rf_wd_sel_q    <= rf_wd_sel_d;
          is_branch_q    <= is_branch_d;
          is_jal_q       <= is_jal_d;
          is_jalr_q      <= is_jalr_d;
          lsu_req_dec_q  <= lsu_req_dec_d;
          lsu_we_dec_q   <= lsu_we_dec_d;
          lsu_type_dec_q <= lsu_type_dec_d;
          lsu_sign_dec_q <= lsu_sign_dec_d;
          is_xd_q        <= is_xd_d;
          lane_op_q      <= lane_op_d;
        end
      end

      assign alu_operator = alu_operator_q;
      assign alu_op_a_sel = alu_op_a_sel_q;
      assign alu_op_b_sel = alu_op_b_sel_q;
      assign imm_operand  = imm_operand_q;
      assign imm_target   = imm_target_q;   // extiende con ceros: solo se usan PcW bits
      assign rf_we_dec    = rf_we_dec_q;
      assign rf_wd_sel    = rf_wd_sel_q;
      assign is_branch    = is_branch_q;
      assign is_jal       = is_jal_q;
      assign is_jalr      = is_jalr_q;
      assign lsu_req_dec  = lsu_req_dec_q;
      assign lsu_we_dec   = lsu_we_dec_q;
      assign lsu_type_dec = lsu_type_dec_q;
      assign lsu_sign_dec = lsu_sign_dec_q;
      assign is_xd        = is_xd_q;
      assign lane_op      = lane_op_q;

      assign rf_waddr_o   = instr_q[10:7];
      assign instr_ex_o   = instr_q;
      assign rf_ready_o   = 1'b1;
`ifdef MUTA_LOADUSE
      // MUTACIÓN (solo para make mutaciones): el banco usa el stall del ciclo
      // anterior. La instrucción que sigue a una carga lee sus operandos un
      // flanco antes de que la carga escriba y no vuelve a leer.
      reg stall_q;
      always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) stall_q <= 1'b0;
        else         stall_q <= stall_i;
      end
      assign rf_rd_en_o = ~stall_q;
`elsif MUTA_RDEN
      // MUTACIÓN (solo para make mutaciones): el banco lee en todos los
      // flancos. Durante la espera de una carga pierde los operandos de la
      // carga y la LSU alinea el dato con la dirección equivocada.
      assign rf_rd_en_o = 1'b1;
`else
      assign rf_rd_en_o = advance;
`endif
    end else begin : g_base
      // ---- Espino base: synchronous-read wait FSM ----
      reg  ops_valid_q;
      always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni)      ops_valid_q <= 1'b0;
        else if (advance) ops_valid_q <= 1'b0;
        else              ops_valid_q <= 1'b1;
      end

      assign alu_operator = alu_operator_d;
      assign alu_op_a_sel = alu_op_a_sel_d;
      assign alu_op_b_sel = alu_op_b_sel_d;
      assign imm_operand  = imm_operand_d;
      assign imm_target   = imm_target_d;
      assign rf_we_dec    = rf_we_dec_d;
      assign rf_wd_sel    = rf_wd_sel_d;
      assign is_branch    = is_branch_d;
      assign is_jal       = is_jal_d;
      assign is_jalr      = is_jalr_d;
      assign lsu_req_dec  = lsu_req_dec_d;
      assign lsu_we_dec   = lsu_we_dec_d;
      assign lsu_type_dec = lsu_type_dec_d;
      assign lsu_sign_dec = lsu_sign_dec_d;
      assign is_xd        = is_xd_d;
      assign lane_op      = lane_op_d;

      assign rf_waddr_o   = instr_rdata_i[10:7];
      assign instr_ex_o   = instr_rdata_i;
      assign rf_ready_o   = ops_valid_q;
      assign rf_rd_en_o   = 1'b1;
      wire _unused_next = &{1'b0, instr_next_i};
    end
  endgenerate

  // Operando A desplazado de mulstep, emad y devk
  wire [31:0] xd_opa_a;
  wire        xd_opa_b_cero;
  generate
    if (XdOpa != 0) begin : g_opa
      xd_opa #(.MULSTEP(XdMulAlu), .EMAD_KB(XdEmadKb), .DEVK_KB(XdDevkKb), .BCAST(XdBcastAlu)) u_opa (
        .rs1_i    (rf_rdata_a_i),
        .funct3_i (instr_ex_o[14:12]),
        .funct7_i (instr_ex_o[31:25]),
        .a_o      (xd_opa_a),
        .b_cero_o (xd_opa_b_cero)
      );
    end else begin : g_sin_opa
      assign xd_opa_a      = 32'b0;
      assign xd_opa_b_cero = 1'b0;
    end
  endgenerate

  // Operand muxes
  reg  [31:0] operand_a;
  wire [31:0] operand_b;
  always @* begin
    case (alu_op_a_sel)
      OP_A_PC:   operand_a = pc_id_i;
      OP_A_ZERO: operand_a = 32'b0;
      OP_A_XD:   operand_a = (XdOpa != 0) ? xd_opa_a : rf_rdata_a_i;
      default:   operand_a = rf_rdata_a_i;
    endcase
  end
  // En mulstep el operando B vale cero cuando el bit que sale del
  // multiplicador (rs1[31]) es 0
  wire mul_anula = (XdOpa != 0) & (alu_op_a_sel == OP_A_XD) & xd_opa_b_cero;
  assign operand_b = (alu_op_b_sel == OP_B_IMM) ? imm_operand :
                     mul_anula                  ? 32'b0       : rf_rdata_b_i;

  wire [31:0] alu_result;
  wire        alu_cmp_result;
  generate
    if (XdLanes >= 0) begin : g_alu_carriles
      xd_alu u_alu (
        .operator_i   (alu_operator),
        .operand_a_i  (operand_a),
        .operand_b_i  (operand_b),
        .lane_op_i    (lane_op),
        .result_o     (alu_result),
        .cmp_result_o (alu_cmp_result)
      );
    end else begin : g_alu
      espino_alu u_alu (
        .operator_i   (alu_operator),
        .operand_a_i  (operand_a),
        .operand_b_i  (operand_b),
        .result_o     (alu_result),
        .cmp_result_o (alu_cmp_result)
      );
      wire _unused_lane = &{1'b0, lane_op};
    end
  endgenerate

  // Extensión en custom-0: una unidad combinacional de un ciclo. Recibe los
  // dos operandos del banco de registros y los campos funct3 y funct7 de la
  // instrucción en ejecución.
  wire [31:0] xd_result;
  generate
    if (XdF3 != 8'b0) begin : g_xd
      xd_unit #(
        .EMA_KB(XdEmaKb), .EMA_ALU(XdEmaAlu), .SRAK_KB(XdSrakKb), .SIMD(XdSimd),
        .MULSTEP(XdMulstep), .DIVSTEP(XdDivstep), .MULC_AW(XdMulcAw)
      ) u_xd (
        .rs1_i    (rf_rdata_a_i),
        .rs2_i    (rf_rdata_b_i),
        .alu_i    (alu_result),
        .funct3_i (instr_ex_o[14:12]),
        .funct7_i (instr_ex_o[31:25]),
        .result_o (xd_result)
      );
    end else begin : g_sin_xd
      assign xd_result = 32'b0;
    end
  endgenerate

  // LSU control
  assign lsu_req_o   = lsu_req_dec & instr_valid_i & rf_ready_o;
  assign lsu_we_o    = lsu_we_dec;
  assign lsu_type_o  = lsu_type_dec;
  assign lsu_sign_o  = lsu_sign_dec;
  assign lsu_addr_o  = alu_result;
  assign lsu_wdata_o = rf_rdata_b_i;

  // Control transfer. Con PcW < 32 el destino y el enlace se calculan con el
  // ancho real del contador de programa y los bits altos valen cero.
  wire [PcW-1:0] pc_plus_imm = pc_id_i[PcW-1:0] + imm_target[PcW-1:0];
  wire [PcW-1:0] pc_plus_4   = pc_id_i[PcW-1:0] + 32'd4;

  assign branch_taken_o = is_branch & alu_cmp_result;
  assign jump_o         = is_jal | is_jalr;
  assign pc_target_o    = is_jalr ? (alu_result & ~32'h1) : pc_plus_imm;

  wire commit = instr_valid_i & ~stall_i;

  always @* begin
    case (rf_wd_sel)
      WD_LSU:  rf_wdata_o = lsu_rdata_i;
      WD_PC4:  rf_wdata_o = pc_plus_4;
      default: rf_wdata_o = is_xd ? xd_result : alu_result;
    endcase
  end

  assign rf_we_o = rf_we_dec & commit;

endmodule
