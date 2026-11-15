// tb_barrel.sv: prueba funcional y conteo por hilo del Espino barrel.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre un programa en el SoC compilado con el core barrel (pochoco_soc con
// -DESPINO_BARREL), con el bus SPI quieto, y entrega:
//
// 1. Instrucciones completadas y ciclos, por hilo y en total, con el CPI de
//    cada hilo y el agregado. Se mide en régimen: la ventana parte en el
//    ciclo 5 después del reset, cuando las dos burbujas del arranque ya
//    salieron, y dura un múltiplo de 4 ciclos. Comprueba el modelo de costo
//    del barrel: cada hilo completa exactamente una instrucción cada 4
//    ciclos, sea de ALU, load, store o salto, tomado o no.
//
// 2. Comprobaciones al final de la corrida:
//      -DESPERADO=\"archivo\"   una línea "dirección valor" (hexadecimal) por
//                              palabra de memoria que debe tener ese valor.
//      -DLEDS=n                valor esperado de los LEDs.
//      -DDISP=n                valor esperado del registro del display.
//
// 3. Con -DTRAZA=\"prefijo\", una traza por hilo (prefijo_h0.txt a
//    prefijo_h3.txt) con el formato de tb/core_trace_tb.v: escrituras al
//    banco de registros y accesos al bus de datos de ese hilo, con el número
//    de ciclo. Sirve para comparar cada hilo contra el Espino base con
//    tb/comparar_trazas.py --modo funcional --tipos rf,bus. Los cambios de
//    las salidas van a prefijo_io.txt (no se pueden atribuir a un hilo).
//
// 4. Monitor de valores desconocidos usados, como el de tb/core_trace_tb.v:
//    dato escrito al banco con X, o dirección, bytes o dato de un acceso al
//    bus con X.
//
// El ciclo k es el intervalo que termina en el flanco de subida número k
// después de que se suelta el reset.
//
// Uso: tools/barrel/humo.sh y tools/barrel/medir_cpi.sh (make barrel-humo, make barrel-cpi).

`timescale 1ns/1ps

`ifndef PROGRAMA
  `define PROGRAMA "build/barrel/sw/hilos_distintos.hex"
`endif
`ifndef CICLOS
  `define CICLOS 4000
`endif

module tb_barrel;

  reg        clk = 1'b0;
  wire [3:0] led;
  wire [6:0] seg1, seg2;

  pochoco_soc #(.MemFile(`PROGRAMA), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(led), .i_Switch(4'b0000),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  always #20 clk = ~clk;

  // Señales internas del core
  wire        x_valid = dut.u_core.tb_valid_x;      // instrucción de verdad en X
  wire [1:0]  x_tid   = dut.u_core.tb_tid_x;
  wire [31:0] x_instr = dut.u_core.tb_instr_x;
  wire        x_taken = dut.u_core.tb_taken;
  wire        m_we    = dut.u_core.tb_rf_we;
  wire [1:0]  m_tid   = dut.u_core.tb_tid_m;
  wire [3:0]  m_wa    = dut.u_core.tb_rf_wa;
  wire [31:0] m_wd    = dut.u_core.tb_rf_wd;
  wire        d_req   = dut.u_core.data_req_o;
  wire        d_we    = dut.u_core.data_we_o;
  wire [3:0]  d_be    = dut.u_core.data_be_o;
  wire [31:0] d_addr  = dut.u_core.data_addr_o;
  wire [31:0] d_wd    = dut.u_core.data_wdata_o;

  localparam int VENTANA = ((`CICLOS - 4) / 4) * 4;   // ciclos 5 a 4 + VENTANA

  longint ic [4], n_load [4], n_store [4], n_br_t [4], n_br_nt [4], n_jump [4], n_otras [4];
  longint ic_total = 0, ciclos_v = 0;
  int     primer_x [4];
  int     fd [4];
  int     fd_io = 0;
  int     ciclo = 0;
  int     x_rf = 0, x_bus = 0, n_rf = 0, n_bus = 0;
  int     fallas = 0;
  reg [3:0]  led_prev;
  reg [13:0] seg_prev;

  task automatic comprobar(input bit ok, input string texto);
    if (ok) $display("PASS %s", texto);
    else begin $display("FAIL %s", texto); fallas++; end
  endtask

`ifdef ESPERADO
  task automatic revisar_memoria;
    int f, r, n = 0, malas = 0;
    logic [31:0] dir, valor, leido;
    f = $fopen(`ESPERADO, "r");
    if (f == 0) begin $display("FAIL no se encontro %s", `ESPERADO); fallas++; return; end
    while (!$feof(f)) begin
      r = $fscanf(f, "%h %h\n", dir, valor);
      if (r == 2) begin
        n++;
        leido = dut.u_ram.mem[dir[10:2]];
        if (leido !== valor) begin
          $display("FAIL memoria[%h] = %h, se esperaba %h", dir, leido, valor);
          malas++;
        end
      end
    end
    $fclose(f);
    comprobar(malas == 0 && n > 0, $sformatf("%0d de %0d palabras de memoria con el valor esperado", n - malas, n));
  endtask
`endif

  initial begin
    string prefijo;
    for (int t = 0; t < 4; t++) begin
      ic[t] = 0; n_load[t] = 0; n_store[t] = 0; n_br_t[t] = 0; n_br_nt[t] = 0; n_jump[t] = 0; n_otras[t] = 0;
      primer_x[t] = 0; fd[t] = 0;
    end
`ifdef TRAZA
    prefijo = `TRAZA;
    for (int t = 0; t < 4; t++) fd[t] = $fopen($sformatf("%s_h%0d.txt", prefijo, t), "w");
    fd_io = $fopen($sformatf("%s_io.txt", prefijo), "w");
`endif
    wait (dut.rst_ni);
    led_prev = led;
    seg_prev = {seg1, seg2};
    repeat (`CICLOS) begin
      @(posedge clk);
      ciclo++;

      // Monitor de X y traza
      if (m_we) begin
        n_rf++;
        if (^m_wd === 1'bx || ^m_wa === 1'bx) x_rf++;
        if (fd[m_tid] != 0) $fdisplay(fd[m_tid], "%0d rf x%0d = %h", ciclo, m_wa, m_wd);
      end
      if (d_req) begin
        n_bus++;
        if (^d_addr === 1'bx || ^d_be === 1'bx || (d_we && ^d_wd === 1'bx)) x_bus++;
        if (fd[x_tid] != 0)
          $fdisplay(fd[x_tid], "%0d bus %s be=%b addr=%h wdata=%h", ciclo, d_we ? "W" : "R", d_be, d_addr, d_wd);
      end
      if (led !== led_prev || {seg1, seg2} !== seg_prev) begin
        if (fd_io != 0) $fdisplay(fd_io, "%0d io led=%b seg=%b_%b", ciclo, led, seg1, seg2);
      end
      led_prev = led;
      seg_prev = {seg1, seg2};

      // Primera instrucción de cada hilo
      if (x_valid && primer_x[x_tid] == 0) primer_x[x_tid] = ciclo;

      // Conteo en régimen
      if (ciclo >= 5 && ciclo < 5 + VENTANA) begin
        ciclos_v++;
        if (x_valid) begin
          ic[x_tid]++;
          ic_total++;
          case (x_instr[6:0])
            7'h03:        n_load[x_tid]++;
            7'h23:        n_store[x_tid]++;
            7'h63:        if (x_taken) n_br_t[x_tid]++; else n_br_nt[x_tid]++;
            7'h6f, 7'h67: n_jump[x_tid]++;
            default:      n_otras[x_tid]++;
          endcase
        end
      end
    end
    for (int t = 0; t < 4; t++) if (fd[t] != 0) $fclose(fd[t]);
    if (fd_io != 0) $fclose(fd_io);

    $display("Programa:                 %s", `PROGRAMA);
    $display("Ciclos simulados:         %0d despues del reset", `CICLOS);
    $display("Primera instruccion en ejecucion (ciclo): hilo 0 en %0d, hilo 1 en %0d, hilo 2 en %0d, hilo 3 en %0d",
             primer_x[0], primer_x[1], primer_x[2], primer_x[3]);
    $display("Ventana de medicion:      %0d ciclos (del 5 al %0d)", ciclos_v, 4 + VENTANA);
    $display("  hilo      IC   ciclos    CPI   loads  stores  br.tom  br.no  jal/jalr   otras");
    for (int t = 0; t < 4; t++)
      $display("  %0d    %6d  %7d  %5.3f  %6d  %6d  %6d  %5d  %8d  %6d", t, ic[t], ciclos_v,
               real'(ciclos_v) / real'(ic[t]), n_load[t], n_store[t], n_br_t[t], n_br_nt[t], n_jump[t], n_otras[t]);
    $display("  todos %6d  %7d  %5.3f", ic_total, ciclos_v, real'(ciclos_v) / real'(ic_total));
    $display("CPI agregado:             %0.4f  (%0.2f MIPS a 25 MHz)", real'(ciclos_v) / real'(ic_total),
             25.0 * real'(ic_total) / real'(ciclos_v));
    $display("CPI de un hilo:           %0.4f  (%0.2f MIPS a 25 MHz)", real'(ciclos_v) / real'(ic[0]),
             25.0 * real'(ic[0]) / real'(ciclos_v));
    $display("Monitor de X:             %0d valores desconocidos usados en %0d escrituras al banco y %0d accesos al bus",
             x_rf + x_bus, n_rf, n_bus);

    comprobar(ic_total == ciclos_v, "modelo de costo agregado: una instruccion completada por ciclo");
    comprobar(4 * ic[0] == ciclos_v && 4 * ic[1] == ciclos_v && 4 * ic[2] == ciclos_v && 4 * ic[3] == ciclos_v,
              "modelo de costo por hilo: una instruccion cada 4 ciclos, de cualquier clase");
    comprobar(x_rf + x_bus == 0, "ningun valor desconocido llega al banco ni al bus");
`ifdef ESPERADO
    revisar_memoria();
`endif
`ifdef LEDS
    comprobar(led === `LEDS, $sformatf("LEDs = %b (se esperaba %b)", led, 4'(`LEDS)));
`endif
`ifdef DISP
    comprobar(dut.u_periph.digit_q === `DISP, $sformatf("display = %h (se esperaba %h)", dut.u_periph.digit_q, 8'(`DISP)));
`endif
    if (fallas == 0) $display("RESULTADO: PASS");
    else             $display("RESULTADO: FAIL (%0d comprobaciones fallaron)", fallas);
    $finish;
  end

endmodule
