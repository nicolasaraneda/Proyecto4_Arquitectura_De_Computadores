// tb_barrel_ticks.sv: mediciones por tick de un programa en el Espino barrel.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es tb/tb_cpi.sv adaptado al core barrel (factibilidad/a_barrel/README.md).
// La maestra SPI, la serie de precios y las dos ventanas por tick son las
// mismas. Qué cambió:
//   - Las señales internas: el barrel no tiene commit, pc_set ni instr_ex.
//     Se usan tb_valid_x, tb_tid_x, tb_taken y tb_instr_x de
//     espino_barrel_core (la instrucción que está en la etapa de ejecución y
//     a qué hilo pertenece).
//   - El conteo global y el modelo de costo: en el barrel sale una
//     instrucción por ciclo y cada hilo completa una cada 4 ciclos.
//   - El conteo por tick separa las instrucciones del hilo gestor (el que
//     lee el precio y escribe DECISION, -DHILO_GESTOR, por defecto 0) de las
//     de todos los hilos.
//   - Se quitó la traza para el gemelo digital: el gemelo no modela el barrel.
//
// Ventanas por tick, que parten cuando llega el precio (byte_done):
//   - respuesta: hasta la escritura de DECISION. Es la que mide el testbench
//     oficial y la que se compara con el presupuesto.
//   - tick completo: hasta que el hilo gestor vuelve a sondear STATUS.
//
// Parámetros (todos con -D): PROGRAMA, SERIE (CSV "tick,price"; sin SERIE los
// precios salen de un LFSR), NTICKS, PERIODO_NS, INICIO_NS, CS_SETUP_NS,
// SCLK_MEDIO_NS, CS_HOLD_NS, POR_BITS, TICKS_CSV, HILO_GESTOR.

`timescale 1ns/1ps

`ifndef PROGRAMA
  `define PROGRAMA "sw/trade.hex"
`endif
`ifndef NTICKS
  `define NTICKS 200
`endif
`ifndef PERIODO_NS
  `define PERIODO_NS 100000
`endif
`ifndef INICIO_NS
  `define INICIO_NS 4000
`endif
`ifndef CS_SETUP_NS
  `define CS_SETUP_NS 1000
`endif
`ifndef SCLK_MEDIO_NS
  `define SCLK_MEDIO_NS 500
`endif
`ifndef CS_HOLD_NS
  `define CS_HOLD_NS 500
`endif
`ifndef POR_BITS
  `define POR_BITS 12
`endif

`ifndef HILO_GESTOR
  `define HILO_GESTOR 0
`endif

module tb_barrel_ticks;

  localparam int SPI_NS = `CS_SETUP_NS + 16 * `SCLK_MEDIO_NS + `CS_HOLD_NS;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;

  pochoco_soc #(.MemFile(`PROGRAMA), .PorBits(`POR_BITS)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // Señales internas
  wire        x_valid = dut.u_core.tb_valid_x;   // instrucción de verdad en la etapa X
  wire [1:0]  x_tid   = dut.u_core.tb_tid_x;     // hilo al que pertenece
  wire        x_taken = dut.u_core.tb_taken;     // salto tomado
  wire [31:0] instr   = dut.u_core.tb_instr_x;
  wire        gestor  = x_valid && x_tid == `HILO_GESTOR;
  wire        spi_wr_dec  = dut.u_spi.wr && dut.u_spi.off == 2;
  wire        spi_rd_stat = dut.u_spi.rd && dut.u_spi.off == 0;
  wire [7:0]  spi_precio  = {dut.u_spi.rx_shift[6:0], dut.u_spi.mosi};

  int         tick_tx = 0;           // transacción en curso (la fija el estímulo)
  logic [7:0] leido [200000];        // byte que la maestra leyó en cada transacción

  // Transacción SPI, modo 0. Con los valores por defecto es la del testbench oficial.
  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #(`CS_SETUP_NS);
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #(`SCLK_MEDIO_NS) sclk = 1;
      recibido[b] = (miso === 1'b1);
      if (b == 0) leido[tick_tx] = recibido;
      #(`SCLK_MEDIO_NS) sclk = 0;
    end
    #(`CS_HOLD_NS) cs_n = 1;
  endtask

  // --- Serie de precios -------------------------------------------------------
  int precio [200000];

`ifdef SERIE
  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(`SERIE, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", `SERIE); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < `NTICKS; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  endtask
`else
  task automatic leer_serie;
    logic [7:0] lfsr = 8'h5A;
    for (int n = 0; n < `NTICKS; n++) begin
      lfsr = {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};   // entre 1 y 255
      precio[n] = lfsr;
    end
  endtask
`endif

  // --- Conteo global, por clase ---------------------------------------------
  // La ventana parte cuando el pipeline ya está lleno (cuarta instrucción
  // válida) y se cierra en un múltiplo de 4 ciclos.
  bit     midiendo = 0;
  longint ciclos = 0, ic = 0, ic_g = 0, n_load = 0, n_store = 0, n_br_t = 0, n_br_nt = 0, n_jump = 0, n_otras = 0;
  longint s_ciclos = 0, s_ic = 0, s_ic_g = 0, s_load = 0, s_store = 0, s_br_t = 0, s_br_nt = 0, s_jump = 0, s_otras = 0;
  int     llenando = 0;

  // --- Conteo por tick ----------------------------------------------------------
  longint ciclo = 0;                 // número del flanco de subida actual
  longint t0 = 0;
  int     tick_m = 0, precio_m = 0;
  int     t_ic = 0, r_ciclos = 0, r_ic = 0;       // instrucciones del hilo gestor
  int     t_ic_todos = 0, r_ic_todos = 0;         // instrucciones de los cuatro hilos
  bit     esp_dec = 0, esp_fin = 0;
  int     ticks_medidos = 0;
  int     peor_r_ciclos = 0, peor_r_ic = 0, peor_t_ciclos = 0, peor_t_ic = 0;
  longint suma_r_ciclos = 0, suma_r_ic = 0, suma_t_ciclos = 0, suma_t_ic = 0;
  longint suma_r_ic_todos = 0, suma_t_ic_todos = 0;
  int     fd_ticks = 0;

  always @(posedge clk) begin
    // Global
    if (midiendo) begin
      ciclos++;
      if (x_valid) begin
        ic++;
        if (gestor) ic_g++;
        case (instr[6:0])
          7'h03:        n_load++;
          7'h23:        n_store++;
          7'h63:        if (x_taken) n_br_t++; else n_br_nt++;
          7'h6f, 7'h67: n_jump++;
          default:      n_otras++;
        endcase
      end
      if (ciclos % 4 == 0) begin
        s_ciclos = ciclos; s_ic = ic; s_ic_g = ic_g; s_load = n_load; s_store = n_store;
        s_br_t = n_br_t; s_br_nt = n_br_nt; s_jump = n_jump; s_otras = n_otras;
      end
    end else if (x_valid) begin
      llenando++;
      if (llenando == 4) midiendo = 1;
    end

    // Por tick
    if (dut.u_spi.byte_done) begin
      t0 = ciclo; t_ic = 0; t_ic_todos = 0; esp_dec = 1; esp_fin = 0;
      tick_m = tick_tx; precio_m = spi_precio;
    end else begin
      if (esp_fin && spi_rd_stat && x_tid == `HILO_GESTOR) begin
        // El programa volvió a sondear: termina el tick completo
        ticks_medidos++;
        suma_r_ciclos += r_ciclos;      suma_r_ic += r_ic;
        suma_t_ciclos += ciclo - t0;    suma_t_ic += t_ic;
        suma_r_ic_todos += r_ic_todos;  suma_t_ic_todos += t_ic_todos;
        if (r_ciclos > peor_r_ciclos)   peor_r_ciclos = r_ciclos;
        if (r_ic > peor_r_ic)           peor_r_ic = r_ic;
        if (ciclo - t0 > peor_t_ciclos) peor_t_ciclos = ciclo - t0;
        if (t_ic > peor_t_ic)           peor_t_ic = t_ic;
        if (fd_ticks != 0)
          $fdisplay(fd_ticks, "%0d,%0d,%02x,%0d,%0d,%0d,%0d,%0d", tick_m, precio_m, leido[tick_m],
                    t0, r_ciclos, r_ic, ciclo - t0, t_ic);
        esp_fin = 0;
      end
      if (gestor)  t_ic++;
      if (x_valid) t_ic_todos++;
      if (esp_dec && spi_wr_dec) begin
        r_ciclos = ciclo - t0; r_ic = t_ic; r_ic_todos = t_ic_todos;
        esp_dec = 0; esp_fin = 1;
      end
    end
    ciclo++;
  end

  // --- Estímulo ---------------------------------------------------------------
  longint modelo;
  logic [7:0] rx;
  real    ns_ciclo = 40.0;

  task automatic fila(input string nombre, input real ic_v, input real ciclos_v);
    $display("  %-28s IC %7.2f   ciclos %7.2f   CPI %5.3f   tiempo %7.3f us   (%6.3f %% de T)",
             nombre, ic_v, ciclos_v, ciclos_v / ic_v, ciclos_v * ns_ciclo / 1000.0,
             100.0 * ciclos_v * ns_ciclo / `PERIODO_NS);
  endtask

  initial begin
    leer_serie();
`ifdef TICKS_CSV
    fd_ticks = $fopen(`TICKS_CSV, "w");
    $fdisplay(fd_ticks, "tick,precio,decision_leida,ciclo_precio,ciclos_respuesta,ic_respuesta,ciclos_tick,ic_tick");
`endif
    #(`INICIO_NS);
    for (int n = 0; n < `NTICKS; n++) begin
      tick_tx = n;
      spi(precio[n][7:0], rx);
      #(`PERIODO_NS - SPI_NS);
    end
    if (fd_ticks != 0) $fclose(fd_ticks);

    modelo = s_ic;
    $display("Programa:                 %s", `PROGRAMA);
    $display("Ticks:                    %0d con periodo de %0d ns", `NTICKS, `PERIODO_NS);
    $display("Hilo gestor:              %0d", `HILO_GESTOR);
    $display("Instrucciones (IC):       %0d de los cuatro hilos, %0d del hilo gestor", s_ic, s_ic_g);
    $display("Ciclos:                   %0d", s_ciclos);
    $display("CPI agregado:             %0.4f", real'(s_ciclos) / real'(s_ic));
    $display("CPI del hilo gestor:      %0.4f", real'(s_ciclos) / real'(s_ic_g));
    $display("  loads:                  %0d", s_load);
    $display("  stores:                 %0d", s_store);
    $display("  branches tomados:       %0d", s_br_t);
    $display("  branches no tomados:    %0d", s_br_nt);
    $display("  jal y jalr:             %0d", s_jump);
    $display("  otras:                  %0d", s_otras);
    $display("Modelo barrel: ciclos = IC de los cuatro hilos = 4 x IC del gestor: %0d y %0d (diferencia con lo medido: %0d y %0d)",
             modelo, 4 * s_ic_g, s_ciclos - modelo, s_ciclos - 4 * s_ic_g);
    if (ticks_medidos > 0) begin
      $display("Por tick, %0d ticks medidos, T = %0d ns, presupuesto %0d ciclos:", ticks_medidos, `PERIODO_NS,
               (`PERIODO_NS - SPI_NS) / 40);
      $display("  (IC del hilo gestor; el CPI es ciclos / IC del gestor)");
      fila("respuesta, promedio",     real'(suma_r_ic) / ticks_medidos, real'(suma_r_ciclos) / ticks_medidos);
      fila("respuesta, peor caso",    real'(peor_r_ic),                 real'(peor_r_ciclos));
      fila("tick completo, promedio", real'(suma_t_ic) / ticks_medidos, real'(suma_t_ciclos) / ticks_medidos);
      fila("tick completo, peor caso", real'(peor_t_ic),                real'(peor_t_ciclos));
    end
    if (ticks_medidos > 0)
      $display("  IC de los cuatro hilos por tick: respuesta %0.2f, tick completo %0.2f",
               real'(suma_r_ic_todos) / ticks_medidos, real'(suma_t_ic_todos) / ticks_medidos);
    if (s_ciclos != modelo || s_ciclos != 4 * s_ic_g) begin
      $display("FAIL el modelo de costo no coincide con lo medido");
      $fatal(1);
    end
    $display("PASS el modelo de costo coincide con lo medido");
    $finish;
  end

endmodule
