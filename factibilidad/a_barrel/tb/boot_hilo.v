// boot_hilo.v: hace partir al Espino base en la entrada de un hilo.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// En el Espino barrel el hilo t parte en la dirección 4 t. Para comparar ese
// hilo con el Espino base se corre el mismo programa en el SoC original
// (rtl/, sin modificar) con tb/core_trace_tb.v (sin modificar), pero partiendo
// en 4 t. Este módulo se agrega como segunda raíz de la simulación
// (iverilog -s core_trace_tb -s boot_hilo -DHILO=t) y cambia el parámetro
// BootAddr del core con defparam, que tiene precedencia sobre el valor que le
// pasa pochoco_soc.

`ifndef HILO
  `define HILO 0
`endif

module boot_hilo;
  defparam core_trace_tb.dut.u_core.BootAddr = 4 * `HILO;
  defparam core_trace_tb.dut.u_core.u_if.BootAddr = 4 * `HILO;
endmodule
