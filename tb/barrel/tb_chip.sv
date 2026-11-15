// tb_chip.sv: simula un bitstream del SoC barrel por los pines y revisa LEDs y display.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El módulo chip es lo que tools/chip_vlog.py (icebox_vlog) reconstruye desde
// el .asc del place and route: lo mismo que icepack empaqueta en el .bin que
// se graba en la placa, con el contenido inicial de las BRAM. Los nombres de
// los puertos son los del goboard.pcf. El reset de encendido es el de la
// placa (4095 ciclos), así que hay que simular más que eso.
//
// Sirve para saber qué se debe ver en la Go Board antes de programarla: los
// segmentos son activos en bajo, igual que en la placa.
//
// Uso: tools/barrel/bitstream.sh (make barrel-bitstream). Definiciones: CICLOS, LEDS, SEG1,
// SEG2 (segmentos en lógica positiva, {G, F, E, D, C, B, A}).

`timescale 1ns/1ps

`ifndef CICLOS
  `define CICLOS 12000
`endif

module tb_chip;
  reg        clk = 1'b0;
  wire [3:0] led;
  wire [6:0] seg1_n, seg2_n;
  wire       miso;

  chip dut (
    .i_Clk(clk), .\i_Switch (4'b0000), .\o_LED (led),
    .i_UART_RX(1'b1), .o_UART_TX(1'b1),
    .o_Segment1_A(seg1_n[0]), .o_Segment1_B(seg1_n[1]), .o_Segment1_C(seg1_n[2]), .o_Segment1_D(seg1_n[3]),
    .o_Segment1_E(seg1_n[4]), .o_Segment1_F(seg1_n[5]), .o_Segment1_G(seg1_n[6]),
    .o_Segment2_A(seg2_n[0]), .o_Segment2_B(seg2_n[1]), .o_Segment2_C(seg2_n[2]), .o_Segment2_D(seg2_n[3]),
    .o_Segment2_E(seg2_n[4]), .o_Segment2_F(seg2_n[5]), .o_Segment2_G(seg2_n[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO(miso));

  always #20 clk = ~clk;

  wire [6:0] seg1 = ~seg1_n;
  wire [6:0] seg2 = ~seg2_n;
  bit ok = 1;

  initial begin
    repeat (`CICLOS) @(posedge clk);
    #1;
    $display("LEDs = %b, display = %b %b", led, seg1, seg2);
    if (led !== `LEDS)  begin $display("FAIL LEDs: se esperaba %b", 4'(`LEDS)); ok = 0; end
    if (seg1 !== `SEG1) begin $display("FAIL digito 1: se esperaba %b", 7'(`SEG1)); ok = 0; end
    if (seg2 !== `SEG2) begin $display("FAIL digito 2: se esperaba %b", 7'(`SEG2)); ok = 0; end
    if (ok) $display("RESULTADO: PASS");
    else    $display("RESULTADO: FAIL");
    $finish;
  end
endmodule
