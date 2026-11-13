// tb_bitstream.sv: simula el bitstream final, no el RTL.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// icebox_vlog reconstruye un módulo Verilog (chip) a partir del .asc que sale
// del place and route: las LUT, los flip-flops y las BRAM con su contenido
// inicial, que incluye el programa. Este testbench conecta ese módulo solo
// por los pines de la placa y emula a la maestra con el mismo timing del
// testbench oficial. Escribe el byte que la maestra lee en cada tick.
//
// tools/sim_bitstream.sh rehace con esos bytes la contabilidad oficial
// (ref/market.py) y exige que el resultado sea idéntico al de ref/trader.py.
// Con eso se comprueba, antes de programar la placa, que lo que quedó dentro
// del bitstream decide igual que la referencia.
//
// No se puede usar el testbench oficial para esto, porque entra al diseño por
// jerarquía (dut.u_spi.byte_done) y en el bitstream esos nombres ya no existen.

`timescale 1ns/1ps

`ifndef SERIE
  `define SERIE "tb/practica.csv"
`endif
`ifndef NTICKS
  `define NTICKS 2000
`endif
`ifndef PERIODO_NS
  `define PERIODO_NS 100000
`endif
`ifndef SALIDA
  `define SALIDA "build/bitstream/bytes.csv"
`endif

module tb_bitstream;

  localparam int SPI_NS = 9500;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;

  chip dut (
    .i_Clk(clk), .\i_Switch (4'b0000), .\o_LED (),
    .i_UART_RX(1'b1), .o_UART_TX(1'b1),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

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

  logic [7:0] decision;
  int fd;

  initial begin
    leer_serie();
    fd = $fopen(`SALIDA, "w");
    $fdisplay(fd, "tick,precio,decision");
    #4000;
    for (int n = 0; n < `NTICKS; n++) begin
      spi(precio[n][7:0], decision);
      $fdisplay(fd, "%0d,%0d,%02h", n, precio[n], decision);
      #(`PERIODO_NS - SPI_NS);
    end
    $fclose(fd);
    $display("Bits de MISO con X: %0d", bits_x);
    $finish;
  end

endmodule
