// tb_p10_modo.sv: qué lee una maestra SPI en modo 3 (SCLK en reposo alto)
// (revisión P10, docs/revision_p10.md, observación 4).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El esclavo SPI del curso es de modo 0: carga el byte de DECISION al bajar
// CS_n y lo corre en cada flanco de bajada de SCLK. El testbench oficial es de
// modo 0. Aquí la maestra usa MODO=0 o MODO=3 (SCLK en reposo alto: cada bit
// es una bajada y una subida, y se muestrea en la subida), con la transacción
// del testbench oficial cada 100 us y precios que obligan a comprar y a
// vender. En cada transacción se compara el byte que la maestra arma con el
// que el esclavo tenía en tx_hold al bajar CS_n.
//
// Termina con "RESUMEN modo=... transacciones=... distintos=..." y algunos
// ejemplos.

`timescale 1ns/1ps

`ifndef MODO
  `define MODO 3
`endif

module tb_p10_modo;

  logic clk = 0;
  always #20 clk = ~clk;
  logic sclk = (`MODO == 3), mosi = 0, cs_n = 1;
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

  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      if (`MODO == 3) begin
        #500 sclk = 0;
        #500 sclk = 1;
        recibido[b] = (miso === 1'b1);
      end else begin
        #500 sclk = 1;
        recibido[b] = (miso === 1'b1);
        #500 sclk = 0;
      end
    end
    #500 cs_n = 1;
  endtask

  int n = 0, distintos = 0, ejemplos = 0;
  logic [7:0] leido, esperado;
  int precios [0:7] = '{100, 60, 60, 60, 140, 140, 140, 100};

  initial begin
    #4000;
    for (int t = 0; t < 400; t++) begin
      fork
        spi(precios[(t / 25) % 8], leido);
        begin #100; esperado = dut.u_spi.tx_hold; end
      join
      if (t >= 3) begin
        n++;
        if (leido !== esperado) begin
          distintos++;
          if (ejemplos < 4) begin
            $display("  transaccion %0d: el esclavo tenia %h y la maestra leyo %h", t, esperado, leido);
            ejemplos++;
          end
        end
      end
      #(100000 - 9500);
    end
    $display("RESUMEN modo=%0d transacciones=%0d distintos=%0d", `MODO, n, distintos);
    $finish;
  end

endmodule
