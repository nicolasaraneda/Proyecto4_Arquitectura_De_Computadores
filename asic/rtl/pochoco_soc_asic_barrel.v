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
// pochoco_soc_asic_barrel.v: el SoC del fondo en un chip (R1) para la edición ASIC.
// Copia de factibilidad/g_asic/rtl/pochoco_soc_asic.v, hecha por Nicolás Araneda,
// Vicente Calderón y Santiago Muñoz (asic/README.md), con tres cambios y nada más:
//   1. El core es espino_barrel_core (rtl/espino_core/espino_barrel_core.v, sin
//      copiar), con la extensión elegida por el parámetro Xd: 3 son emad y devk
//      (la máscara de R1) y 7 agrega mulstep (la edición de exhibición).
//   2. La tabla de parámetros de sw/fondo.s, en 0x8002_0000, con la misma
//      decodificación que rtl/pochoco_soc.v. Su contenido es una ROM generada
//      desde sw/fondo_tabla.hex (asic/build/gen/pochoco_tabla_rom.v), porque en
//      celdas estándar no hay $readmemh.
//   3. El fetch es el del Espino base (FetchMode = 0): el barrel busca como el
//      core base, con la instrucción registrada, igual que en la FPGA.
// El esclavo SPI, el periférico y el mapa de memoria son los de rtl/.
//
// Encabezado de la copia de la que parte:
//
// Copia de rtl/pochoco_soc.v para la edición ASIC (factibilidad/g_asic).
// Modificada por Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Qué cambia respecto del archivo de rtl/:
//   - El módulo se llama pochoco_soc_asic, para que no se confunda con el de
//     la FPGA, que es el que usa el testbench oficial.
//   - Reset: se quitó el contador de power-on reset, que depende del valor
//     inicial de un registro (en silicio no hay valores iniciales) y existía
//     para esperar a las BRAM del iCE40. El reset entra por el puerto rst_ni,
//     ya sincronizado por asic_top.
//   - Memoria: pochoco_mem_asic en vez de pochoco_ram (programa en una ROM
//     combinacional y datos en flip-flops). Desaparecen MemFile y NumWords.
//   - Variante del core: el parámetro Pipeline vale 0 (Espino base) o 2
//     (pipeline de 3 etapas con ROM combinacional). La variante 1, que lee
//     una BRAM en el flanco de bajada, no tiene sentido sin BRAM.
//
// Qué no cambia: el core, el mapa de memoria, el multiplexor de lectura, los
// periféricos, el esclavo SPI (instancia u_spi) y los puertos de la placa.

module pochoco_soc_asic_barrel #(
  parameter integer Xd        = 3,    // extensión: bit 0 emad, bit 1 devk, bit 2 mulstep
  parameter integer DataWords = 16,   // sw/fondo.s usa las palabras de 0x7C0 a 0x7FC
  parameter integer PcW       = 11    // memoria de 512 palabras, como en pochoco_soc
) (
  input  wire       i_Clk,
  input  wire       rst_ni,

  output wire [3:0] o_LED,
  input  wire [3:0] i_Switch,

  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,

  input  wire       i_SPI_SCLK,
  input  wire       i_SPI_MOSI,
  input  wire       i_SPI_CS_n,
  output wire       o_SPI_MISO
);

  wire clk;
  assign clk = i_Clk;

  // Core-memory wiring
  wire        instr_req;
  wire [31:0] instr_addr, instr_rdata;
  wire [31:0] instr_next;

  wire        data_req, data_we;
  wire [3:0]  data_be;
  wire [31:0] data_addr, data_wdata, data_rdata;

  wire [1:0] hilo_x;
  espino_barrel_core #(.BootAddr(32'h0000_0000), .PcW(PcW), .Xd(Xd[2:0])) u_core (
    .clk_i         (clk),
    .rst_ni        (rst_ni),
    .hilo_x_o      (hilo_x),
    .instr_req_o   (instr_req),
    .instr_addr_o  (instr_addr),
    .instr_rdata_i (instr_rdata),
    .data_req_o    (data_req),
    .data_we_o     (data_we),
    .data_be_o     (data_be),
    .data_addr_o   (data_addr),
    .data_wdata_o  (data_wdata),
    .data_rdata_i  (data_rdata)
  );

  wire _unused_barrel = &{1'b0, hilo_x, instr_next};

  // Decodificación de rtl/pochoco_soc.v con la tabla (Tabla = 1)
  wire is_mmio, spi_sel, per_sel, tab_sel;
  assign is_mmio = data_addr[31];
  assign tab_sel = is_mmio & data_addr[17];
  assign per_sel = is_mmio & ~data_addr[16] & ~tab_sel;
  assign spi_sel = is_mmio &  data_addr[16] & ~tab_sel;

  wire ram_b_req, per_req, spi_req;
  assign ram_b_req = data_req & ~is_mmio;
  assign per_req   = data_req &  per_sel;
  assign spi_req   = data_req &  spi_sel;

  wire [31:0] ram_b_rdata, per_rdata, spi_rdata, tab_rdata;

  reg rd_is_per, rd_is_spi, rd_is_tab;
  always @(posedge clk or negedge rst_ni) begin
    if (!rst_ni) begin
      rd_is_per <= 1'b0;
      rd_is_spi <= 1'b0;
      rd_is_tab <= 1'b0;
    end else if (data_req & ~data_we) begin
      rd_is_per <= per_sel;
      rd_is_spi <= spi_sel;
      rd_is_tab <= tab_sel;
    end
  end
  assign data_rdata = rd_is_per ? per_rdata :
                      rd_is_spi ? spi_rdata :
                      rd_is_tab ? tab_rdata : ram_b_rdata;

  // Tabla de parámetros de solo lectura (ROM generada desde sw/fondo_tabla.hex)
  pochoco_tabla u_tabla (
    .clk_i   (clk),
    .rd_i    (data_req & tab_sel & ~data_we),
    .idx_i   (data_addr[9:2]),
    .rdata_o (tab_rdata)
  );

  pochoco_mem_asic #(.DataWords(DataWords), .FetchMode(0)) u_ram (
    .clk_i     (clk),
    .a_req_i   (instr_req),
    .a_addr_i  (instr_addr),
    .a_rdata_o (instr_rdata),
    .a_next_o  (instr_next),
    .b_req_i   (ram_b_req),
    .b_we_i    (data_we),
    .b_be_i    (data_be),
    .b_addr_i  (data_addr),
    .b_wdata_i (data_wdata),
    .b_rdata_o (ram_b_rdata)
  );

  // Peripherals
  wire [6:0] seg1, seg2;

  pochoco_periph u_periph (
    .clk_i     (clk),
    .rst_ni    (rst_ni),
    .sel_i     (per_sel),
    .req_i     (per_req),
    .we_i      (data_we),
    .addr_i    (data_addr[7:0]),
    .wdata_i   (data_wdata),
    .rdata_o   (per_rdata),
    .leds_o    (o_LED),
    .btn_i     (i_Switch),
    .seg1_o    (seg1),
    .seg2_o    (seg2)
  );

  // SPI Slave
  pochoco_spi_slave u_spi (
    .clk_i      (clk),
    .rst_ni     (rst_ni),
    .sel_i      (spi_sel),
    .req_i      (spi_req),
    .we_i       (data_we),
    .addr_i     (data_addr[7:0]),
    .wdata_i    (data_wdata),
    .rdata_o    (spi_rdata),
    .spi_sclk_i (i_SPI_SCLK),
    .spi_mosi_i (i_SPI_MOSI),
    .spi_cs_n_i (i_SPI_CS_n),
    .spi_miso_o (o_SPI_MISO)
  );

  // 7-seg is active-low on the board
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~seg2;

endmodule
