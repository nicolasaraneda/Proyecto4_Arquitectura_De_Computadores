// tb_xd_alu.sv: testbench de los carriles de xd_alu (carriles en el sumador de la ALU).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Usa los mismos vectores de tb_xd_simd8.sv, que salen del modelo ref/xd.py
// y son exhaustivos por carril (los 65 536 pares de cada operación en cada
// carril). El selector es el número de operación del grupo de carriles; aquí
// se traduce al operador de la ALU y a lane_op, igual que lo hace el
// decodificador del core. Solo las cinco operaciones que tiene xd_alu: padd8
// (0), psub8 (1), pcmpltu8 (2), paddus8 (6) y psubus8 (7). Que xd_alu sin
// carriles sea igual a espino_alu lo prueba formal/xd.sby (tarea alu_base).
// Se corre con `make tb` desde factibilidad/d_isa.

`timescale 1ns/1ps

module tb_xd_alu;
  wire [31:0] r;
  `include "xd_vectores.svh"
  wire        resta = (sel[3:0] == 4'd1) || (sel[3:0] == 4'd2) || (sel[3:0] == 4'd7);
  wire [2:0]  lane  = (sel[3:0] == 4'd2) ? 3'd2 :
                      (sel[3:0] == 4'd6) ? 3'd3 :
                      (sel[3:0] == 4'd7) ? 3'd4 : 3'd1;
  xd_alu dut (.operator_i(resta ? 4'd1 : 4'd0), .operand_a_i(a), .operand_b_i(b), .lane_op_i(lane),
              .result_o(r), .cmp_result_o());
endmodule
