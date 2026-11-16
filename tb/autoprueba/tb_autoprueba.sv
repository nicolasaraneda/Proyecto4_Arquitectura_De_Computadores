// tb_autoprueba.sv: simulación del bitstream de autoprueba (rtl/autoprueba/,
// docs/autoprueba.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Hace lo mismo que una persona con la placa: espera, aprieta el botón del
// período, espera a que se encienda LED2 y lee la firma en los 7 segmentos,
// con y sin SW4. No mira señales internas: solo los pines, así que sirve igual
// para el RTL (autoprueba_top) y para el bitstream ya ruteado (el módulo chip
// que arma tools/chip_vlog.py desde el .asc, con -DCHIP).
//
// Plusargs: +BOTON=1|2|3 (SW1 10 ms, SW2 1 ms, SW3 0,1 ms), +FIRMA=hhhh (la
// esperada, en hexadecimal), +LIMITE_MS=30000 (tiempo simulado máximo).
// Imprime una línea RESULTADO y termina con PASS o FAIL.

`timescale 1ns/1ps

module tb_autoprueba;

  // Solo para el RTL: el programa y la firma esperada que lleva adentro
  // (en el bitstream ya vienen fijados)
  parameter string       PROGRAMA = "sw/trade.hex";
  parameter logic [15:0] FIRMA_P  = 16'h0000;

  logic clk = 0;
  always #20 clk = ~clk;

  logic [3:0] sw = 4'b0000;
  wire  [3:0] led;
  wire  [6:0] s1, s2;            // A..G de cada dígito, activos en bajo

`ifdef CHIP
  chip dut (
    .i_Clk(clk), .\i_Switch (sw), .\o_LED (led),
    .i_UART_RX(1'b1), .o_UART_TX(),
    .o_Segment1_A(s1[0]), .o_Segment1_B(s1[1]), .o_Segment1_C(s1[2]), .o_Segment1_D(s1[3]),
    .o_Segment1_E(s1[4]), .o_Segment1_F(s1[5]), .o_Segment1_G(s1[6]),
    .o_Segment2_A(s2[0]), .o_Segment2_B(s2[1]), .o_Segment2_C(s2[2]), .o_Segment2_D(s2[3]),
    .o_Segment2_E(s2[4]), .o_Segment2_F(s2[5]), .o_Segment2_G(s2[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());
`else
  autoprueba_top #(.MemFile(PROGRAMA), .FIRMA_ESPERADA(FIRMA_P)) dut (
    .i_Clk(clk), .i_Switch(sw), .o_LED(led),
    .o_Segment1_A(s1[0]), .o_Segment1_B(s1[1]), .o_Segment1_C(s1[2]), .o_Segment1_D(s1[3]),
    .o_Segment1_E(s1[4]), .o_Segment1_F(s1[5]), .o_Segment1_G(s1[6]),
    .o_Segment2_A(s2[0]), .o_Segment2_B(s2[1]), .o_Segment2_C(s2[2]), .o_Segment2_D(s2[3]),
    .o_Segment2_E(s2[4]), .o_Segment2_F(s2[5]), .o_Segment2_G(s2[6]));
`endif

  // Lee un dígito de los 7 segmentos (activos en bajo). -1 si no es un dígito.
  function automatic int digito(input logic [6:0] s);
    case (~s)
      7'b0111111: return 0;  7'b0000110: return 1;  7'b1011011: return 2;  7'b1001111: return 3;
      7'b1100110: return 4;  7'b1101101: return 5;  7'b1111101: return 6;  7'b0000111: return 7;
      7'b1111111: return 8;  7'b1101111: return 9;  7'b1110111: return 10; 7'b1111100: return 11;
      7'b0111001: return 12; 7'b1011110: return 13; 7'b1111001: return 14; 7'b1110001: return 15;
      default: return -1;
    endcase
  endfunction

  int boton = 3, limite_ms = 30000;
  logic [15:0] esperada = 16'h0000;
  int alto, bajo, d1, d2;
  longint t_inicio, t_fin;

  initial begin
    void'($value$plusargs("BOTON=%d", boton));
    void'($value$plusargs("FIRMA=%h", esperada));
    void'($value$plusargs("LIMITE_MS=%d", limite_ms));
    if (boton < 1 || boton > 3) begin $display("ERROR: +BOTON debe ser 1, 2 o 3"); $finish; end

    // Placa encendida y SoC fuera de reset (164 us): recién ahí se aprieta
    #500_000;
    if (led !== 4'b0000) begin $display("FAIL LED encendidos antes de partir: %b", led); $finish; end
    sw[boton - 1] = 1;
    #2_000_000;                       // 2 ms apretado, como una persona
    sw[boton - 1] = 0;
    t_inicio = $time;

    fork
      wait (led[1] === 1'b1);
      #(longint'(limite_ms) * 1_000_000);
    join_any
    t_fin = $time;
    if (led[1] !== 1'b1) begin
      $display("RESULTADO boton=%0d FAIL: no termino en %0d ms simulados (LED %b)", boton, limite_ms, led);
      $finish;
    end
    #1000;
    d1 = digito(s1); d2 = digito(s2); bajo = (d1 << 4) | d2;
    sw[3] = 1;
    #1000;
    d1 = digito(s1); d2 = digito(s2); alto = (d1 << 4) | d2;
    sw[3] = 0;
    #1000;
    if (d1 < 0 || d2 < 0 || bajo < 0) begin
      $display("RESULTADO boton=%0d FAIL: los 7 segmentos no muestran digitos", boton); $finish;
    end
    $display("RESULTADO boton=%0d firma=%02x%02x esperada=%04x LED=%b duracion_ms=%0d %s", boton, alto, bajo,
             esperada, led, (t_fin - t_inicio) / 1_000_000,
             ({alto[7:0], bajo[7:0]} == esperada && led == 4'b0110) ? "PASS" : "FAIL");
    $finish;
  end

endmodule
