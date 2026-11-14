// tb_relevo.sv: simula el relevo completo, desde que el programa se cuelga
// hasta que la imagen de respaldo vuelve a operar.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// La reconfiguración de la FPGA no se puede simular con el RTL. Aquí se
// modela con tres fases y lo que dicen los documentos de Lattice:
//
//   fase 0  corre el SoC principal (copia con vigilante). Su programa responde
//           a los primeros K precios y después se cuelga (sw/cuelgue.s).
//   fase 1  desde DBOOT_NS después de que el vigilante sube BOOT, y hasta
//           TCFG_NS después de BOOT: la FPGA se está reconfigurando. Ningún
//           SoC tiene reloj y el pin MISO está en alta impedancia. La maestra
//           lee el nivel TIRON: 1 si manda el pull-up interno del iCE40, 0 si
//           la maestra tuviera un pull-down más fuerte. Con DBOOT_NS mayor
//           que 0 el SoC principal sigue manejando el pin ese tiempo: sirve
//           para ver qué pasa si el pin tarda en soltarse.
//   fase 2  corre el SoC de respaldo (core base, sw/trade.hex) partiendo de
//           cero: reset de 4095 ciclos y programa desde el comienzo.
//
// La maestra es la del testbench oficial (misma transacción, misma
// contabilidad). El testbench informa en qué tick dispara el vigilante,
// cuántos ticks lee la maestra con el pin suelto y qué bytes ve, si alguna
// transacción queda cortada por un cambio de fase, cuántas órdenes se
// ejecutan durante el corte y cuándo vuelve a operar el respaldo.
//
// Lo que este testbench NO demuestra: que la placa real se comporte como el
// modelo (duración de la fase 1, nivel del pin suelto). Eso se mide en la
// placa y con la maestra real.
//
// Macros: PERIODO_NS, TCFG_NS, DBOOT_NS, TIRON, NTICKS, PROG_PRINCIPAL,
// PROG_RESPALDO, SERIE, SALIDA.

`timescale 1ns/1ps

`ifndef PERIODO_NS
  `define PERIODO_NS 100000
`endif
`ifndef TCFG_NS
  `define TCFG_NS 53000000
`endif
`ifndef DBOOT_NS
  `define DBOOT_NS 0
`endif
`ifndef TIRON
  `define TIRON 1'b1
`endif
`ifndef NTICKS
  `define NTICKS 700
`endif
`ifndef PROG_PRINCIPAL
  `define PROG_PRINCIPAL "factibilidad/e_warmboot/build/cuelgue_k20.hex"
`endif
`ifndef PROG_RESPALDO
  `define PROG_RESPALDO "sw/trade.hex"
`endif
`ifndef SERIE
  `define SERIE "tb/practica.csv"
`endif
`ifndef SALIDA
  `define SALIDA "relevo.csv"
`endif

module tb_relevo;

  localparam int PERIODO_NS = `PERIODO_NS;
  // TCFG_NS y DBOOT_NS también se pueden pasar al correr (+tcfg=, +dboot=),
  // para barrerlos sin compilar de nuevo.
  int TCFG_NS    = `TCFG_NS;
  int DBOOT_NS   = `DBOOT_NS;
  localparam int NTICKS     = `NTICKS;
  localparam int CAJA0      = 10000;
  localparam int COMISION   = 5;
  localparam int SPI_NS     = 9500;

  logic clk = 0;
  always #20 clk = ~clk;

  // Fases del relevo. Cambian en el flanco de bajada para no recortar el reloj.
  int  fase = 0;
  wire clk_prin = clk & (fase == 0);
  wire clk_resp = clk & (fase == 2);

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso_prin, miso_resp;
  wire  miso = (fase == 0) ? miso_prin : (fase == 1) ? `TIRON : miso_resp;

  pochoco_soc #(.MemFile(`PROG_PRINCIPAL), .Vigilante(1)) u_prin (
    .i_Clk(clk_prin), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso_prin));

  pochoco_soc #(.MemFile(`PROG_RESPALDO), .Vigilante(0)) u_resp (
    .i_Clk(clk_resp), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso_resp));

  // --- Modelo de la reconfiguración -------------------------------------------
  longint t_boot = -1, t_vuelta = -1;
  int     tick_actual = -1, tick_boot = -1, tick_vuelta = -1;
  bit     cs_bajo_al_boot = 0;
  int     s_boot = -1;

  always @(negedge clk) begin
    if (fase == 0 && t_boot < 0 && u_prin.g_vig.boot === 1'b1) begin
      t_boot          = $time;
      tick_boot       = tick_actual;
      cs_bajo_al_boot = (cs_n === 1'b0);
      s_boot          = {u_prin.g_vig.u_warmboot.S1, u_prin.g_vig.u_warmboot.S0};
    end
    if (fase == 0 && t_boot >= 0 && $time - t_boot >= DBOOT_NS) begin
      fase            = 1;
    end else if (fase == 1 && $time - t_boot >= TCFG_NS) begin
      fase        = 2;
      t_vuelta    = $time;
      tick_vuelta = tick_actual;
    end
  end

  // --- Serie -------------------------------------------------------------------
  int precio [200000];
  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(`SERIE, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", `SERIE); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < NTICKS; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  endtask

  // --- Maestra: la transacción del testbench oficial --------------------------
  int bits_x = 0;
  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #500 sclk = 1;
      if (miso !== 1'b0 && miso !== 1'b1) bits_x++;
      recibido[b] = (miso === 1'b1);
      #500 sclk = 0;
    end
    #500 cs_n = 1;
  endtask

  // --- Contabilidad oficial ----------------------------------------------------
  int caja = CAJA0, acciones = 0, w = CAJA0, ordenes = 0;
  task automatic ejecutar(input logic [7:0] decision, input int p);
    int q = decision[5:0];
    case (decision[7:6])
      2'b01: begin
        if (q > (caja - COMISION) / p) q = (caja - COMISION) / p;
        if (q > 0) begin caja -= q * p + COMISION; acciones += q; ordenes++; end
      end
      2'b10: begin
        if (q > acciones) q = acciones;
        if (q > 0 && caja + q * p >= COMISION) begin caja += q * p - COMISION; acciones -= q; ordenes++; end
      end
      default: ;
    endcase
    w = caja + acciones * p;
  endtask

  // --- Seguimiento de los dos programas ----------------------------------------
  int ultimo_tick_respondido = -1;       // último precio que respondió el principal
  int primer_precio_respaldo = -1;       // primer tick cuyo precio recibió el respaldo
  int primera_escritura_respaldo = -1;   // tick en que el respaldo escribió DECISION por primera vez
  always @(posedge clk_prin)
    if (u_prin.u_spi.wr && u_prin.u_spi.off == 2) ultimo_tick_respondido = tick_actual;
  always @(posedge clk_resp) begin
    if (u_resp.u_spi.byte_done && primer_precio_respaldo < 0) primer_precio_respaldo = tick_actual;
    if (u_resp.u_spi.wr && u_resp.u_spi.off == 2 && primera_escritura_respaldo < 0)
      primera_escritura_respaldo = tick_actual;
  end

  // --- Simulación --------------------------------------------------------------
  logic [7:0] decision;
  int fd, fase_ini, fase_fin;
  int ticks_sueltos = 0, ticks_cortados = 0;
  int ordenes_al_boot = -1, acciones_al_boot = -1, w_al_boot = -1;
  int ordenes_en_el_corte = 0;
  int tick_posicion_cero = -1;
  int n_ff = 0, n_00 = 0, n_otros = 0;
  string cortados = "";

  string salida = `SALIDA;
  initial begin
    void'($value$plusargs("tcfg=%d", TCFG_NS));
    void'($value$plusargs("dboot=%d", DBOOT_NS));
    void'($value$plusargs("salida=%s", salida));
    leer_serie();
    fd = $fopen(salida, "w");
    $fdisplay(fd, "tick,precio,decision,fase_inicio,fase_fin,caja,acciones,patrimonio");
    #4000;

    for (int n = 0; n < NTICKS; n++) begin
      tick_actual = n;
      fase_ini = fase;
      spi(precio[n], decision);
      fase_fin = fase;
      if (tick_boot >= 0 && ordenes_al_boot < 0) begin    // primer tick después del disparo
        ordenes_al_boot  = ordenes;
        acciones_al_boot = acciones;
        w_al_boot        = w;
      end
      ejecutar(decision, precio[n]);
      $fdisplay(fd, "%0d,%0d,%02h,%0d,%0d,%0d,%0d,%0d", n, precio[n], decision, fase_ini, fase_fin, caja, acciones, w);

      if (fase_ini == 1 && fase_fin == 1) begin
        ticks_sueltos++;
        if (decision == 8'hFF) n_ff++; else if (decision == 8'h00) n_00++; else n_otros++;
      end
      if (fase_ini != fase_fin) begin
        ticks_cortados++;
        cortados = {cortados, $sformatf(" tick %0d: fase %0d a %0d, byte %02h;", n, fase_ini, fase_fin, decision)};
      end
      if (primera_escritura_respaldo < 0 && ordenes_al_boot >= 0) ordenes_en_el_corte = ordenes - ordenes_al_boot;
      if (primera_escritura_respaldo >= 0 && tick_posicion_cero < 0 && acciones == 0) tick_posicion_cero = n;
      #(PERIODO_NS - SPI_NS);
    end
    $fclose(fd);

    $display("RELEVO periodo_ns=%0d tcfg_ns=%0d dboot_ns=%0d tiron=%0d nticks=%0d", PERIODO_NS, TCFG_NS, DBOOT_NS, `TIRON, NTICKS);
    $display("ultimo_precio_respondido_por_el_principal: tick %0d", ultimo_tick_respondido);
    $display("disparo_del_vigilante: tick %0d (t = %0d ns), S1S0 = %02b, CS_n en bajo al disparar: %0d",
             tick_boot, t_boot, s_boot[1:0], cs_bajo_al_boot);
    $display("al_disparar: acciones %0d, patrimonio %0d", acciones_al_boot, w_al_boot);
    $display("ticks_con_el_pin_suelto: %0d (bytes FF: %0d, 00: %0d, otros: %0d)", ticks_sueltos, n_ff, n_00, n_otros);
    $display("transacciones_cortadas_por_un_cambio_de_fase: %0d%s", ticks_cortados, cortados);
    $display("respaldo: empieza a correr en el tick %0d (t = %0d ns), primer precio recibido en el tick %0d, primera escritura en DECISION en el tick %0d",
             tick_vuelta, t_vuelta, primer_precio_respaldo, primera_escritura_respaldo);
    $display("ticks_sin_decision_nueva: %0d (desde el ultimo precio respondido hasta la primera escritura del respaldo)",
             primera_escritura_respaldo - ultimo_tick_respondido - 1);
    $display("ordenes_ejecutadas_durante_el_corte: %0d", ordenes_en_el_corte);
    $display("posicion_en_cero_en_el_tick: %0d", tick_posicion_cero);
    $display("final: caja %0d, acciones %0d, patrimonio %0d, ordenes %0d, bits de MISO con X: %0d", caja, acciones, w, ordenes, bits_x);

    if (tick_boot >= 0 && !cs_bajo_al_boot && bits_x == 0 && primera_escritura_respaldo >= 0 && ordenes_en_el_corte == 0 && n_otros == 0)
      $display("PASS relevo");
    else
      $display("FAIL relevo");
    $finish;
  end

endmodule
