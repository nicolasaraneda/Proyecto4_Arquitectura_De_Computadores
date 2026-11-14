// tb_duplicador.v: testbench del duplicador de reloj, con retardos.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Simula duplicador_reloj con su modelo de retardo (SIM_RETARDO) para un
// caso: semiperíodo alto y bajo del reloj de entrada, retardo de la cadena
// para el flanco de subida y para el de bajada, y retardo común. Los valores
// se pasan con -P al compilar y salen de las mediciones del diseño ruteado
// (scripts/casos_tb.py los toma de scripts/sta_icestorm.py).
//
// Comprueba, sobre NPER períodos del reloj de entrada:
//   1. que el reloj doblado tiene exactamente dos flancos de subida por
//      período de entrada;
//   2. que el ancho de cada pulso es el retardo de la cadena para ese flanco;
//   3. que los períodos alternan y valen el semiperíodo alto y el bajo de la
//      entrada, corridos por la diferencia entre el retardo común de subida
//      y de bajada (aquí es la misma, así que valen exactamente eso);
//   4. que ni el tiempo en alto ni el tiempo en bajo quedan por debajo de
//      PulsoMinPs;
//   5. que un contador en el reloj doblado avanza el doble que uno en el
//      reloj de entrada.
// Imprime PASS o FAIL por comprobación y una línea RESULTADO al final.
//
// Qué demuestra: que la lógica del duplicador y la aritmética de pulsos y
// períodos son las que se describen, con los retardos que se le entregan.
// Qué no demuestra: que esos retardos sean los del chip. Tampoco ve el
// jitter del oscilador, el ancho de pulso mínimo real de la red global ni
// las violaciones de setup de la lógica que use este reloj.

`timescale 1ps/1ps

module tb_duplicador;

  parameter integer AltoPs     = 20000;  // semiperíodo alto del reloj de entrada
  parameter integer BajoPs     = 20000;  // semiperíodo bajo
  parameter integer RetSubePs  = 8000;
  parameter integer RetBajaPs  = 7200;
  parameter integer RetComunPs = 2000;
  parameter integer PulsoMinPs = 1000;   // supuesto, ver README
  parameter integer NPER       = 200;

  reg clk = 1'b0;
  initial begin
    #1000;
    forever begin
      clk = 1'b1; #(AltoPs);
      clk = 1'b0; #(BajoPs);
    end
  end

  wire clk2x, pulso, ret;
  duplicador_reloj #(
    .N(8), .RetSubePs(RetSubePs), .RetBajaPs(RetBajaPs), .RetComunPs(RetComunPs)
  ) dut (
    .clk_i(clk), .clk2x_o(clk2x), .pulso_o(pulso), .ret_o(ret), .toma_o()
  );

  // Contadores para la comprobación 5
  integer cnt1 = 0, cnt2 = 0;
  always @(posedge clk)   cnt1 = cnt1 + 1;
  always @(posedge clk2x) cnt2 = cnt2 + 1;

  // Mediciones sobre el reloj doblado
  time    t_sube = 0, t_sube_ant = 0, t_baja = 0;
  integer n_sube = 0;
  integer alto_min = 1 << 30, alto_max = 0, bajo_min = 1 << 30, bajo_max = 0;
  integer per_min = 1 << 30, per_max = 0;
  integer err_ancho = 0, err_periodo = 0;
  integer ancho, periodo, bajo;
  reg     medir = 1'b0;

  always @(posedge clk2x) begin
    t_sube_ant = t_sube;
    t_sube     = $time;
    if (medir) begin
      n_sube = n_sube + 1;
      if (t_sube_ant != 0) begin
        periodo = t_sube - t_sube_ant;
        if (periodo < per_min) per_min = periodo;
        if (periodo > per_max) per_max = periodo;
        if (periodo != AltoPs && periodo != BajoPs) err_periodo = err_periodo + 1;
        bajo = t_sube - t_baja;
        if (bajo < bajo_min) bajo_min = bajo;
        if (bajo > bajo_max) bajo_max = bajo;
      end
    end
  end

  always @(negedge clk2x) begin
    t_baja = $time;
    if (medir && t_sube != 0) begin
      ancho = t_baja - t_sube;
      if (ancho < alto_min) alto_min = ancho;
      if (ancho > alto_max) alto_max = ancho;
      if (ancho != RetSubePs && ancho != RetBajaPs) err_ancho = err_ancho + 1;
    end
  end

  integer fallas = 0;
  task chequear(input ok, input [8*64-1:0] nombre);
    begin
      if (ok) $display("PASS %0s", nombre);
      else begin $display("FAIL %0s", nombre); fallas = fallas + 1; end
    end
  endtask

  integer c1, c2;
  initial begin
    // Deja pasar los primeros períodos y mide una ventana de NPER períodos
    // completos del reloj de entrada, de flanco de subida a flanco de subida.
    repeat (4) @(posedge clk);
    #1;
    medir = 1'b1; c1 = cnt1; c2 = cnt2;
    repeat (NPER) @(posedge clk);
    #1;
    medir = 1'b0; c1 = cnt1 - c1; c2 = cnt2 - c2;
    #(AltoPs + BajoPs);

    $display("Caso: alto %0d ps, bajo %0d ps, cadena %0d/%0d ps (sube/baja), comun %0d ps",
             AltoPs, BajoPs, RetSubePs, RetBajaPs, RetComunPs);
    $display("Flancos de subida del reloj doblado: %0d en %0d periodos de entrada", n_sube, NPER);
    $display("Tiempo en alto: %0d a %0d ps. Tiempo en bajo: %0d a %0d ps. Periodo: %0d a %0d ps",
             alto_min, alto_max, bajo_min, bajo_max, per_min, per_max);
    chequear(n_sube == 2 * NPER,                 "dos flancos de subida por periodo de entrada");
    chequear(err_ancho == 0 && alto_max != 0,    "el ancho del pulso es el retardo de la cadena");
    chequear(err_periodo == 0 && per_max != 0,   "los periodos alternan entre el semiperiodo alto y el bajo");
    chequear(alto_min >= PulsoMinPs && bajo_min >= PulsoMinPs, "tiempos en alto y en bajo sobre el minimo");
    chequear(c2 == 2 * c1,                       "el contador del reloj doblado avanza el doble");
    if (fallas == 0) $display("RESULTADO: PASS");
    else             $display("RESULTADO: FAIL (%0d comprobaciones)", fallas);
    $finish;
  end

endmodule
