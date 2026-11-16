// tb_xd_divstep.sv: testbench de xd_divstep (un paso de división con restauración).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Compara el módulo con los vectores que genera tools/gen_vectores.py desde
// el modelo de referencia ref/xd.py. Se corre con `make tb-divstep` desde
// factibilidad/d_isa (ver el Makefile para las definiciones VEC y NOMBRE).

`timescale 1ns/1ps
// Además de pasos sueltos, aplica 8 pasos seguidos y compara con el cociente
// y el resto, incluido el caso de la contabilidad: (caja - 5) / precio.

module tb_xd_divstep;
  wire [31:0] r;
  `include "xd_vectores.svh"
  xd_divstep dut (.a_i(a), .b_i(b), .r_o(r));
endmodule
