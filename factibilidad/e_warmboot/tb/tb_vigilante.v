// tb_vigilante.v: testbench del módulo vigilante.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Dos partes:
//
//   1. Casos dirigidos, con el resultado esperado escrito a mano: programa
//      sano, N - 1 precios sin respuesta (no dispara), N sin respuesta y
//      llega otro (dispara cuando CS_n sube y no antes), respuesta que llega
//      antes de que CS_n suba,
//      escritura en el mismo ciclo que el precio, disparo manual con CS_n en
//      bajo y en alto, reset a media cuenta y maestra detenida.
//   2. Estímulo aleatorio contra un modelo de referencia, comparando BOOT en
//      cada ciclo, con resets intercalados para que haya muchos disparos.
//
// El valor de N se cambia con -DN_VIG=valor.

`timescale 1ns/1ps

`ifndef N_VIG
  `define N_VIG 4
`endif
`ifndef CICLOS_AZAR
  `define CICLOS_AZAR 400000
`endif

module tb_vigilante;

  localparam integer N = `N_VIG;

  reg clk = 0;
  always #20 clk = ~clk;

  reg rst_n = 0, precio = 0, wr = 0, cs = 0, forzar = 0;
  wire boot;
  wire [1:0] sel;

  vigilante #(.N(N), .Destino(2'b01)) dut (
    .clk_i(clk), .rst_ni(rst_n), .precio_i(precio), .decision_wr_i(wr),
    .cs_activo_i(cs), .forzar_i(forzar), .boot_o(boot), .sel_o(sel));

  integer fallas = 0, casos = 0;

  task comprobar(input cond, input [8*72-1:0] texto);
    begin
      casos = casos + 1;
      if (cond) $display("  ok    %0s", texto);
      else begin $display("  FALLA %0s", texto); fallas = fallas + 1; end
    end
  endtask

  // Las entradas cambian en el flanco de bajada, lejos del flanco activo.
  task ciclos(input integer n);
    repeat (n) @(negedge clk);
  endtask

  task reset;
    begin
      rst_n = 0; precio = 0; wr = 0; cs = 0; forzar = 0;
      ciclos(3);
      rst_n = 1;
      ciclos(1);
    end
  endtask

  // Una transacción como la del testbench oficial vista desde adentro: CS_n
  // baja, el precio llega cerca del final y CS_n sube 25 ciclos después.
  // Si responde = 1, el programa escribe DECISION "demora" ciclos después del
  // precio (44 es el peor caso medido de trade.s en el core base).
  task tick(input responde, input integer demora);
    integer i;
    begin
      cs = 1;
      ciclos(200);
      precio = 1; ciclos(1); precio = 0;
      for (i = 1; i <= 60; i = i + 1) begin
        if (i == 25) cs = 0;
        if (responde && i == demora) wr = 1; else wr = 0;
        ciclos(1);
      end
      wr = 0;
      ciclos(40);
    end
  endtask

  // --- Modelo de referencia para la parte aleatoria --------------------------
  integer m_pend = 0;
  reg     m_boot = 0;
  integer difs = 0, disparos = 0, ciclos_azar = 0;
  reg     azar = 0;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      m_pend = 0;
      m_boot = 0;
    end else begin
      if ((m_pend >= N + 1 || forzar) && !cs) m_boot = 1;
      if (precio) begin
        if (wr) m_pend = 1;
        else if (m_pend < N + 1) m_pend = m_pend + 1;
      end else if (wr) m_pend = 0;
    end
  end

  reg boot_ant = 0;
  always @(negedge clk) begin
    if (azar) begin
      ciclos_azar = ciclos_azar + 1;
      if (boot !== m_boot) difs = difs + 1;
      if (boot && !boot_ant) disparos = disparos + 1;
    end
    boot_ant = boot;
  end

  integer i, semilla;

  initial begin
    semilla = 20261113;
    $display("vigilante, N = %0d", N);

    // 1. Reset
    reset;
    comprobar(boot === 1'b0 && sel === 2'b01, "despues del reset BOOT esta en 0 y el destino es 01");

    // 2. Programa sano: 2000 ticks con respuesta a los 44 ciclos
    for (i = 0; i < 2000; i = i + 1) tick(1, 44);
    comprobar(boot === 1'b0, "2000 ticks con respuesta: no dispara");

    // 3. N - 1 precios sin respuesta y despues el programa vuelve a responder
    //    a los 44 ciclos (despues de que CS_n sube): no dispara
    reset;
    for (i = 0; i < N - 1; i = i + 1) tick(0, 0);
    comprobar(boot === 1'b0, "N - 1 precios sin respuesta: no dispara");
    for (i = 0; i < 20; i = i + 1) tick(1, 44);
    comprobar(boot === 1'b0, "el programa vuelve a responder: la cuenta parte de cero");
    for (i = 0; i < N - 1; i = i + 1) tick(0, 0);
    tick(1, 44);
    comprobar(boot === 1'b0, "otra racha de N - 1 sin respuesta: tampoco dispara");

    // 4. N precios sin respuesta y llega el siguiente: dispara, y solo cuando
    //    CS_n sube
    reset;
    for (i = 0; i < N; i = i + 1) tick(0, 0);
    comprobar(boot === 1'b0, "N precios sin respuesta: espera al siguiente");
    cs = 1; ciclos(200);
    precio = 1; ciclos(1); precio = 0;
    ciclos(24);
    comprobar(boot === 1'b0, "llega el precio N + 1 con CS_n en bajo: BOOT espera");
    cs = 0;
    ciclos(1);
    comprobar(boot === 1'b1, "CS_n sube: BOOT sube en el ciclo siguiente");
    wr = 1; ciclos(1); wr = 0; ciclos(5);
    comprobar(boot === 1'b1, "una escritura posterior no baja BOOT");

    // 5. La respuesta al precio N + 1 llega antes de que CS_n suba: no dispara
    reset;
    for (i = 0; i < N; i = i + 1) tick(0, 0);
    tick(1, 10);
    comprobar(boot === 1'b0, "respuesta antes de que CS_n suba: no dispara");

    // 6. Escritura en el mismo ciclo que el precio: responde al anterior
    reset;
    for (i = 0; i < 3 * N + 3; i = i + 1) begin
      cs = 1; ciclos(200);
      precio = 1; wr = (i > 0); ciclos(1); precio = 0; wr = 0;
      ciclos(25); cs = 0; ciclos(60);
    end
    comprobar(boot === 1'b0, "escritura simultanea con el precio: cuenta como respuesta");

    // 7. Disparo manual
    reset;
    cs = 1; ciclos(10);
    forzar = 1; ciclos(50);
    comprobar(boot === 1'b0, "disparo manual con CS_n en bajo: espera");
    cs = 0; ciclos(1);
    comprobar(boot === 1'b1, "disparo manual: BOOT sube cuando CS_n sube");
    reset;
    forzar = 1; ciclos(1); forzar = 0; ciclos(2);
    comprobar(boot === 1'b1, "disparo manual con CS_n en alto: inmediato");

    // 8. Reset a media cuenta
    reset;
    for (i = 0; i < N; i = i + 1) tick(0, 0);
    reset;
    for (i = 0; i < N; i = i + 1) tick(0, 0);
    comprobar(boot === 1'b0, "el reset borra la cuenta");

    // 9. Maestra detenida, con rebotes de CS_n pero sin precios completos
    reset;
    for (i = 0; i < 5000; i = i + 1) begin cs = ~cs; ciclos(7); end
    cs = 0; ciclos(100000);
    comprobar(boot === 1'b0, "sin precios no dispara, aunque CS_n se mueva");

    // 10. Estímulo aleatorio contra el modelo
    reset;
    azar = 1;
    for (i = 0; i < `CICLOS_AZAR; i = i + 1) begin
      precio = ($random(semilla) & 31) == 0;
      wr     = ($random(semilla) & 63) == 0;
      if (($random(semilla) & 15) == 0) cs = ~cs;
      forzar = ($random(semilla) & 8191) == 0;
      if (($random(semilla) & 2047) == 0) begin rst_n = 0; ciclos(1); rst_n = 1; end
      ciclos(1);
    end
    azar = 0;
    $display("  aleatorio: %0d ciclos, %0d disparos, %0d diferencias con el modelo", ciclos_azar, disparos, difs);
    comprobar(difs == 0 && disparos > 20, "BOOT igual al modelo en todos los ciclos, con disparos");

    if (fallas == 0) $display("PASS vigilante N=%0d: %0d comprobaciones", N, casos);
    else             $display("FAIL vigilante N=%0d: %0d fallas de %0d", N, fallas, casos);
    $finish;
  end

endmodule
