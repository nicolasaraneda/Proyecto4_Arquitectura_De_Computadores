// Copyright 2026 Universidad de los Andes.
// Licensed under the Solderpad Hardware License, Version 0.51 (the "License");
// you may not use this file except in compliance with the License.
// SPDX-License-Identifier: SHL-0.51
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Reemplazo del modelo funcional del flip-flop sin reset del PDK
// (gf180mcu_fd_sc_mcu7t5v0__dffq_func), que arranca en x. Viene de
// asic/potencia/dffq_func_init.v de nuestro Proyecto 3. Tiene el mismo
// comportamiento (Q <= D en el flanco de subida, sin retardos, igual que el
// modelo del PDK con -DFUNCTIONAL) pero con el estado inicial definido por
// INIT_FF (0 o 1).
//
// Sirve para el experimento de sensibilidad de scripts/potencia.sh (fase
// xinit): los registros que trade.s nunca escribe (x1 y x10 a x15 del banco y
// tres de las cuatro palabras de datos) quedan en x durante toda la
// simulación, los nodos que los leen pasan por x y OpenSTA no cuenta esas
// transiciones. Con este modelo esos registros valen 0 o 1 y se mide cuánto
// cambia la potencia.
//
// Se compila junto a la biblioteca del PDK definiendo su guarda, para que el
// módulo original quede fuera:
//   iverilog -g2012 -DFUNCTIONAL -DINIT_FF=0 -DGF180MCU_FD_SC_MCU7T5V0__DFFQ_FUNC_V \
//     ... tb/dffq_func_init.v <netlist> primitives.v gf180mcu_fd_sc_mcu7t5v0.v
// Solo cambia el dffq. Los flip-flops con reset (dffrnq y dffsnq) no se tocan.

`ifndef INIT_FF
  `define INIT_FF 0
`endif

module gf180mcu_fd_sc_mcu7t5v0__dffq_func( CLK, D, Q, notifier );
  input  CLK, D, notifier;
  output reg Q;
  initial Q = `INIT_FF;
  always @(posedge CLK) Q <= D;
endmodule
