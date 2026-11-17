// tb_p10_soc.sv: prueba dirigida del SoC de R1 con un programa de un hilo
// (revisión P10, docs/revision_p10.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre el programa con el bus SPI quieto durante CICLOS ciclos y comprueba:
//   - las palabras de memoria del archivo ESPERADO ("dirección valor" en
//     hexadecimal por línea);
//   - que nadie escribió DECISION (tx_hold sigue en 0), los LED ni los
//     7 segmentos;
//   - que ningún valor desconocido llegó al bus de datos.
//
// Uso (tools/p10/ro_custom0.sh):
//   iverilog -g2012 -s tb_p10_soc -DPROGRAMA=\"x.hex\" -DESPERADO=\"x.txt\" \
//     -DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA ...

`timescale 1ns/1ps

`ifndef CICLOS
  `define CICLOS 6000
`endif

module tb_p10_soc;

  reg clk = 1'b0;
  always #20 clk = ~clk;
  wire [3:0] led;
  wire [6:0] seg1, seg2;

  pochoco_soc #(.MemFile(`PROGRAMA), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(led), .i_Switch(4'b0000),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  int fallas = 0, x_bus = 0, escrituras_mmio = 0;

  task automatic comprobar(input bit ok, input string texto);
    if (ok) $display("PASS %s", texto);
    else begin $display("FAIL %s", texto); fallas++; end
  endtask

  task automatic revisar_memoria;
    int f, r, n = 0, malas = 0;
    logic [31:0] dir, valor, leido;
    f = $fopen(`ESPERADO, "r");
    if (f == 0) begin $display("FAIL no se encontro %s", `ESPERADO); fallas++; return; end
    while (!$feof(f)) begin
      r = $fscanf(f, "%h %h\n", dir, valor);
      if (r == 2) begin
        n++;
        leido = dut.u_ram.mem[dir[10:2]];
        if (leido !== valor) begin
          $display("FAIL memoria[%h] = %h, se esperaba %h", dir, leido, valor);
          malas++;
        end
      end
    end
    $fclose(f);
    comprobar(malas == 0 && n > 0, $sformatf("%0d de %0d palabras de memoria con el valor esperado", n - malas, n));
  endtask

  initial begin
    wait (dut.rst_ni);
    repeat (`CICLOS) begin
      @(posedge clk);
      if (dut.data_req) begin
        if (^dut.data_addr === 1'bx || (dut.data_we && ^dut.data_wdata === 1'bx)) x_bus++;
        if (dut.data_we && dut.data_addr[31]) escrituras_mmio++;
      end
    end
    revisar_memoria();
    comprobar(dut.u_spi.tx_hold === 8'h00, $sformatf("DECISION no se escribio (tx_hold = %h)", dut.u_spi.tx_hold));
    comprobar(led === 4'b0000, $sformatf("los LED no se escribieron (%b)", led));
    comprobar(dut.u_periph.digit_q === 8'h00, $sformatf("los 7 segmentos no se escribieron (%h)", dut.u_periph.digit_q));
    comprobar(x_bus == 0, $sformatf("ningun valor desconocido en el bus de datos (%0d)", x_bus));
    $display("Escrituras a la zona 0x8000_0000 en adelante: %0d", escrituras_mmio);
    $display("RESUMEN fallas=%0d", fallas);
    $finish;
  end

endmodule
