// tb_tabla512.sv: testbench de rtl/pochoco_tabla512.v, la tabla de solo lectura
// de 512 palabras de 16 bits de R3.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Carga el módulo con un archivo (+TABLA, por defecto sw/c1_tabla.hex) y lo
// compara con una copia leída aparte del mismo archivo:
//   1. Las 512 palabras, en orden y en un orden salteado (paso 211, primo con
//      512): la lectura es registrada, el dato sale al ciclo siguiente.
//   2. Extensión de signo: los 16 bits altos de rdata_o copian el bit 15.
//   3. Sin rd_i la salida no cambia, aunque cambie el índice.
//   4. Un patrón propio (+PATRON=1): cada palabra distinta, con el bit 15 en 1
//      en la mitad, para que un índice recortado o una palabra cruzada no pase.
// Imprime PASS o FAIL con el número de comparaciones.
`timescale 1ns/1ps

module tb_tabla512;

  parameter MemFile = "sw/c1_tabla.hex";

  logic clk = 0;
  always #20 clk = ~clk;

  logic        rd = 0;
  logic [8:0]  idx = 0;
  wire  [31:0] rdata;

  pochoco_tabla512 #(.MemFile(MemFile)) dut (.clk_i(clk), .rd_i(rd), .idx_i(idx), .rdata_o(rdata));

  logic [15:0] esperado [0:511];
  int errores = 0, comparaciones = 0;

  task automatic leer(input int i);
    @(negedge clk); rd = 1; idx = i[8:0];
    @(negedge clk); rd = 0;
    comparaciones++;
    if (rdata !== {{16{esperado[i][15]}}, esperado[i]}) begin
      errores++;
      if (errores <= 10) $display("ERROR palabra %0d: %08x y se esperaba %08x", i, rdata, {{16{esperado[i][15]}}, esperado[i]});
    end
  endtask

  initial begin
    logic [31:0] antes;
    int patron = 0;
    void'($value$plusargs("PATRON=%d", patron));
    if (patron != 0) begin
      for (int i = 0; i < 512; i++) begin
        esperado[i] = 16'(i * 16'h9E37 + 16'h1234) ^ {i[0], 15'b0};
        dut.mem[i] = esperado[i];
      end
    end else $readmemh(MemFile, esperado);
    repeat (3) @(negedge clk);
    for (int i = 0; i < 512; i++) leer(i);
    for (int i = 0; i < 512; i++) leer((i * 211) % 512);
    // sin rd_i la salida se queda
    leer(5); antes = rdata;
    for (int i = 0; i < 512; i += 37) begin
      @(negedge clk); idx = i[8:0]; rd = 0;
      @(negedge clk);
      comparaciones++;
      if (rdata !== antes) begin errores++; $display("ERROR: la salida cambio sin rd_i (indice %0d)", i); end
    end
    if (errores == 0) $display("PASS: %0d comparaciones, cero errores", comparaciones);
    else $display("FAIL: %0d errores en %0d comparaciones", errores, comparaciones);
    $finish;
  end

endmodule
