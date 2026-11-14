// tb_xd_mulc.sv: testbench de xd_mulc (producto combinacional angosto).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Compara el módulo con los vectores que genera tools/gen_vectores.py desde
// el modelo de referencia ref/xd.py. Se corre con `make tb-mulc` desde
// factibilidad/d_isa (ver el Makefile para las definiciones VEC y NOMBRE).

`timescale 1ns/1ps
`ifndef AW
  `define AW 16
`endif

module tb_xd_mulc;
  wire [31:0] r;
  `include "xd_vectores.svh"
  xd_mulc #(.AW(`AW), .BW(8)) dut (.a_i(a), .b_i(b), .r_o(r));
endmodule
