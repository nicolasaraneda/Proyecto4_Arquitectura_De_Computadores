// tb_netlist.sv: corre la netlist sintetizada del SoC barrel y revisa las salidas.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El módulo pochoco_soc que se instancia aquí es la salida de Yosys
// (write_verilog después de synth_ice40): LUT4, flip-flops y BRAM del iCE40,
// con el programa dentro de las BRAM. No tiene parámetros ni señales internas
// con nombre, así que solo se miran los pines: después de CICLOS ciclos los
// LEDs y el display deben mostrar lo que el programa deja al terminar.
//
// Comprueba que la síntesis conserva el comportamiento del RTL, en particular
// el banco de registros con cuatro contextos y la memoria compartida.
//
// Uso: tools/netlist.sh (make netlist). Definiciones: CICLOS, LEDS, SEG1, SEG2
// (valores esperados; los segmentos en lógica positiva, antes de la inversión
// de la placa).

`timescale 1ns/1ps

`ifndef CICLOS
  `define CICLOS 24000
`endif

module tb_netlist;
  reg        clk = 1'b0;
  wire [3:0] led;
  wire [6:0] seg1_n, seg2_n;

  pochoco_soc dut (
    .i_Clk(clk), .o_LED(led), .i_Switch(4'b0000),
    .o_Segment1_A(seg1_n[0]), .o_Segment1_B(seg1_n[1]), .o_Segment1_C(seg1_n[2]), .o_Segment1_D(seg1_n[3]),
    .o_Segment1_E(seg1_n[4]), .o_Segment1_F(seg1_n[5]), .o_Segment1_G(seg1_n[6]),
    .o_Segment2_A(seg2_n[0]), .o_Segment2_B(seg2_n[1]), .o_Segment2_C(seg2_n[2]), .o_Segment2_D(seg2_n[3]),
    .o_Segment2_E(seg2_n[4]), .o_Segment2_F(seg2_n[5]), .o_Segment2_G(seg2_n[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

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
