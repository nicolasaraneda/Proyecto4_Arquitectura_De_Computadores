// tb_xd_srak.sv: testbench de xd_srak (desplazamiento aritmético restringido).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Compara el módulo con los vectores que genera tools/gen_vectores.py desde
// el modelo de referencia ref/xd.py. Se corre con `make tb-srak` desde
// factibilidad/d_isa (ver el Makefile para las definiciones VEC y NOMBRE).

`timescale 1ns/1ps
`ifndef KB
  `define KB 0
`endif

module tb_xd_srak;
  wire [31:0] r;
  `include "xd_vectores.svh"
  xd_srak #(.KB(`KB)) dut (.a_i(a), .k_i(sel[4:0]), .r_o(r));
  wire _sin_uso = &{1'b0, b};
endmodule
