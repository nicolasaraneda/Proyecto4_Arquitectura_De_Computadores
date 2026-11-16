// mon_vigilante.sv: monitor del vigilante para el testbench oficial.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El testbench oficial no se modifica. Este módulo se compila junto a él como
// un segundo módulo raíz (iverilog -s tb_proyecto_4 -s mon_vigilante) y mira
// por jerarquía el vigilante de la copia del SoC. Cuenta los ciclos con BOOT
// en alto y el valor máximo que alcanzó la cuenta de precios sin respuesta, y
// lo escribe en un archivo que revisa scripts/probar_soc.sh.

`timescale 1ns/1ps

`ifndef SALIDA_MON
  `define SALIDA_MON "mon_vigilante.txt"
`endif

module mon_vigilante;

  integer ciclos_boot = 0, max_cuenta = 0, precios = 0, escrituras = 0;
  integer fd;

  // El testbench oficial termina con $finish: el resumen se escribe en cada
  // precio, después de actualizar las cuentas, para que el archivo quede al día.
  always @(posedge tb_proyecto_4.clk) begin
    if (tb_proyecto_4.dut.g_vig.u_vig.boot_o === 1'b1) ciclos_boot = ciclos_boot + 1;
    if (tb_proyecto_4.dut.g_vig.u_vig.rst_ni === 1'b1) begin
      if (tb_proyecto_4.dut.g_vig.u_vig.sin_resp > max_cuenta)
        max_cuenta = tb_proyecto_4.dut.g_vig.u_vig.sin_resp;
      if (tb_proyecto_4.dut.g_vig.u_vig.precio_i)      precios    = precios + 1;
      if (tb_proyecto_4.dut.g_vig.u_vig.decision_wr_i) escrituras = escrituras + 1;
      if (tb_proyecto_4.dut.g_vig.u_vig.precio_i || tb_proyecto_4.dut.g_vig.u_vig.decision_wr_i) begin
        fd = $fopen(`SALIDA_MON, "w");
        $fdisplay(fd, "precios=%0d escrituras=%0d max_sin_respuesta=%0d ciclos_con_BOOT=%0d N=%0d",
                  precios, escrituras, max_cuenta, ciclos_boot, tb_proyecto_4.dut.g_vig.u_vig.N);
        $fclose(fd);
      end
    end
  end

endmodule
