// tb_fondo.sv: mediciones por tick y estado interno de sw/fondo.s en el Espino barrel.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es factibilidad/a_barrel/tb/tb_barrel_ticks.sv adaptado a un programa con
// los cuatro hilos ocupados (factibilidad/b_fondo_hilos/README.md). La maestra
// SPI, la serie de precios, la contabilidad y los cuatro chequeos son los de
// tb/tb_proyecto_4.sv. Qué agrega:
//
//   - Conteo por tick y por hilo. Una ventana va de un byte_done al siguiente.
//     De cada hilo se cuentan las instrucciones ejecutadas (ic) y cuántas de
//     ellas están fuera de los lazos de espera (trab). Los lazos de espera
//     son: el supervisor sondeando el SPI (3 instrucciones por vuelta) o
//     esperando a un gestor (3 por vuelta y por gestor), y un gestor
//     sondeando PUB (2 por vuelta). El trabajo de un hilo en un tick es trab
//     más una vuelta de cada lazo, la que encuentra lo que esperaba: 3 + 9
//     en el supervisor y 2 en cada gestor. Las direcciones de los lazos salen
//     de simbolos.vh, que genera tools/simbolos.py desde el mismo programa.
//   - Los hitos del protocolo dentro del tick, en ciclos desde byte_done: el
//     supervisor publica PUB, cada gestor publica EST_k y el supervisor
//     escribe DECISION.
//   - Cuándo termina cada hilo: el último ciclo de la ventana en que ejecutó
//     una instrucción fuera de su lazo de sondeo.
//   - Instrucciones del espejo de la cuenta y de la frontera de ventana.
//   - Estado interno al cerrar cada ventana, leído de la memoria del SoC:
//     espejo de la caja y de las acciones, posición y desempeño de cada
//     gestor, pesos y byte de DECISION. tools/comparar_estado.py lo compara
//     con la traza del módulo en C.
//   - decisiones.csv con el formato del testbench oficial.
//
// El programa se fija al compilar (-DPROGRAMA, parámetro MemFile, igual que
// en el testbench oficial). Lo demás se elige al correr, para usar un solo
// binario en todas las corridas de un programa:
//   +serie=ARCHIVO  +nticks=N  +periodo=NS  +inicio=NS
//   +ticks_csv=ARCHIVO  +dec_csv=ARCHIVO

`timescale 1ns/1ps

`include "simbolos.vh"

`ifndef PROGRAMA
  `define PROGRAMA "sw/trade.hex"
`endif

module tb_fondo;

  localparam int CAJA0    = 10000;
  localparam int COMISION = 5;
  localparam int SPI_NS   = 9500;

  string serie = "tb/practica.csv", ticks_csv = "", dec_csv = "";
  int    nticks = 2000, periodo_ns = 100000, inicio_ns = 4000;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;

  pochoco_soc #(.MemFile(`PROGRAMA)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // --- Señales internas ---------------------------------------------------------
  wire        x_valid = dut.u_core.tb_valid_x;   // instrucción de verdad en la etapa X
  wire [1:0]  x_tid   = dut.u_core.tb_tid_x;     // hilo al que pertenece
  wire [31:0] pc      = dut.u_core.tb_pc_x;
  wire        spi_wr_dec = dut.u_spi.wr && dut.u_spi.off == 2;
  wire [7:0]  spi_precio = {dut.u_spi.rx_shift[6:0], dut.u_spi.mosi};
  wire        ram_wr     = dut.u_ram.b_req_i && dut.u_ram.b_we_i;
  wire [8:0]  ram_pal    = dut.u_ram.b_word;

  // Lazos de espera de cada hilo
  wire en_spi    = x_tid == 0 && pc >= `PC_S_ESPERA && pc < `PC_S_ESPERA + 12;
  wire en_ges    = x_tid == 0 && pc >= `PC_S_G1 && pc < `PC_S_G3 + 12;
  wire en_pub    = x_tid != 0 && ((pc >= `PC_G_ESPERA && pc < `PC_G_ESPERA + 8) ||
                                  (pc >= `PC_G_PRIMERO && pc < `PC_G_PRIMERO + 8));
  wire en_sondeo = en_spi || en_pub;      // el hilo no tiene nada pendiente de este tick
  wire en_espejo   = x_valid && x_tid == 0 && pc >= `PC_ESPEJO && pc < `PC_E_FIN;
  wire en_frontera = x_valid && x_tid == 0 && pc >= `PC_FRONTERA && pc < `PC_HILO1;

  // --- Serie de precios ---------------------------------------------------------
  int precio [200000];

  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(serie, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", serie); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < nticks; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  endtask

  // --- Maestra SPI y contabilidad: las del testbench oficial --------------------
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

  // --- Conteo por tick ------------------------------------------------------------
  longint ciclo = 0, t0 = 0;
  bit     abierta = 0, esp_dec = 0;
  int     n_visto = 0;                 // número de precio visto por el programa (desde 0)
  int     tick_tx = 0, tick_m = 0, precio_m = 0;
  int     ic [4], trab [4], fin [4], c_est [4];
  int     ic_spi = 0, ic_ges = 0, ic_espejo = 0, ic_frontera = 0, n_wr = 0;
  int     r_ciclos = 0, r_ic0 = 0, c_pub = 0;
  int     peor_caso = 0, respuestas = 0, precios_perdidos = 0;
  int     fd_ticks = 0;

  task automatic cerrar_ventana;
    if (fd_ticks != 0)
      $fdisplay(fd_ticks, "%0d,%0d,%0d,%02x,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
        n_visto, tick_m, precio_m, dut.u_spi.tx_hold, n_wr, r_ciclos, r_ic0,
        c_pub, c_est[1], c_est[2], c_est[3],
        ic[0], ic[1], ic[2], ic[3], trab[0], trab[1], trab[2], trab[3], ic_spi, ic_ges,
        fin[0], fin[1], fin[2], fin[3], ic_espejo, ic_frontera,
        $signed(dut.u_ram.mem[`PAL_CAJA]), $signed(dut.u_ram.mem[`PAL_ACC]),
        dut.u_ram.mem[`PAL_EST1] & 1, dut.u_ram.mem[`PAL_EST2] & 1, dut.u_ram.mem[`PAL_EST3] & 1,
        $signed(dut.u_ram.mem[`PAL_DES1]), $signed(dut.u_ram.mem[`PAL_DES2]), $signed(dut.u_ram.mem[`PAL_DES3]),
        dut.u_ram.mem[`PAL_W1], dut.u_ram.mem[`PAL_W2], dut.u_ram.mem[`PAL_W3]);
    n_visto++;
  endtask

  always @(posedge clk) begin
    if (dut.u_spi.byte_done) begin
      if (dut.u_spi.new_price_q) precios_perdidos++;      // el precio anterior no se leyó
      if (abierta) cerrar_ventana();
      abierta = 1; esp_dec = 1; t0 = ciclo;
      tick_m = tick_tx; precio_m = spi_precio;
      for (int t = 0; t < 4; t++) begin ic[t] = 0; trab[t] = 0; fin[t] = 0; c_est[t] = 0; end
      ic_spi = 0; ic_ges = 0; ic_espejo = 0; ic_frontera = 0; n_wr = 0; r_ciclos = 0; r_ic0 = 0; c_pub = 0;
    end
    if (abierta) begin                 // el ciclo de byte_done ya cuenta para la ventana nueva
      if (x_valid) begin
        ic[x_tid]++;
        if (!en_sondeo) fin[x_tid] = ciclo - t0;
        if (!en_sondeo && !en_ges) trab[x_tid]++;
        if (en_spi) ic_spi++;
        if (en_ges) ic_ges++;
      end
      if (en_espejo) ic_espejo++;
      if (en_frontera) ic_frontera++;
      if (ram_wr && ram_pal == `PAL_PUB)  c_pub    = ciclo - t0;
      if (ram_wr && ram_pal == `PAL_EST1) c_est[1] = ciclo - t0;
      if (ram_wr && ram_pal == `PAL_EST2) c_est[2] = ciclo - t0;
      if (ram_wr && ram_pal == `PAL_EST3) c_est[3] = ciclo - t0;
      if (spi_wr_dec && !dut.u_spi.byte_done) begin
        n_wr++;
        if (esp_dec) begin
          r_ciclos = ciclo - t0; r_ic0 = ic[0];
          if (r_ciclos > peor_caso) peor_caso = r_ciclos;
          respuestas++;
          esp_dec = 0;
        end
      end
    end
    ciclo++;
  end

  // --- Estímulo ---------------------------------------------------------------------
  logic [7:0] decision;
  int fd_dec = 0, presupuesto, aprobados = 0;

  initial begin
    void'($value$plusargs("serie=%s", serie));
    void'($value$plusargs("nticks=%d", nticks));
    void'($value$plusargs("periodo=%d", periodo_ns));
    void'($value$plusargs("inicio=%d", inicio_ns));
    void'($value$plusargs("ticks_csv=%s", ticks_csv));
    void'($value$plusargs("dec_csv=%s", dec_csv));
    leer_serie();
    if (ticks_csv != "") begin
      fd_ticks = $fopen(ticks_csv, "w");
      $fdisplay(fd_ticks, "n,tick,precio,decision,escrituras,r_ciclos,r_ic0,c_pub,c_est1,c_est2,c_est3,ic0,ic1,ic2,ic3,trab0,trab1,trab2,trab3,ic_spi,ic_ges,fin0,fin1,fin2,fin3,ic_espejo,ic_frontera,caja,acciones,pos1,pos2,pos3,des1,des2,des3,w1,w2,w3");
    end
    if (dec_csv != "") begin
      fd_dec = $fopen(dec_csv, "w");
      $fdisplay(fd_dec, "tick,precio,decision,caja,acciones,patrimonio");
    end
    #(inicio_ns);
    for (int n = 0; n < nticks; n++) begin
      tick_tx = n;
      spi(precio[n][7:0], decision);
      ejecutar(decision, precio[n]);
      if (fd_dec != 0) $fdisplay(fd_dec, "%0d,%0d,%02h,%0d,%0d,%0d", n, precio[n], decision, caja, acciones, w);
      #(periodo_ns - SPI_NS);
    end
    @(posedge clk);
    if (abierta) cerrar_ventana();
    if (fd_ticks != 0) $fclose(fd_ticks);
    if (fd_dec != 0) $fclose(fd_dec);

    presupuesto = (periodo_ns - SPI_NS) / 40;
    $display("Programa:                  %s", `PROGRAMA);
    $display("Serie:                     %s, %0d ticks con periodo de %0d ns, inicio en %0d ns", serie, nticks, periodo_ns, inicio_ns);
    $display("Precios vistos:            %0d", n_visto);
    $display("Precios perdidos:          %0d", precios_perdidos);
    $display("Respuestas:                %0d", respuestas);
    $display("Patrimonio final:          %0d", w);
    $display("Ordenes ejecutadas:        %0d", ordenes);
    $display("Peor caso precio->decision: %0d ciclos (disponibles: %0d)", peor_caso, presupuesto);
    if (bits_x == 0)             begin aprobados++; $display("PASS MISO sin valores X"); end else $display("FAIL MISO sin valores X");
    if (respuestas > 0)          begin aprobados++; $display("PASS el programa escribe DECISION"); end else $display("FAIL el programa escribe DECISION");
    if (precios_perdidos == 0)   begin aprobados++; $display("PASS el programa lee todos los precios"); end else $display("FAIL el programa lee todos los precios (%0d perdidos)", precios_perdidos);
    if (peor_caso < presupuesto) begin aprobados++; $display("PASS la decision llega antes del siguiente tick"); end else $display("FAIL la decision llega antes del siguiente tick");
    $display("Chequeos aprobados: %0d/4", aprobados);
    $finish;
  end

endmodule
