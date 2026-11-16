// tb_xd_mul_mmio.sv: testbench de xd_mul_mmio (periférico multiplicador serial).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Repite ciclo a ciclo el tráfico de bus que genera tools/gen_vectores.py y
// compara rdata después de cada flanco con el del modelo ref/xd.py (clase
// MulMMIO), que tiene exactitud de ciclo. El tráfico incluye productos
// dirigidos (escribir, sondear BUSY 8 ciclos y leer) y accesos al azar, con
// escrituras a MULB mientras hay un producto en curso. Una línea por ciclo:
//     <req> <we> <off> <wdata> <rdata esperado después del flanco>
// Se corre con `make tb-mmio` desde factibilidad/d_isa.

`timescale 1ns/1ps

module tb_xd_mul_mmio;
  logic        clk = 0, rst_n = 0;
  logic        req = 0, we = 0;
  logic [1:0]  off = 0;
  logic [31:0] wdata = 0, esperado;
  wire  [31:0] rdata;
  int          fd, n = 0, errores = 0, v_req, v_we, v_off;

  always #20 clk = ~clk;

  xd_mul_mmio dut (.clk_i(clk), .rst_ni(rst_n), .req_i(req), .we_i(we), .off_i(off),
                   .wdata_i(wdata), .rdata_o(rdata));

  initial begin
    fd = $fopen(`VEC, "r");
    if (fd == 0) begin
      $display("ERROR: no se encontro %s", `VEC);
      $fatal(1);
    end
    repeat (2) @(posedge clk);
    #1 rst_n = 1;
    while ($fscanf(fd, "%d %d %d %h %h\n", v_req, v_we, v_off, wdata, esperado) == 5) begin
      req = v_req[0]; we = v_we[0]; off = v_off[1:0];
      @(posedge clk);
      #1;
      if (rdata !== esperado) begin
        errores++;
        if (errores <= 10)
          $display("  diferencia en el ciclo %0d: req=%0d we=%0d off=%0d wdata=%08x  rdata=%08x esperado=%08x",
                   n, req, we, off, wdata, rdata, esperado);
      end
      n++;
    end
    $fclose(fd);
    if (errores == 0 && n > 0) begin
      $display("PASS tb_xd_mul_mmio: %0d ciclos identicos al modelo ref/xd.py", n);
    end else begin
      $display("FAIL tb_xd_mul_mmio: %0d diferencias en %0d ciclos", errores, n);
      $fatal(1);
    end
    $finish;
  end
endmodule
