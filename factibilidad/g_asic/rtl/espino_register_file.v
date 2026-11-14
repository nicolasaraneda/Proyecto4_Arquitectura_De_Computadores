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
// Copia de rtl/espino_core/espino_register_file.v para la edición ASIC
// (factibilidad/g_asic). Modificada por Nicolás Araneda, Vicente Calderón y
// Santiago Muñoz. Arquitectura de Computadores, Universidad de los Andes,
// 2026-2.
//
// Qué cambia respecto del archivo de rtl/:
//   - El banco ya no instancia SB_RAM40_4K, que es una BRAM del iCE40 y no
//     existe en una biblioteca de celdas estándar. Los registros x1 a x15 son
//     flip-flops.
//   - En la FPGA el banco se duplica (u_bankA y u_bankB) porque cada BRAM
//     tiene un solo puerto de lectura. Con flip-flops no hace falta: los dos
//     puertos de lectura son multiplexores sobre el mismo arreglo.
//   - x0 no se almacena. En la BRAM valía 0 porque la memoria partía en cero
//     y nunca se escribía. En silicio un flip-flop arranca en cualquier
//     valor, así que leer la dirección 0 entrega 0 por hardware.
//   - x1 a x15 no tienen reset, igual que en la BRAM. En la FPGA parten en 0
//     y en el ASIC parten indefinidos: un programa no puede leer un registro
//     antes de escribirlo. trade.s no lo hace.
//
// Qué no cambia: la interfaz, la temporización (lectura registrada, con
// rd_en_i; si se lee y se escribe el mismo registro en el mismo flanco la
// lectura entrega el valor viejo, como la BRAM) y el adelantamiento de
// Bypass = 1, que se copió sin las mutaciones de prueba (MUTA_FWD y MUTA_X0).
// Es la misma solución del banco de registros de nuestro Proyecto 3.

module espino_register_file #(
  parameter integer Bypass = 0
) (
  input  wire        clk_i,
  input  wire        rst_ni,     // unused
  input  wire        rd_en_i,
  input  wire [3:0]  raddr_a_i,
  output wire [31:0] rdata_a_o,
  input  wire [3:0]  raddr_b_i,
  output wire [31:0] rdata_b_o,
  input  wire [3:0]  waddr_i,
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  wire wr = we_i & (waddr_i != 4'd0);

  reg [31:0] regs [1:15];

  always @(posedge clk_i) begin
    if (wr) regs[waddr_i] <= wdata_i;
  end

  // Lectura registrada: reemplaza al registro de salida de la BRAM
  reg [31:0] bank_a, bank_b;

  always @(posedge clk_i) begin
    if (rd_en_i) begin
      bank_a <= (raddr_a_i == 4'd0) ? 32'b0 : regs[raddr_a_i];
      bank_b <= (raddr_b_i == 4'd0) ? 32'b0 : regs[raddr_b_i];
    end
  end

  generate
    if (Bypass != 0) begin : g_bypass
      wire fwd_a = wr & (raddr_a_i == waddr_i);
      wire fwd_b = wr & (raddr_b_i == waddr_i);
      reg        fwd_a_q, fwd_b_q;
      reg [31:0] wdata_q;
      // Sin reset: el dato adelantado solo se usa si la instrucción es válida
      always @(posedge clk_i) begin
        if (rd_en_i) begin
          fwd_a_q <= fwd_a;
          fwd_b_q <= fwd_b;
          wdata_q <= wdata_i;
        end
      end
      assign rdata_a_o = fwd_a_q ? wdata_q : bank_a;
      assign rdata_b_o = fwd_b_q ? wdata_q : bank_b;
    end else begin : g_directo
      assign rdata_a_o = bank_a;
      assign rdata_b_o = bank_b;
    end
  endgenerate

  // rst_ni intentionally unused
  wire _unused = &{1'b0, rst_ni};
endmodule
