// tb_vig_barrel.sv: el vigilante con SB_WARMBOOT sobre el barrel, con el hilo
// supervisor colgado y los otros tres hilos trabajando.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre sw/cuelgue_supervisor.s (el hilo 0 responde K precios y se cuelga; los
// hilos 1, 2 y 3 cuentan y escriben en la memoria sin parar) con una maestra
// SPI que tiene los tiempos del testbench oficial. Comprueba:
//   1. mientras el supervisor responde, BOOT no sube y la cuenta de precios
//      sin respuesta no pasa de 1;
//   2. BOOT sube después del precio número K + N + 1, ni antes ni después, y
//      solo cuando CS_n ya está en alto;
//   3. el destino que se le pide a SB_WARMBOOT es S1 S0 = 01 (BOOT, S1 y S0
//      se miran en las entradas de la primitiva);
//   4. los tres hilos de estrategia siguen avanzando después del cuelgue del
//      supervisor y hasta el disparo (sus cuentas en la memoria crecen): el
//      vigilante dispara aunque el core esté vivo, porque lo que vigila es la
//      respuesta a la maestra;
//   5. BOOT no vuelve a bajar.
//
// Parámetros por la línea de comandos de vvp: +hex=PROGRAMA +k=K +n=N
// +periodo=NS. El SoC se compila con -DI_VIGILANTE (N = 4 por defecto; con
// -DVIG_N=1 este testbench instancia el SoC con VigN = 1).

`timescale 1ns/1ps

`ifndef VIG_N
  `define VIG_N 4
`endif

module tb_vig_barrel;
  localparam int N   = `VIG_N;
  localparam int CNT = 'h700 / 4;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;
  wire [3:0] leds;

  pochoco_soc #(.MemFile(""), .PorBits(4), .VigN(N)) dut (
    .i_Clk(clk), .o_LED(leds), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // BOOT y el destino se miran en las entradas de la primitiva SB_WARMBOOT y
  // no en los cables que salen del vigilante: así la prueba cubre también la
  // conexión entre los dos. Mirando los cables, una primitiva con BOOT en 0 o
  // con S1 y S0 cruzados pasaba la prueba (lo encontró la auditoría).
  wire       boot   = dut.g_vig.u_warmboot.BOOT;
  wire [1:0] s1s0_p = {dut.g_vig.u_warmboot.S1, dut.g_vig.u_warmboot.S0};

  // Maestra con los tiempos del testbench oficial
  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #500 sclk = 1;
      recibido[b] = (miso === 1'b1);
      #500 sclk = 0;
    end
    #500 cs_n = 1;
  endtask

  string  hex;
  int     k = 20, periodo = 100000, errores = 0;
  int     enviados = 0, precio_del_disparo = -1, max_cuenta = 0, cuenta_sano = 0;
  logic [7:0] rx;
  logic [31:0] c1, c2, c3;
  bit     boot_visto = 0, cs_en_bajo_al_disparar = 0, boot_bajo_despues = 0;

  // Vigila BOOT, CS_n y la cuenta en cada ciclo
  always @(posedge clk) begin
    if (dut.rst_ni === 1'b1 && dut.g_vig.u_vig.sin_resp > max_cuenta && !boot_visto)
      max_cuenta = dut.g_vig.u_vig.sin_resp;
    if (boot === 1'b1 && !boot_visto) begin
      boot_visto = 1;
      precio_del_disparo = enviados;
      if (cs_n !== 1'b1) cs_en_bajo_al_disparar = 1;
    end
    if (boot_visto && boot !== 1'b1) boot_bajo_despues = 1;
  end

  task automatic falla(input string que);
    errores++; $display("  FALLA: %s", que);
  endtask

  initial begin
    if (!$value$plusargs("hex=%s", hex)) begin $display("falta +hex=ARCHIVO"); $fatal(1); end
    void'($value$plusargs("k=%d", k));
    void'($value$plusargs("periodo=%d", periodo));
    $readmemh(hex, dut.u_ram.mem);
    wait (dut.rst_ni === 1'b1);
    #2000;

    // 1. El supervisor responde K precios
    for (int i = 0; i < k; i++) begin
      spi(8'd100 + i[7:0], rx); enviados++;
      #(periodo - 9500);
    end
    if (boot_visto) falla("BOOT subio mientras el supervisor respondia");
    cuenta_sano = max_cuenta;
    if (cuenta_sano > 1) falla($sformatf("la cuenta de precios sin respuesta llego a %0d con el supervisor sano", cuenta_sano));
    if (rx !== 8'h7F) falla($sformatf("la maestra no recibe la decision del supervisor (recibio %02x)", rx));

    // 2. El supervisor ya no responde. Llegan N precios mas: todavia no dispara.
    c1 = dut.u_ram.mem[CNT + 1]; c2 = dut.u_ram.mem[CNT + 2]; c3 = dut.u_ram.mem[CNT + 3];
    for (int i = 0; i < N; i++) begin
      spi(8'd200, rx); enviados++;
      #(periodo - 9500);
    end
    if (boot_visto) falla($sformatf("BOOT subio antes de tiempo, con el precio %0d (esperado %0d)", precio_del_disparo, k + N + 1));

    // 3. El precio N + 1 sin respuesta: dispara cuando CS_n sube
    spi(8'd201, rx); enviados++;
    #(periodo - 9500);
    if (!boot_visto) falla("BOOT no subio despues de N + 1 precios sin respuesta");
    else if (precio_del_disparo != k + N + 1) falla($sformatf("BOOT subio con el precio %0d, esperado %0d", precio_del_disparo, k + N + 1));
    if (cs_en_bajo_al_disparar) falla("BOOT subio con CS_n en bajo");
    if (s1s0_p !== 2'b01) falla($sformatf("destino S1 S0 = %b en la primitiva, esperado 01", s1s0_p));

    // 4. Los hilos de estrategia siguieron contando despues del cuelgue
    if (!(dut.u_ram.mem[CNT + 1] > c1 && dut.u_ram.mem[CNT + 2] > c2 && dut.u_ram.mem[CNT + 3] > c3))
      falla("algun hilo de estrategia dejo de contar");
    if (c1 == 0 || c2 == 0 || c3 == 0) falla("algun hilo de estrategia no habia partido");

    // 5. BOOT se queda arriba con mas precios
    for (int i = 0; i < 3; i++) begin
      spi(8'd202, rx); enviados++;
      #(periodo - 9500);
    end
    if (boot_bajo_despues) falla("BOOT volvio a bajar");

    if (errores == 0)
      $display("PASS tb_vig_barrel N=%0d: el supervisor responde %0d precios (cuenta maxima %0d mientras responde), BOOT sube con el precio %0d = K + N + 1 con CS_n en alto, destino 01; estrategias vivas: cuentas %0d %0d %0d al colgarse y %0d %0d %0d al final",
               N, k, cuenta_sano, precio_del_disparo, c1, c2, c3, dut.u_ram.mem[CNT + 1], dut.u_ram.mem[CNT + 2], dut.u_ram.mem[CNT + 3]);
    else begin
      $display("FAIL tb_vig_barrel N=%0d: %0d fallas", N, errores);
      $fatal(1);
    end
    $finish;
  end
endmodule
