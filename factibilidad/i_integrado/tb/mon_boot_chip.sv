// mon_boot_chip.sv: vigila la entrada BOOT de SB_WARMBOOT en la simulación de
// un bitstream.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Se compila como segundo módulo raíz junto a tb/tb_bitstream.sv del
// repositorio, que no se modifica. En el módulo que tools/chip_vlog.py
// reconstruye desde el .asc, la primitiva queda con el nombre u_warmboot
// (scripts/chip_vlog_wb.py de factibilidad/e_warmboot). El archivo de salida
// dice si BOOT estuvo alguna vez en alto: con el programa sano no debe.

`timescale 1ns/1ps

`ifndef SALIDA_BOOT
  `define SALIDA_BOOT "mon_boot.txt"
`endif

module mon_boot_chip;
  integer fd;
  bit     visto = 0;

  initial begin
    fd = $fopen(`SALIDA_BOOT, "w");
    $fdisplay(fd, "boot_en_alto=0 S1S0=%b%b", tb_bitstream.dut.u_warmboot.S1, tb_bitstream.dut.u_warmboot.S0);
    $fclose(fd);
  end

  always @(tb_bitstream.dut.u_warmboot.BOOT) begin
    if (tb_bitstream.dut.u_warmboot.BOOT === 1'b1 && !visto) begin
      visto = 1;
      fd = $fopen(`SALIDA_BOOT, "w");
      $fdisplay(fd, "boot_en_alto=1 en t=%0t", $time);
      $fclose(fd);
    end
  end
endmodule
