// monitor_x2.sv: observador para la prueba de humo del SoC con el reloj doblado.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Se compila como segundo módulo raíz junto al testbench oficial sin
// modificar (iverilog -s tb_proyecto_4 -s monitor_x2) y mira por jerarquía
// las mismas señales que él. Mide dos cosas que el testbench oficial no
// puede medir cuando el reloj interno va al doble:
//
//   1. Cuántos pulsos de byte_done y cuántas escrituras de DECISION hubo de
//      verdad (muestreando con el reloj interno del SoC) y cuántos alcanza a
//      ver el testbench oficial, que muestrea con su reloj de 25 MHz. Cada
//      pulso dura un ciclo del reloj interno, o sea medio ciclo del reloj
//      del testbench.
//   2. La respuesta en ciclos del reloj interno, desde byte_done hasta la
//      escritura de DECISION, y los dos períodos que alternan.
//
// Escribe su resumen al terminar la simulación.

`timescale 1ns/1ps

module monitor_x2;

  int done_real = 0, wr_real = 0;      // con el reloj interno
  int done_tb = 0, wr_tb = 0;          // con el reloj de 25 MHz, como el testbench oficial
  int ciclos = 0, peor = 0, respuestas = 0;
  longint suma = 0;
  bit esperando = 0;

  always @(posedge tb_proyecto_4.dut.clk) begin
    ciclos++;
    if (tb_proyecto_4.dut.u_spi.byte_done) begin
      done_real++;
      ciclos = 0;
      esperando = 1;
    end else if (tb_proyecto_4.dut.u_spi.wr && tb_proyecto_4.dut.u_spi.off == 2) begin
      wr_real++;
      if (esperando) begin
        respuestas++;
        suma += ciclos;
        if (ciclos > peor) peor = ciclos;
        esperando = 0;
      end
    end
  end

  always @(posedge tb_proyecto_4.clk) begin
    if (tb_proyecto_4.dut.u_spi.byte_done) done_tb++;
    if (tb_proyecto_4.dut.u_spi.wr && tb_proyecto_4.dut.u_spi.off == 2) wr_tb++;
  end

  // Períodos del reloj interno y ciclos por cada ciclo del reloj de entrada
  realtime t_ant = 0;
  real per_min = 1.0e9, per_max = 0.0;
  longint flancos_int = 0, flancos_ext = 0;
  always @(posedge tb_proyecto_4.dut.clk) begin
    flancos_int++;
    if (t_ant != 0) begin
      if ($realtime - t_ant < per_min) per_min = $realtime - t_ant;
      if ($realtime - t_ant > per_max) per_max = $realtime - t_ant;
    end
    t_ant = $realtime;
  end
  always @(posedge tb_proyecto_4.clk) flancos_ext++;

  final begin
    $display("MONITOR reloj interno: %0d flancos por %0d del reloj de entrada, periodos de %0.3f a %0.3f ns",
             flancos_int, flancos_ext, per_min, per_max);
    $display("MONITOR byte_done: %0d reales, %0d vistos con el reloj de 25 MHz", done_real, done_tb);
    $display("MONITOR escrituras de DECISION: %0d reales, %0d vistas con el reloj de 25 MHz", wr_real, wr_tb);
    $display("MONITOR respuesta en ciclos del reloj interno: promedio %0.2f, peor caso %0d, %0d respuestas",
             respuestas ? real'(suma) / respuestas : 0.0, peor, respuestas);
  end

endmodule
