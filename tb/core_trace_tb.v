// core_trace_tb.v: traza del core para comparar dos variantes del Espino.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Viene del tb/core_trace_tb.v de nuestro Proyecto 3, adaptado al SoC de la
// FPGA (pochoco_soc en vez de asic_top). Corre el programa PROGRAMA durante
// CICLOS ciclos después del reset y escribe en TRAZA, una línea por evento y
// con el número de ciclo:
//   - cada escritura al banco de registros (registro y valor);
//   - cada acceso al bus de datos (lectura o escritura, bytes, dirección y
//     dato escrito);
//   - cada cambio de LEDs y display.
// Si dos variantes del core producen la misma traza, ejecutan el programa
// igual, ciclo a ciclo. Si producen las mismas secuencias de eventos sin
// mirar el ciclo, hacen lo mismo en otros ciclos (tb/comparar_trazas.py).
//
// La variante del core se elige igual que en el RTL: sin nada es el Espino
// base, -DESPINO_SEGMENTADO es el pipeline de 3 etapas y -DESPINO_ROM es el
// pipeline con el programa en una ROM combinacional.
//
// Con -DSWITCH_CONTADOR los interruptores cambian en cada ciclo (lo usa
// sw/hazard_cycles.s). Sin eso valen 0. El bus SPI queda quieto.
//
// Monitor de valores desconocidos usados: cuenta, en cada flanco, rf_wdata
// con algún bit X cuando se escribe el banco; dirección, bytes o dato del bus
// con X en un acceso; operandos de la ALU con X en una instrucción que usa su
// resultado; y salidas con X. Un X que nadie usa es normal. Uno usado, no.
//
// Uso: make riesgos (tools/riesgos.sh).

`timescale 1ns/1ps

`ifndef PROGRAMA
  `define PROGRAMA "sw/trade.hex"
`endif
`ifndef TRAZA
  `define TRAZA "build/traza.txt"
`endif
`ifndef CICLOS
  `define CICLOS 4000
`endif

module core_trace_tb;

  reg        clk = 1'b0;
  wire [3:0] led;
  wire [6:0] seg1, seg2;
  reg  [3:0] sw = 4'b0000;

  pochoco_soc #(.MemFile(`PROGRAMA), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(led), .i_Switch(sw),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  always #20 clk = ~clk;

`ifdef SWITCH_CONTADOR
  // Los interruptores cambian en cada ciclo, a mitad del período
  always @(negedge clk) sw <= sw + 4'd1;
`endif

  integer f, ciclo, retiradas, ciclo_evt, retiradas_evt;
  reg [3:0]  led_prev;
  reg [13:0] seg_prev;

  integer x_rf = 0, x_bus = 0, x_alu = 0, x_io = 0, n_rf = 0;
  wire commit_m  = dut.u_core.instr_valid_id & ~dut.u_core.stall;
  wire alu_usada = commit_m & (dut.u_core.u_id.lsu_req_o | dut.u_core.u_id.is_branch |
                               dut.u_core.u_id.is_jalr |
                               (dut.u_core.u_id.rf_we_o & (dut.u_core.u_id.rf_wd_sel == 2'd0)));
  task monitor_x;
    begin
      if (dut.u_core.rf_we) begin
        n_rf = n_rf + 1;
        if (^dut.u_core.rf_wdata === 1'bx) x_rf = x_rf + 1;
      end
      if (dut.u_core.data_req_o &&
          (^dut.u_core.data_addr_o === 1'bx || ^dut.u_core.data_be_o === 1'bx ||
           (dut.u_core.data_we_o && ^dut.u_core.data_wdata_o === 1'bx)))
        x_bus = x_bus + 1;
      if (alu_usada && (^dut.u_core.u_id.operand_a === 1'bx || ^dut.u_core.u_id.operand_b === 1'bx))
        x_alu = x_alu + 1;
      if (^led === 1'bx || ^seg1 === 1'bx || ^seg2 === 1'bx)
        x_io = x_io + 1;
    end
  endtask

  initial begin
    f = $fopen(`TRAZA, "w");
    wait (dut.rst_ni);
    ciclo     = 0;
    retiradas = 0;
    ciclo_evt = 0;
    retiradas_evt = 0;
    led_prev  = led;
    seg_prev  = {seg1, seg2};
    repeat (`CICLOS) begin
      @(posedge clk);
      ciclo = ciclo + 1;
      monitor_x;
      // Instrucción completada: hay una instrucción válida en ejecución y el
      // core no está detenido.
      if (dut.u_core.instr_valid_id && !dut.u_core.stall)
        retiradas = retiradas + 1;
      if (dut.u_core.rf_we) begin
        $fdisplay(f, "%0d rf x%0d = %h", ciclo,
                  dut.u_core.rf_waddr, dut.u_core.rf_wdata);
      end
      if (dut.u_core.data_req_o) begin
        $fdisplay(f, "%0d bus %s be=%b addr=%h wdata=%h", ciclo,
                  dut.u_core.data_we_o ? "W" : "R",
                  dut.u_core.data_be_o, dut.u_core.data_addr_o,
                  dut.u_core.data_wdata_o);
      end
      if (led !== led_prev || {seg1, seg2} !== seg_prev) begin
        $fdisplay(f, "%0d io led=%b seg=%b_%b", ciclo, led, seg1, seg2);
        ciclo_evt = ciclo; retiradas_evt = retiradas;
      end
      led_prev = led;
      seg_prev = {seg1, seg2};
    end
    $fclose(f);
    $display("core_trace_tb: %0d ciclos, traza en %0s", `CICLOS, `TRAZA);
    // CPI hasta el último cambio de las salidas: después el programa queda
    // en un lazo infinito que no representa nada.
    $display("core_trace_tb: CPI = %0d ciclos / %0d instrucciones = %.3f (hasta el ultimo cambio de las salidas)",
             ciclo_evt, retiradas_evt, retiradas_evt > 0 ? $itor(ciclo_evt) / $itor(retiradas_evt) : 0.0);
    $display("core_trace_tb: monitor de X: %0d valores desconocidos usados en %0d escrituras al banco (rf_wdata %0d, bus %0d, operandos ALU %0d, salidas %0d)",
             x_rf + x_bus + x_alu + x_io, n_rf, x_rf, x_bus, x_alu, x_io);
    $finish;
  end

endmodule
