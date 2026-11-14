// tb_xd_opa.sv: testbench de xd_opa (operando A desplazado para la ALU).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// xd_opa solo entrega el operando A: la suma o la resta la hace la ALU del
// core. Aquí el testbench hace el papel de la ALU (A + B, A - B, y B anulado
// en mulstep) y compara el resultado de la instrucción completa con los
// vectores que genera tools/gen_vectores.py desde el modelo ref/xd.py
// (funciones mulstep, emad y devk). El selector lleva funct3 en los bits 7:5
// y k en los bits 4:0. La misma instrucción dentro del core, con la ALU de
// verdad, se prueba con tb_xd_core.sv. Se corre con `make tb` desde
// factibilidad/d_isa.

`timescale 1ns/1ps
`ifndef KB
  `define KB 0
`endif

module tb_xd_opa;
  wire [31:0] r, opa;
  wire        b_cero;
  `include "xd_vectores.svh"
  xd_opa #(.MULSTEP(1), .EMAD_KB(`KB), .DEVK_KB(`KB)) dut (
    .rs1_i(a), .funct3_i(sel[7:5]), .funct7_i({2'b00, sel[4:0]}), .a_o(opa), .b_cero_o(b_cero));
  // Lo que hace la ALU: resta en devk (funct3 = 101), suma en el resto
  assign r = (sel[7:5] == 3'b101) ? opa - b : opa + (b_cero ? 32'b0 : b);
endmodule
