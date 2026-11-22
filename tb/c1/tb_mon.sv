// tb_mon.sv: monitor de la cuenta que emula R3 contra la contabilidad de la maestra.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Instancia el testbench oficial (o una copia parametrizada, como la que arma
// tools/c1/contabilidad_rtl.py) sin cambiarle una línea, y mira desde fuera. En
// cada bajada de CS_n, o sea justo antes de la transacción siguiente, compara
//   lo que lleva el programa de R3 en su memoria de datos: D_CAJA, D_ACC y D_W
//   lo que lleva la maestra del testbench: caja, acciones y w
// después de ejecutar el byte del tick anterior. Para entonces el programa ya
// procesó ese precio (responde en menos de 1131 ciclos de los 2262 de la ronda 3).
// El último tick se compara al terminar la simulación (bloque final).
//
// D_W lleva el modo en su byte alto (sw/c1.s, telemetría): se compara con 24 bits.
//
// Plusargs (las direcciones salen del ensamblado de sw/c1.s):
//   +A_CAJA=n +A_ACC=n +A_W=n   direcciones de byte de D_CAJA, D_ACC y D_W
//   +MON=archivo.csv            una fila por tick
//   +DESFASE=1                  control negativo: compara el programa del tick n con la maestra del tick n-1,
//                               como si R3 ejecutara cada orden un tick tarde. Tiene que dar diferencias
// Termina con una línea "MONITOR ticks=N diferencias=K primera=T".

`timescale 1ns/1ps

module tb_mon;

  tb_proyecto_4 u_tb();

  int a_caja = 0, a_acc = 0, a_w = 0;
  int fd = 0, k = 0, ticks = 0, difs = 0, primero = -1, desfase = 0;
  int mc_prev = 0, ma_prev = 0, mw_prev = 0;
  bit hay_prev = 0;
  string ruta = "monitor.csv";

  initial begin
    void'($value$plusargs("A_CAJA=%d", a_caja));
    void'($value$plusargs("A_ACC=%d", a_acc));
    void'($value$plusargs("A_W=%d", a_w));
    void'($value$plusargs("MON=%s", ruta));
    void'($value$plusargs("DESFASE=%d", desfase));
    fd = $fopen(ruta, "w");
    $fdisplay(fd, "tick,prog_caja,prog_acciones,prog_patrimonio,maestra_caja,maestra_acciones,maestra_patrimonio,igual");
  end

  task automatic comparar(input int tick);
    int pc, pa, pw, mc, ma, mw;
    bit igual;
    pc = u_tb.dut.u_ram.mem[a_caja / 4];
    pa = u_tb.dut.u_ram.mem[a_acc / 4];
    pw = u_tb.dut.u_ram.mem[a_w / 4] & 32'h00FFFFFF;
    mc = u_tb.caja;
    ma = u_tb.acciones;
    mw = u_tb.w;
    if (desfase != 0) begin                       // control: la maestra de un tick antes
      int tc = mc, ta = ma, tw = mw;
      mc = hay_prev ? mc_prev : pc;
      ma = hay_prev ? ma_prev : pa;
      mw = hay_prev ? mw_prev : pw;
      mc_prev = tc; ma_prev = ta; mw_prev = tw; hay_prev = 1;
    end
    igual = (pc == mc) && (pa == ma) && (pw == mw);
    ticks++;
    if (!igual) begin
      difs++;
      if (primero < 0) primero = tick;
    end
    $fdisplay(fd, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d", tick, pc, pa, pw, mc, ma, mw, igual);
  endtask

  always @(negedge u_tb.cs_n) begin
    if (k > 0) comparar(k - 1);
    k++;
  end

  final begin
    if (k > 0) comparar(k - 1);
    $fclose(fd);
    $display("MONITOR ticks=%0d diferencias=%0d primera=%0d", ticks, difs, primero);
  end

endmodule
