// tb_testigo.sv: simulación de la imagen testigo (rtl/autoprueba/testigo_top.v),
// la imagen 1 de las imágenes múltiples de prueba de R2.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Solo mira pines, así que sirve para el RTL y para el bitstream ruteado
// (-DCHIP, el módulo chip de tools/chip_vlog.py). Comprueba: los cuatro LED
// encendidos, "--" en los 7 segmentos, "00" con SW4 al arrancar, el eco de la
// UART y MISO del PMOD en 0. En el RTL el minuto se acorta a MINUTO ciclos y
// se comprueba además que con SW4 se vea "01" después de un minuto y "02"
// después de dos. Imprime una línea RESULTADO con PASS o FAIL.

`timescale 1ns/1ps

module tb_testigo;

  parameter int MINUTO = 1000;

  logic clk = 0;
  always #20 clk = ~clk;

  logic [3:0] sw = 4'b0000;
  logic       rx = 1'b1;
  wire  [3:0] led;
  wire  [6:0] s1, s2;
  wire        tx, miso_pmod;

`ifdef CHIP
  chip dut (
    .i_Clk(clk), .\i_Switch (sw), .\o_LED (led),
    .i_UART_RX(rx), .o_UART_TX(tx),
    .o_Segment1_A(s1[0]), .o_Segment1_B(s1[1]), .o_Segment1_C(s1[2]), .o_Segment1_D(s1[3]),
    .o_Segment1_E(s1[4]), .o_Segment1_F(s1[5]), .o_Segment1_G(s1[6]),
    .o_Segment2_A(s2[0]), .o_Segment2_B(s2[1]), .o_Segment2_C(s2[2]), .o_Segment2_D(s2[3]),
    .o_Segment2_E(s2[4]), .o_Segment2_F(s2[5]), .o_Segment2_G(s2[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO(miso_pmod));
`else
  testigo_top #(.MINUTO(MINUTO)) dut (
    .i_Clk(clk), .i_Switch(sw), .o_LED(led), .i_UART_RX(rx), .o_UART_TX(tx), .o_SPI_MISO(miso_pmod),
    .o_Segment1_A(s1[0]), .o_Segment1_B(s1[1]), .o_Segment1_C(s1[2]), .o_Segment1_D(s1[3]),
    .o_Segment1_E(s1[4]), .o_Segment1_F(s1[5]), .o_Segment1_G(s1[6]),
    .o_Segment2_A(s2[0]), .o_Segment2_B(s2[1]), .o_Segment2_C(s2[2]), .o_Segment2_D(s2[3]),
    .o_Segment2_E(s2[4]), .o_Segment2_F(s2[5]), .o_Segment2_G(s2[6]));
`endif

  localparam logic [6:0] GUION = ~7'b1000000;   // activos en bajo
  localparam logic [6:0] CERO  = ~7'b0111111;
  localparam logic [6:0] UNO   = ~7'b0000110;
  localparam logic [6:0] DOS   = ~7'b1011011;
  localparam logic [6:0] NUEVE = ~7'b1101111;

  int fallas = 0;

  task automatic comprobar(input bit ok, input string texto);
    if (!ok) fallas++;
    $display("%s %s", ok ? "PASS" : "FAIL", texto);
  endtask

  initial begin
    #1000;
    comprobar(led === 4'b1111, $sformatf("los cuatro LED encendidos (%b)", led));
    comprobar(s1 === GUION && s2 === GUION, "los 7 segmentos muestran --");
    sw[3] = 1;
    #100;
    comprobar(s1 === CERO && s2 === CERO, "con SW4 muestran 00 al arrancar");
    sw[3] = 0;
    for (int i = 0; i < 8; i++) begin
      rx = i[0];
      #100;
      if (tx !== rx || miso_pmod !== 1'b0) fallas++;
    end
    comprobar(fallas == 0, "eco de la UART y MISO del PMOD en 0");
    rx = 1'b1;
`ifndef CHIP
    #(longint'(MINUTO) * 40);
    sw[3] = 1;
    #100;
    comprobar(s1 === CERO && s2 === UNO, "con SW4 muestran 01 después de un minuto");
    #(longint'(MINUTO) * 40);
    comprobar(s1 === CERO && s2 === DOS, "con SW4 muestran 02 después de dos minutos");
    #(longint'(MINUTO) * 40 * 120);
    comprobar(s1 === NUEVE && s2 === NUEVE, "con SW4 muestran 99 después de 122 minutos (se detiene)");
    sw[3] = 0;
    #100;
    comprobar(s1 === GUION && s2 === GUION && led === 4'b1111, "al soltar SW4 vuelve a --");
`endif
    $display("RESULTADO testigo %s", fallas == 0 ? "PASS" : "FAIL");
    $finish;
  end

endmodule
