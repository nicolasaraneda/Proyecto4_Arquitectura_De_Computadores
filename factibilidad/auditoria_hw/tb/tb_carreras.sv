// tb_carreras.sv: búsqueda de carreras entre los hilos del fondo (sw/fondo.s).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Testbench de la auditoría. No reutiliza tb/tb_fondo.sv de la pieza auditada.
// Corre el programa del fondo sobre el SoC con el core barrel y hace tres
// cosas que las pruebas de la pieza no hacen:
//
//   1. Mueve al azar la fase de llegada del precio. El período de cada tick
//      es periodo + un valor al azar entre 0 y jitter nanosegundos, así que
//      byte_done cae en cualquier ciclo de la rotación de hilos y en cualquier
//      punto de los lazos de espera.
//   2. Mueve al azar los cuatro interruptores de la placa. El programa que se
//      prueba es sw/fondo.s con lazos de retardo agregados por
//      tools/prog_carreras.py: cada gestor y el supervisor leen los
//      interruptores y dan esa cantidad de vueltas, así que cada hilo demora
//      distinto en cada tick, antes y después de publicar.
//   3. Vigila el protocolo con monitores que no dependen de la referencia.
//      Miran cada escritura en PUB, EST_k, DES_k y DECISION:
//        M1  solo el hilo 0 accede al esclavo SPI
//        M2  PUB avanza de a un tick, y cuando el supervisor publica el tick
//            n + 1 los tres EST_k ya son del tick n
//        M3  cada EST_k se escribe con el número de tick que tiene PUB en ese
//            momento, y una sola vez por tick
//        M4  DES_k solo se escribe antes que el EST_k del mismo tick
//        M5  cuando se escribe DECISION los tres EST_k son del tick de PUB
//        M6  el byte escrito en DECISION es el voto de las posiciones y los
//            pesos que hay en la memoria en ese ciclo
//        M7  una sola escritura en DECISION por cada precio publicado
//        M8  todo acceso al esclavo SPI es una instrucción load o store del
//            programa (la lectura de PRICE es un load y la escritura de
//            DECISION un store)
//        M9  lo último que el supervisor cargó de cada EST_k antes de escribir
//            DECISION lleva el número de tick de PUB (el del tick anterior en
//            la variante que decide con lo publicado en el tick anterior)
//      M5 y M6 miran la memoria en el ciclo en que se escribe DECISION. Entre
//      la carga de EST_k y esa escritura pasan varias instrucciones, y en ese
//      rato un gestor atrasado puede publicar: M5 no vería que el supervisor
//      cargó un dato viejo. M9 mira la carga misma (el load del hilo 0 sobre
//      EST_k), así que no depende de ese margen. M2, M6 y M9 juntos dicen que
//      el supervisor nunca decide con datos de dos ticks distintos.
//      Además cuenta cuántas veces el supervisor cargó un EST_k que todavía
//      era del tick anterior (y tuvo que volver a leer): es la medida de
//      cuánto se ejercitó cada espera.
//
// Además escribe dos archivos para comparar con la referencia en C:
//   +vistos_csv   la serie de precios que el supervisor publicó, en orden. La
//                 referencia se corre sobre esta serie, así que la comparación
//                 sirve aunque el programa pierda precios por ir atrasado.
//   +estado_csv   el estado de la memoria al terminar cada tick del
//                 supervisor (justo cuando publica el siguiente): espejo de
//                 la cuenta, posiciones, puntajes, pesos y byte de DECISION.
//
// El programa se fija al compilar (-DPROGRAMA). Parámetros al correr:
//   +serie=ARCHIVO +nticks=N +periodo=NS +jitter=NS +inicio=NS +semilla=S
//   +sw_cada=C (los interruptores cambian, en promedio, cada C ciclos; 0 = fijos en 0)
//   +mem_fin=ARCHIVO (vuelca la memoria al terminar, para tools/reglas.sh)
// Con -DAUD_I1 (SoC de i_integrado con vigilante y tabla de 256 x 16) informa
// además cuántos ciclos estuvo BOOT en alto y cuántas entradas de la tabla
// quedaron distintas de cero.
//   +anterior=1 (el programa es la variante que decide con el tick anterior:
//                M6 compara con el voto de la memoria al publicar y M5 no aplica)

`timescale 1ns/1ps

`include "simbolos.vh"

`ifndef PROGRAMA
  `define PROGRAMA "sw/trade.hex"
`endif

module tb_carreras;

  localparam int SPI_NS = 9500;

  string serie = "tb/practica.csv", vistos_csv = "", estado_csv = "", mem_fin = "";
  int    nticks = 2000, periodo_ns = 100000, jitter_ns = 0, inicio_ns = 4000;
  int    semilla = 1, sw_cada = 0, anterior = 0;

  logic clk = 0;
  always #20 clk = ~clk;

  logic       sclk = 0, mosi = 0, cs_n = 1;
  logic [3:0] sw = 4'b0000;
  wire        miso;

  pochoco_soc #(.MemFile(`PROGRAMA)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(sw),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // --- Señales internas -------------------------------------------------------
  wire [1:0]  x_tid   = dut.u_core.tb_tid_x;
  wire        spi_acc = dut.u_spi.sel_i && dut.u_spi.req_i;
  wire        dec_wr  = dut.u_spi.wr && dut.u_spi.off == 2;
  wire        ram_wr  = dut.u_ram.b_req_i && dut.u_ram.b_we_i;
  wire        ram_rd  = dut.u_ram.b_req_i && !dut.u_ram.b_we_i;
  wire [8:0]  ram_pal = dut.u_ram.b_word;
  wire [31:0] ram_wd  = dut.u_ram.b_wdata_i;
  wire [31:0] bus_wd  = dut.u_spi.wdata_i;

  wire [31:0] m_pub  = dut.u_ram.mem[`PAL_PUB];
  wire [31:0] m_est1 = dut.u_ram.mem[`PAL_EST1];
  wire [31:0] m_est2 = dut.u_ram.mem[`PAL_EST2];
  wire [31:0] m_est3 = dut.u_ram.mem[`PAL_EST3];

  // --- Números al azar (dos generadores congruenciales, reproducibles) --------
  int unsigned lcg_m = 1, lcg_s = 1;
  function automatic int unsigned azar_m();
    lcg_m = lcg_m * 32'd1664525 + 32'd1013904223;
    return lcg_m >> 8;
  endfunction

  // Interruptores: cambian en el flanco de bajada, lejos del muestreo
  always @(negedge clk) begin
    if (sw_cada > 0) begin
      lcg_s = lcg_s * 32'd22695477 + 32'd1;
      if (((lcg_s >> 10) % sw_cada) == 0) sw <= lcg_s[31:28];
    end
  end

  // --- Serie de precios -------------------------------------------------------
  int precio [200000];
  task automatic leer_serie;
    int fd, t, r;
    string encabezado;
    fd = $fopen(serie, "r");
    if (fd == 0) begin $display("ERROR: no se encontro %s", serie); $finish; end
    r = $fgets(encabezado, fd);
    for (int n = 0; n < nticks; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  endtask

  // --- Maestra SPI: los tiempos del testbench oficial -------------------------
  int bits_x = 0;
  task automatic spi(input logic [7:0] enviar, output logic [7:0] recibido);
    cs_n = 0;
    #1000;
    for (int b = 7; b >= 0; b--) begin
      mosi = enviar[b];
      #500 sclk = 1;
      if (miso !== 1'b0 && miso !== 1'b1) bits_x++;
      recibido[b] = (miso === 1'b1);
      #500 sclk = 0;
    end
    #500 cs_n = 1;
  endtask

  // --- Monitores --------------------------------------------------------------
  longint ciclo = 0;
  int     v [10];                        // violaciones de M1 a M9 (índices 1 a 9)
  logic [23:0] carga_tick [4];           // M9: número de tick del último EST_k que cargó el supervisor
  bit     carga_hay [4];                 //     y si lo cargó después de la decisión anterior
  int     n_viejo [4];                   // cargas del supervisor que encontraron el EST_k de otro tick
  int     n_lee_precio = 0, ciclos_boot = 0, tabla_no_cero = 0;
  int     n_precios = 0, precio_boot = -1, ultimo_dec = -1;      // precios recibidos (byte_done)
  int     max_sin_resp = 0;                                      // cuenta máxima del vigilante
  wire [6:0] x_opcode = dut.u_core.tb_instr_x[6:0];
  int     n_pub = 0, n_dec = 0, n_est [4], n_des [4];
  int     dec_en_tick = 0, perdidos = 0, peor = 0, t0_valido = 0;
  longint t0 = 0;
  bit     esp_dec = 0;
  int     fd_vistos = 0, fd_estado = 0;
  int     primera [10];                  // número de publicación de la primera violación

  function automatic logic [23:0] tick_de(input logic [31:0] palabra);
    return palabra[31:8];
  endfunction

  task automatic viola(input int k, input string que);
    v[k]++;
    if (primera[k] < 0) begin
      primera[k] = n_pub;
      $display("  M%0d, primera violacion en el precio publicado %0d (ciclo %0d): %s", k, n_pub, ciclo, que);
    end
  endtask

  // Voto esperado con lo que hay en la memoria
  function automatic logic [7:0] voto();
    int f;
    f = 0;
    if (m_est1[0]) f += dut.u_ram.mem[`PAL_W1];
    if (m_est2[0]) f += dut.u_ram.mem[`PAL_W2];
    if (m_est3[0]) f += dut.u_ram.mem[`PAL_W3];
    return (f >= 8) ? 8'h7F : 8'hBF;
  endfunction

  task automatic fila_estado;
    if (fd_estado != 0)
      $fdisplay(fd_estado, "%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%02x",
        n_pub - 1, m_pub[7:0],
        $signed(dut.u_ram.mem[`PAL_CAJA]), $signed(dut.u_ram.mem[`PAL_ACC]),
        m_est1[0], m_est2[0], m_est3[0],
        $signed(dut.u_ram.mem[`PAL_DES1]), $signed(dut.u_ram.mem[`PAL_DES2]), $signed(dut.u_ram.mem[`PAL_DES3]),
        dut.u_ram.mem[`PAL_W1], dut.u_ram.mem[`PAL_W2], dut.u_ram.mem[`PAL_W3], dut.u_spi.tx_hold);
  endtask

  wire [23:0] t_pub = tick_de(m_pub);
  // En la variante que decide con lo del tick anterior el supervisor toma las
  // posiciones antes de publicar: el voto esperado es el de la memoria en el
  // ciclo en que escribe PUB, y M5 no aplica (un gestor rápido puede publicar
  // el tick nuevo antes de que el supervisor escriba DECISION).
  logic [7:0] voto_pub = 8'hBF;

  always @(posedge clk) begin
    if (dut.rst_ni) begin
      if (dut.u_spi.byte_done) begin
        if (dut.u_spi.new_price_q) perdidos++;
        t0 = ciclo; esp_dec = 1; t0_valido = 1;
        n_precios++;
      end

      // M1: solo el hilo 0 toca el esclavo SPI
      if (spi_acc && x_tid != 2'd0) viola(1, $sformatf("el hilo %0d accede al SPI", x_tid));
      // M8: y lo hace con instrucciones load y store del programa
      if (spi_acc && !(dut.u_spi.we_i ? (x_opcode == 7'b0100011) : (x_opcode == 7'b0000011)))
        viola(8, $sformatf("acceso al SPI con una instruccion de opcode %07b", x_opcode));
      if (dec_wr && x_opcode != 7'b0100011) viola(8, "DECISION no la escribe un store");
      if (dut.u_spi.price_read) n_lee_precio++;
`ifdef AUD_I1
      if (int'(dut.g_vig.u_vig.sin_resp) > max_sin_resp) max_sin_resp = int'(dut.g_vig.u_vig.sin_resp);
      if (dut.g_vig.u_warmboot.BOOT === 1'b1) begin
        if (ciclos_boot == 0) precio_boot = n_precios;
        ciclos_boot++;
      end
`endif

      if (ram_wr && ram_pal == `PAL_PUB) begin
        // M2: de a un tick, y con los tres gestores al día
        if (tick_de(ram_wd) != t_pub + 24'd1)
          viola(2, $sformatf("PUB pasa del tick %0d al %0d", t_pub, tick_de(ram_wd)));
        if (n_pub > 0 && (tick_de(m_est1) != t_pub || tick_de(m_est2) != t_pub || tick_de(m_est3) != t_pub))
          viola(2, $sformatf("se publica el tick %0d con EST en %0d %0d %0d", tick_de(ram_wd), tick_de(m_est1), tick_de(m_est2), tick_de(m_est3)));
        // M7: una decisión por precio publicado
        if (n_pub > 0 && dec_en_tick != 1) viola(7, $sformatf("%0d escrituras en DECISION en el tick", dec_en_tick));
        if (n_pub > 0) fila_estado();
        if (fd_vistos != 0) $fdisplay(fd_vistos, "%0d,%0d", n_pub, ram_wd[7:0]);
        voto_pub = voto();
        n_pub++; dec_en_tick = 0;
      end

      // M3 y M4, por gestor
      if (ram_wr && ram_pal == `PAL_EST1) begin
        n_est[1]++;
        if (tick_de(ram_wd) != t_pub) viola(3, $sformatf("EST_1 se escribe con el tick %0d y PUB tiene el %0d", tick_de(ram_wd), t_pub));
        if (tick_de(m_est1) == t_pub && n_pub > 0) viola(3, "EST_1 se escribe dos veces en el mismo tick");
        if (x_tid != 2'd1) viola(3, $sformatf("EST_1 la escribe el hilo %0d", x_tid));
      end
      if (ram_wr && ram_pal == `PAL_EST2) begin
        n_est[2]++;
        if (tick_de(ram_wd) != t_pub) viola(3, $sformatf("EST_2 se escribe con el tick %0d y PUB tiene el %0d", tick_de(ram_wd), t_pub));
        if (tick_de(m_est2) == t_pub && n_pub > 0) viola(3, "EST_2 se escribe dos veces en el mismo tick");
        if (x_tid != 2'd2) viola(3, $sformatf("EST_2 la escribe el hilo %0d", x_tid));
      end
      if (ram_wr && ram_pal == `PAL_EST3) begin
        n_est[3]++;
        if (tick_de(ram_wd) != t_pub) viola(3, $sformatf("EST_3 se escribe con el tick %0d y PUB tiene el %0d", tick_de(ram_wd), t_pub));
        if (tick_de(m_est3) == t_pub && n_pub > 0) viola(3, "EST_3 se escribe dos veces en el mismo tick");
        if (x_tid != 2'd3) viola(3, $sformatf("EST_3 la escribe el hilo %0d", x_tid));
      end
      if (ram_wr && ram_pal == `PAL_DES1) begin
        n_des[1]++;
        if (tick_de(m_est1) == t_pub && n_pub > 0) viola(4, "DES_1 se escribe despues que EST_1 en el mismo tick");
      end
      if (ram_wr && ram_pal == `PAL_DES2) begin
        n_des[2]++;
        if (tick_de(m_est2) == t_pub && n_pub > 0) viola(4, "DES_2 se escribe despues que EST_2 en el mismo tick");
      end
      if (ram_wr && ram_pal == `PAL_DES3) begin
        n_des[3]++;
        if (tick_de(m_est3) == t_pub && n_pub > 0) viola(4, "DES_3 se escribe despues que EST_3 en el mismo tick");
      end

      // M9: qué número de tick lleva cada EST_k que el supervisor carga. El
      // load muestrea la memoria en este flanco, así que lo cargado es lo que
      // hay ahora en la palabra. En las dos variantes el EST_k que el
      // supervisor espera es el del tick que tiene PUB en el momento de la
      // carga: si lleva otro, tiene que volver a leer.
      if (ram_rd && x_tid == 2'd0) begin
        if (ram_pal == `PAL_EST1) begin carga_tick[1] = tick_de(m_est1); carga_hay[1] = 1; if (tick_de(m_est1) != t_pub) n_viejo[1]++; end
        if (ram_pal == `PAL_EST2) begin carga_tick[2] = tick_de(m_est2); carga_hay[2] = 1; if (tick_de(m_est2) != t_pub) n_viejo[2]++; end
        if (ram_pal == `PAL_EST3) begin carga_tick[3] = tick_de(m_est3); carga_hay[3] = 1; if (tick_de(m_est3) != t_pub) n_viejo[3]++; end
      end

      // M5, M6 y M9: la decisión
      if (dec_wr) begin
        n_dec++; dec_en_tick++; ultimo_dec = n_precios;
        for (int k = 1; k <= 3; k++) begin
          if (!carga_hay[k])
            viola(9, $sformatf("DECISION del tick %0d sin haber cargado EST_%0d desde la decision anterior", t_pub, k));
          else if (carga_tick[k] != (anterior ? t_pub - 24'd1 : t_pub))
            viola(9, $sformatf("DECISION del tick %0d con el EST_%0d que el supervisor cargo del tick %0d", t_pub, k, carga_tick[k]));
          carga_hay[k] = 0;
        end
        if (!anterior && (tick_de(m_est1) != t_pub || tick_de(m_est2) != t_pub || tick_de(m_est3) != t_pub))
          viola(5, $sformatf("DECISION del tick %0d con EST en %0d %0d %0d", t_pub, tick_de(m_est1), tick_de(m_est2), tick_de(m_est3)));
        if (bus_wd[7:0] != (anterior ? voto_pub : voto()))
          viola(6, $sformatf("DECISION = %02x y el voto esperado es %02x", bus_wd[7:0], anterior ? voto_pub : voto()));
        if (esp_dec && t0_valido != 0) begin
          if (ciclo - t0 > peor) peor = ciclo - t0;
          esp_dec = 0;
        end
      end
    end
    ciclo++;
  end

  // --- Estímulo ---------------------------------------------------------------
  logic [7:0] rx;
  int         total = 0;

  initial begin
    void'($value$plusargs("serie=%s", serie));
    void'($value$plusargs("nticks=%d", nticks));
    void'($value$plusargs("periodo=%d", periodo_ns));
    void'($value$plusargs("jitter=%d", jitter_ns));
    void'($value$plusargs("inicio=%d", inicio_ns));
    void'($value$plusargs("semilla=%d", semilla));
    void'($value$plusargs("sw_cada=%d", sw_cada));
    void'($value$plusargs("anterior=%d", anterior));
    void'($value$plusargs("vistos_csv=%s", vistos_csv));
    void'($value$plusargs("estado_csv=%s", estado_csv));
    void'($value$plusargs("mem_fin=%s", mem_fin));
    lcg_m = 32'd2463534242 ^ (semilla * 32'd2654435761);
    lcg_s = 32'd88172645 ^ (semilla * 32'd40503);
    for (int k = 0; k < 10; k++) begin v[k] = 0; primera[k] = -1; end
    for (int k = 0; k < 4; k++) begin n_est[k] = 0; n_des[k] = 0; n_viejo[k] = 0; carga_hay[k] = 0; carga_tick[k] = 24'd0; end
    leer_serie();
    if (vistos_csv != "") begin fd_vistos = $fopen(vistos_csv, "w"); $fdisplay(fd_vistos, "tick,price"); end
    if (estado_csv != "") begin
      fd_estado = $fopen(estado_csv, "w");
      $fdisplay(fd_estado, "tick,precio,caja,acciones,pos1,pos2,pos3,des1,des2,des3,w1,w2,w3,decision");
    end
    #(inicio_ns);
    for (int n = 0; n < nticks; n++) begin
      spi(precio[n][7:0], rx);
      #(periodo_ns - SPI_NS + ((jitter_ns > 0) ? (azar_m() % (jitter_ns + 1)) : 0));
    end
    repeat (4) @(posedge clk);
    if (fd_vistos != 0) $fclose(fd_vistos);
    if (fd_estado != 0) $fclose(fd_estado);

    if (mem_fin != "") $writememh(mem_fin, dut.u_ram.mem);
`ifdef AUD_I1
    for (int k = 0; k < 256; k++) if (dut.g_tabla_mmio.u_tabla.mem[k] !== 16'b0) tabla_no_cero++;
`endif
    for (int k = 1; k <= 9; k++) total += v[k];
    $display("Programa:            %s", `PROGRAMA);
    $display("Corrida:             %s, %0d ticks, periodo %0d ns + 0..%0d ns, interruptores cada %0d ciclos, semilla %0d", serie, nticks, periodo_ns, jitter_ns, sw_cada, semilla);
    $display("Precios publicados:  %0d (perdidos por atraso: %0d)", n_pub, perdidos);
    $display("Decisiones:          %0d", n_dec);
    $display("Ultima decision con el precio numero: %0d de %0d recibidos", ultimo_dec, n_precios);
    $display("Escrituras EST:      %0d %0d %0d", n_est[1], n_est[2], n_est[3]);
    $display("Escrituras DES:      %0d %0d %0d", n_des[1], n_des[2], n_des[3]);
    $display("Peor respuesta:      %0d ciclos", peor);
    $display("MISO con X:          %0d bits", bits_x);
    $display("Lecturas de PRICE:   %0d", n_lee_precio);
`ifdef AUD_I1
    $display("Ciclos con BOOT:     %0d", ciclos_boot);
    $display("BOOT sube con el precio numero: %0d", precio_boot);
    $display("Cuenta maxima del vigilante: %0d", max_sin_resp);
    $display("Tabla distinta de 0: %0d entradas", tabla_no_cero);
`endif
    $display("Violaciones M1..M7:  %0d %0d %0d %0d %0d %0d %0d", v[1], v[2], v[3], v[4], v[5], v[6], v[7]);
    $display("Violaciones M8:      %0d", v[8]);
    $display("Violaciones M9:      %0d", v[9]);
    $display("Cargas de EST_k del supervisor con otro tick (esperas): %0d %0d %0d", n_viejo[1], n_viejo[2], n_viejo[3]);
    if (total == 0 && n_dec > 0) $display("PASS monitores: ninguna violacion en %0d decisiones", n_dec);
    else                         $display("FAIL monitores: %0d violaciones en %0d decisiones", total, n_dec);
    $finish;
  end

endmodule
