// tb_asic_barrel_puertos.sv: el macro ASIC del barrel por sus puertos, para la
// potencia con actividad real (asic/scripts/potencia_barrel.sh).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Copia de factibilidad/g_asic/tb/tb_asic_puertos.sv con asic_top_barrel y sin la
// sonda (que buscaba el lazo de sondeo de trade.s). La maestra es la del testbench
// oficial, la serie es la de práctica y los bytes que lee la maestra quedan en
// SALIDA para compararlos con ref/fondo.py. Con +vcd=archivo vuelca la actividad
// de la ventana pedida; potencia_barrel.sh pone ese archivo en /dev/shm (memoria,
// no disco) y lo borra después de usarlo.
// Con -DNETLIST el macro es un netlist y no lleva parámetros. Sin esa definición
// es el RTL y el parámetro XD elige la extensión (iverilog -Ptb_asic_barrel_puertos.XD=7).

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

module tb_asic_barrel_puertos;

  parameter int XD = 3;
  localparam int SPI_NS = 9500;

  logic clk = 0;
  always #20 clk = ~clk;

  logic rst_n = 0;
  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;
  wire [3:0] led;
  wire [6:0] seg1, seg2;

`ifdef NETLIST
  asic_top_barrel dut (
`else
  asic_top_barrel #(.Xd(XD)) dut (
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
