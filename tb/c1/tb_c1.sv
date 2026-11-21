// tb_c1.sv: testbench de medición y de protocolo de sw/c1.s sobre el Espino
// barrel con la tabla de 512 palabras (R3).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Parte de tb/fondo/tb_fondo.sv (misma maestra SPI configurable y misma
// medición de byte_done a la primera escritura en DECISION que el testbench
// oficial) y cambia lo que es propio del programa de cuatro hilos:
//
//   - Conteo por tick y por hilo: instrucciones ejecutadas y cuántas fueron
//     vueltas del lazo de espera de cada hilo (+A_ESPERAk, +L_ESPERAk).
//   - Hitos del tick, en ciclos desde byte_done: store de D_PUB, de D_REG, de
//     D_TAB y de D_POL (+A_PUB, +A_REG, +A_TAB, +A_POL), y DECISION.
//   - Vigilancia del protocolo: solo el hilo 0 toca el SPI; del periférico, el
//     hilo 0 solo escribe los LED y el hilo 3 solo lee los interruptores y
//     escribe los dígitos; nadie escribe en la tabla; cada palabra de la RAM
//     tiene un solo hilo que la escribe; ningún store cae fuera de los datos
//     (+A_DATOS es la primera palabra de datos).
//   - Estado al cerrar el tick: las palabras de datos del programa, en
//     hexadecimal, para comparar con ref/c1/c1.py (tools/c1/revisar.py).
//   - Vigilante (solo con -DESPINO_VIGILANTE), como en tb_fondo.sv.
//
//   +PROGRAMA=build/c1/c1.hex  +TABLA=sw/c1_tabla.hex  +SERIE=archivo.csv
//   +NTICKS=2000  +PERIODO_NS=100000  +INICIO_NS=4000  +BOTONES=0
//   +RONDA_TICKS=0 +PAUSA_NS=0 +PERIODO2_NS +PERIODO3_NS
//   +SCLK_MEDIO_NS=500  +CS_SETUP_NS=1500  +CS_HOLD_NS=500
//   +SALIDA=archivo.csv   "tick,precio,decision" (lo que lee la maestra)
//   +ESTADO=archivo.csv   una fila por precio recibido
//
// Al final imprime una línea RESUMEN con los conteos que usa tools/c1/revisar.py.
`timescale 1ns/1ps

module tb_c1;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;
  wire [3:0] leds;
  wire [6:0] seg1, seg2;
  logic [3:0] botones = 4'b0000;

  pochoco_soc #(.MemFile("")) dut (
    .i_Clk(clk), .o_LED(leds), .i_Switch(botones),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // --- Configuración en tiempo de ejecución ------------------------------------
  string programa = "build/c1/c1.hex", serie = "data/practica_meta.csv", tabla = "sw/c1_tabla.hex";
  string salida = "build/c1/salida.csv", estado = "";
  int ntick = 2000, ronda_ticks = 0;
  longint pausa_ns = 0, periodo_ns = 100000, periodo2_ns = -1, periodo3_ns = -1;
  longint inicio_ns = 4000, sclk_medio_ns = 500, cs_setup_ns = 1500, cs_hold_ns = 500;
  int a_espera [4] = '{-1, -1, -1, -1}, l_espera [4] = '{12, 8, 8, 8};
  int a_pub = -1, a_reg = -1, a_tab = -1, a_pol = -1, a_datos = 32'h800, n_botones = 0;

  int precio [];

  task automatic leer_serie;
    int fd, t, r, n;
    string encabezado;
    precio = new[ntick];
    fd = $fopen(serie, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", serie); $finish; end
    r = $fgets(encabezado, fd);
    for (n = 0; n < ntick; n++) begin
      r = $fscanf(fd, "%d,%d\n", t, precio[n]);
      if (r != 2) begin $display("ERROR: %s tiene %0d ticks", serie, n); $finish; end
    end
    $fclose(fd);
  endtask

  int bits_x = 0;
  int tick_tx = 0;

  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #(cs_setup_ns - sclk_medio_ns);
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #(sclk_medio_ns) sclk = 1;
      if (miso !== 1'b0 && miso !== 1'b1) bits_x++;
      recibido[b] = (miso === 1'b1);
      #(sclk_medio_ns) sclk = 0;
    end
    #(cs_hold_ns) cs_n = 1;
  endtask

  // --- Señales internas ----------------------------------------------------------
  wire        xv   = dut.u_core.tb_valid_x;      // instrucción de verdad en la etapa X
  wire [1:0]  xt   = dut.u_core.tb_tid_x;        // hilo al que pertenece
  wire [31:0] xpc  = dut.u_core.tb_pc_x;
  wire        dreq = dut.data_req;
  wire        dwe  = dut.data_we;
  wire [31:0] dad  = dut.data_addr;
  wire [31:0] dwd  = dut.data_wdata;
  wire        wr_dec = dut.u_spi.wr && dut.u_spi.off == 2;
  wire        wr_ram = dreq && dwe && !dad[31];
  wire        es_tab = dad[31] && dad[17];
  wire        es_per = dad[31] && !dad[16] && !es_tab;
  wire        es_spi = dad[31] &&  dad[16] && !es_tab;
  wire        wr_per = dreq && dwe && es_per;
  wire [11:0] wa     = {dad[11:2], 2'b00};

  // --- Medición igual a la del oficial -------------------------------------------
  int ciclos = 0, peor_caso = 0, respuestas = 0, precios_perdidos = 0, recibidos = 0, sin_respuesta = 0;
  longint suma_ciclos = 0;
  bit esperando = 0;

  // --- Por tick --------------------------------------------------------------------
  longint ciclo = 0, t0 = 0;
  bit     abierta = 0;
  int     v_tick, v_precio;
  int     ic [4], son [4];
  int     n_dec, n_tel, c_fin, r_ciclos;
  int     c_pub, c_reg, c_tab, c_pol;
  int     escritor [512];
  logic [7:0]  s_byte;
  int     fd_estado = 0;

  int violaciones = 0, dec_multiples = 0, tel_multiples = 0, stores_ram = 0;

  task automatic violacion(input string que);
    violaciones++;
    if (violaciones <= 10)
      $display("VIOLACION ciclo %0d hilo %0d pc %03x dir %08x: %s", ciclo, xt, xpc[11:0], dad, que);
  endtask

  task automatic cerrar_tick;
    if (n_dec != 1) dec_multiples++;
    if (n_tel > 2)  tel_multiples++;
    if (fd_estado != 0) begin
      $fwrite(fd_estado, "%0d,%0d,%0d,%0d,%02x,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
        v_tick, v_precio, t0, r_ciclos, s_byte, n_dec, n_tel, c_fin,
        ic[0], ic[1], ic[2], ic[3], son[0], son[1], son[2], son[3], c_pub, c_reg, c_tab, c_pol,
        dut.u_periph.led_q, dut.u_periph.digit_q);
      for (int i = a_datos / 4; i < 512; i++) $fwrite(fd_estado, ",%08x", dut.u_ram.mem[i]);
      $fwrite(fd_estado, "\n");
    end
  endtask
  function automatic bit en_lazo(input int pc, input int base, input int largo);
    return base >= 0 && pc >= base && pc < base + largo;
  endfunction

  always @(posedge clk) begin
    // Medición del oficial
    ciclos++;
    if (dut.u_spi.byte_done) begin
      if (dut.u_spi.new_price_q) precios_perdidos++;
      if (esperando) sin_respuesta++;
      recibidos++;
      ciclos = 0;
      esperando = 1;
    end else if (esperando && wr_dec) begin
      if (ciclos > peor_caso) peor_caso = ciclos;
      suma_ciclos += ciclos;
      respuestas++;
      esperando = 0;
    end

    // Por tick
    if (dut.u_spi.byte_done) begin
      if (abierta) cerrar_tick();
      abierta = 1; t0 = ciclo;
      v_tick = tick_tx; v_precio = {dut.u_spi.rx_shift[6:0], dut.u_spi.mosi};
      for (int h = 0; h < 4; h++) begin ic[h] = 0; son[h] = 0; end
      n_dec = 0; n_tel = 0; c_fin = -1; r_ciclos = -1;
      c_pub = -1; c_reg = -1; c_tab = -1; c_pol = -1;
      s_byte = 0;
    end else if (abierta) begin
      if (xv) begin
        ic[xt]++;
        if (en_lazo(xpc, a_espera[xt], l_espera[xt])) son[xt]++;
        if (xt == 0 && n_dec > 0 && c_fin < 0 && xpc == a_espera[0]) c_fin = ciclo - t0;
      end
      if (xv && wr_ram) begin
        if (wa == a_pub && c_pub < 0) c_pub = ciclo - t0;
        if (wa == a_reg && c_reg < 0) c_reg = ciclo - t0;
        if (wa == a_tab && c_tab < 0) c_tab = ciclo - t0;
        if (wa == a_pol && c_pol < 0) c_pol = ciclo - t0;
      end
      if (wr_dec) begin
        n_dec++;
        if (n_dec == 1) begin
          r_ciclos = ciclo - t0;
          s_byte = dwd[7:0];
        end
      end
      if (wr_per) n_tel++;
    end

    // Vigilancia del protocolo
    if (xv && dreq && es_spi && xt != 0) violacion("un hilo distinto del 0 toca el SPI");
    if (xv && dreq && es_per && !(xt == 0 && dwe && dad[7:2] == 1) && !(xt == 3 && dwe && dad[7:2] == 0)
        && !(xt == 3 && !dwe && dad[7:2] == 2)) violacion("acceso al periferico fuera de lo permitido");
    if (xv && dreq && dwe && es_tab) violacion("store a la tabla");
    if (xv && wr_ram) begin
      stores_ram++;
      if (wa < a_datos) violacion("store fuera de los datos");
      else if (escritor[wa[11:2]] < 0) escritor[wa[11:2]] = xt;
      else if (escritor[wa[11:2]] != xt) violacion("dos hilos escriben la misma palabra");
    end
    ciclo++;
  end

  // --- Vigilante -----------------------------------------------------------------------
  int vig_boot = 0, vig_max = 0, vig_tick = -1;
`ifdef ESPINO_VIGILANTE
  always @(posedge clk) begin
    if (dut.g_vig.boot && vig_boot == 0) begin vig_boot = 1; vig_tick = tick_tx; end
    if (dut.g_vig.u_vig.sin_resp > vig_max) vig_max = dut.g_vig.u_vig.sin_resp;
  end
`endif

  // --- Estímulo ------------------------------------------------------------------------
  logic [7:0] decision;
  int fd;
  longint dur, per, presupuesto, presupuesto_min = 64'h7fffffff;

  initial begin
    void'($value$plusargs("PROGRAMA=%s", programa));
    void'($value$plusargs("TABLA=%s", tabla));
    void'($value$plusargs("SERIE=%s", serie));
    void'($value$plusargs("SALIDA=%s", salida));
    void'($value$plusargs("ESTADO=%s", estado));
    void'($value$plusargs("NTICKS=%d", ntick));
    void'($value$plusargs("RONDA_TICKS=%d", ronda_ticks));
    void'($value$plusargs("PAUSA_NS=%d", pausa_ns));
    void'($value$plusargs("PERIODO_NS=%d", periodo_ns));
    void'($value$plusargs("PERIODO2_NS=%d", periodo2_ns));
    void'($value$plusargs("PERIODO3_NS=%d", periodo3_ns));
    void'($value$plusargs("INICIO_NS=%d", inicio_ns));
    void'($value$plusargs("SCLK_MEDIO_NS=%d", sclk_medio_ns));
    void'($value$plusargs("CS_SETUP_NS=%d", cs_setup_ns));
    void'($value$plusargs("CS_HOLD_NS=%d", cs_hold_ns));
    void'($value$plusargs("A_ESPERA0=%d", a_espera[0]));
    void'($value$plusargs("A_ESPERA1=%d", a_espera[1]));
    void'($value$plusargs("A_ESPERA2=%d", a_espera[2]));
    void'($value$plusargs("A_ESPERA3=%d", a_espera[3]));
    void'($value$plusargs("A_PUB=%d", a_pub));
    void'($value$plusargs("A_REG=%d", a_reg));
    void'($value$plusargs("A_TAB=%d", a_tab));
    void'($value$plusargs("A_POL=%d", a_pol));
    void'($value$plusargs("A_DATOS=%d", a_datos));
    void'($value$plusargs("BOTONES=%d", n_botones));
    botones = n_botones[3:0];
    for (int i = 0; i < 512; i++) escritor[i] = -1;
    if (periodo2_ns < 0) periodo2_ns = periodo_ns;
    if (periodo3_ns < 0) periodo3_ns = periodo2_ns;
    if (cs_setup_ns < sclk_medio_ns) begin
      $display("ERROR: CS_SETUP_NS debe ser al menos SCLK_MEDIO_NS"); $finish;
    end
    dur = cs_setup_ns + 15 * sclk_medio_ns + cs_hold_ns;    // duración de la transacción

    $readmemh(programa, dut.u_ram.mem);
    $readmemh(tabla, dut.g_tabla.u_tabla.mem);
    leer_serie();
    fd = $fopen(salida, "w");
    $fdisplay(fd, "tick,precio,decision");
    if (estado != "") begin
      fd_estado = $fopen(estado, "w");
      $fdisplay(fd_estado, "tick,precio,ciclo,respuesta,byte,n_dec,n_tel,c_fin,ic0,ic1,ic2,ic3,son0,son1,son2,son3,c_pub,c_reg,c_tab,c_pol,leds,digitos,datos...");
    end
    #(inicio_ns);

    for (int n = 0; n < ntick; n++) begin
      int r;   // sin valor inicial: con valor inicial seria estatica y quedaria en 0
      r = (ronda_ticks > 0) ? n / ronda_ticks : 0;
      per = (r == 0) ? periodo_ns : (r == 1) ? periodo2_ns : periodo3_ns;
      if (ronda_ticks > 0 && n > 0 && n % ronda_ticks == 0) #(pausa_ns);
      tick_tx = n;
      spi(precio[n][7:0], decision);
      $fdisplay(fd, "%0d,%0d,%02h", n, precio[n], decision);
      presupuesto = (per - dur) / 40;
      if (presupuesto < presupuesto_min) presupuesto_min = presupuesto;
      if (per <= dur) begin $display("ERROR: el periodo no alcanza para la transaccion"); $finish; end
      #(per - dur);
    end
    $fclose(fd);
    if (esperando) sin_respuesta++;
    if (abierta) cerrar_tick();
    if (fd_estado != 0) $fclose(fd_estado);

    $display("RESUMEN ticks=%0d recibidos=%0d respuestas=%0d sin_respuesta=%0d precios_perdidos=%0d bits_x=%0d peor_caso=%0d suma_ciclos=%0d presupuesto=%0d violaciones=%0d dec_distinto_de_1=%0d tel_mas_de_1=%0d ticks_plazo=0 stores_ram=%0d vig_boot=%0d vig_max=%0d vig_tick=%0d",
             ntick, recibidos, respuestas, sin_respuesta, precios_perdidos, bits_x, peor_caso, suma_ciclos, presupuesto_min,
             violaciones, dec_multiples, tel_multiples, stores_ram,
             vig_boot, vig_max, vig_tick);
    $finish;
  end

endmodule
