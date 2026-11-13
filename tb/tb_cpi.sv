// tb_cpi.sv: mediciones por tick (IC, ciclos, CPI y tiempo) y traza del SoC.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre un programa en el Pochoco SoC mientras emula a la maestra SPI con el
// mismo timing del testbench oficial. Entrega tres cosas:
//
// 1. CPI global y por clase de instrucción, comparado con el modelo de costo
//    leído del RTL del Espino base:
//        ciclos = 2 * IC + loads + saltos tomados (branch tomado, jal, jalr)
//
// 2. Mediciones por tick, en dos ventanas que parten cuando llega el precio
//    (byte_done):
//      - respuesta: hasta la escritura de DECISION. Es la misma ventana que
//        mide el testbench oficial y la que se compara con el presupuesto.
//      - tick completo: hasta que el programa vuelve a sondear STATUS. Incluye
//        el trabajo que el programa deja para después de responder.
//    Para cada ventana: IC, ciclos, CPI y tiempo, promedio y peor caso. Con
//    -DTICKS_CSV=\"archivo\" se escribe además una fila por tick.
//
// 3. Con -DTRAZA=\"archivo\", una traza con el número de ciclo de cada evento:
//        <ciclo> C <byte>                   CS_n baja: byte que va a salir por MISO
//        <ciclo> B <precio>                 llegó un precio (byte_done)
//        <ciclo> L <dirección>              lectura por el bus de datos
//        <ciclo> W <dirección> <be> <dato>  escritura por el bus de datos
//        <ciclo> R <registro> <valor>       escritura al banco de registros
//    El gemelo digital (ref/gemelo/) escribe la misma traza y los mismos datos
//    por tick, y se comparan línea por línea. El formato viene del
//    tb/core_trace_tb.v del Proyecto 3.
//
// El ciclo k es el intervalo que termina en el flanco de subida número k del
// reloj (el primero es el 0, a los 20 ns). Un evento del ciclo k es lo que se
// muestrea en ese flanco.
//
// Desde la raíz del repositorio:
//   make cpi
// Parámetros (todos con -D): PROGRAMA, SERIE (CSV "tick,price"; sin SERIE los
// precios salen de un LFSR), NTICKS, PERIODO_NS, INICIO_NS, CS_SETUP_NS,
// SCLK_MEDIO_NS, CS_HOLD_NS, TICKS_CSV, TRAZA.
//
// Este testbench mira señales internas del Espino base (u_core.u_id.commit,
// u_core.pc_set, u_core.rf_we). Si la microarquitectura cambia, hay que
// actualizar esas rutas.

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

module tb_cpi;

  localparam int SPI_NS = `CS_SETUP_NS + 16 * `SCLK_MEDIO_NS + `CS_HOLD_NS;

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

  // Señales internas
  wire        commit = dut.u_core.u_id.commit;      // instrucción completada en este ciclo
  wire        pc_set = dut.u_core.pc_set;           // salto tomado en este ciclo
  wire [31:0] instr  = dut.u_core.instr_rdata_i;
  wire        rf_we  = dut.u_core.rf_we;
  wire [3:0]  rf_wa  = dut.u_core.rf_waddr;
  wire [31:0] rf_wd  = dut.u_core.rf_wdata;
  wire        d_req  = dut.u_core.data_req_o;
  wire        d_we   = dut.u_core.data_we_o;
  wire [3:0]  d_be   = dut.u_core.data_be_o;
  wire [31:0] d_addr = dut.u_core.data_addr_o;
  wire [31:0] d_wd   = dut.u_core.data_wdata_o;
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
  // La ventana parte justo después de una instrucción completada que no saltó
  // y termina en otra igual, para que no queden burbujas a medias en los bordes.
  bit     midiendo = 0;
  longint ciclos = 0, ic = 0, n_load = 0, n_store = 0, n_br_t = 0, n_br_nt = 0, n_jump = 0, n_otras = 0;
  longint s_ciclos = 0, s_ic = 0, s_load = 0, s_store = 0, s_br_t = 0, s_br_nt = 0, s_jump = 0, s_otras = 0;

  // --- Conteo por tick ----------------------------------------------------------
  longint ciclo = 0;                 // número del flanco de subida actual
  longint t0 = 0;
  int     tick_m = 0, precio_m = 0;
  int     t_ic = 0, r_ciclos = 0, r_ic = 0;
  bit     esp_dec = 0, esp_fin = 0;
  int     ticks_medidos = 0;
  int     peor_r_ciclos = 0, peor_r_ic = 0, peor_t_ciclos = 0, peor_t_ic = 0;
  longint suma_r_ciclos = 0, suma_r_ic = 0, suma_t_ciclos = 0, suma_t_ic = 0;
  int     fd_ticks = 0, fd_traza = 0;

  always @(posedge clk) begin
    // Traza
    if (fd_traza != 0) begin
      if (dut.u_spi.cs_assert) $fdisplay(fd_traza, "%0d C %02x", ciclo, dut.u_spi.tx_hold);
      if (dut.u_spi.byte_done) $fdisplay(fd_traza, "%0d B %02x", ciclo, spi_precio);
      if (d_req && !d_we)      $fdisplay(fd_traza, "%0d L %08x", ciclo, d_addr);
      if (d_req && d_we)       $fdisplay(fd_traza, "%0d W %08x %x %08x", ciclo, d_addr, d_be, d_wd);
      if (rf_we && rf_wa != 0) $fdisplay(fd_traza, "%0d R %0d %08x", ciclo, rf_wa, rf_wd);
    end

    // Global
    if (midiendo) begin
      ciclos++;
      if (commit) begin
        ic++;
        case (instr[6:0])
          7'h03:        n_load++;
          7'h23:        n_store++;
          7'h63:        if (pc_set) n_br_t++; else n_br_nt++;
          7'h6f, 7'h67: n_jump++;
          default:      n_otras++;
        endcase
        if (!pc_set) begin
          s_ciclos = ciclos; s_ic = ic; s_load = n_load; s_store = n_store;
          s_br_t = n_br_t; s_br_nt = n_br_nt; s_jump = n_jump; s_otras = n_otras;
        end
      end
    end else if (commit && !pc_set) begin
      midiendo = 1;
    end

    // Por tick
    if (dut.u_spi.byte_done) begin
      t0 = ciclo; t_ic = 0; esp_dec = 1; esp_fin = 0;
      tick_m = tick_tx; precio_m = spi_precio;
    end else begin
      if (esp_fin && spi_rd_stat) begin
        // El programa volvió a sondear: termina el tick completo
        ticks_medidos++;
        suma_r_ciclos += r_ciclos;      suma_r_ic += r_ic;
        suma_t_ciclos += ciclo - t0;    suma_t_ic += t_ic;
        if (r_ciclos > peor_r_ciclos)   peor_r_ciclos = r_ciclos;
        if (r_ic > peor_r_ic)           peor_r_ic = r_ic;
        if (ciclo - t0 > peor_t_ciclos) peor_t_ciclos = ciclo - t0;
        if (t_ic > peor_t_ic)           peor_t_ic = t_ic;
        if (fd_ticks != 0)
          $fdisplay(fd_ticks, "%0d,%0d,%02x,%0d,%0d,%0d,%0d,%0d", tick_m, precio_m, leido[tick_m],
                    t0, r_ciclos, r_ic, ciclo - t0, t_ic);
        esp_fin = 0;
      end
      if (commit) t_ic++;
      if (esp_dec && spi_wr_dec) begin
        r_ciclos = ciclo - t0; r_ic = t_ic;
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
`ifdef TRAZA
    fd_traza = $fopen(`TRAZA, "w");
`endif
    #(`INICIO_NS);
    for (int n = 0; n < `NTICKS; n++) begin
      tick_tx = n;
      spi(precio[n][7:0], rx);
      #(`PERIODO_NS - SPI_NS);
    end
    if (fd_ticks != 0) $fclose(fd_ticks);
    if (fd_traza != 0) $fclose(fd_traza);

    modelo = 2 * s_ic + s_load + s_br_t + s_jump;
    $display("Programa:                 %s", `PROGRAMA);
    $display("Ticks:                    %0d con periodo de %0d ns", `NTICKS, `PERIODO_NS);
    $display("Instrucciones (IC):       %0d", s_ic);
    $display("Ciclos:                   %0d", s_ciclos);
    $display("CPI medido:               %0.4f", real'(s_ciclos) / real'(s_ic));
    $display("  loads:                  %0d", s_load);
    $display("  stores:                 %0d", s_store);
    $display("  branches tomados:       %0d", s_br_t);
    $display("  branches no tomados:    %0d", s_br_nt);
    $display("  jal y jalr:             %0d", s_jump);
    $display("  otras:                  %0d", s_otras);
    $display("Modelo 2*IC+loads+saltos: %0d ciclos (diferencia con lo medido: %0d)", modelo, s_ciclos - modelo);
    if (ticks_medidos > 0) begin
      $display("Por tick, %0d ticks medidos, T = %0d ns, presupuesto %0d ciclos:", ticks_medidos, `PERIODO_NS,
               (`PERIODO_NS - SPI_NS) / 40);
      fila("respuesta, promedio",     real'(suma_r_ic) / ticks_medidos, real'(suma_r_ciclos) / ticks_medidos);
      fila("respuesta, peor caso",    real'(peor_r_ic),                 real'(peor_r_ciclos));
      fila("tick completo, promedio", real'(suma_t_ic) / ticks_medidos, real'(suma_t_ciclos) / ticks_medidos);
      fila("tick completo, peor caso", real'(peor_t_ic),                real'(peor_t_ciclos));
    end
    if (s_ciclos != modelo) begin
      $display("FAIL el modelo de costo no coincide con lo medido");
      $fatal(1);
    end
    $display("PASS el modelo de costo coincide con lo medido");
    $finish;
  end

endmodule
