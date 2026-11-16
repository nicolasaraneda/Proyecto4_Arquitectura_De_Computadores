// tb_placa_x2.v: testbench de la prueba de placa del duplicador (rtl/placa_x2.v).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Simula placa_x2 con su modelo de retardo (SIM_RETARDO) y contadores
// cortos, y recorre lo mismo que se hace con la placa en la mano:
//   1. Sin botones: el contador del reloj doblado avanza el doble, los
//      displays muestran los bits altos de cada contador, LED1 encendido y
//      LED2 apagado, y el pin de prueba entrega el reloj doblado dividido
//      por 2.
//   2. SW3 (toma de 2 LUT): cambia la toma en marcha, se borra el error con
//      SW4 y la prueba vuelve a quedar en verde.
//   3. SW1 (sin cadena): con los parámetros de este testbench el pulso
//      queda más angosto que el mínimo del modelo, el reloj doblado se
//      detiene y la prueba lo avisa (LED1 apagado, LED2 encendido). Al
//      soltar el botón y borrar con SW4 se recupera.
//   4. SW4 sostenido: el anillo corre, los displays muestran su medición y
//      el pin de prueba entrega el pulso crudo.
// Con Control = 1 la cadena completa se alarga hasta casi llenar el
// semiperíodo: el hueco entre pulsos queda bajo el mínimo y la prueba tiene
// que marcar error. Es el control negativo.
//
// Qué demuestra: que la lógica de la prueba (contadores, comparador,
// detección de reloj detenido, medición del anillo, displays y pin de
// prueba) hace lo que el encabezado de placa_x2.v dice. Qué no demuestra:
// nada sobre los retardos reales. El ancho mínimo de pulso, el retardo de
// cada LUT y el período del anillo aquí son parámetros.

`timescale 1ps/1ps

module tb_placa_x2;

  parameter integer Control     = 0;
  parameter integer RetCadenaPs = 9000;    // cadena completa
  parameter integer RetMuxPs    = 1500;
  parameter integer PulsoMinPs  = 2000;    // exagerado, para que la toma sin cadena falle
  parameter integer RetComunPs  = 3000;
  parameter integer RetAnilloPs = 8400;

  localparam integer ContBits = 12;
  localparam integer VentBits = 6;
  localparam integer VentAniBits = 10;
  localparam integer NRet = 8;
  localparam integer VENTANA = (1 << VentBits) * 40000;      // ps
  localparam integer VENTANA_ANI = (1 << VentAniBits) * 40000;

  reg clk = 1'b0;
  always #20000 clk = ~clk;

  reg  [3:0] sw = 4'b0000;
  wire [3:0] led;
  wire [6:0] s1, s2;
  wire       prueba;

  placa_x2 #(
    .NRet(NRet), .ContBits(ContBits), .VentBits(VentBits), .VentAniBits(VentAniBits),
    .RetSubePs(RetCadenaPs), .RetBajaPs(RetCadenaPs), .RetMuxPs(RetMuxPs),
    .RetComunPs(RetComunPs), .PulsoMinPs(PulsoMinPs), .RetAnilloPs(RetAnilloPs)
  ) dut (
    .i_Clk(clk), .i_Switch(sw), .o_LED(led),
    .o_Segment1_A(s1[0]), .o_Segment1_B(s1[1]), .o_Segment1_C(s1[2]), .o_Segment1_D(s1[3]),
    .o_Segment1_E(s1[4]), .o_Segment1_F(s1[5]), .o_Segment1_G(s1[6]),
    .o_Segment2_A(s2[0]), .o_Segment2_B(s2[1]), .o_Segment2_C(s2[2]), .o_Segment2_D(s2[3]),
    .o_Segment2_E(s2[4]), .o_Segment2_F(s2[5]), .o_Segment2_G(s2[6]),
    .o_Prueba(prueba)
  );

  // Decodificador de referencia, escrito aparte del de placa_x2: segmentos
  // encendidos (G..A) de cada dígito hexadecimal.
  function [6:0] segmentos;
    input [3:0] h;
    begin
      case (h)
        4'h0: segmentos = 7'h3F; 4'h1: segmentos = 7'h06; 4'h2: segmentos = 7'h5B; 4'h3: segmentos = 7'h4F;
        4'h4: segmentos = 7'h66; 4'h5: segmentos = 7'h6D; 4'h6: segmentos = 7'h7D; 4'h7: segmentos = 7'h07;
        4'h8: segmentos = 7'h7F; 4'h9: segmentos = 7'h6F; 4'hA: segmentos = 7'h77; 4'hB: segmentos = 7'h7C;
        4'hC: segmentos = 7'h39; 4'hD: segmentos = 7'h5E; 4'hE: segmentos = 7'h79; default: segmentos = 7'h71;
      endcase
    end
  endfunction

  integer fallas = 0;
  task chequear(input ok, input [8*80-1:0] nombre);
    begin
      if (ok) $display("PASS %0s", nombre);
      else begin $display("FAIL %0s", nombre); fallas = fallas + 1; end
    end
  endtask

  // Mediciones del pin de prueba
  time    tp_sube = 0, tp_ant = 0, tp_baja = 0;
  integer per_prueba = 0, alto_prueba = 0;
  always @(posedge prueba) begin
    tp_ant = tp_sube; tp_sube = $time;
    if (tp_ant != 0) per_prueba = tp_sube - tp_ant;
  end
  always @(negedge prueba) begin
    tp_baja = $time;
    if (tp_sube != 0) alto_prueba = tp_baja - tp_sube;
  end

  integer c1, c2, d_esp, i;
  reg [6:0] seg_ok;
  initial begin
    if (Control) begin
      #(8 * VENTANA);
      $display("Control negativo: cadena de %0d ps con semiperiodo de 20000 ps", RetCadenaPs + RetMuxPs);
      chequear(led[0] === 1'b0 && led[1] === 1'b1, "la prueba marca error (LED1 apagado, LED2 encendido)");
    end else begin
      // 1. Sin botones
      #(6 * VENTANA);
      @(negedge clk); c1 = dut.cnt1_q; c2 = dut.cnt2_q;
      #(40000 * 300);
      @(negedge clk); c1 = dut.cnt1_q - c1; c2 = dut.cnt2_q - c2;
      $display("Sin botones: %0d ciclos de 25 MHz, %0d del reloj doblado", c1, c2);
      chequear(c2 >= 2 * c1 - 1 && c2 <= 2 * c1 + 1, "el contador del reloj doblado avanza el doble");
      chequear(led[0] === 1'b1 && led[1] === 1'b0, "LED1 encendido y LED2 apagado");
      seg_ok = 0;
      for (i = 0; i < 40; i = i + 1) begin      // en varios instantes, lejos de los flancos
        @(negedge clk); #7000;
        if (~s1 !== segmentos(dut.cnt1_q[ContBits-1:ContBits-4])) seg_ok[0] = 1;
        if (~s2 !== segmentos(dut.cnt2_q[ContBits-1:ContBits-4])) seg_ok[1] = 1;
        #(40000 * 97);
      end
      chequear(seg_ok == 0, "los displays muestran los bits altos de cada contador");
      chequear(per_prueba == 40000, "pin de prueba: reloj doblado dividido por 2 (periodo de 40 ns)");

      // 2. Toma de 2 LUT
      sw = 4'b0100;
      #(3 * VENTANA);
      sw = 4'b1100; #(40000 * 8); sw = 4'b0100;
      #(5 * VENTANA);
      chequear(led[0] === 1'b1 && led[1] === 1'b0, "SW3 (toma de 2 LUT): en verde despues de borrar con SW4");

      // 3. Sin cadena: pulso bajo el mínimo del modelo
      sw = 4'b0001;
      #(5 * VENTANA);
      $display("SW1: pulso ideal de %0d ps con minimo de %0d ps", RetMuxPs, PulsoMinPs);
      chequear(led[0] === 1'b0 && led[1] === 1'b1, "SW1 (sin cadena): reloj detenido, la prueba marca error");
      sw = 4'b0000;
      #(4 * VENTANA);
      chequear(led[1] === 1'b1, "el error queda retenido al soltar SW1");
      sw = 4'b1000; #(40000 * 8); sw = 4'b0000;
      #(5 * VENTANA);
      chequear(led[0] === 1'b1 && led[1] === 1'b0, "en verde otra vez despues de borrar con SW4");

      // 4. Anillo
      sw = 4'b1000;
      #(3 * VENTANA_ANI + 40000 * 20);
      d_esp = (1280 * 1000) / (2 * RetAnilloPs);
      $display("SW4: el anillo mide D = %0d (0x%02x). Esperado 1280 / %0.2f ns = %0d", dut.dani_q, dut.dani_q,
               2 * RetAnilloPs / 1000.0, d_esp);
      chequear(dut.dani_q >= d_esp - 1 && dut.dani_q <= d_esp + 1, "la medicion del anillo es 1280 / periodo");
      chequear(~s1 === segmentos(dut.dani_q[7:4]) && ~s2 === segmentos(dut.dani_q[3:0]),
               "con SW4 los displays muestran la medicion del anillo");
      $display("SW4: pulso crudo en el pin de prueba, %0d ps en alto", alto_prueba);
      chequear(alto_prueba == RetCadenaPs + RetMuxPs, "con SW4 el pin de prueba entrega el pulso crudo");
      sw = 4'b0000;
      #(2 * VENTANA_ANI);
      chequear(dut.dani_q >= d_esp - 1 && dut.dani_q <= d_esp + 1, "la medicion queda guardada al soltar SW4");
      chequear(led[0] === 1'b1 && led[1] === 1'b0, "el duplicador sigue en verde despues de usar el anillo");
    end
    if (fallas == 0) $display("RESULTADO: PASS");
    else             $display("RESULTADO: FAIL (%0d comprobaciones)", fallas);
    $finish;
  end

endmodule
