// tb_fondo.sv: testbench de medición y de protocolo de sw/fondo.s sobre el
// Espino barrel (docs/fondo.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// No reemplaza al testbench oficial (tb/tb_proyecto_4.sv), que se corre sin
// modificar con tools/fondo/oficial.sh. Usa la misma maestra SPI configurable
// de tb/tb_estres.sv (misma transacción y misma medición de byte_done a la
// primera escritura en DECISION) y agrega lo que el oficial no mira:
//
//   - Conteo por tick y por hilo: instrucciones ejecutadas y cuántas de ellas
//     fueron vueltas de un lazo de sondeo.
//   - Hitos del protocolo en ciclos desde byte_done: cuándo se escribe PUB,
//     cuándo publica su voto cada gestor y cuándo el supervisor vuelve a
//     sondear.
//   - Estado compartido en el momento de decidir: PUB, los tres votos, los
//     tres puntajes y los tres pesos, para compararlos con ref/fondo.py.
//   - Vigilancia del protocolo: cada palabra compartida la escribe solo su
//     dueño, nadie escribe en el programa ni en la tabla de parámetros, y solo
//     el hilo 0 toca el SPI y el periférico.
//   - Telemetría: escrituras al periférico por tick y valor de los LED y de los
//     7 segmentos al cerrar el tick.
//
//   - Vigilante (solo si el SoC se compiló con -DESPINO_VIGILANTE): si pidió
//     la reconfiguración y cuántos precios seguidos llegó a contar sin
//     respuesta.
//
// Todo se fija con plusargs, para compilar una sola vez por hardware. El
// programa y la tabla de parámetros se cargan al empezar, no al compilar.
//
//   +PROGRAMA=build/fondo/fondo.hex
//   +TABLA=sw/fondo_tabla.hex   contenido de la BRAM de la tabla
//   +SERIE=archivo.csv       CSV "tick,precio"
//   +NTICKS=2000  +PERIODO_NS=100000  +INICIO_NS=4000
//   +RONDA_TICKS=0 +PAUSA_NS=0 +PERIODO2_NS +PERIODO3_NS   rondas seguidas sin reset
//   +SCLK_MEDIO_NS=500  +CS_SETUP_NS=1500  +CS_HOLD_NS=500
//   +SALIDA=archivo.csv      "tick,precio,decision" (lo que lee la maestra)
//   +ESTADO=archivo.csv      una fila por precio recibido (ver ENCABEZADO)
//   +A_S_ESPERA, +A_S_PRIMERO, +A_S_VOTOS, +A_PLAZO, +A_FRONTERA, +A_G_ESPERA,
//   +A_G_PRIMERO             direcciones de las etiquetas (tools/fondo/simbolos.py)
//   +PUB, +W1, +REF1, +G1    direcciones de los datos (las demás son contiguas)
//
// Al final imprime una línea RESUMEN con los conteos que usa tools/fondo/revisar.py.

`timescale 1ns/1ps

module tb_fondo;

  logic clk = 0;
  always #20 clk = ~clk;

  logic sclk = 0, mosi = 0, cs_n = 1;
  wire  miso;
  wire [3:0] leds;
  wire [6:0] seg1, seg2;

  pochoco_soc #(.MemFile("")) dut (
    .i_Clk(clk), .o_LED(leds), .i_Switch(4'b0000),
    .o_Segment1_A(seg1[0]), .o_Segment1_B(seg1[1]), .o_Segment1_C(seg1[2]), .o_Segment1_D(seg1[3]),
    .o_Segment1_E(seg1[4]), .o_Segment1_F(seg1[5]), .o_Segment1_G(seg1[6]),
    .o_Segment2_A(seg2[0]), .o_Segment2_B(seg2[1]), .o_Segment2_C(seg2[2]), .o_Segment2_D(seg2[3]),
    .o_Segment2_E(seg2[4]), .o_Segment2_F(seg2[5]), .o_Segment2_G(seg2[6]),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // --- Configuración en tiempo de ejecución ------------------------------------
  string programa = "build/fondo/fondo.hex", serie = "tb/practica.csv", tabla = "sw/fondo_tabla.hex";
  string salida = "build/fondo/salida.csv", estado = "";
  int ntick = 2000, ronda_ticks = 0;
  longint pausa_ns = 0, periodo_ns = 100000, periodo2_ns = -1, periodo3_ns = -1;
  longint inicio_ns = 4000, sclk_medio_ns = 500, cs_setup_ns = 1500, cs_hold_ns = 500;
  int a_s_espera = -1, a_s_primero = -1, a_s_votos = -1, a_plazo = -1, a_frontera = -1;
  int a_g_espera = -1, a_g_primero = -1;
  int d_pub = 'h7C0, d_w1 = 'h7C4, d_ref1 = 'h7D0, d_g1 = 'h7DC;

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
  wire        wr_per = dreq && dwe && dad[31] && !dad[16] && !es_tab;
  wire [11:0] wa     = {dad[11:2], 2'b00};

  // Copia de las palabras compartidas, hecha con los stores que se ven en el bus
  logic [31:0] m_pub = 0, m_w [3] = '{0, 0, 0}, m_des [3] = '{0, 0, 0}, m_est [3] = '{0, 0, 0};

  // --- Medición igual a la del oficial -------------------------------------------
  int ciclos = 0, peor_caso = 0, respuestas = 0, precios_perdidos = 0, recibidos = 0, sin_respuesta = 0;
  longint suma_ciclos = 0;
  bit esperando = 0;

  // --- Por tick --------------------------------------------------------------------
  longint ciclo = 0, t0 = 0;
  bit     abierta = 0;
  int     v_tick, v_precio;
  int     ic [4], son [4];
  int     n_dec, n_tel, n_pub, vueltas, plazo, front;
  int     c_pub, c_est [3], c_fin, r_ciclos;
  logic [7:0]  s_byte;
  logic [31:0] s_pub, s_w [3], s_des [3], s_est [3];
  int     fd_estado = 0;

  int violaciones = 0, dec_multiples = 0, tel_multiples = 0, ticks_plazo = 0, ticks_frontera = 0, max_vueltas = 0;

  task automatic violacion(input string que);
    violaciones++;
    if (violaciones <= 10)
      $display("VIOLACION ciclo %0d hilo %0d pc %03x dir %08x: %s", ciclo, xt, xpc[11:0], dad, que);
  endtask

  task automatic cerrar_tick;
    if (n_dec != 1) dec_multiples++;
    if (n_tel > 1)  tel_multiples++;
    if (plazo != 0) ticks_plazo++;
    if (front != 0) ticks_frontera++;
    if (vueltas > max_vueltas) max_vueltas = vueltas;
    if (fd_estado != 0)
      $fdisplay(fd_estado, "%0d,%0d,%0d,%0d,%02x,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
        v_tick, v_precio, t0, r_ciclos, s_byte, n_dec, n_tel, n_pub, vueltas, plazo, front,
        c_pub, c_est[0], c_est[1], c_est[2], c_fin,
        ic[0], ic[1], ic[2], ic[3], son[0], son[1], son[2], son[3],
        s_pub, s_est[0], s_est[1], s_est[2], $signed(s_des[0]), $signed(s_des[1]), $signed(s_des[2]),
        s_w[0], s_w[1], s_w[2], leds, seg1, seg2);
  endtask

  int k;

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
      n_dec = 0; n_tel = 0; n_pub = 0; vueltas = 0; plazo = 0; front = 0;
      c_pub = -1; c_est[0] = -1; c_est[1] = -1; c_est[2] = -1; c_fin = -1; r_ciclos = -1;
      s_byte = 0;
    end else if (abierta) begin
      if (xv) begin
        ic[xt]++;
        if (xt == 0) begin
          if (en_lazo(xpc, a_s_espera, 12) || en_lazo(xpc, a_s_primero, 12)) son[0]++;
          if (xpc == a_s_votos)  vueltas++;
          if (xpc == a_plazo)    plazo = 1;
          if (xpc == a_frontera) front = 1;
          if (n_dec > 0 && c_fin < 0 && xpc == a_s_espera) c_fin = ciclo - t0;
        end else begin
          if (en_lazo(xpc, a_g_espera, 8) || en_lazo(xpc, a_g_primero, 8)) son[xt]++;
        end
      end
      if (wr_dec) begin
        n_dec++;
        if (n_dec == 1) begin
          r_ciclos = ciclo - t0;
          s_byte = dwd[7:0]; s_pub = m_pub;
          for (int k = 0; k < 3; k++) begin s_w[k] = m_w[k]; s_des[k] = m_des[k]; s_est[k] = m_est[k]; end
        end
      end
      if (wr_per) n_tel++;
    end

    // Copia de las palabras compartidas y vigilancia del protocolo
    if (xv && dreq && dad[31] && !es_tab && xt != 0) violacion("un gestor toca el SPI o el periferico");
    if (xv && dreq && dwe && es_tab) violacion("store a la tabla de parametros");
    if (xv && wr_ram) begin
      if (wa == d_pub) begin
        if (xt != 0) violacion("PUB escrita por un gestor");
        m_pub = dwd;
        if (abierta) begin n_pub++; if (c_pub < 0) c_pub = ciclo - t0; end
      end else if (wa >= d_w1 && wa < d_w1 + 12) begin
        if (xt != 0) violacion("peso escrito por un gestor");
        m_w[(wa - d_w1) >> 2] = dwd;
      end else if (wa >= d_ref1 && wa < d_ref1 + 12) begin
        if (xt != 0) violacion("REF escrita por un gestor");
      end else if (wa >= d_g1 && wa < d_g1 + 24) begin
        k = (wa - d_g1) >> 3;
        if (xt != k + 1) violacion("bloque de un gestor escrito por otro hilo");
        if (((wa - d_g1) & 4) == 0) m_des[k] = dwd;
        else begin
          m_est[k] = dwd;
          if (abierta && c_est[k] < 0 && dwd[31:8] == m_pub[31:8]) c_est[k] = ciclo - t0;
        end
      end else violacion("store fuera de las palabras compartidas");
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
    void'($value$plusargs("A_S_ESPERA=%d", a_s_espera));
    void'($value$plusargs("A_S_PRIMERO=%d", a_s_primero));
    void'($value$plusargs("A_S_VOTOS=%d", a_s_votos));
    void'($value$plusargs("A_PLAZO=%d", a_plazo));
    void'($value$plusargs("A_FRONTERA=%d", a_frontera));
    void'($value$plusargs("A_G_ESPERA=%d", a_g_espera));
    void'($value$plusargs("A_G_PRIMERO=%d", a_g_primero));
    void'($value$plusargs("PUB=%d", d_pub));
    void'($value$plusargs("W1=%d", d_w1));
    void'($value$plusargs("REF1=%d", d_ref1));
    void'($value$plusargs("G1=%d", d_g1));
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
      $fdisplay(fd_estado, "tick,precio,ciclo,respuesta,byte,n_dec,n_tel,n_pub,vueltas,plazo,frontera,c_pub,c_est1,c_est2,c_est3,c_fin,ic0,ic1,ic2,ic3,son0,son1,son2,son3,pub,est1,est2,est3,des1,des2,des3,w1,w2,w3,leds,seg1,seg2");
    end
    #(inicio_ns);

    for (int n = 0; n < ntick; n++) begin
      int r = (ronda_ticks > 0) ? n / ronda_ticks : 0;
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

    $display("RESUMEN ticks=%0d recibidos=%0d respuestas=%0d sin_respuesta=%0d precios_perdidos=%0d bits_x=%0d peor_caso=%0d suma_ciclos=%0d presupuesto=%0d violaciones=%0d dec_distinto_de_1=%0d tel_mas_de_1=%0d ticks_plazo=%0d ticks_frontera=%0d max_vueltas=%0d vig_boot=%0d vig_max=%0d vig_tick=%0d",
             ntick, recibidos, respuestas, sin_respuesta, precios_perdidos, bits_x, peor_caso, suma_ciclos, presupuesto_min,
             violaciones, dec_multiples, tel_multiples, ticks_plazo, ticks_frontera, max_vueltas,
             vig_boot, vig_max, vig_tick);
    $finish;
  end

endmodule
