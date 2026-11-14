// tb_asic_puertos.sv: simula el macro ASIC solo por sus puertos.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Viene de tb/tb_bitstream.sv. Emula a la maestra con la misma transacción
// SPI del testbench oficial y escribe el byte que lee en cada tick. Sirve
// igual para el RTL de asic_top y para sus netlists de celdas estándar
// (después de la síntesis y después del place and route), porque no entra al
// diseño por jerarquía: en un netlist aplanado esos nombres ya no existen.
//
// scripts/sim_puertos.sh rehace la contabilidad oficial con esos bytes
// (ref/market.py) y exige que el resultado sea idéntico al de ref/trader.py.
//
// El reset externo dura RESET_CICLOS ciclos y se suelta antes del primer
// precio, así que el programa los ve todos (referencia con --perdidos 0).
//
// Con +vcd=archivo +vcd_t0=ns +vcd_t1=ns vuelca la actividad de todas las
// señales del macro entre esos dos instantes y termina la simulación en el
// segundo, para el cálculo de potencia con OpenSTA (scripts/potencia.sh). El
// tick n empieza en 4000 + n * PERIODO_NS.
//
// El volcado es de profundidad 2 ($dumpvars(2, dut)): los nets del netlist
// plano y además los puertos de cada celda. El read_vcd de OpenSTA anota la
// actividad por nombre de pin (instancia/pin), así que con profundidad 1 solo
// reconoce los 28 puertos del macro y el resto de la actividad la inventa por
// propagación. Lo medimos en el Proyecto 3 y volvió a pasar aquí: la primera
// versión de este testbench volcaba con profundidad 1 y scripts/potencia.sh
// ahora falla si queda algún pin sin anotar.
//
// Con -DSONDA (solo RTL) informa, para los ticks 20 a 23, cuándo llega el
// precio, cuándo se escribe DECISION y cuándo el programa vuelve al lazo de
// sondeo, en ns desde el inicio del tick. Sirve para ubicar las ventanas de
// potencia.
//
// Con -DNETLIST el macro es un netlist y no lleva parámetros. Sin esa
// definición es el RTL y el parámetro PIPELINE elige la variante del core
// (iverilog -Ptb_asic_puertos.PIPELINE=2).

`timescale 1ns/1ps

`ifndef SERIE
  `define SERIE "tb/practica.csv"
`endif
`ifndef NTICKS
  `define NTICKS 300
`endif
`ifndef PERIODO_NS
  `define PERIODO_NS 100000
`endif
`ifndef SALIDA
  `define SALIDA "bytes.csv"
`endif
`ifndef RESET_CICLOS
  `define RESET_CICLOS 10
`endif

module tb_asic_puertos;

  parameter int PIPELINE = 0;
  localparam int SPI_NS = 9500;

  logic clk = 0;
  always #20 clk = ~clk;

  logic rst_n = 0;
  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;
  wire [3:0] led;
  wire [6:0] seg1, seg2;

`ifdef NETLIST
  asic_top dut (
`else
  asic_top #(.Pipeline(PIPELINE)) dut (
`endif
    .clk(clk), .rst_n(rst_n), .led(led), .btn(4'b0000),
    .seg1(seg1), .seg2(seg2),
    .spi_sclk(sclk), .spi_mosi(mosi), .spi_cs_n(cs_n), .spi_miso(miso));

  int precio [200000];
  int bits_x = 0;

  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(`SERIE, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", `SERIE); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < `NTICKS; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  endtask

  // Misma transacción que el testbench oficial
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

  // Reset externo: se suelta lejos del flanco de subida del reloj
  initial begin
    repeat (`RESET_CICLOS) @(posedge clk);
    #10 rst_n = 1;
  end

  logic [7:0] decision;
  int fd;
  string vcd;
  longint vcd_t0 = 0, vcd_t1 = 0;

  // Volcado de actividad para la potencia
  initial begin
    if ($value$plusargs("vcd=%s", vcd)) begin
      void'($value$plusargs("vcd_t0=%d", vcd_t0));
      void'($value$plusargs("vcd_t1=%d", vcd_t1));
      #(vcd_t0);
      $dumpfile(vcd);
      $dumpvars(2, dut);
      #(vcd_t1 - vcd_t0);
      $dumpflush;
      $display("VCD de %0d a %0d ns", vcd_t0, vcd_t1);
      $finish;
    end
  end

  int      tick_actual = -1;
  longint  t_tick = 0;

`ifdef SONDA
  bit espera_dec = 0, espera_lazo = 0;
  wire sonda_on = (tick_actual >= 20 && tick_actual <= 23);
  always @(posedge clk) begin
    if (dut.u_soc.u_spi.byte_done) begin
      if (sonda_on) $display("SONDA tick %0d: precio (byte_done) a %0d ns", tick_actual, $time - t_tick);
      espera_dec = 1;
    end
    if (espera_dec && dut.u_soc.u_spi.wr && dut.u_soc.u_spi.off == 2) begin
      if (sonda_on) $display("SONDA tick %0d: DECISION a %0d ns", tick_actual, $time - t_tick);
      espera_dec = 0; espera_lazo = 1;
    end
    if (espera_lazo && dut.u_soc.u_core.instr_addr_o == 32'h34) begin
      if (sonda_on) $display("SONDA tick %0d: vuelve al sondeo (PC = 0x34) a %0d ns", tick_actual, $time - t_tick);
      espera_lazo = 0;
    end
  end
`endif

  initial begin
    leer_serie();
    fd = $fopen(`SALIDA, "w");
    $fdisplay(fd, "tick,precio,decision");
    #4000;
    for (int n = 0; n < `NTICKS; n++) begin
      tick_actual = n;
      t_tick = $time;
      spi(precio[n][7:0], decision);
      $fdisplay(fd, "%0d,%0d,%02h", n, precio[n], decision);
      $fflush(fd);
      #(`PERIODO_NS - SPI_NS);
    end
    $fclose(fd);
    $display("Bits de MISO con X: %0d", bits_x);
    $finish;
  end

endmodule
