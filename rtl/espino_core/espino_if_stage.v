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
// Santiago Muñoz (docs/espino_segmentado.md):
//   - PcW: bits del contador de programa que se implementan. Con 32 es el
//     módulo original. El core segmentado usa el ancho real de la memoria
//     (11 bits para 512 palabras) y los bits altos se leen como cero.
//   - Pipeline: solo lo usa la mutación de prueba MUTA_SQUASH, que se activa
//     desde la línea de comandos (make mutaciones) y afecta al segmentado.

module espino_if_stage #(
  parameter [31:0] BootAddr = 32'h0000_0000,
  parameter integer PcW     = 32,
  parameter integer Pipeline = 0
) (
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

  reg  [PcW-1:0] pc_q;
  wire [PcW-1:0] pc_next;
  reg  [PcW-1:0] pc_id_q;
  reg            valid_q;
  wire           valid_d;

  assign pc_next = pc_set_i ? pc_target_i[PcW-1:0] : (pc_q + 32'd4);
`ifdef MUTA_SQUASH
  // MUTACIÓN (solo para make mutaciones): en el core segmentado la
  // instrucción que sigue a un salto tomado no se anula.
  assign valid_d = (Pipeline != 0) ? 1'b1 : ~pc_set_i;
`else
  assign valid_d = ~pc_set_i;
`endif

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      pc_q    <= BootAddr[PcW-1:0];
      pc_id_q <= BootAddr[PcW-1:0];
      valid_q <= 1'b0;
    end else if (!stall_i) begin
      pc_q    <= pc_next;
      pc_id_q <= pc_q;
      valid_q <= valid_d;
    end
  end

  assign instr_req_o      = ~stall_i;
  // Con PcW < 32 la asignación extiende con ceros
  assign instr_addr_o     = pc_q;
  assign pc_id_o          = pc_id_q;
  assign instr_valid_id_o = valid_q;

endmodule