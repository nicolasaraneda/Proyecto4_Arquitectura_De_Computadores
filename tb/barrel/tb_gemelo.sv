// tb_gemelo.sv: traza ciclo a ciclo del Espino barrel para validar el gemelo
// digital (ref/gemelo/gemelo.c con --barrel, docs/gemelo.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es la versión para el barrel de tb/tb_cpi.sv, con la maestra configurable de
// tb/tb_estres.sv (rondas seguidas sin reset, SCLK y tiempos de CS_n
// distintos). Escribe tres archivos que el gemelo escribe igual, y que
// tools/gemelo_barrel.sh compara con cmp:
//
//   +TRAZA=archivo     un evento por línea, con su número de ciclo:
//        <ciclo> C <byte>                   CS_n baja: byte que va a salir por MISO
//        <ciclo> B <precio>                 llegó un precio (byte_done)
//        <ciclo> L <dirección>              lectura por el bus de datos
//        <ciclo> W <dirección> <be> <dato>  escritura por el bus de datos
//        <ciclo> R <hilo> <registro> <valor>  escritura al banco de registros
//   +TICKS=archivo     una fila por tick, con las columnas de tb_cpi.sv. El IC
//                      es el del hilo 0, el que decide: instrucciones de ese
//                      hilo que pasan por la etapa X dentro de la ventana.
//   +SALIDA=archivo    el decisiones.csv del testbench oficial, con la misma
//                      contabilidad (caja 10 000, comisión 5)
//
// Maestra, todo con plusargs para compilar una sola vez por hardware:
//   +PROGRAMA=x.hex  +SERIE=x.csv  +NTICKS=300
//   +PERIODO_NS=100000  +PERIODO2_NS  +PERIODO3_NS  +RONDA_TICKS=0  +PAUSA_NS=0
//   +INICIO_NS=4000  +SCLK_MEDIO_NS=500
//   +CS_SETUP_NS=1500  de la bajada de CS_n al primer flanco de subida de SCLK
//   +CS_HOLD_NS=500    del último flanco de bajada a la subida de CS_n
// Con los valores por defecto la transacción es la del oficial: 9500 ns.
//
// El ancho del reset se fija al compilar: -GPOR=12.
//
// El ciclo k es el intervalo que termina en el flanco de subida número k del
// reloj (el primero a los 20 ns). Un evento del ciclo k es lo que se muestrea
// en ese flanco: es la convención de tb_cpi.sv y del gemelo.

`timescale 1ns/1ps

module tb_gemelo;

  parameter int POR = 12;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;

  pochoco_soc #(.MemFile(""), .PorBits(POR)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // --- Configuración ---------------------------------------------------------------
  string programa = "build/fondo/fondo.hex", serie = "tb/practica.csv";
  string traza = "", ticks = "", salida = "";
  int ntick = 300, ronda_ticks = 0;
  longint pausa_ns = 0, periodo_ns = 100000, periodo2_ns = -1, periodo3_ns = -1;
  longint inicio_ns = 4000, sclk_medio_ns = 500, cs_setup_ns = 1500, cs_hold_ns = 500;

  int precio [];
  int tick_tx = 0;
  logic [7:0] leido [];

  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    precio = new[ntick];
    leido = new[ntick];
    fd = $fopen(serie, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", serie); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < ntick; n++) begin
      r = $fscanf(fd, "%d,%d\n", t, precio[n]);
      if (r != 2) begin $display("ERROR: %s tiene %0d ticks", serie, n); $finish; end
    end
    $fclose(fd);
  endtask

  // Transacción SPI, modo 0, igual a la de tb_estres.sv
  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #(cs_setup_ns - sclk_medio_ns);
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #(sclk_medio_ns) sclk = 1;
      recibido[b] = (miso === 1'b1);
      if (b == 0) leido[tick_tx] = recibido;
      #(sclk_medio_ns) sclk = 0;
    end
    #(cs_hold_ns) cs_n = 1;
  endtask

  // --- Contabilidad del testbench oficial ---------------------------------------------
  int caja = 10000, acciones = 0, w = 10000, ordenes = 0;
  task automatic ejecutar(input logic [7:0] decision, input int p);
    int q;
    q = decision[5:0];
    case (decision[7:6])
      2'b01: begin
        if (q > (caja - 5) / p) q = (caja - 5) / p;
        if (q > 0) begin caja -= q * p + 5; acciones += q; ordenes++; end
      end
      2'b10: begin
        if (q > acciones) q = acciones;
        if (q > 0 && caja + q * p >= 5) begin caja += q * p - 5; acciones -= q; ordenes++; end
      end
      default: ;
    endcase
    w = caja + acciones * p;
  endtask

  // --- Señales internas -------------------------------------------------------------
  wire        xv     = dut.u_core.tb_valid_x;
  wire [1:0]  xt     = dut.u_core.tb_tid_x;
  wire        rf_we  = dut.u_core.tb_rf_we;
  wire [3:0]  rf_wa  = dut.u_core.tb_rf_wa;
  wire [31:0] rf_wd  = dut.u_core.tb_rf_wd;
  wire [1:0]  rf_t   = dut.u_core.tb_tid_m;
  wire        d_req  = dut.data_req;
  wire        d_we   = dut.data_we;
  wire [3:0]  d_be   = dut.data_be;
  wire [31:0] d_addr = dut.data_addr;
  wire [31:0] d_wd   = dut.data_wdata;
  wire        spi_wr_dec  = dut.u_spi.wr && dut.u_spi.off == 2;
  wire        spi_rd_stat = dut.u_spi.rd && dut.u_spi.off == 0;
  wire [7:0]  spi_precio  = {dut.u_spi.rx_shift[6:0], dut.u_spi.mosi};
  wire        commit0     = xv && xt == 2'd0;    // instrucción del hilo 0 en la etapa X

  // --- Traza y mediciones por tick, igual que tb_cpi.sv -----------------------------------
  longint ciclo = 0, t0 = 0;
  int     tick_m = 0, precio_m = 0, t_ic = 0, r_ciclos = 0, r_ic = 0;
  bit     esp_dec = 0, esp_fin = 0;
  int     fd_ticks = 0, fd_traza = 0;

  always @(posedge clk) begin
    if (fd_traza != 0) begin
      if (dut.u_spi.cs_assert) $fdisplay(fd_traza, "%0d C %02x", ciclo, dut.u_spi.tx_hold);
      if (dut.u_spi.byte_done) $fdisplay(fd_traza, "%0d B %02x", ciclo, spi_precio);
      if (d_req && !d_we)      $fdisplay(fd_traza, "%0d L %08x", ciclo, d_addr);
      if (d_req && d_we)       $fdisplay(fd_traza, "%0d W %08x %x %08x", ciclo, d_addr, d_be, d_wd);
      if (rf_we)               $fdisplay(fd_traza, "%0d R %0d %0d %08x", ciclo, rf_t, rf_wa, rf_wd);
    end

    if (dut.u_spi.byte_done) begin
      t0 = ciclo; t_ic = 0; esp_dec = 1; esp_fin = 0;
      tick_m = tick_tx; precio_m = spi_precio;
    end else begin
      if (esp_fin && spi_rd_stat) begin
        if (fd_ticks != 0)
          $fdisplay(fd_ticks, "%0d,%0d,%02x,%0d,%0d,%0d,%0d,%0d", tick_m, precio_m, leido[tick_m],
                    t0, r_ciclos, r_ic, ciclo - t0, t_ic);
        esp_fin = 0;
      end
      if (commit0) t_ic++;
      if (esp_dec && spi_wr_dec) begin
        r_ciclos = ciclo - t0; r_ic = t_ic;
        esp_dec = 0; esp_fin = 1;
      end
    end
    ciclo++;
  end

  // --- Estímulo -------------------------------------------------------------------------
  logic [7:0] decision;
  int fd_sal = 0;
  longint dur, per;

  initial begin
    void'($value$plusargs("PROGRAMA=%s", programa));
    void'($value$plusargs("SERIE=%s", serie));
    void'($value$plusargs("TRAZA=%s", traza));
    void'($value$plusargs("TICKS=%s", ticks));
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
    dur = cs_setup_ns + 15 * sclk_medio_ns + cs_hold_ns;

    $readmemh(programa, dut.u_ram.mem);
    leer_serie();
    if (traza != "") fd_traza = $fopen(traza, "w");
    if (ticks != "") begin
      fd_ticks = $fopen(ticks, "w");
      $fdisplay(fd_ticks, "tick,precio,decision_leida,ciclo_precio,ciclos_respuesta,ic_respuesta,ciclos_tick,ic_tick");
    end
    if (salida != "") begin
      fd_sal = $fopen(salida, "w");
      $fdisplay(fd_sal, "tick,precio,decision,caja,acciones,patrimonio");
    end
    #(inicio_ns);
    for (int n = 0; n < ntick; n++) begin
      int r;   // sin valor inicial: con valor inicial seria estatica y quedaria en 0
      r = (ronda_ticks > 0) ? n / ronda_ticks : 0;
      per = (r == 0) ? periodo_ns : (r == 1) ? periodo2_ns : periodo3_ns;
      if (per <= dur) begin $display("ERROR: el periodo no alcanza para la transaccion"); $finish; end
      if (ronda_ticks > 0 && n > 0 && n % ronda_ticks == 0) #(pausa_ns);
      tick_tx = n;
      spi(precio[n][7:0], decision);
      ejecutar(decision, precio[n]);
      if (fd_sal != 0) $fdisplay(fd_sal, "%0d,%0d,%02h,%0d,%0d,%0d", n, precio[n], decision, caja, acciones, w);
      #(per - dur);
    end
    if (fd_traza != 0) $fclose(fd_traza);
    if (fd_ticks != 0) $fclose(fd_ticks);
    if (fd_sal != 0) $fclose(fd_sal);
    $display("RESUMEN ticks=%0d patrimonio=%0d ordenes=%0d ciclos=%0d", ntick, w, ordenes, ciclo);
    $finish;
  end

endmodule
