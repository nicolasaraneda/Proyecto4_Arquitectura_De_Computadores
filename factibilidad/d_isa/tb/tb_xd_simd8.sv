// tb_xd_simd8.sv: testbench de xd_simd8 (cuatro carriles de 8 bits).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Compara el módulo con los vectores que genera tools/gen_vectores.py desde
// el modelo de referencia ref/xd.py. Se corre con `make tb-simd` desde
// factibilidad/d_isa (ver el Makefile para las definiciones VEC y NOMBRE).

`timescale 1ns/1ps
// MASCARA elige las opciones del módulo, con los mismos bits que el parámetro
// SIMD de xd_unit: 1 CON_SIGNO, 2 MINMAX, 4 SATURA, 8 BCAST, 16 MOVMSK,
// 32 CMP_BIT. Cada operación presente se prueba con los 65 536 pares de
// valores en cada carril.
`ifndef MASCARA
  `define MASCARA 31
`endif

module tb_xd_simd8;
  wire [31:0] r;
  `include "xd_vectores.svh"
  xd_simd8 #(
    .CON_SIGNO((`MASCARA >> 0) & 1), .MINMAX((`MASCARA >> 1) & 1), .SATURA((`MASCARA >> 2) & 1),
    .BCAST((`MASCARA >> 3) & 1), .MOVMSK((`MASCARA >> 4) & 1), .CMP_BIT((`MASCARA >> 5) & 1)
  ) dut (.a_i(a), .b_i(b), .op_i(sel[3:0]), .r_o(r));
endmodule
