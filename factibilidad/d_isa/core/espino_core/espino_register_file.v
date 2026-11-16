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
// Santiago Muñoz, para el core segmentado (docs/espino_segmentado.md). Los dos
// agregados vienen del banco de registros de nuestro Proyecto 3, adaptados a
// las BRAM del iCE40:
//   - rd_en_i: habilita la lectura. El core base lo deja en 1. El segmentado
//     lo baja mientras una carga espera su dato, para conservar los operandos.
//   - Bypass = 1: adelantamiento. Si en el mismo flanco se escribe el registro
//     que se está leyendo, la BRAM entrega el valor viejo. Un registro guarda
//     el dato escrito y un multiplexor a la salida lo elige en vez del de la
//     BRAM. Con Bypass = 0 el módulo es el original.

module espino_regbank32 (
  input  wire        clk_i,
  input  wire        rd_en_i,
  input  wire [3:0]  raddr_i,
  output wire [31:0] rdata_o,
  input  wire [3:0]  waddr_i,
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  wire [10:0] ra = {7'b0, raddr_i};
  wire [10:0] wa = {7'b0, waddr_i};

  SB_RAM40_4K #(
    .READ_MODE(0), .WRITE_MODE(0),
    .INIT_0(256'h0)
  ) u_lo (
    .RDATA (rdata_o[15:0]),
    .RADDR (ra), .RCLK (clk_i), .RCLKE (rd_en_i), .RE (1'b1),
    .WDATA (wdata_i[15:0]),
    .WADDR (wa), .WCLK (clk_i), .WCLKE (1'b1), .WE (we_i),
    .MASK  (16'h0000)
  );

  SB_RAM40_4K #(
    .READ_MODE(0), .WRITE_MODE(0),
    .INIT_0(256'h0)
  ) u_hi (
    .RDATA (rdata_o[31:16]),
    .RADDR (ra), .RCLK (clk_i), .RCLKE (rd_en_i), .RE (1'b1),
    .WDATA (wdata_i[31:16]),
    .WADDR (wa), .WCLK (clk_i), .WCLKE (1'b1), .WE (we_i),
    .MASK  (16'h0000)
  );
endmodule

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

  wire [31:0] bank_a, bank_b;

  espino_regbank32 u_bankA (   // serves read port A
    .clk_i (clk_i), .rd_en_i (rd_en_i),
    .raddr_i (raddr_a_i), .rdata_o (bank_a),
    .waddr_i (waddr_i), .wdata_i (wdata_i), .we_i (wr)
  );

  espino_regbank32 u_bankB (   // serves read port B
    .clk_i (clk_i), .rd_en_i (rd_en_i),
    .raddr_i (raddr_b_i), .rdata_o (bank_b),
    .waddr_i (waddr_i), .wdata_i (wdata_i), .we_i (wr)
  );

  generate
    if (Bypass != 0) begin : g_bypass
`ifdef MUTA_FWD
      // MUTACIÓN (solo para make mutaciones): sin adelantamiento.
      wire fwd_a = 1'b0;
      wire fwd_b = 1'b0;
`elsif MUTA_X0
      // MUTACIÓN (solo para make mutaciones): el adelantamiento no excluye
      // a x0, así que leer x0 justo después de escribirlo entrega el dato.
      wire fwd_a = we_i & (raddr_a_i == waddr_i);
      wire fwd_b = we_i & (raddr_b_i == waddr_i);
`else
      wire fwd_a = wr & (raddr_a_i == waddr_i);
      wire fwd_b = wr & (raddr_b_i == waddr_i);
`endif
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
