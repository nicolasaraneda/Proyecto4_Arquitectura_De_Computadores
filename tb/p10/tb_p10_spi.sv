// tb_p10_spi.sv: precios fantasma del esclavo SPI después de una transacción
// de 7 flancos (revisión P10, docs/revision_p10.md, hallazgo sobre byte_done).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// En rtl/pochoco_spi_slave.v, byte_done = sclk_r & (bit_cnt == 7) no mira
// CS_n, y bit_cnt solo vuelve a 0 cuando CS_n baja. Si una transacción termina
// después de 7 flancos de subida (o si el reset de encendido termina a mitad
// de una, con 7 flancos por delante), bit_cnt queda en 7 con CS_n en alto, y
// cada flanco de subida de SCLK que llegue con CS_n en alto es un "precio".
//
// El testbench corre sw/fondo.s en el SoC (R1 o R2 según las definiciones) con
// la transacción del testbench oficial (CS_n baja, 1000 ns, 8 bits a 1 MHz,
// 500 ns) cada 100 us, y en el medio un escenario:
//
//   ESCENARIO=0  control: después de una transacción normal, 20 flancos de
//                SCLK con CS_n en alto. No debe pasar nada.
//   ESCENARIO=1  una transacción de 7 flancos y después 20 flancos de SCLK
//                con CS_n en alto.
//   ESCENARIO=2  la primera transacción empieza 1600 ns antes de que termine
//                el reset de encendido (le quedan 7 flancos al salir del
//                reset), y después 20 flancos de SCLK con CS_n en alto.
//
// Informa cuántos byte_done hubo con CS_n en alto, cuántas escrituras en
// DECISION, y si el vigilante (R2) pidió la reconfiguración. Termina con una
// línea "RESUMEN fantasmas=... boot=... decisiones=...".

`timescale 1ns/1ps

`ifndef ESCENARIO
  `define ESCENARIO 1
`endif

module tb_p10_spi;

  logic clk = 0;
  always #20 clk = ~clk;
  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;
  wire [3:0] leds;
  wire [6:0] seg1, seg2;

  pochoco_soc #(.MemFile(`PROGRAMA)) dut (
    .i_Clk(clk), .o_LED(leds), .i_Switch(4'b0000),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  int fantasmas = 0, precios = 0, decisiones = 0, boot = 0, ciclo_boot = -1, ciclo = 0;
  logic [7:0] ultimo_fantasma = 0;

  always @(posedge clk) begin
    ciclo++;
    if (dut.u_spi.byte_done) begin
      precios++;
      if (!dut.u_spi.cs_active) begin
        fantasmas++;
        ultimo_fantasma = {dut.u_spi.rx_shift[6:0], dut.u_spi.mosi};
      end
    end
    if (dut.u_spi.wr && dut.u_spi.off == 6'd2) decisiones++;
`ifdef ESPINO_VIGILANTE
    if (dut.g_vig.boot && !boot) begin boot = 1; ciclo_boot = ciclo; end
`endif
  end

  task automatic spi(input logic [7:0] enviar, input int nbits);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 8 - nbits; b--) begin
      mosi = enviar[b];
      #500 sclk = 1;
      #500 sclk = 0;
    end
    #500 cs_n = 1;
  endtask

  task automatic sclk_libre(input int n);
    for (int i = 0; i < n; i++) begin
      #500 sclk = 1;
      #500 sclk = 0;
    end
  endtask

  initial begin
    if (`ESCENARIO == 2) begin
      // El reset dura 4095 ciclos: termina en el flanco de 163 780 ns. La
      // transacción empieza 1600 ns antes, así que su primer flanco de SCLK
      // cae durante el reset y le quedan 7 flancos al salir de él.
      #(163800 - 1600);
      spi(8'd100, 8);
      #2000;
      sclk_libre(20);
      #(100000 - 9500 - 22000);
    end else begin
      #4000;
      spi(8'd100, 8);
      #(100000 - 9500);
    end
    for (int n = 1; n < 6; n++) begin
      spi(8'd100 + n, 8);
      #(100000 - 9500);
    end
    if (`ESCENARIO != 2) begin
      if (`ESCENARIO == 1) spi(8'd120, 7);
      else                 spi(8'd120, 8);
      #2000;
      sclk_libre(20);
      #(100000 - 9500 - 22000);
    end
    for (int n = 0; n < 5; n++) begin
      spi(8'd130 + n, 8);
      #(100000 - 9500);
    end
    $display("Escenario %0d: %0d byte_done en total, %0d con CS_n en alto (ultimo precio fantasma %0d), %0d escrituras en DECISION",
             `ESCENARIO, precios, fantasmas, ultimo_fantasma, decisiones);
`ifdef ESPINO_VIGILANTE
    if (boot) $display("El vigilante pidio la reconfiguracion en el ciclo %0d", ciclo_boot);
    else      $display("El vigilante no se disparo");
`endif
    $display("RESUMEN fantasmas=%0d boot=%0d decisiones=%0d precios=%0d", fantasmas, boot, decisiones, precios);
    $finish;
  end

endmodule
