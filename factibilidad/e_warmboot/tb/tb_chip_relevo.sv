// tb_chip_relevo.sv: simula, desde el .asc, la imagen principal de la prueba
// de relevo (SoC con vigilante y sw/cuelgue.s).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El módulo chip sale de icebox_vlog (scripts/chip_vlog_wb.py): es lo mismo
// que queda en el .bin que se graba. La maestra es la del testbench oficial.
//
// Modos (+modo=N):
//   0  con maestra. El programa responde K precios con "comprar 63" y se
//      cuelga. Se comprueba que BOOT no sube antes, que sube una sola vez,
//      con CS_n en alto, después de N + 1 precios sin respuesta, con S1 S0 =
//      01, y que el LED 1 y los displays muestran lo que corresponde.
//   1  sin maestra. Se aprieta el interruptor 4 y BOOT tiene que subir.
//
// La reconfiguración no se simula: el testbench termina cuando BOOT sube.
//
// Macros: K (precios que responde el programa), N_VIG, PERIODO_NS, SERIE.

`timescale 1ns/1ps

`ifndef K
  `define K 500
`endif
`ifndef N_VIG
  `define N_VIG 4
`endif
`ifndef PERIODO_NS
  `define PERIODO_NS 100000
`endif
`ifndef SERIE
  `define SERIE "tb/practica.csv"
`endif

module tb_chip_relevo;

  localparam int K          = `K;
  localparam int N          = `N_VIG;
  localparam int PERIODO_NS = `PERIODO_NS;
  localparam int SPI_NS     = 9500;
  localparam int NTICKS     = K + N + 40;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  logic [3:0] sw = 4'b0000;
  wire  [3:0] led;
  wire  miso;
  wire s1a, s1b, s1c, s1d, s1e, s1f, s1g;
  wire s2a, s2b, s2c, s2d, s2e, s2f, s2g;

  chip dut (
    .i_Clk(clk), .\i_Switch (sw), .\o_LED (led),
    .i_UART_RX(1'b1), .o_UART_TX(),
    .o_Segment1_A(s1a), .o_Segment1_B(s1b), .o_Segment1_C(s1c), .o_Segment1_D(s1d),
    .o_Segment1_E(s1e), .o_Segment1_F(s1f), .o_Segment1_G(s1g),
    .o_Segment2_A(s2a), .o_Segment2_B(s2b), .o_Segment2_C(s2c), .o_Segment2_D(s2d),
    .o_Segment2_E(s2e), .o_Segment2_F(s2f), .o_Segment2_G(s2g),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  wire       boot = dut.u_warmboot.BOOT;
  wire [1:0] sel  = {dut.u_warmboot.S1, dut.u_warmboot.S0};

  // Segmentos encendidos, {G,F,E,D,C,B,A} (los pines son activos en bajo)
  wire [6:0] seg1 = ~{s1g, s1f, s1e, s1d, s1c, s1b, s1a};
  wire [6:0] seg2 = ~{s2g, s2f, s2e, s2d, s2c, s2b, s2a};
  localparam [6:0] CERO = 7'b0111111;

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

  // Vigilancia de BOOT
  int  tick_actual = -1, tick_boot = -1, subidas = 0, sel_malo = 0;
  bit  cs_bajo_al_boot = 0;
  longint t_boot = -1, t_cs_sube = -1;
  logic boot_ant = 0;
  always @(posedge cs_n) t_cs_sube = $time;
  always @(negedge clk) begin
    if (boot === 1'b1 && boot_ant !== 1'b1) begin
      subidas++;
      if (tick_boot < 0) begin
        tick_boot       = tick_actual;
        t_boot          = $time;
        cs_bajo_al_boot = (cs_n === 1'b0);
      end
    end
    if (boot === 1'b1 && sel !== 2'b01) sel_malo++;
    boot_ant = boot;
  end

  int fallas = 0;
  task automatic comprobar(input bit cond, input string texto);
    if (cond) $display("  ok    %s", texto);
    else begin $display("  FALLA %s", texto); fallas++; end
  endtask

  logic [7:0] decision;
  int modo, primer_7f = -1, n_7f = 0, n_00 = 0, n_otros = 0, esperado;

  initial begin
    if (!$value$plusargs("modo=%d", modo)) modo = 0;
    leer_serie();
    #4000;

    if (modo == 0) begin
      $display("imagen principal de la prueba de relevo, con maestra (K = %0d, N = %0d, periodo %0d ns)", K, N, PERIODO_NS);
      for (int n = 0; n < NTICKS && tick_boot < 0; n++) begin
        tick_actual = n;
        spi(precio[n][7:0], decision);
        if (decision == 8'h7F) begin n_7f++; if (primer_7f < 0) primer_7f = n; end
        else if (decision == 8'h00) n_00++;
        else n_otros++;
        if (n == K / 2) begin
          comprobar(boot !== 1'b1,   "a mitad de los K precios BOOT sigue en 0");
          comprobar(led === 4'b0001, "LED 1 encendido: corre la imagen principal");
        end
        #(PERIODO_NS - SPI_NS);
      end
      esperado = primer_7f - 1 + K + N;
      $display("  primer byte 0x7F leido en el tick %0d; bytes 0x00: %0d, 0x7F: %0d, otros: %0d", primer_7f, n_00, n_7f, n_otros);
      $display("  BOOT sube en el tick %0d (esperado %0d), %0d ns despues de que CS_n sube; S1 S0 = %02b",
               tick_boot, esperado, t_boot - t_cs_sube, sel);
      comprobar(tick_boot == esperado,    "BOOT sube despues de N + 1 precios sin respuesta, ni antes ni despues");
      comprobar(!cs_bajo_al_boot,         "BOOT sube con CS_n en alto");
      comprobar(sel === 2'b01,            "S1 S0 = 01: la imagen de respaldo");
      comprobar(seg1 === CERO && seg2 === CERO, "los displays muestran 00: no quedan precios por responder");
      comprobar(n_otros == 0,             "la maestra solo leyo 0x00 y 0x7F");
      comprobar(bits_x == 0,              "MISO sin valores X");
      repeat (2000) @(posedge clk);
      comprobar(subidas == 1 && boot === 1'b1 && sel_malo == 0, "BOOT queda en alto y el destino no cambia");
    end else begin
      $display("imagen principal de la prueba de relevo, sin maestra (disparo con el interruptor 4)");
      repeat (20000) @(posedge clk);
      comprobar(boot !== 1'b1,            "sin maestra y sin tocar nada, BOOT sigue en 0 despues de 20 000 ciclos");
      comprobar(led === 4'b0001,          "LED 1 encendido: corre la imagen principal");
      sw[0] = 1; repeat (200) @(posedge clk); sw[0] = 0;
      sw[1] = 1; repeat (200) @(posedge clk); sw[1] = 0;
      sw[2] = 1; repeat (200) @(posedge clk); sw[2] = 0;
      comprobar(boot !== 1'b1,            "los interruptores 1, 2 y 3 no disparan");
      sw[3] = 1;
      repeat (10) @(posedge clk);
      comprobar(boot === 1'b1,            "el interruptor 4 sube BOOT");
      comprobar(sel === 2'b01,            "S1 S0 = 01: la imagen de respaldo");
      sw[3] = 0;
      repeat (200) @(posedge clk);
      comprobar(subidas == 1 && boot === 1'b1 && sel_malo == 0, "BOOT queda en alto al soltar el interruptor");
    end

    if (fallas == 0) $display("PASS imagen principal modo %0d", modo);
    else             $display("FAIL imagen principal modo %0d: %0d fallas", modo, fallas);
    $finish;
  end

endmodule
