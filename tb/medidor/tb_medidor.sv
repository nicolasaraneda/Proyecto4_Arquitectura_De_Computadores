// tb_medidor.sv: testbench de rtl/medidor/medidor_spi.v.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Una maestra SPI de modo 0 con tiempos configurables manda transacciones al
// medidor, y se compara cada medida con la que corresponde a esos tiempos
// (con un ciclo de tolerancia por la sincronización). Los casos cubren las
// tres rondas del testbench oficial, SCLK de 100 kHz y 115 kHz, tiempos de
// CS_n distintos, una transacción de 7 bits y flancos de SCLK con CS_n en
// alto, que deben encender la alarma. Las
// medidas se leen por los 7 segmentos, apretando los botones como en la
// placa, y no por jerarquía. Con -DCHIP el mismo testbench corre sobre el
// bitstream ruteado (tools/medidor.sh, paso 5).
//
// Uso: make medidor   (iverilog -g2012)

`timescale 1ns/1ps

module tb_medidor;

  reg        clk = 1'b0;
  reg [3:0]  sw = 4'b0000;
  reg        sclk = 1'b0, mosi = 1'b0, cs_n = 1'b1;
  wire [3:0] led;
  wire       a1, b1, c1, d1, e1, f1, g1, a2, b2, c2, d2, e2, f2, g2;
  wire       miso;

  always #20 clk = ~clk;                 // 25 MHz

`ifdef CHIP
  // El bitstream ruteado (tools/chip_vlog.py), construido con REBOTE = 8
  chip dut (
    .i_Clk(clk), .\i_Switch (sw), .\o_LED (led),
    .i_UART_RX(1'b1), .o_UART_TX(),
    .o_Segment1_A(a1), .o_Segment1_B(b1), .o_Segment1_C(c1), .o_Segment1_D(d1),
    .o_Segment1_E(e1), .o_Segment1_F(f1), .o_Segment1_G(g1),
    .o_Segment2_A(a2), .o_Segment2_B(b2), .o_Segment2_C(c2), .o_Segment2_D(d2),
    .o_Segment2_E(e2), .o_Segment2_F(f2), .o_Segment2_G(g2),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));
`else
  medidor_spi #(.REBOTE(8)) dut (
    .i_Clk(clk), .i_Switch(sw), .o_LED(led),
    .o_Segment1_A(a1), .o_Segment1_B(b1), .o_Segment1_C(c1), .o_Segment1_D(d1),
    .o_Segment1_E(e1), .o_Segment1_F(f1), .o_Segment1_G(g1),
    .o_Segment2_A(a2), .o_Segment2_B(b2), .o_Segment2_C(c2), .o_Segment2_D(d2),
    .o_Segment2_E(e2), .o_Segment2_F(f2), .o_Segment2_G(g2),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));
`endif

  integer fallas = 0, pruebas = 0;

  function [3:0] seg2hex(input [6:0] s);  // s = {g, f, e, d, c, b, a}, activo en alto
    case (s)
      7'b0111111: seg2hex = 4'h0;  7'b0000110: seg2hex = 4'h1;
      7'b1011011: seg2hex = 4'h2;  7'b1001111: seg2hex = 4'h3;
      7'b1100110: seg2hex = 4'h4;  7'b1101101: seg2hex = 4'h5;
      7'b1111101: seg2hex = 4'h6;  7'b0000111: seg2hex = 4'h7;
      7'b1111111: seg2hex = 4'h8;  7'b1101111: seg2hex = 4'h9;
      7'b1110111: seg2hex = 4'hA;  7'b1111100: seg2hex = 4'hB;
      7'b0111001: seg2hex = 4'hC;  7'b1011110: seg2hex = 4'hD;
      7'b1111001: seg2hex = 4'hE;  default:    seg2hex = 4'hF;
    endcase
  endfunction

  wire [7:0] visible = {seg2hex(~{g1, f1, e1, d1, c1, b1, a1}), seg2hex(~{g2, f2, e2, d2, c2, b2, a2})};

  task automatic apretar(input integer i);
    begin
      sw[i] = 1'b1; repeat (30) @(posedge clk);
      sw[i] = 1'b0; repeat (30) @(posedge clk);
    end
  endtask

  // Lee la medida m por los 7 segmentos: SW1 hasta que los LED digan m, y SW4
  // para el byte alto.
  task automatic leer(input integer m, output [15:0] v);
    integer k;
    begin
      k = 0;
      while (led[2:0] != m[2:0] && k < 10) begin apretar(0); k = k + 1; end
      repeat (5) @(posedge clk);
      v[7:0] = visible;
      sw[3] = 1'b1; repeat (30) @(posedge clk);
      v[15:8] = visible;
      sw[3] = 1'b0; repeat (30) @(posedge clk);
    end
  endtask

  task automatic revisar(input [8*40-1:0] nombre, input integer m, input integer esperado, input integer tol);
    reg [15:0] v;
    begin
      leer(m, v);
      pruebas = pruebas + 1;
      if ((v > esperado ? v - esperado : esperado - v) > tol) begin
        fallas = fallas + 1;
        $display("FAIL %0s: medida %0d = 0x%04h (%0d), esperado %0d", nombre, m, v, v, esperado);
      end else
        $display("PASS %0s: medida %0d = 0x%04h (%0d), esperado %0d", nombre, m, v, v, esperado);
    end
  endtask

  // Una transacción de nbits bits, modo 0, con los tiempos en ns
  task automatic transaccion(input integer setup, input integer medio, input integer hold, input integer nbits,
                             input [7:0] dato);
    integer i;
    begin
      cs_n = 1'b0;
      #(setup - medio);
      for (i = 0; i < nbits; i = i + 1) begin
        mosi = dato[7 - i];
        #(medio); sclk = 1'b1;
        #(medio); sclk = 1'b0;
      end
      #(hold); cs_n = 1'b1;
    end
  endtask

  // n transacciones con período per (ns, de bajada a bajada de CS_n)
  task automatic ronda(input integer n, input integer per, input integer setup, input integer medio, input integer hold);
    integer i, dur;
    begin
      dur = setup - medio + 16 * medio + hold;
      for (i = 0; i < n; i = i + 1) begin
        transaccion(setup, medio, hold, 8, i[7:0] + 8'd1);
        #(per - dur);
      end
    end
  endtask

  // Revisa las 8 medidas de una ronda con período per, SCLK de medio período
  // medio y CS_n con setup y hold dados (todos en ns)
  task automatic caso(input [8*40-1:0] nombre, input integer n, input integer per, input integer setup,
                      input integer medio, input integer hold);
    integer dur, libre;
    begin
      apretar(2);                        // borrar
      #(1000);
      ronda(n, per, setup, medio, hold);
      dur   = setup - medio + 16 * medio + hold;
      libre = per - dur;
      $display("-- %0s: %0d transacciones, periodo %0d ns, SCLK %0d kHz, setup %0d ns, hold %0d ns",
               nombre, n, per, 500000 / medio, setup, hold);
      revisar(nombre, 0, 2 * medio / 40, 1);
      revisar(nombre, 1, 2 * medio / 40, 1);
      revisar(nombre, 2, per / 640, 1);
      revisar(nombre, 3, per / 640, 1);
      revisar(nombre, 4, dur / 40, 1);
      revisar(nombre, 5, setup / 40, 1);
      revisar(nombre, 6, libre / 40 > 65535 ? 65535 : libre / 40, 1);
      revisar(nombre, 7, n, 0);
      pruebas = pruebas + 1;
      if (led[3]) begin fallas = fallas + 1; $display("FAIL %0s: alarma encendida", nombre); end
      else $display("PASS %0s: alarma apagada", nombre);
    end
  endtask

  initial begin
    repeat (20) @(posedge clk);
    // Las tres rondas del testbench oficial: CS_n baja, 1000 ns, 8 bits a 1 MHz, 500 ns
    caso("ronda 3, oficial", 20, 100000, 1500, 500, 500);
    caso("ronda 2, oficial", 5, 1000000, 1500, 500, 500);
    caso("ronda 1, oficial", 3, 10000000, 1500, 500, 500);
    // SCLK lento en la ronda 3: 100 kHz y 115 kHz
    caso("SCLK 100 kHz", 10, 100000, 15000, 5000, 5000);
    caso("SCLK 115 kHz", 10, 100000, 13040, 4348, 4348);
    // Tiempos de CS_n distintos
    caso("CS_n corto", 10, 50000, 600, 500, 80);
    caso("CS_n largo", 10, 100000, 5000, 500, 3000);
    // Una transacción de 7 bits enciende la alarma
    apretar(2);
    #(1000);
    transaccion(1500, 500, 500, 7, 8'hAA);
    #(90000);
    pruebas = pruebas + 1;
    if (!led[3]) begin fallas = fallas + 1; $display("FAIL transaccion de 7 bits: alarma apagada"); end
    else $display("PASS transaccion de 7 bits: alarma encendida");
    // Y SW3 la borra
    apretar(2);
    pruebas = pruebas + 1;
    if (led[3]) begin fallas = fallas + 1; $display("FAIL SW3 no borra la alarma"); end
    else $display("PASS SW3 borra la alarma");
    // Flancos de SCLK con CS_n en alto (revisión P10): encienden la alarma
    apretar(2);
    #(1000);
    ronda(3, 100000, 1500, 500, 500);
    pruebas = pruebas + 1;
    if (led[3]) begin fallas = fallas + 1; $display("FAIL antes de SCLK con CS_n en alto: alarma encendida"); end
    else $display("PASS antes de SCLK con CS_n en alto: alarma apagada");
    repeat (20) begin #(500); sclk = 1'b1; #(500); sclk = 1'b0; end
    #(2000);
    pruebas = pruebas + 1;
    if (!led[3]) begin fallas = fallas + 1; $display("FAIL SCLK con CS_n en alto: alarma apagada"); end
    else $display("PASS SCLK con CS_n en alto: alarma encendida");
    apretar(2);
    // MISO siempre en 0
    pruebas = pruebas + 1;
    if (miso !== 1'b0) begin fallas = fallas + 1; $display("FAIL MISO no es 0"); end
    else $display("PASS MISO en 0");

    $display("RESUMEN pruebas=%0d fallas=%0d", pruebas, fallas);
    $display("%0s", fallas == 0 ? "PASS: medidor_spi mide lo esperado en todos los casos" : "FAIL");
    $finish;
  end

endmodule
