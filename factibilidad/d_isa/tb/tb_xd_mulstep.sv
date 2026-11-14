// tb_xd_mulstep.sv: testbench de xd_mulstep (un paso de multiplicación).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Compara el módulo con los vectores que genera tools/gen_vectores.py desde
// el modelo de referencia ref/xd.py. Se corre con `make tb-mulstep` desde
// factibilidad/d_isa (ver el Makefile para las definiciones VEC y NOMBRE).

`timescale 1ns/1ps
// Además de pasos sueltos, aplica 8 y 16 pasos seguidos y compara con el
// producto: todos los multiplicadores de 8 bits, y el caso 8 x 8 completo.

module tb_xd_mulstep;
  wire [31:0] r;
  `include "xd_vectores.svh"
  xd_mulstep dut (.a_i(a), .b_i(b), .r_o(r));
endmodule
