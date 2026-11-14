// tb_pines.sv: traza de los pines del SoC barrel, para comparar el RTL con la
// netlist sintetizada ciclo a ciclo.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Instancia pochoco_soc, que puede ser el RTL del prototipo o la salida de
// Yosys (con -DNETLIST: la netlist no tiene parámetros y trae el programa
// dentro de las BRAM). Solo usa los pines. Una maestra SPI manda un byte cada
// 287 a 350 ciclos y anota el byte que recibe, y se anota cada cambio de los
// LEDs y del display, todo con su número de ciclo.
//
// El RTL y la netlist son el mismo circuito, así que las dos trazas tienen
// que ser idénticas línea a línea. Con programas aleatorios de cuatro hilos
// que leen STATUS y PRICE y escriben DECISION, LEDs y display, lo que sale por
// los pines depende del banco de registros de los cuatro contextos, de la
// memoria y del esclavo SPI.
//
// La maestra cambia sus señales en el flanco de bajada del reloj, lejos del
// flanco en que el SoC las muestrea, para que la comparación no dependa de
// cómo el simulador ordena los eventos de un mismo instante.
//
// Uso: tools/netlist_aleatorio.sh (make netlist-aleatorio).

`timescale 1ns/1ps

`ifndef CICLOS
  `define CICLOS 34000
`endif
`ifndef TRAZA
  `define TRAZA "pines.txt"
`endif

module tb_pines;
  reg        clk = 1'b0;
  reg        sclk = 1'b0, mosi = 1'b0, cs_n = 1'b1;
  wire       miso;
  wire [3:0] led;
  wire [6:0] seg1, seg2;

`ifdef NETLIST
  pochoco_soc dut (
`else
  pochoco_soc #(.MemFile(`PROGRAMA)) dut (
`endif
    .i_Clk(clk), .o_LED(led), .i_Switch(4'b0110),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  always #20 clk = ~clk;

  integer f, ciclo = 0, n_spi = 0, n_io = 0, n_x = 0;
  reg [3:0]  led_prev;
  reg [13:0] seg_prev;
  reg [15:0] lfsr = 16'hACE1;
  reg [7:0]  rx;
  integer    b;

  // Cambios de las salidas. Los dos primeros ciclos no se miran: en el RTL
  // los registros con reset asíncrono valen X hasta el primer flanco (el
  // simulador no ve bajar el reset en el instante 0) y en la netlist parten
  // en 0, que es lo que hace la FPGA.
  always @(posedge clk) begin
    ciclo = ciclo + 1;
    if (ciclo > 2 && (led !== led_prev || {seg1, seg2} !== seg_prev)) begin
      $fdisplay(f, "%0d io led=%b seg=%b_%b", ciclo, led, seg1, seg2);
      n_io = n_io + 1;
    end
    if (ciclo > 2 && ^{led, seg1, seg2, miso} === 1'bx) n_x = n_x + 1;
    led_prev = led;
    seg_prev = {seg1, seg2};
  end

  // Maestra SPI, modo 0
  initial begin
    f = $fopen(`TRAZA, "w");
    repeat (4200) @(negedge clk);          // el reset de encendido dura 4095 ciclos
    while (ciclo < `CICLOS) begin
      lfsr = {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
      cs_n = 1'b0;
      repeat (25) @(negedge clk);
      for (b = 7; b >= 0; b = b - 1) begin
        mosi = lfsr[b];
        repeat (12) @(negedge clk);
        sclk = 1'b1;
        rx[b] = miso;
        repeat (13) @(negedge clk);
        sclk = 1'b0;
      end
      repeat (12) @(negedge clk);
      cs_n = 1'b1;
      $fdisplay(f, "%0d spi tx=%h rx=%h", ciclo, lfsr[7:0], rx);
      n_spi = n_spi + 1;
      repeat (50 + lfsr[13:8]) @(negedge clk);
    end
    $fclose(f);
    $display("tb_pines: %0d ciclos, %0d transacciones SPI, %0d cambios de LEDs o display, %0d ciclos con X en los pines",
             ciclo, n_spi, n_io, n_x);
    $finish;
  end
endmodule
