// tb_relevo.sv: relevo de punta a punta en RTL, desde que el supervisor del
// fondo se cuelga hasta que la imagen de respaldo vuelve a operar.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Viene del estudio de factibilidad (rama factibilidad-fondo,
// factibilidad/e_warmboot/tb/tb_relevo.sv). Se corre con
// tools/vigilante/relevo.sh (make vig-relevo), que compara cada byte con lo
// que calcula tools/vigilante/relevo_ref.py.
//
// Hay dos SoC en el mismo testbench, conectados a la misma maestra:
//
//   imagen 0  u_img0, pochoco_soc_r2: copia de rtl/pochoco_soc.v con las
//             definiciones de R2 (barrel, emad, devk, tabla y vigilante). La
//             arma relevo.sh, porque los dos SoC son el mismo módulo con
//             definiciones distintas y no pueden llamarse igual. Corre el
//             fondo, o una variante con el supervisor colgado.
//   imagen 1  u_img1, pochoco_soc sin definiciones: Espino base con
//             sw/trade.hex (max_media).
//
// La reconfiguración de la FPGA no se puede simular con el RTL. Se modela con
// tres fases:
//
//   fase 0  corre la imagen 0 y la maestra ve su MISO. La imagen 1 no tiene
//           reloj.
//   fase 1  empieza medio ciclo después de que el vigilante sube BOOT. La FPGA
//           se está reconfigurando: ningún SoC tiene reloj y el pin MISO está
//           suelto. La maestra lee 1, que es el pull-up del iCE40 durante la
//           configuración. Dura T_RECONF_NS.
//   fase 2  corre la imagen 1 partiendo de cero (reset de encendido de 4095
//           ciclos y programa desde el comienzo) y la maestra ve su MISO.
//
// Las fases cambian en el flanco de bajada del reloj, para no recortar ningún
// pulso de los relojes de cada imagen.
//
// La maestra es la de tb/fondo/tb_fondo.sv, con los tiempos del testbench
// oficial por defecto: CS_n baja, 1000 ns, 8 bits con SCLK de 1 MHz (MISO se
// lee en el flanco de subida), 500 ns y CS_n sube.
//
// Lo que este testbench no demuestra: que la placa se comporte como el modelo
// (duración de la fase 1 y nivel del pin suelto). Eso se mide en la placa.
//
// Plusargs:
//   +PROGRAMA=archivo.hex   programa de la imagen 0
//   +TABLA=sw/fondo_tabla.hex
//   +RESPALDO=sw/trade.hex  programa de la imagen 1
//   +SERIE=archivo.csv      CSV "tick,precio"
//   +NTICKS=800 +PERIODO_NS=100000 +INICIO_NS=4000
//   +T_RECONF_NS=53000000
//   +SALIDA=archivo.csv     "tick,precio,decision,fase_ini,fase_fin"
//
// Al final imprime una línea RESUMEN con todo lo medido. Los tiempos están en
// ns y los ticks son transacciones de la maestra contadas desde 0. Un valor
// -1 significa que eso no ocurrió.

`timescale 1ns/1ps

module tb_relevo;

  logic clk = 0;
  always #20 clk = ~clk;

  int  fase = 0;
  wire clk0 = clk & (fase == 0);
  wire clk1 = clk & (fase == 2);

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso0, miso1;
  wire  miso = (fase == 0) ? miso0 : (fase == 1) ? 1'b1 : miso1;

  pochoco_soc_r2 #(.MemFile("")) u_img0 (
    .i_Clk(clk0), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso0));

  pochoco_soc #(.MemFile("")) u_img1 (
    .i_Clk(clk1), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso1));

  // --- Configuración ---------------------------------------------------------------
  string programa = "build/vigilante/relevo/fondo.hex", tabla = "sw/fondo_tabla.hex";
  string respaldo = "sw/trade.hex", serie = "tb/practica.csv", salida = "build/vigilante/relevo/salida.csv";
  int     ntick = 800;
  longint periodo_ns = 100000, inicio_ns = 4000, t_reconf_ns = 53000000;
  localparam longint SCLK_MEDIO_NS = 500, CS_SETUP_NS = 1500, CS_HOLD_NS = 500;
  localparam longint DUR_NS = CS_SETUP_NS + 15 * SCLK_MEDIO_NS + CS_HOLD_NS;

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

  // --- Maestra -----------------------------------------------------------------------
  int bits_x = 0;
  int tick_tx = -1;      // transacción en curso, o la última que terminó
  bit en_tx = 0;         // hay una transacción en curso (CS_n en bajo)

  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0; en_tx = 1;
    #(CS_SETUP_NS - SCLK_MEDIO_NS);
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #(SCLK_MEDIO_NS) sclk = 1;
      if (miso !== 1'b0 && miso !== 1'b1) bits_x++;
      recibido[b] = (miso === 1'b1);
      #(SCLK_MEDIO_NS) sclk = 0;
    end
    #(CS_HOLD_NS) cs_n = 1; en_tx = 0;
  endtask

  // --- Modelo de la reconfiguración -------------------------------------------------
  // BOOT sube en un flanco de subida del reloj. Aquí se mira en el flanco de
  // bajada siguiente, 20 ns después: t_boot guarda el instante del flanco de
  // subida.
  longint t_boot = -1, t_fase2 = -1;
  int     tick_boot = -1, cs_n_al_boot = -1, en_tx_al_boot = -1, s1s0_al_boot = -1;

  always @(negedge clk) begin
    if (fase == 0 && u_img0.g_vig.boot === 1'b1) begin
      t_boot        = $time - 20;
      tick_boot     = tick_tx;
      cs_n_al_boot  = (cs_n === 1'b1) ? 1 : 0;
      en_tx_al_boot = en_tx ? 1 : 0;
      s1s0_al_boot  = {u_img0.g_vig.u_warmboot.S1, u_img0.g_vig.u_warmboot.S0};
      fase          = 1;
    end else if (fase == 1 && $time - t_boot >= t_reconf_ns) begin
      fase    = 2;
      t_fase2 = $time;
    end
  end

  // --- Seguimiento de la imagen 0 ----------------------------------------------------
  wire wr_dec0 = u_img0.u_spi.wr && u_img0.u_spi.off == 2;
  int  recibidos0 = 0, escrituras0 = 0, vig_max = 0;
  int  primer_precio0 = -1, ultima_escritura0 = -1, precios_tras_ultima = 0;
  always @(posedge clk0) begin
    if (u_img0.u_spi.byte_done) begin
      recibidos0++;
      precios_tras_ultima++;
      if (primer_precio0 < 0) primer_precio0 = tick_tx;
    end
    if (wr_dec0) begin
      escrituras0++;
      ultima_escritura0   = tick_tx;
      precios_tras_ultima = u_img0.u_spi.byte_done ? 1 : 0;
    end
    if (u_img0.g_vig.u_vig.sin_resp > vig_max) vig_max = u_img0.g_vig.u_vig.sin_resp;
  end

  // --- Seguimiento de la imagen 1 ----------------------------------------------------
  // t_rst1 es el flanco de subida en que el contador de reset se llena.
  wire wr_dec1 = u_img1.u_spi.wr && u_img1.u_spi.off == 2;
  longint t_rst1 = -1, t_escritura1 = -1;
  int  recibidos1 = 0, escrituras1 = 0, ciclos1 = 0;
  int  primer_precio1 = -1, primera_escritura1 = -1, resp1 = -1;
  always @(negedge clk1)
    if (t_rst1 < 0 && u_img1.rst_ni === 1'b1) t_rst1 = $time - 20;
  always @(posedge clk1) begin
    ciclos1++;
    if (u_img1.u_spi.byte_done) begin
      recibidos1++;
      if (primer_precio1 < 0) begin primer_precio1 = tick_tx; ciclos1 = 0; end
    end
    if (wr_dec1) begin
      escrituras1++;
      if (primera_escritura1 < 0) begin
        primera_escritura1 = tick_tx;
        t_escritura1       = $time;
        resp1              = ciclos1;
      end
    end
  end

  // --- Estímulo ------------------------------------------------------------------------
  logic [7:0] decision;
  int fd, fase_ini;

  initial begin
    void'($value$plusargs("PROGRAMA=%s", programa));
    void'($value$plusargs("TABLA=%s", tabla));
    void'($value$plusargs("RESPALDO=%s", respaldo));
    void'($value$plusargs("SERIE=%s", serie));
    void'($value$plusargs("SALIDA=%s", salida));
    void'($value$plusargs("NTICKS=%d", ntick));
    void'($value$plusargs("PERIODO_NS=%d", periodo_ns));
    void'($value$plusargs("INICIO_NS=%d", inicio_ns));
    void'($value$plusargs("T_RECONF_NS=%d", t_reconf_ns));
    if (periodo_ns <= DUR_NS) begin $display("ERROR: el periodo no alcanza para la transaccion"); $finish; end

    $readmemh(programa, u_img0.u_ram.mem);
    $readmemh(tabla, u_img0.g_tabla.u_tabla.mem);
    $readmemh(respaldo, u_img1.u_ram.mem);
    leer_serie();
    fd = $fopen(salida, "w");
    $fdisplay(fd, "tick,precio,decision,fase_ini,fase_fin");
    #(inicio_ns);

    for (int n = 0; n < ntick; n++) begin
      tick_tx  = n;
      fase_ini = fase;
      spi(precio[n][7:0], decision);
      $fdisplay(fd, "%0d,%0d,%02h,%0d,%0d", n, precio[n], decision, fase_ini, fase);
      #(periodo_ns - DUR_NS);
    end
    $fclose(fd);

    $display("RESUMEN ticks=%0d periodo_ns=%0d inicio_ns=%0d t_reconf_ns=%0d bits_x=%0d recibidos0=%0d escrituras0=%0d primer_precio0=%0d ultima_escritura0=%0d precios_tras_ultima=%0d vig_max=%0d t_boot=%0d tick_boot=%0d cs_n_al_boot=%0d en_tx_al_boot=%0d s1s0=%0d t_fase2=%0d t_rst1=%0d recibidos1=%0d escrituras1=%0d primer_precio1=%0d primera_escritura1=%0d t_escritura1=%0d resp1=%0d",
             ntick, periodo_ns, inicio_ns, t_reconf_ns, bits_x, recibidos0, escrituras0, primer_precio0,
             ultima_escritura0, precios_tras_ultima, vig_max, t_boot, tick_boot, cs_n_al_boot, en_tx_al_boot,
             s1s0_al_boot, t_fase2, t_rst1, recibidos1, escrituras1, primer_precio1, primera_escritura1,
             t_escritura1, resp1);
    $finish;
  end

endmodule
