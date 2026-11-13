// tb_mv2x2.sv: testbench del producto 2x2 en punto fijo.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Compara contra los vectores de ref/mv2x2.py (estado, precio, resultado
// esperado) las tres implementaciones: coeficientes fijos en forma
// factorizada, coeficientes fijos en forma directa y multiplicadores reales
// con los mismos coeficientes en sus entradas. Lo corre tools/costo_mv2x2.sh,
// que genera los módulos y pasa la matriz con -D.
//
// Hay dos matrices: la de la forma factorizada (G00..G11 con S bits de
// fracción) y la de la forma directa (GD00..GD11 con SD bits). Cada módulo de
// coeficientes fijos se compara con el multiplicador que usa su matriz.

`timescale 1ns/1ps

module tb_mv2x2;

`ifndef VECTORES
  `define VECTORES "build/mv2x2/vectores_fact.hex"
`endif
`ifndef VECTORES_D
  `define VECTORES_D "build/mv2x2/vectores_dir.hex"
`endif
`ifndef NVEC
  `define NVEC 20000
`endif

  reg [71:0] vec   [0:`NVEC-1];
  reg [71:0] vec_d [0:`NVEC-1];

  reg  [31:0] estado;
  reg  [7:0]  precio;
  wire [31:0] y_fact, y_dir, y_mult, y_mult_d;

  kal2_fact u_fact (.estado_i(estado), .precio_i(precio), .estado_o(y_fact));
  kal2_dir  u_dir  (.estado_i(estado), .precio_i(precio), .estado_o(y_dir));

  mv2x2_mult #(.CW(16), .S(`S)) u_mult (
    .estado_i(estado), .precio_i(precio),
    .g00_i(`G00), .g01_i(`G01), .g10_i(`G10), .g11_i(`G11),
    .estado_o(y_mult)
  );
  mv2x2_mult #(.CW(16), .S(`SD)) u_mult_d (
    .estado_i(estado), .precio_i(precio),
    .g00_i(`GD00), .g01_i(`GD01), .g10_i(`GD10), .g11_i(`GD11),
    .estado_o(y_mult_d)
  );

  integer i, errores;
  initial begin
    $readmemh(`VECTORES, vec);
    $readmemh(`VECTORES_D, vec_d);
    errores = 0;
    for (i = 0; i < `NVEC; i = i + 1) begin
      {estado, precio} = vec[i][71:32];
      #1;
      if (y_fact !== vec[i][31:0] || y_mult !== vec[i][31:0]) begin
        errores = errores + 1;
        if (errores < 10)
          $display("FAIL factorizada %0d: estado %h precio %h esperado %h fijo %h mult %h",
                   i, estado, precio, vec[i][31:0], y_fact, y_mult);
      end
      {estado, precio} = vec_d[i][71:32];
      #1;
      if (y_dir !== vec_d[i][31:0] || y_mult_d !== vec_d[i][31:0]) begin
        errores = errores + 1;
        if (errores < 10)
          $display("FAIL directa %0d: estado %h precio %h esperado %h fijo %h mult %h",
                   i, estado, precio, vec_d[i][31:0], y_dir, y_mult_d);
      end
    end
    if (errores == 0)
      $display("PASS tb_mv2x2: %0d vectores por matriz, las tres implementaciones coinciden con ref/mv2x2.py", `NVEC);
    else
      $display("FAIL tb_mv2x2: %0d diferencias", errores);
    $finish;
  end

endmodule
