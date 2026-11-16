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
// COPIA PARA EL DISEÑO INTEGRADO (factibilidad/i_integrado/README.md). Parte
// de factibilidad/a_barrel/rtl/pochoco_soc.v, que ya instancia el core barrel
// (4 hilos, pipeline de 4 etapas), y le agrega dos piezas que se eligen al
// compilar. Sin definiciones es el SoC del prototipo del barrel.
//
//   -DI_VIGILANTE     Vigilante con la primitiva SB_WARMBOOT, tomado de
//                     factibilidad/e_warmboot/soc/pochoco_soc.v sin cambios de
//                     lógica: si llegan VigN precios seguidos sin escritura en
//                     DECISION, la FPGA se reconfigura con la imagen
//                     VigDestino. Usa la copia del esclavo SPI de e_warmboot,
//                     que saca tres señales que ya existían.
//   -DI_TABLA=1       Memoria para la tabla de política, forma 1: una BRAM
//                     aparte de 256 palabras de 16 bits por MMIO, en
//                     0x8002_0000 (rtl/tabla_mmio.v). La palabra i está en el
//                     desplazamiento 4 i. Son 13 de 16 BRAM.
//   -DI_TABLA=2       Forma 2: la memoria de datos crece de 512 a 1024
//                     palabras. Las 512 nuevas (direcciones 0x800 a 0xFFF) son
//                     solo de datos: el contador de programa sigue teniendo 11
//                     bits y no se pueden ejecutar (rtl/tabla_ram.v). Son 16
//                     de 16 BRAM. Una memoria de 1024 palabras completa, con
//                     las dos lecturas, necesitaría 20 BRAM y no cabe.
//
// Otras diferencias con la copia del barrel:
//   - Se quitaron el registro HILO y el arranque común (-DBARREL_MMIO_HILO y
//     -DBARREL_BOOT_PASO), la alternativa a la tabla de arranque que el
//     estudio del barrel midió y descartó.
//   - El nombre del módulo del esclavo SPI se puede cambiar con
//     -DPOCHOCO_SPI_MODULE=nombre, igual que el del SoC con
//     -DPOCHOCO_SOC_MODULE, para instanciar este SoC junto al original en un
//     mismo testbench (tools/verif_rv32e.sh). Sin esas definiciones se llaman
//     pochoco_spi_slave y pochoco_soc.
// No cambian los puertos, MemFile, u_spi, u_ram, u_periph ni el mapa de
// registros del esclavo SPI y de los periféricos.
`ifndef POCHOCO_SOC_MODULE
  `define POCHOCO_SOC_MODULE pochoco_soc
`endif
`ifndef POCHOCO_SPI_MODULE
  `define POCHOCO_SPI_MODULE pochoco_spi_slave
`endif
`ifdef I_VIGILANTE
  `define I_VIGILANTE_DEF 1
`else
  `define I_VIGILANTE_DEF 0
`endif
`ifdef I_TABLA
  `define I_TABLA_DEF `I_TABLA
`else
  `define I_TABLA_DEF 0
`endif

module `POCHOCO_SOC_MODULE #(
  parameter NumWords   = 512,
  parameter MemFile    = "sw/trade.hex",   // ruta relativa a la raíz del repositorio
  parameter PorBits    = 12,               // el reset dura 2^PorBits - 1 ciclos
  // Bits del contador de programa: el ancho real de la memoria (11 bits con
  // 512 palabras). Con 32 se comporta como el del Espino base.
  parameter PcW        = $clog2(NumWords) + 2,
  // Vigilante: si llegan VigN precios seguidos sin escritura en DECISION, la
  // FPGA se reconfigura con la imagen VigDestino (S1 S0 de SB_WARMBOOT).
  parameter       Vigilante  = `I_VIGILANTE_DEF,
  parameter       VigN       = 4,
  parameter [1:0] VigDestino = 2'b01,
  // VigBoton = 1: el interruptor 4 (i_Switch[3]) fuerza el disparo. Es solo
  // para probar el relevo en la placa sin la maestra. Por defecto no se usa.
  parameter       VigBoton   = 0,
  // Memoria para la tabla de política: 0 no hay, 1 BRAM de 256 x 16 por MMIO,
  // 2 otras 512 palabras de datos. TablaFile es su contenido inicial (un
  // valor hexadecimal por línea). Vacío, parte en cero.
  parameter       Tabla      = `I_TABLA_DEF,
  parameter       TablaFile  = ""
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

  localparam AddrW = $clog2(NumWords);

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

  espino_barrel_core #(.BootAddr(32'h0000_0000), .BootPaso(4), .PcW(PcW)) u_core (
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
  wire _unused_hilo = &{1'b0, hilo_x};

  // Selección. Con Tabla = 0 es la del SoC original: tab_mmio y tab_ram valen
  // cero y no queda lógica.
  wire is_mmio, spi_sel, per_sel, tab_mmio, tab_ram, tab_sel;
  assign is_mmio  = data_addr[31];
  assign tab_mmio = (Tabla == 1) ? (is_mmio & data_addr[17])         : 1'b0;
  assign tab_ram  = (Tabla == 2) ? (~is_mmio & data_addr[AddrW + 2]) : 1'b0;
  assign tab_sel  = tab_mmio | tab_ram;
  assign per_sel  = is_mmio & ~data_addr[16] & ~tab_mmio;
  assign spi_sel  = is_mmio &  data_addr[16] & ~tab_mmio;

  wire ram_b_req, per_req, spi_req, tab_req;
  assign ram_b_req = data_req & ~is_mmio & ~tab_ram;
  assign per_req   = data_req &  per_sel;
  assign spi_req   = data_req &  spi_sel;
  assign tab_req   = data_req &  tab_sel;

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

  // Memoria para la tabla de política
  generate
    if (Tabla == 1) begin : g_tabla_mmio
      wire [15:0] tab_q;
      tabla_mmio #(.MemFile(TablaFile)) u_tabla (
        .clk_i   (clk),
        .req_i   (tab_req),
        .we_i    (data_we),
        .be_i    (data_be[1:0]),
        .idx_i   (data_addr[9:2]),
        .wdata_i (data_wdata[15:0]),
        .rdata_o (tab_q)
      );
      assign tab_rdata = {16'b0, tab_q};
    end else if (Tabla == 2) begin : g_tabla_ram
      tabla_ram #(.NumWords(NumWords), .MemFile(TablaFile)) u_tabla (
        .clk_i   (clk),
        .req_i   (tab_req),
        .we_i    (data_we),
        .be_i    (data_be),
        .idx_i   (data_addr[AddrW+1:2]),
        .wdata_i (data_wdata),
        .rdata_o (tab_rdata)
      );
    end else begin : g_sin_tabla
      assign tab_rdata = 32'b0;
      wire _unused_tab = &{1'b0, tab_req};
    end
  endgenerate

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
  wire spi_precio, spi_decision_wr, spi_cs_activo;
  `POCHOCO_SPI_MODULE u_spi (
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
    .spi_miso_o (o_SPI_MISO),
    .byte_done_o   (spi_precio),
    .decision_wr_o (spi_decision_wr),
    .cs_active_o   (spi_cs_activo)
  );

  // Vigilante y primitiva de warm boot. El disparo manual solo se conecta si
  // VigBoton = 1, a través de un sincronizador de dos etapas.
  generate
    if (Vigilante != 0) begin : g_vig
      wire       boot;
      wire [1:0] sel;
      wire       forzar;
      if (VigBoton != 0) begin : g_boton
        reg [1:0] sw_sync;
        always @(posedge clk or negedge rst_ni) begin
          if (!rst_ni) sw_sync <= 2'b00;
          else         sw_sync <= {sw_sync[0], i_Switch[3]};
        end
        assign forzar = sw_sync[1];
      end else begin : g_sin_boton
        assign forzar = 1'b0;
      end
      vigilante #(.N(VigN), .Destino(VigDestino)) u_vig (
        .clk_i         (clk),
        .rst_ni        (rst_ni),
        .precio_i      (spi_precio),
        .decision_wr_i (spi_decision_wr),
        .cs_activo_i   (spi_cs_activo),
        .forzar_i      (forzar),
        .boot_o        (boot),
        .sel_o         (sel)
      );
      SB_WARMBOOT u_warmboot (
        .BOOT (boot),
        .S1   (sel[1]),
        .S0   (sel[0])
      );
    end else begin : g_sin_vig
      wire _unused_vig = &{1'b0, spi_precio, spi_decision_wr, spi_cs_activo};
    end
  endgenerate

  // 7-seg is active-low on the board
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~seg2;

endmodule
