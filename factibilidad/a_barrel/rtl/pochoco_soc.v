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
// Santiago Muñoz: programa por defecto sw/trade.hex y power-on reset largo.
//
// COPIA PARA EL PROTOTIPO DE FACTIBILIDAD DEL ESPINO BARREL
// (factibilidad/a_barrel/README.md). Diferencias con rtl/pochoco_soc.v:
//   - El core es espino_barrel_core (4 hilos, pipeline de 4 etapas) en vez de
//     espino_core. Se quitaron el parámetro Pipeline y el cable instr_next.
//   - La memoria se instancia siempre con FetchMode = 0 (la original).
//   - El contador de programa tiene por defecto el ancho real de la memoria.
//   - Con -DBARREL_SIN_PERIPH no se instancia pochoco_periph (LEDs, display e
//     interruptores). Solo sirve para medir cuánto ocupa.
//   - Con -DBARREL_MMIO_HILO se agrega el registro HILO, de solo lectura, en
//     0x8000_000C: entrega el número del hilo que lo lee. Con
//     -DBARREL_BOOT_PASO=0 los cuatro hilos parten en la dirección 0 en vez de
//     hacerlo en 0, 4, 8 y 12. Las dos cosas juntas son la alternativa a la
//     tabla de arranque que se midió (README, sección de arranque). Sin esas
//     definiciones no cambia nada.
//   - El nombre del módulo se puede cambiar con -DPOCHOCO_SOC_MODULE=nombre,
//     para instanciar este SoC junto al original en un mismo testbench. Sin
//     esa definición se llama pochoco_soc, como exige el testbench oficial.
// El resto es igual: mismos puertos, MemFile, u_spi, u_ram, u_periph, mapa de
// memoria y multiplexor de lectura.
`ifndef POCHOCO_SOC_MODULE
  `define POCHOCO_SOC_MODULE pochoco_soc
`endif
`ifndef BARREL_BOOT_PASO
  `define BARREL_BOOT_PASO 4
`endif

module `POCHOCO_SOC_MODULE #(
  parameter NumWords   = 512,
  parameter MemFile    = "sw/trade.hex",   // ruta relativa a la raíz del repositorio
  parameter PorBits    = 12,               // el reset dura 2^PorBits - 1 ciclos
  // Bits del contador de programa: el ancho real de la memoria (11 bits con
  // 512 palabras). Con 32 se comporta como el del Espino base.
  parameter PcW        = $clog2(NumWords) + 2
) (
  input  wire       i_Clk,

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

  // Power-on reset. Con PorBits = 12 dura 4095 ciclos (164 us a 25 MHz).
  // Las BRAM del iCE40 no entregan datos válidos hasta un tiempo después de
  // configurar la FPGA: con el reset original de 15 ciclos, en la placa el
  // core arrancaba leyendo ceros y el programa empezaba por la mitad (lo
  // medimos en el Proyecto 2).
  reg  [PorBits-1:0] por_cnt = {PorBits{1'b0}};
  wire               rst_ni;
  always @(posedge clk) begin
    if (~&por_cnt) por_cnt <= por_cnt + 1'b1;
  end
  assign rst_ni = &por_cnt;

  // Core-memory wiring
  wire        instr_req;
  wire [31:0] instr_addr, instr_rdata;

  wire        data_req, data_we;
  wire [3:0]  data_be;
  wire [31:0] data_addr, data_wdata, data_rdata;

  wire [1:0] hilo_x;

  espino_barrel_core #(.BootAddr(32'h0000_0000), .BootPaso(`BARREL_BOOT_PASO), .PcW(PcW)) u_core (
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

  wire is_mmio, spi_sel, per_sel;
  assign is_mmio = data_addr[31];
  assign per_sel = is_mmio & ~data_addr[16];
  assign spi_sel = is_mmio &  data_addr[16];

  wire ram_b_req, per_req, spi_req;
  assign ram_b_req = data_req & ~is_mmio;
  assign per_req   = data_req &  per_sel;
  assign spi_req   = data_req &  spi_sel;

  wire [31:0] ram_b_rdata, per_rdata, spi_rdata;

  reg rd_is_per, rd_is_spi;
  always @(posedge clk or negedge rst_ni) begin
    if (!rst_ni) begin
      rd_is_per <= 1'b0;
      rd_is_spi <= 1'b0;
    end else if (data_req & ~data_we) begin
      rd_is_per <= per_sel;
      rd_is_spi <= spi_sel;
    end
  end
`ifdef BARREL_MMIO_HILO
  // Registro HILO (0x8000_000C, solo lectura): número del hilo que lo lee.
  // Se guarda el hilo que está en X cuando pide la lectura y se entrega en M,
  // igual que los demás registros de lectura.
  reg       rd_is_hilo;
  reg [1:0] hilo_q;
  always @(posedge clk or negedge rst_ni) begin
    if (!rst_ni) begin
      rd_is_hilo <= 1'b0;
      hilo_q     <= 2'd0;
    end else if (data_req & ~data_we) begin
      rd_is_hilo <= per_sel & (data_addr[7:2] == 6'd3);
      hilo_q     <= hilo_x;
    end
  end
  assign data_rdata = rd_is_hilo ? {30'b0, hilo_q} :
                      rd_is_per  ? per_rdata :
                      rd_is_spi  ? spi_rdata : ram_b_rdata;
`else
  wire _unused_hilo = &{1'b0, hilo_x};
  assign data_rdata = rd_is_per ? per_rdata :
                      rd_is_spi ? spi_rdata : ram_b_rdata;
`endif

  wire [31:0] ram_a_next_nc;
  pochoco_ram #(.NumWords(NumWords), .MemFile(MemFile), .FetchMode(0)) u_ram (
    .clk_i     (clk),
    .a_req_i   (instr_req),
    .a_addr_i  (instr_addr),
    .a_rdata_o (instr_rdata),
    .a_next_o  (ram_a_next_nc),
    .b_req_i   (ram_b_req),
    .b_we_i    (data_we),
    .b_be_i    (data_be),
    .b_addr_i  (data_addr),
    .b_wdata_i (data_wdata),
    .b_rdata_o (ram_b_rdata)
  );

  // Peripherals
  wire [6:0] seg1, seg2;

`ifdef BARREL_SIN_PERIPH
  assign per_rdata = 32'b0;
  assign o_LED     = 4'b0;
  assign seg1      = 7'b0;
  assign seg2      = 7'b0;
  wire _unused_per = &{1'b0, per_req, i_Switch};
`else
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
`endif

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
