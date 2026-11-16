// tb_tabla_mod.sv: los dos módulos de memoria para la tabla de política,
// solos, contra un modelo, con accesos al azar.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// tabla_mmio (256 x 16) y tabla_ram (512 x 32) reciben en cada ciclo un acceso
// al azar: lectura, escritura con cualquier combinación de bytes habilitados,
// o nada. Un modelo escrito de otra forma (máscara por bit en vez de un if por
// byte) lleva el contenido y el dato que debe estar en la salida:
//   - una lectura deja en la salida la palabra pedida en el flanco siguiente;
//   - una escritura cambia solo los bytes habilitados y no mueve la salida;
//   - sin acceso no cambia nada.
// Una tercera instancia comprueba el contenido inicial que se carga de un
// archivo (-DTABLA_INIT="archivo", una palabra por línea con el valor
// 3 i + 1). Las otras dos parten en cero.
//
// Uso: tools/tabla.sh. CICLOS se cambia con +ciclos=N (por defecto 200 000).

`timescale 1ns/1ps

`ifndef TABLA_INIT
  `define TABLA_INIT ""
`endif

module tb_tabla_mod;
  logic clk = 0;
  always #5 clk = ~clk;

  // Estímulo común
  logic        req = 0, we = 0;
  logic [3:0]  be = 0;
  logic [8:0]  idx = 0;
  logic [31:0] wdata = 0;

  wire [15:0] q16;
  wire [31:0] q32;
  tabla_mmio u_mmio (.clk_i(clk), .req_i(req), .we_i(we), .be_i(be[1:0]), .idx_i(idx[7:0]), .wdata_i(wdata[15:0]), .rdata_o(q16));
  tabla_ram #(.NumWords(512)) u_ram (.clk_i(clk), .req_i(req), .we_i(we), .be_i(be), .idx_i(idx), .wdata_i(wdata), .rdata_o(q32));

  // Contenido inicial desde un archivo
  logic       req_i = 0;
  logic [7:0] idx_i = 0;
  wire [15:0] q_ini;
  tabla_mmio #(.MemFile(`TABLA_INIT)) u_ini (.clk_i(clk), .req_i(req_i), .we_i(1'b0), .be_i(2'b00), .idx_i(idx_i), .wdata_i(16'h0), .rdata_o(q_ini));

  logic [15:0] m16 [0:255];
  logic [31:0] m32 [0:511];
  logic [15:0] e16;
  logic [31:0] e32, mascara;
  logic        e16_valido = 0, e32_valido = 0;   // ya hubo una lectura: la salida está definida
  int          ciclos = 200000, errores = 0, lecturas = 0, escrituras = 0, ociosos = 0;
  int          semilla = 1;

  initial begin
    void'($value$plusargs("ciclos=%d", ciclos));
    void'($value$plusargs("semilla=%d", semilla));
    for (int k = 0; k < 256; k++) m16[k] = 16'h0;
    for (int k = 0; k < 512; k++) m32[k] = 32'h0;

    // 1. Contenido inicial cargado del archivo: 3 i + 1
    for (int k = 0; k < 256; k++) begin
      @(negedge clk); req_i = 1; idx_i = k[7:0];
      @(negedge clk); req_i = 0;
      if (q_ini !== 16'(3 * k + 1)) begin
        errores++;
        if (errores <= 5) $display("  contenido inicial [%0d] = %04x, esperado %04x", k, q_ini, 16'(3 * k + 1));
      end
    end

    // 2. Accesos al azar
    void'($urandom(semilla));
    for (int c = 0; c < ciclos; c++) begin
      @(negedge clk);
      // Compara la salida con lo que dejó el flanco anterior
      if (e16_valido && q16 !== e16) begin
        errores++;
        if (errores <= 5) $display("  tabla_mmio: salida %04x, esperado %04x (ciclo %0d)", q16, e16, c);
      end
      if (e32_valido && q32 !== e32) begin
        errores++;
        if (errores <= 5) $display("  tabla_ram: salida %08x, esperado %08x (ciclo %0d)", q32, e32, c);
      end
      // Estímulo nuevo. Las direcciones se concentran en pocas palabras la
      // mitad de las veces, para que se lea lo recién escrito.
      req   = ($urandom_range(0, 9) != 0);
      we    = $urandom_range(0, 1);
      be    = $urandom_range(0, 15);
      idx   = $urandom_range(0, 1) ? $urandom_range(0, 511) : $urandom_range(0, 7);
      wdata = $urandom();
      // Modelo de lo que hará el flanco siguiente
      if (req && we) begin
        escrituras++;
        mascara = {{8{be[3]}}, {8{be[2]}}, {8{be[1]}}, {8{be[0]}}};
        m32[idx]      = (m32[idx] & ~mascara) | (wdata & mascara);
        m16[idx[7:0]] = (m16[idx[7:0]] & ~mascara[15:0]) | (wdata[15:0] & mascara[15:0]);
      end else if (req) begin
        lecturas++;
        e32 = m32[idx];      e32_valido = 1;
        e16 = m16[idx[7:0]]; e16_valido = 1;
      end else ociosos++;
    end

    // El último acceso al azar todavía no pasó por un flanco: se deja que
    // ocurra antes de cambiar el estímulo.
    @(negedge clk);
    if (e16_valido && q16 !== e16) begin errores++; $display("  tabla_mmio: salida %04x, esperado %04x (ultimo acceso)", q16, e16); end
    if (e32_valido && q32 !== e32) begin errores++; $display("  tabla_ram: salida %08x, esperado %08x (ultimo acceso)", q32, e32); end

    // 3. Contenido final completo, leído por el puerto
    req = 0; we = 0;
    for (int k = 0; k < 512; k++) begin
      @(negedge clk); req = 1; we = 0; idx = k[8:0];
      @(negedge clk); req = 0;
      if (q32 !== m32[k]) begin
        errores++;
        if (errores <= 5) $display("  tabla_ram: contenido final [%0d] = %08x, esperado %08x", k, q32, m32[k]);
      end
      if (k < 256 && q16 !== m16[k]) begin
        errores++;
        if (errores <= 5) $display("  tabla_mmio: contenido final [%0d] = %04x, esperado %04x", k, q16, m16[k]);
      end
    end

    if (errores == 0)
      $display("PASS tb_tabla_mod: %0d lecturas, %0d escrituras y %0d ciclos sin acceso iguales al modelo; contenido inicial (256 palabras) y final (256 y 512 palabras) correctos",
               lecturas, escrituras, ociosos);
    else begin
      $display("FAIL tb_tabla_mod: %0d diferencias", errores);
      $fatal(1);
    end
    $finish;
  end
endmodule
