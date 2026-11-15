// tb_estres.sv: maestra SPI configurable para la matriz de estrés y el barrido
// de fases de la puerta de simulación (CLAUDE.md, sección 16.4, criterios 4 y 7).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Parte del testbench oficial (tb/tb_proyecto_4.sv), que no se modifica. Mismo
// SoC, misma forma de la transacción (SPI modo 0, MSB primero) y misma medición
// de ciclos entre byte_done y la primera escritura en DECISION. Lo que cambia se
// fija en tiempo de ejecución con plusargs, para compilar una sola vez:
//
//   +PROGRAMA=sw/trade.hex   (solo informativo: el programa se elige al compilar
//                             con -GPROGRAMA, igual que MemFile)
//   +SERIE=archivo.csv       CSV "tick,precio" con todas las rondas seguidas
//   +NTICKS=2000             ticks totales a enviar (suma de las rondas)
//   +RONDA_TICKS=0           largo de cada ronda; 0 es una sola ronda
//   +PAUSA_NS=0              pausa entre rondas, sin reset de la placa
//   +PERIODO_NS=100000       período de la primera ronda
//   +PERIODO2_NS, +PERIODO3_NS  período de la segunda y de la tercera ronda en
//                            adelante (por defecto el de la primera)
//   +INICIO_NS=4000          cuándo baja CS_n por primera vez
//   +SCLK_MEDIO_NS=500       medio período de SCLK (500 es 1 MHz)
//   +CS_SETUP_NS=1500        de la bajada de CS_n al primer flanco de subida
//   +CS_HOLD_NS=500          del último flanco de bajada a la subida de CS_n
//   +SALIDA=archivo.csv      escribe "tick,precio,decision" (lo que lee la maestra)
//
// Con los valores por defecto la transacción es la del oficial: 9500 ns.
// Al final imprime una línea RESUMEN con los conteos que usa tools/estres.py.

`timescale 1ns/1ps

module tb_estres;

  parameter string PROGRAMA = "sw/trade.hex";

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;

  pochoco_soc #(.MemFile(PROGRAMA)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // Configuración en tiempo de ejecución
  string serie = "tb/practica.csv", salida = "build/estres/salida.csv";
  int ntick = 2000, ronda_ticks = 0;
  longint pausa_ns = 0, periodo_ns = 100000, periodo2_ns = -1, periodo3_ns = -1;
  longint inicio_ns = 4000, sclk_medio_ns = 500, cs_setup_ns = 1500, cs_hold_ns = 500;

  int precio [];

  task automatic leer_serie;
    int fd, t, r, n;
    string encabezado;
    precio = new[ntick];
    fd = $fopen(serie, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", serie); $finish; end
    r = $fgets(encabezado, fd);
    for (n = 0; n < ntick; n++) begin
      r = $fscanf(fd, "%d,%d\n", t, precio[n]);
      if (r != 2) begin $display("ERROR: %s tiene %0d ticks", serie, n); $finish; end
    end
    $fclose(fd);
  endtask

  int bits_x = 0;

  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #(cs_setup_ns - sclk_medio_ns);
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #(sclk_medio_ns) sclk = 1;
      if (miso !== 1'b0 && miso !== 1'b1) bits_x++;
      recibido[b] = (miso === 1'b1);
      #(sclk_medio_ns) sclk = 0;
    end
    #(cs_hold_ns) cs_n = 1;
  endtask

  // Igual que el oficial: ciclos entre byte_done y la primera escritura en
  // DECISION. Además cuenta los precios que llegaron y los que no tuvieron
  // respuesta antes del siguiente.
  int ciclos = 0, peor_caso = 0, respuestas = 0, precios_perdidos = 0, recibidos = 0, sin_respuesta = 0;
  longint suma_ciclos = 0;
  bit esperando = 0;

  always @(posedge clk) begin
    ciclos++;
    if (dut.u_spi.byte_done) begin
      if (dut.u_spi.new_price_q) precios_perdidos++;
      if (esperando) sin_respuesta++;
      recibidos++;
      ciclos = 0;
      esperando = 1;
    end else if (esperando && dut.u_spi.wr && dut.u_spi.off == 2) begin
      if (ciclos > peor_caso) peor_caso = ciclos;
      suma_ciclos += ciclos;
      respuestas++;
      esperando = 0;
    end
  end

  logic [7:0] decision;
  int fd;
  longint dur, per, presupuesto, presupuesto_min = 64'h7fffffff;

  initial begin
    void'($value$plusargs("SERIE=%s", serie));
    void'($value$plusargs("SALIDA=%s", salida));
    void'($value$plusargs("NTICKS=%d", ntick));
    void'($value$plusargs("RONDA_TICKS=%d", ronda_ticks));
    void'($value$plusargs("PAUSA_NS=%d", pausa_ns));
    void'($value$plusargs("PERIODO_NS=%d", periodo_ns));
    void'($value$plusargs("PERIODO2_NS=%d", periodo2_ns));
    void'($value$plusargs("PERIODO3_NS=%d", periodo3_ns));
    void'($value$plusargs("INICIO_NS=%d", inicio_ns));
    void'($value$plusargs("SCLK_MEDIO_NS=%d", sclk_medio_ns));
    void'($value$plusargs("CS_SETUP_NS=%d", cs_setup_ns));
    void'($value$plusargs("CS_HOLD_NS=%d", cs_hold_ns));
    if (periodo2_ns < 0) periodo2_ns = periodo_ns;
    if (periodo3_ns < 0) periodo3_ns = periodo2_ns;
    if (cs_setup_ns < sclk_medio_ns) begin
      $display("ERROR: CS_SETUP_NS debe ser al menos SCLK_MEDIO_NS"); $finish;
    end
    dur = cs_setup_ns + 15 * sclk_medio_ns + cs_hold_ns;    // duración de la transacción

    leer_serie();
    fd = $fopen(salida, "w");
    $fdisplay(fd, "tick,precio,decision");
    #(inicio_ns);

    for (int n = 0; n < ntick; n++) begin
      int r = (ronda_ticks > 0) ? n / ronda_ticks : 0;
      per = (r == 0) ? periodo_ns : (r == 1) ? periodo2_ns : periodo3_ns;
      if (ronda_ticks > 0 && n > 0 && n % ronda_ticks == 0) #(pausa_ns);
      spi(precio[n][7:0], decision);
      $fdisplay(fd, "%0d,%0d,%02h", n, precio[n], decision);
      presupuesto = (per - dur) / 40;
      if (presupuesto < presupuesto_min) presupuesto_min = presupuesto;
      if (per <= dur) begin $display("ERROR: el periodo no alcanza para la transaccion"); $finish; end
      #(per - dur);
    end
    $fclose(fd);
    if (esperando) sin_respuesta++;

    $display("RESUMEN ticks=%0d recibidos=%0d respuestas=%0d sin_respuesta=%0d precios_perdidos=%0d bits_x=%0d peor_caso=%0d suma_ciclos=%0d presupuesto=%0d",
             ntick, recibidos, respuestas, sin_respuesta, precios_perdidos, bits_x, peor_caso, suma_ciclos, presupuesto_min);
    $finish;
  end

endmodule
