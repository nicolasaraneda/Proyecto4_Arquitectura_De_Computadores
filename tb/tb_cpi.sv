// tb_cpi.sv: mide instrucciones completadas (IC), ciclos y CPI del Espino Core.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre un programa en el Pochoco SoC mientras emula a la maestra SPI con el
// mismo timing del testbench oficial (los precios salen de un LFSR, no de la
// serie de práctica). Cuenta, por clase de instrucción, cuántas se completan
// y cuántos ciclos pasan, y compara el total con el modelo de costo leído del
// RTL del Espino base:
//
//   ciclos = 2 * IC + loads + saltos tomados (branch tomado, jal, jalr)
//
// Además reporta IC y ciclos por tick, entre que llega el precio (byte_done)
// y la escritura de DECISION, igual que mide el testbench oficial.
//
// Desde la raíz del repositorio:
//   make cpi
// o con otro programa y otro número de ticks:
//   iverilog -g2012 -s tb_cpi -DPROGRAMA=\"sw/blink.hex\" -DNTICKS=50 -o build/tb_cpi \
//     $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_cpi.sv
//   vvp -n build/tb_cpi
//
// Este testbench mira señales internas del Espino base (u_core.u_id.commit,
// u_core.pc_set). Si la microarquitectura cambia, hay que actualizar esas rutas.

`timescale 1ns/1ps

`ifndef PROGRAMA
  `define PROGRAMA "sw/trade.hex"
`endif
`ifndef NTICKS
  `define NTICKS 200
`endif
`ifndef PERIODO_NS
  `define PERIODO_NS 100000
`endif

module tb_cpi;

  localparam int SPI_NS = 9500;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;

  pochoco_soc #(.MemFile(`PROGRAMA)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // Señales internas del core
  wire        commit = dut.u_core.u_id.commit;      // instrucción completada en este ciclo
  wire        pc_set = dut.u_core.pc_set;           // salto tomado en este ciclo
  wire [31:0] instr  = dut.u_core.instr_rdata_i;

  // Transacción SPI con el timing del testbench oficial
  task automatic spi(input logic [7:0] enviar);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #500 sclk = 1;
      #500 sclk = 0;
    end
    #500 cs_n = 1;
  endtask

  // --- Conteo global, por clase ---------------------------------------------
  // La ventana parte justo después de una instrucción completada que no saltó
  // y termina en otra igual, para que no queden burbujas a medias en los bordes.
  bit     midiendo = 0;
  longint ciclos = 0, ic = 0, n_load = 0, n_store = 0, n_br_t = 0, n_br_nt = 0, n_jump = 0, n_otras = 0;
  longint s_ciclos = 0, s_ic = 0, s_load = 0, s_store = 0, s_br_t = 0, s_br_nt = 0, s_jump = 0, s_otras = 0;

  always @(posedge clk) begin
    if (midiendo) begin
      ciclos++;
      if (commit) begin
        ic++;
        case (instr[6:0])
          7'h03:        n_load++;
          7'h23:        n_store++;
          7'h63:        if (pc_set) n_br_t++; else n_br_nt++;
          7'h6f, 7'h67: n_jump++;
          default:      n_otras++;
        endcase
        if (!pc_set) begin
          s_ciclos = ciclos; s_ic = ic; s_load = n_load; s_store = n_store;
          s_br_t = n_br_t; s_br_nt = n_br_nt; s_jump = n_jump; s_otras = n_otras;
        end
      end
    end else if (commit && !pc_set) begin
      midiendo = 1;
    end
  end

  // --- Conteo por tick: desde byte_done hasta la escritura de DECISION --------
  int  t_ciclos = 0, t_ic = 0, ticks_medidos = 0;
  int  peor_ciclos = 0, peor_ic = 0;
  longint suma_ciclos = 0, suma_ic = 0;
  bit  esperando = 0;

  always @(posedge clk) begin
    t_ciclos++;
    if (commit) t_ic++;
    if (dut.u_spi.byte_done) begin
      t_ciclos = 0; t_ic = 0; esperando = 1;
    end else if (esperando && dut.u_spi.wr && dut.u_spi.off == 2) begin
      ticks_medidos++;
      suma_ciclos += t_ciclos; suma_ic += t_ic;
      if (t_ciclos > peor_ciclos) peor_ciclos = t_ciclos;
      if (t_ic > peor_ic)         peor_ic = t_ic;
      esperando = 0;
    end
  end

  // --- Estímulo ---------------------------------------------------------------
  logic [7:0] lfsr = 8'h5A;
  longint modelo;

  initial begin
    #4000;
    for (int n = 0; n < `NTICKS; n++) begin
      lfsr = {lfsr[6:0], lfsr[7] ^ lfsr[5] ^ lfsr[4] ^ lfsr[3]};   // precio entre 1 y 255
      spi(lfsr);
      #(`PERIODO_NS - SPI_NS);
    end

    modelo = 2 * s_ic + s_load + s_br_t + s_jump;
    $display("Programa:                 %s", `PROGRAMA);
    $display("Ticks:                    %0d con periodo de %0d ns", `NTICKS, `PERIODO_NS);
    $display("Instrucciones (IC):       %0d", s_ic);
    $display("Ciclos:                   %0d", s_ciclos);
    $display("CPI medido:               %0.4f", real'(s_ciclos) / real'(s_ic));
    $display("  loads:                  %0d", s_load);
    $display("  stores:                 %0d", s_store);
    $display("  branches tomados:       %0d", s_br_t);
    $display("  branches no tomados:    %0d", s_br_nt);
    $display("  jal y jalr:             %0d", s_jump);
    $display("  otras:                  %0d", s_otras);
    $display("Modelo 2*IC+loads+saltos: %0d ciclos (diferencia con lo medido: %0d)", modelo, s_ciclos - modelo);
    if (ticks_medidos > 0) begin
      $display("Por tick (precio -> DECISION), %0d ticks:", ticks_medidos);
      $display("  IC promedio %0.2f, peor caso %0d", real'(suma_ic) / ticks_medidos, peor_ic);
      $display("  ciclos promedio %0.2f, peor caso %0d", real'(suma_ciclos) / ticks_medidos, peor_ciclos);
    end
    if (s_ciclos != modelo) begin
      $display("FAIL el modelo de costo no coincide con lo medido");
      $fatal(1);
    end
    $display("PASS el modelo de costo coincide con lo medido");
    $finish;
  end

endmodule
