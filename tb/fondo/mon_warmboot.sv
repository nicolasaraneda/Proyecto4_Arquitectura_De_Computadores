// mon_warmboot.sv: mira la primitiva SB_WARMBOOT de un bitstream simulado
// desde su .asc (tb/tb_bitstream.sv con el chip de R2).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Se compila como segundo módulo de nivel superior, junto a tb_bitstream. No
// conduce nada: imprime una línea cuando BOOT sube, con el tiempo, la imagen
// que se pide (S1 S0) y el estado de CS_n en ese momento. Con eso
// tools/fondo/bitstreams.sh comprueba que el vigilante que quedó dentro del
// bitstream pide el relevo cuando se le inyecta la falla, y que no lo pide en
// una corrida sana.

`timescale 1ns/1ps

module mon_warmboot;

  wire boot = tb_bitstream.dut.u_warmboot.BOOT;
  wire s1   = tb_bitstream.dut.u_warmboot.S1;
  wire s0   = tb_bitstream.dut.u_warmboot.S0;
  bit  visto = 0;

  always @(boot) begin
    if (boot === 1'b1 && !visto) begin
      visto = 1;
      $display("WARMBOOT t_ns=%0d s1s0=%b%b cs_n=%b", $time, s1, s0, tb_bitstream.cs_n);
    end
  end

  final if (!visto) $display("WARMBOOT nunca");

endmodule
