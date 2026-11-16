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
// Santiago Muñoz: programa por defecto sw/trade.hex, power-on reset largo y
// elección de la variante del core (docs/espino_segmentado.md).
//
// COPIA DE FACTIBILIDAD (pieza F, factibilidad/f_doble_frecuencia). Es
// rtl/pochoco_soc.v con un solo cambio: el reloj interno clk ya no es i_Clk
// sino la salida de duplicador_reloj, que entrega dos flancos de subida por
// cada período de i_Clk. Se agregaron los parámetros Doblar, NRet, ModoRet y los
// retardos del modelo de simulación. Con Doblar = 0 es el SoC original. El
// nombre del módulo, sus puertos, MemFile y u_spi no cambian, para que el
// testbench oficial lo instancie sin modificaciones.
//
// Variante del core, parámetro Pipeline:
//   0  Espino base, el del repositorio del curso. Es el valor por defecto.
//   1  Pipeline de 3 etapas, con la memoria de instrucciones leída en el
//      flanco de bajada. Se elige al compilar con -DESPINO_SEGMENTADO.
//   2  Pipeline de 3 etapas, con el programa en una ROM combinacional
//      (módulo pochoco_rom, generado con tools/pochoasm.py --rom). Se elige
//      con -DESPINO_ROM y hay que agregar el archivo de la ROM a las fuentes.
`ifdef ESPINO_ROM
  `define ESPINO_PIPELINE_DEF 2
`elsif ESPINO_SEGMENTADO
  `define ESPINO_PIPELINE_DEF 1
`else
  `define ESPINO_PIPELINE_DEF 0
`endif

module pochoco_soc #(
  parameter NumWords   = 512,
  parameter MemFile    = "sw/trade.hex",   // ruta relativa a la raíz del repositorio
  parameter PorBits    = 12,               // el reset dura 2^PorBits - 1 ciclos
  parameter Pipeline   = `ESPINO_PIPELINE_DEF,
  // Bits del contador de programa. El core base conserva los 32 originales.
  // El segmentado usa el ancho real de la memoria (11 bits con 512 palabras).
  parameter PcW        = (Pipeline != 0) ? $clog2(NumWords) + 2 : 32,
  // Pieza F: reloj doblado por lógica
  parameter Doblar     = 1,                // 1: clk = reloj doblado. 0: clk = i_Clk
  parameter NRet       = 8,                // LUT de la cadena de retardo
  parameter ModoRet    = 1,                // 0: buffer por una entrada. 1: AND y OR de 4 entradas
  parameter RetSubePs  = 9000,             // modelo de simulación (SIM_RETARDO)
  parameter RetBajaPs  = 9000,
  parameter RetComunPs = 2000
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
  generate
    if (Doblar) begin : g_x2
      duplicador_reloj #(
        .N(NRet), .Modo(ModoRet),
        .RetSubePs(RetSubePs), .RetBajaPs(RetBajaPs), .RetComunPs(RetComunPs)
      ) u_dup (
        .clk_i   (i_Clk),
        .clk2x_o (clk),
        .pulso_o (),
        .ret_o   (),
        .toma_o  ()
      );
    end else begin : g_x1
      assign clk = i_Clk;
    end
  endgenerate

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
  wire [31:0] instr_next, ram_a_next;

  wire        data_req, data_we;
  wire [3:0]  data_be;
  wire [31:0] data_addr, data_wdata, data_rdata;

  espino_core #(.BootAddr(32'h0000_0000), .Pipeline(Pipeline), .PcW(PcW)) u_core (
    .clk_i         (clk),
    .rst_ni        (rst_ni),
    .instr_req_o   (instr_req),
    .instr_addr_o  (instr_addr),
    .instr_rdata_i (instr_rdata),
    .instr_next_i  (instr_next),
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
  assign data_rdata = rd_is_per ? per_rdata :
                      rd_is_spi ? spi_rdata : ram_b_rdata;

  pochoco_ram #(.NumWords(NumWords), .MemFile(MemFile), .FetchMode(Pipeline)) u_ram (
    .clk_i     (clk),
    .a_req_i   (instr_req),
    .a_addr_i  (instr_addr),
    .a_rdata_o (instr_rdata),
    .a_next_o  (ram_a_next),
    .b_req_i   (ram_b_req),
    .b_we_i    (data_we),
    .b_be_i    (data_be),
    .b_addr_i  (data_addr),
    .b_wdata_i (data_wdata),
    .b_rdata_o (ram_b_rdata)
  );

  // Origen de la instrucción del pipeline: la BRAM leída en el flanco de
  // bajada o la ROM combinacional del programa.
`ifdef ESPINO_ROM
  pochoco_rom u_rom (
    .addr_i (instr_addr),
    .data_o (instr_next)
  );
`else
  assign instr_next = ram_a_next;
`endif

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