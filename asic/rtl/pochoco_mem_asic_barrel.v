// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Memoria del macro ASIC del barrel (asic/). Copia de
// factibilidad/g_asic/rtl/pochoco_mem_asic.v con una sola diferencia: las
// palabras de datos y el registro de lectura vuelven a 0 con el reset, como la
// BRAM de la FPGA parte en 0 desde MemFile. sw/fondo.s lo supone ("estado
// compartido, parte en cero"): sin esto el netlist final decide distinto según
// el estado inicial de los flip-flops (asic/README.md, sección del arranque).
// El original, que usa la edición ASIC del base, no cambia.
//
// Texto del original:
// Memoria del SoC para la edición ASIC (factibilidad/g_asic). Reemplaza a
// rtl/pochoco_ram.v, que usa $readmemh y se infiere como BRAM del iCE40:
// ninguna de las dos cosas existe en un flujo de celdas estándar. Viene de
// pochoco_mem_rom.v de nuestro Proyecto 3 (estrategia 1 de memoria).
//
//   - Instrucciones: el módulo pochoco_rom, una ROM combinacional que genera
//     tools/pochoasm.py --rom a partir de sw/trade.s. La síntesis la
//     convierte en compuertas.
//       FetchMode = 0 (Espino base): la salida de la ROM pasa por un
//         registro con a_req_i, que cumple el papel del puerto A registrado
//         de la BRAM. El core ve la misma temporización que en la FPGA.
//       FetchMode != 0 (Espino segmentado): la salida de la ROM va directo a
//         a_next_o. Es la variante 2 de pochoco_soc (-DESPINO_ROM).
//   - Datos: DataWords palabras en flip-flops, con escritura por byte y
//     lectura registrada, como el puerto B original. La dirección se toma
//     módulo DataWords (potencia de 2). trade.s usa una sola palabra de
//     trabajo, TMP, en 0x7FC: con 4 palabras cae en la palabra 3.
//
// Diferencias con la memoria de la FPGA que hay que tener presentes:
//   - El puerto de datos no ve las instrucciones (trade.s no las lee como
//     datos) y no puede escribirlas.
//   - Las palabras de datos no tienen valor inicial. En la FPGA parten en 0.
//     (En esta copia parten en 0 con el reset.)
//   - Dos direcciones que difieren en un múltiplo de 4 * DataWords son la
//     misma palabra.

module pochoco_mem_asic_barrel #(
  parameter integer DataWords = 4,
  parameter integer FetchMode = 0
) (
  input  wire        clk_i,
  input  wire        rst_ni,   // reset asíncrono: las palabras de datos vuelven a 0

  // Puerto A: instrucciones
  input  wire        a_req_i,
  input  wire [31:0] a_addr_i,
  output wire [31:0] a_rdata_o,
  output wire [31:0] a_next_o,

  // Puerto B: datos
  input  wire        b_req_i,
  input  wire        b_we_i,
  input  wire [3:0]  b_be_i,
  input  wire [31:0] b_addr_i,
  input  wire [31:0] b_wdata_i,
  output reg  [31:0] b_rdata_o
);

  wire [31:0] rom_data;

  pochoco_rom u_rom (
    .addr_i (a_addr_i),
    .data_o (rom_data)
  );

  generate
    if (FetchMode == 0) begin : g_reg
      reg [31:0] a_q;
      always @(posedge clk_i) begin
        if (a_req_i) a_q <= rom_data;
      end
      assign a_rdata_o = a_q;
      assign a_next_o  = 32'b0;
    end else begin : g_comb
      assign a_rdata_o = 32'b0;
      assign a_next_o  = rom_data;
      wire _unused_req = &{1'b0, a_req_i};
    end
  endgenerate

  localparam integer DAW = (DataWords > 1) ? $clog2(DataWords) : 1;

  reg  [31:0]    ram [0:DataWords-1];
  wire [DAW-1:0] b_word = b_addr_i[DAW+1:2];

  integer i;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (i = 0; i < DataWords; i = i + 1) ram[i] <= 32'b0;
      b_rdata_o <= 32'b0;
    end else begin
      if (b_req_i && b_we_i) begin
        if (b_be_i[0]) ram[b_word][7:0]   <= b_wdata_i[7:0];
        if (b_be_i[1]) ram[b_word][15:8]  <= b_wdata_i[15:8];
        if (b_be_i[2]) ram[b_word][23:16] <= b_wdata_i[23:16];
        if (b_be_i[3]) ram[b_word][31:24] <= b_wdata_i[31:24];
      end
      b_rdata_o <= ram[b_word];
    end
  end

  wire _unused = &{1'b0, b_addr_i[31:DAW+2], b_addr_i[1:0]};

endmodule
