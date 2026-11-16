// tb_verif.sv: cada hilo del Espino barrel contra un Espino base, instrucción
// por instrucción.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es el método de tb/tb_paralelo.sv del repositorio (ejecución en paralelo de
// dos SoC completos), llevado a cuatro hilos. Instancia cinco SoC con el mismo
// programa:
//   dut         el SoC con el core barrel (factibilidad/a_barrel/rtl/).
//   b0 a b3     cuatro SoC originales (rtl/, sin modificar) con el Espino
//               base. El SoC bt parte en la dirección 4 t, que es la entrada
//               del hilo t, y hace de referencia de ese hilo.
// La instrucción número k del hilo t del barrel se compara con la instrucción
// número k del SoC bt:
//   - contador de programa e instrucción;
//   - escritura al banco de registros (registro y valor);
//   - acceso al bus de datos: lectura o escritura, dirección, bytes y dato;
//   - el contexto completo del hilo después de la instrucción: los 16
//     registros leídos de las BRAM del banco (las dos copias), contra los 16
//     del banco del SoC bt;
//   - en un store a memoria, la palabra recién escrita, leída de la RAM;
//   - en un store a un registro del esclavo SPI o de los periféricos, el
//     registro escrito (DECISION, display o LEDs), leído del módulo.
// Al final se compara la RAM completa.
//
// El número de hilo de cada etapa lo calcula el testbench a partir del número
// de ciclo, y se exige que coincida con el que dice el core.
//
// Relojes. No hay un tiempo común: cada SoC tiene su reloj y el testbench los
// mueve de a un flanco. Antes del flanco anota lo que el SoC va a hacer y
// después del flanco lee el estado que quedó (banco, memoria, periféricos).
// Un SoC que va adelantado espera.
//
// Dos formas de referencia:
//   +compartida=0  (por defecto) Cada SoC base corre solo. Sirve cuando lo que
//                  hace un hilo no depende de los otros: un hilo con los demás
//                  en un lazo vacío, o cuatro hilos con zonas de datos
//                  separadas. Es la comparación "cada hilo idéntico a su
//                  corrida en el Espino base".
//   +compartida=1  Los cuatro SoC base ejecutan por turnos, una instrucción
//                  cada uno (0, 1, 2, 3, 0, ...), y cada store a memoria de
//                  uno se copia a la memoria de los otros tres. Es el modelo
//                  de referencia de cuatro hilos que comparten memoria: en el
//                  barrel los accesos al bus también ocurren en ese orden, uno
//                  por ciclo. Sirve para programas en que los hilos leen lo
//                  que escriben los otros.
//
// Precios por el SPI. El bus SPI queda quieto (un precio que llega por los
// pines cae en ciclos distintos en cada SoC). Para ejercitar igual los
// registros del esclavo:
//   - al partir, el registro PRICE de los cinco SoC se deja en 0xA5 y los
//     interruptores en 1010, para que una lectura del SPI, una de los
//     periféricos y una de la memoria entreguen valores distintos;
//   - con +precio_cada=N +hilo_spi=T, cada N instrucciones del hilo T el
//     testbench deja un precio nuevo en el esclavo (PRICE y la bandera de
//     STATUS), en el barrel y en el SoC bT, entre la misma pareja de
//     instrucciones. Solo tiene sentido si T es el único hilo que lee PRICE.
// El tráfico SPI real por los pines se prueba con el testbench oficial
// (tools/verif_spi.sh).
//
// Uso (tools/verif.sh), con Verilator:
//   sim +hex=programa.hex +instrucciones=50000 [+compartida=1]
//       [+precio_cada=97 +hilo_spi=2]
// El programa debe traer las 512 palabras.

`timescale 1ns/1ps

`ifndef PCW_BARREL
  `define PCW_BARREL 11
`endif

module tb_verif;

  localparam int COLA = 16;
  // Bits del contador de programa del barrel. El Espino base tiene 32. Con 11
  // (el que se sintetiza) los dos coinciden mientras el programa se queda en
  // la memoria, y la comparación de un hilo termina, sin error, en la primera
  // instrucción que el base ejecuta fuera de ella (un jalr con una base
  // cualquiera). Con -DPCW_BARREL=32 se compara todo, también lo que pasa
  // fuera de la memoria. Es lo mismo que hace tb/tb_paralelo.sv con PCW_B.
  localparam int PCW  = `PCW_BARREL;

  logic       clk   = 1'b0;       // reloj del barrel
  logic [3:0] clk_b = 4'b0000;    // relojes de los cuatro SoC base
  wire  [3:0] sw    = 4'b1010;

  `define PINES(RELOJ) \
    .i_Clk(RELOJ), .o_LED(), .i_Switch(sw), \
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(), \
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(), \
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(), \
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(), \
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO()

  pochoco_soc_barrel #(.MemFile(""), .PorBits(4), .PcW(PCW)) dut (`PINES(clk));
  pochoco_soc #(.MemFile(""), .PorBits(4), .Pipeline(0)) b0 (`PINES(clk_b[0]));
  pochoco_soc #(.MemFile(""), .PorBits(4), .Pipeline(0)) b1 (`PINES(clk_b[1]));
  pochoco_soc #(.MemFile(""), .PorBits(4), .Pipeline(0)) b2 (`PINES(clk_b[2]));
  pochoco_soc #(.MemFile(""), .PorBits(4), .Pipeline(0)) b3 (`PINES(clk_b[3]));

  // Lo que hizo una instrucción completada
  typedef struct packed {
    logic [31:0]  pc, instr;
    logic         rf_we;
    logic [3:0]   rf_wa;
    logic [31:0]  rf_wd;
    logic         acc, we;          // acceso al bus de datos, y si es escritura
    logic [31:0]  addr, wdata;
    logic [3:0]   be;
    logic [511:0] regs_a, regs_b;   // contexto después de la instrucción (copias A y B del banco)
    logic [31:0]  mem_word;         // palabra de RAM recién escrita
    logic [7:0]   mmio;             // registro de SPI o periféricos recién escrito
  } ev_t;

  ev_t    cola_d [4][COLA];         // barrel, por hilo
  ev_t    cola_b [4][COLA];         // base, por hilo
  longint n_d [4], n_b [4], n_cmp [4];
  longint n_rf [4], n_st [4], n_ld [4], n_salto [4], n_mmio [4], n_spi [4], n_bandera [4], n_lazo [4], n_dist [4];
  longint x_d [4];                  // instrucciones del hilo que pasaron por X en el barrel
  bit     visto [longint unsigned];   // instrucciones ya vistas con esos mismos datos (ver n_dist)
  bit     listo [4], fuera [4];
  longint objetivo = 50000;
  int     compartida = 0, precio_cada = 0, hilo_spi = 0;
  longint ciclo = 0, ciclos_b [4], precios = 0;
  int     turno = 0;
  string  hex;
  logic [31:0] img [512];

  // Acceso al bus que el SoC base hizo desde su última instrucción completada
  logic        ba_acc [4], ba_we [4];
  logic [31:0] ba_addr [4], ba_wdata [4];
  logic [3:0]  ba_be [4];
  int          ba_n [4];

  // Palabras de memoria que el barrel escribió después de que su hilo terminó
  // de compararse: no se revisan al final
  bit  sucia [512];

  // Instrucción del barrel que está en M (pasó por X en el ciclo anterior)
  bit  pend_m = 0;
  int  pend_t = 0;
  ev_t em;

  function automatic logic [7:0] precio_de(input longint k);
    return 8'(k * 37 + 11) ^ 8'(k >> 8);
  endfunction

  task automatic error(input string texto);
    $display("FAIL verif: %s", texto);
    $fatal(1);
  endtask

  // Registro de SPI o de periféricos que escribe un store a la dirección dada
  `define MMIO_DE(SOC, DIR) \
    ((DIR[16]) ? ((DIR[7:2] == 6'd2) ? SOC.u_spi.tx_hold : 8'h00) \
               : ((DIR[7:2] == 6'd0) ? SOC.u_periph.digit_q : \
                  (DIR[7:2] == 6'd1) ? {4'b0, SOC.u_periph.led_q} : 8'h00))

  // --- SoC base ----------------------------------------------------------------
  `define BASE_ANTES(SOC) begin \
      commit = SOC.u_core.u_id.commit; \
      if (SOC.u_core.data_req_o) begin \
        ba_acc[t] = 1'b1; ba_we[t] = SOC.u_core.data_we_o; ba_addr[t] = SOC.u_core.data_addr_o; \
        ba_be[t] = SOC.u_core.data_be_o; ba_wdata[t] = SOC.u_core.data_wdata_o; ba_n[t]++; \
      end \
      e.pc    = SOC.u_core.pc_id; \
      e.instr = SOC.u_core.instr_ex; \
      e.rf_we = SOC.u_core.rf_we && SOC.u_core.rf_waddr != 4'd0; \
      e.rf_wa = SOC.u_core.rf_waddr; \
      e.rf_wd = SOC.u_core.rf_wdata; \
    end

  `define BASE_DESPUES(SOC) begin \
      for (int r = 0; r < 16; r++) begin \
        e.regs_a[32*r +: 32] = {SOC.u_core.u_rf.u_bankA.u_hi.memory[r], SOC.u_core.u_rf.u_bankA.u_lo.memory[r]}; \
        e.regs_b[32*r +: 32] = {SOC.u_core.u_rf.u_bankB.u_hi.memory[r], SOC.u_core.u_rf.u_bankB.u_lo.memory[r]}; \
      end \
      e.mem_word = SOC.u_ram.mem[e.addr[10:2]]; \
      e.mmio     = `MMIO_DE(SOC, e.addr); \
      if (nuevo_precio) begin SOC.u_spi.price_q = precio_de(n_b[t] + 1); SOC.u_spi.new_price_q = 1'b1; end \
    end

  task automatic flanco_base(input int t, output bit completo);
    ev_t e;
    bit  commit, nuevo_precio;
    e = '0;
    case (t)
      0: `BASE_ANTES(b0)
      1: `BASE_ANTES(b1)
      2: `BASE_ANTES(b2)
      default: `BASE_ANTES(b3)
    endcase
    if (commit) begin
      if (ba_n[t] > 1) error($sformatf("el Espino base del hilo %0d hizo %0d accesos al bus en una instruccion", t, ba_n[t]));
      e.acc = ba_acc[t]; e.we = ba_we[t]; e.addr = ba_addr[t]; e.be = ba_be[t]; e.wdata = ba_wdata[t];
      ba_acc[t] = 1'b0; ba_n[t] = 0;
    end
    nuevo_precio = commit && precio_cada > 0 && t == hilo_spi && ((n_b[t] + 1) % precio_cada) == 0;
    clk_b[t] = 1'b1; #1;
    ciclos_b[t]++;
    if (commit) begin
      case (t)
        0: `BASE_DESPUES(b0)
        1: `BASE_DESPUES(b1)
        2: `BASE_DESPUES(b2)
        default: `BASE_DESPUES(b3)
      endcase
      cola_b[t][n_b[t] % COLA] = e;
      n_b[t]++;
      // Memoria compartida: el store se copia a la memoria de los otros tres
      if (compartida != 0 && e.acc && e.we && !e.addr[31]) begin
        if (t != 0) b0.u_ram.mem[e.addr[10:2]] = e.mem_word;
        if (t != 1) b1.u_ram.mem[e.addr[10:2]] = e.mem_word;
        if (t != 2) b2.u_ram.mem[e.addr[10:2]] = e.mem_word;
        if (t != 3) b3.u_ram.mem[e.addr[10:2]] = e.mem_word;
      end
    end
    clk_b[t] = 1'b0; #1;
    completo = commit;
  endtask

  // --- SoC barrel ---------------------------------------------------------------
  task automatic flanco_barrel;
    ev_t ex;
    bit  xv, nuevo_precio;
    int  xt, mt;
    ciclo++;
    xt = int'((ciclo + 1) % 4);       // hilo en X: el 0 en el ciclo 3, el 1 en el 4, ...
    mt = int'(ciclo % 4);             // hilo en M
    if (int'(dut.u_core.tb_tid_x) != xt || int'(dut.u_core.tb_tid_m) != mt)
      error($sformatf("ciclo %0d: el core dice hilo %0d en X y %0d en M, y deberian ser %0d y %0d",
                      ciclo, dut.u_core.tb_tid_x, dut.u_core.tb_tid_m, xt, mt));

    // Etapa M: la instrucción que pasó por X en el ciclo anterior escribe el banco
    if (pend_m) begin
      if (pend_t != mt) error("el hilo en M no es el que estaba en X en el ciclo anterior");
      em.rf_we = dut.u_core.tb_rf_we;
      em.rf_wa = dut.u_core.tb_rf_wa;
      em.rf_wd = dut.u_core.tb_rf_wd;
    end else if (dut.u_core.tb_rf_we) begin
      error($sformatf("ciclo %0d: una burbuja escribe el banco de registros", ciclo));
    end

    // Etapa X
    ex = '0;
    xv = dut.u_core.tb_valid_x;
    // Las únicas burbujas son las dos del arranque (ciclos 1 y 2)
    if (xv != (ciclo >= 3)) error($sformatf("ciclo %0d: la etapa X %s una instruccion", ciclo, xv ? "tiene" : "no tiene"));
    if (xv) begin
      ex.pc    = dut.u_core.tb_pc_x;
      ex.instr = dut.u_core.tb_instr_x;
      ex.acc   = dut.u_core.data_req_o;
      if (ex.acc) begin
        ex.we    = dut.u_core.data_we_o;
        ex.addr  = dut.u_core.data_addr_o;
        ex.be    = dut.u_core.data_be_o;
        ex.wdata = dut.u_core.data_wdata_o;
      end
    end else if (dut.u_core.data_req_o) begin
      error($sformatf("ciclo %0d: una burbuja pide el bus de datos", ciclo));
    end
    nuevo_precio = xv && precio_cada > 0 && xt == hilo_spi && ((x_d[xt] + 1) % precio_cada) == 0;

    clk = 1'b1; #1;

    if (pend_m) begin
      for (int r = 0; r < 16; r++) begin
        em.regs_a[32*r +: 32] = {dut.u_core.u_rf.u_bankA.u_hi.memory[16 * pend_t + r],
                                 dut.u_core.u_rf.u_bankA.u_lo.memory[16 * pend_t + r]};
        em.regs_b[32*r +: 32] = {dut.u_core.u_rf.u_bankB.u_hi.memory[16 * pend_t + r],
                                 dut.u_core.u_rf.u_bankB.u_lo.memory[16 * pend_t + r]};
      end
      if (!listo[pend_t]) begin
        cola_d[pend_t][n_d[pend_t] % COLA] = em;
        n_d[pend_t]++;
      end else if (em.acc && em.we && !em.addr[31]) begin
        sucia[em.addr[10:2]] = 1;      // store de un hilo que ya terminó de compararse
      end
    end
    if (xv) begin
      ex.mem_word = dut.u_ram.mem[ex.addr[10:2]];
      ex.mmio     = `MMIO_DE(dut, ex.addr);
      if (nuevo_precio) begin
        dut.u_spi.price_q     = precio_de(x_d[xt] + 1);
        dut.u_spi.new_price_q = 1'b1;
        precios++;
      end
      x_d[xt]++;
    end
    pend_m = xv;
    pend_t = xt;
    em     = ex;

    clk = 1'b0; #1;
  endtask

  // --- Comparación ----------------------------------------------------------------
  task automatic falla(input int t, input string que, input ev_t ea, input ev_t eb);
    $display("FAIL verif: el hilo %0d difiere del Espino base en su instruccion %0d (%s)", t, n_cmp[t] + 1, que);
    $display("  base:   pc=%08x instr=%08x rf_we=%0d x%0d=%08x bus=%0d we=%0d addr=%08x be=%04b dato=%08x mem=%08x mmio=%02x",
             ea.pc, ea.instr, ea.rf_we, ea.rf_wa, ea.rf_wd, ea.acc, ea.we, ea.addr, ea.be, ea.wdata, ea.mem_word, ea.mmio);
    $display("  barrel: pc=%08x instr=%08x rf_we=%0d x%0d=%08x bus=%0d we=%0d addr=%08x be=%04b dato=%08x mem=%08x mmio=%02x",
             eb.pc, eb.instr, eb.rf_we, eb.rf_wa, eb.rf_wd, eb.acc, eb.we, eb.addr, eb.be, eb.wdata, eb.mem_word, eb.mmio);
    for (int r = 0; r < 16; r++)
      if (ea.regs_a[32*r +: 32] !== eb.regs_a[32*r +: 32] || ea.regs_b[32*r +: 32] !== eb.regs_b[32*r +: 32])
        $display("  x%0d: base %08x/%08x, barrel %08x/%08x (copias A/B del banco)", r,
                 ea.regs_a[32*r +: 32], ea.regs_b[32*r +: 32], eb.regs_a[32*r +: 32], eb.regs_b[32*r +: 32]);
    $display("  (ciclo %0d del barrel; comparadas hasta ahora: %0d, %0d, %0d y %0d)", ciclo, n_cmp[0], n_cmp[1], n_cmp[2], n_cmp[3]);
    $fatal(1);
  endtask

  task automatic comparar(input int t);
    ev_t ea, eb;
    while (!listo[t] && n_cmp[t] < n_b[t] && n_cmp[t] < n_d[t]) begin
      ea = cola_b[t][n_cmp[t] % COLA];
      eb = cola_d[t][n_cmp[t] % COLA];
      if (PCW < 32 && (ea.pc >> PCW) != 0) begin        // el programa salió de la memoria
        fuera[t] = 1; listo[t] = 1;
        // Con memoria compartida los cuatro Espino base ejecutan por turnos:
        // si uno deja de compararse, la corrida termina para todos
        if (compartida != 0) for (int u = 0; u < 4; u++) listo[u] = 1;
        break;
      end
      if (ea.pc !== eb.pc || ea.instr !== eb.instr) falla(t, "contador de programa o instruccion", ea, eb);
      if (ea.rf_we !== eb.rf_we || (ea.rf_we && (ea.rf_wa !== eb.rf_wa || ea.rf_wd !== eb.rf_wd)))
        falla(t, "escritura al banco de registros", ea, eb);
      if (ea.acc !== eb.acc || (ea.acc && (ea.we !== eb.we || ea.addr !== eb.addr || ea.be !== eb.be)) ||
          (ea.acc && ea.we && ea.wdata !== eb.wdata))
        falla(t, "acceso al bus de datos", ea, eb);
      if (ea.regs_a !== eb.regs_a || ea.regs_b !== eb.regs_b || eb.regs_a !== eb.regs_b)
        falla(t, "contexto: contenido del banco de registros", ea, eb);
      if (eb.regs_a[31:0] !== 32'b0) falla(t, "x0 distinto de cero", ea, eb);
      if (ea.acc && ea.we && !ea.addr[31] && ea.mem_word !== eb.mem_word) falla(t, "palabra de memoria escrita", ea, eb);
      if (ea.acc && ea.we && ea.addr[31] && ea.mmio !== eb.mmio) falla(t, "registro de SPI o perifericos escrito", ea, eb);
      if (ea.rf_we) n_rf[t]++;
      if (ea.acc && ea.we) n_st[t]++;
      if (ea.acc && !ea.we) n_ld[t]++;
      if (ea.acc && ea.addr[31]) n_mmio[t]++;
      if (ea.acc && ea.addr[31] && ea.addr[16]) n_spi[t]++;
      // Lecturas de STATUS que vieron la bandera de precio nuevo
      if (ea.acc && !ea.we && ea.addr == 32'h8001_0000 && ea.rf_we && ea.rf_wd[0]) n_bandera[t]++;
      if (ea.instr[6:0] == 7'h63 || ea.instr[6:0] == 7'h6f || ea.instr[6:0] == 7'h67) n_salto[t]++;
      // Lazo vacío: un jal x0 a sí mismo (hilo ocioso o programa que terminó)
      if (ea.instr == 32'h0000_006f) n_lazo[t]++;
      // Instrucciones distintas: mismo contador de programa con otro valor
      // escrito u otro acceso al bus cuenta como distinta. Un programa que
      // repite siempre los mismos valores suma poco aquí aunque corra mucho.
      begin
        longint unsigned k;
        k = 64'(ea.pc) * 64'h9E37_79B9_7F4A_7C15;
        k = (k ^ 64'(ea.rf_wd) ^ (ea.rf_we ? 64'h1_0000_0000 : 64'h0)) * 64'hBF58_476D_1CE4_E5B9;
        k = (k ^ {ea.addr, ea.wdata} ^ 64'(ea.mem_word)) * 64'h94D0_49BB_1331_11EB;
        k = {k[63:2] ^ 62'(k >> 31), 2'(t)};
        if (!visto.exists(k)) begin visto[k] = 1; n_dist[t]++; end
      end
      n_cmp[t]++;
      if (n_cmp[t] >= objetivo) listo[t] = 1;
    end
  endtask

  // --- Memoria al final -------------------------------------------------------------
  function automatic logic [31:0] mem_base(input int t, input int i);
    case (t)
      0: return b0.u_ram.mem[i];
      1: return b1.u_ram.mem[i];
      2: return b2.u_ram.mem[i];
      default: return b3.u_ram.mem[i];
    endcase
  endfunction

  task automatic comparar_memoria(output int iguales, output int en_vuelo);
    bit saltar [512];
    int cambiaron, quien;
    logic [31:0] esperado;
    ev_t e;
    for (int i = 0; i < 512; i++) saltar[i] = sucia[i];
    if (pend_m && em.acc && em.we && !em.addr[31]) saltar[em.addr[10:2]] = 1;
    // Stores que uno de los dos lados ya hizo y todavía no se compararon
    for (int t = 0; t < 4; t++) begin
      for (longint k = n_cmp[t]; k < n_b[t]; k++) begin
        e = cola_b[t][k % COLA];
        if (e.acc && e.we && !e.addr[31]) saltar[e.addr[10:2]] = 1;
      end
      for (longint k = n_cmp[t]; k < n_d[t]; k++) begin
        e = cola_d[t][k % COLA];
        if (e.acc && e.we && !e.addr[31]) saltar[e.addr[10:2]] = 1;
      end
    end
    iguales = 0; en_vuelo = 0;
    for (int i = 0; i < 512; i++) begin
      if (saltar[i]) begin en_vuelo++; continue; end
      if (compartida != 0) begin
        esperado = mem_base(0, i);
        for (int t = 1; t < 4; t++)
          if (mem_base(t, i) !== esperado)
            error($sformatf("memoria compartida: los Espino base 0 y %0d difieren en la palabra %0d", t, i));
      end else begin
        cambiaron = 0; quien = 0;
        for (int t = 0; t < 4; t++) if (mem_base(t, i) !== img[i]) begin cambiaron++; quien = t; end
        if (cambiaron > 1) error($sformatf("la palabra %0d de memoria la escribieron dos hilos: el programa no sirve para +compartida=0", i));
        esperado = (cambiaron == 1) ? mem_base(quien, i) : img[i];
      end
      if (dut.u_ram.mem[i] !== esperado)
        error($sformatf("memoria final: palabra %0d (direccion %03x), barrel %08x, se esperaba %08x",
                        i, 4 * i, dut.u_ram.mem[i], esperado));
      iguales++;
    end
  endtask

  // --- Corrida ------------------------------------------------------------------------
  initial begin
    bit     completo, cabe;
    int     iguales, en_vuelo;
    longint sin_avance = 0, antes;
    if (!$value$plusargs("hex=%s", hex)) begin $display("falta +hex=ARCHIVO"); $fatal(1); end
    void'($value$plusargs("instrucciones=%d", objetivo));
    void'($value$plusargs("compartida=%d", compartida));
    void'($value$plusargs("precio_cada=%d", precio_cada));
    void'($value$plusargs("hilo_spi=%d", hilo_spi));
    for (int i = 0; i < 512; i++) begin img[i] = 32'b0; sucia[i] = 0; end
    $readmemh(hex, img);
    for (int i = 0; i < 512; i++) begin
      dut.u_ram.mem[i] = img[i];
      b0.u_ram.mem[i] = img[i]; b1.u_ram.mem[i] = img[i]; b2.u_ram.mem[i] = img[i]; b3.u_ram.mem[i] = img[i];
    end
    for (int t = 0; t < 4; t++) begin
      n_d[t] = 0; n_b[t] = 0; n_cmp[t] = 0; x_d[t] = 0; ciclos_b[t] = 0;
      n_rf[t] = 0; n_st[t] = 0; n_ld[t] = 0; n_salto[t] = 0; n_mmio[t] = 0; n_spi[t] = 0; n_bandera[t] = 0; n_lazo[t] = 0; n_dist[t] = 0;
      listo[t] = 0; fuera[t] = 0; ba_acc[t] = 0; ba_n[t] = 0;
    end

    // Reset de encendido: los cinco SoC a la vez, hasta que todos lo sueltan
    while (!(dut.rst_ni && b0.rst_ni && b1.rst_ni && b2.rst_ni && b3.rst_ni)) begin
      #1; clk = 1'b1; clk_b = 4'b1111; #1; clk = 1'b0; clk_b = 4'b0000;
    end
    #1;
    // Cada SoC base parte en la entrada de su hilo. El contador de programa
    // del Espino base sale del reset en BootAddr (0) y pochoco_soc no deja
    // cambiar ese parámetro, así que se escribe aquí, antes del primer flanco
    // sin reset. Que parte donde debe se comprueba con la primera instrucción
    // comparada (el contador de programa tiene que ser 4 t).
    b1.u_core.u_if.pc_q = 32'd4;
    b2.u_core.u_if.pc_q = 32'd8;
    b3.u_core.u_if.pc_q = 32'd12;
    // Valor fijo de PRICE, igual en los cinco
    dut.u_spi.price_q = 8'hA5;
    b0.u_spi.price_q = 8'hA5; b1.u_spi.price_q = 8'hA5; b2.u_spi.price_q = 8'hA5; b3.u_spi.price_q = 8'hA5;
    #1;

    while (!(listo[0] && listo[1] && listo[2] && listo[3])) begin
      antes = n_cmp[0] + n_cmp[1] + n_cmp[2] + n_cmp[3];
      // SoC base
      if (compartida != 0) begin
        if (n_b[turno] - n_cmp[turno] < COLA / 2) begin
          flanco_base(turno, completo);
          if (completo) turno = (turno + 1) % 4;
        end
      end else begin
        for (int t = 0; t < 4; t++)
          if (!listo[t] && n_b[t] - n_cmp[t] < COLA / 2) flanco_base(t, completo);
      end
      // Barrel: avanza si ningún hilo tiene la cola llena
      cabe = 1;
      for (int t = 0; t < 4; t++)
        if (!listo[t] && n_d[t] + ((pend_m && pend_t == t) ? 1 : 0) - n_cmp[t] >= COLA / 2) cabe = 0;
      if (cabe) flanco_barrel();
      for (int t = 0; t < 4; t++) comparar(t);
      if (n_cmp[0] + n_cmp[1] + n_cmp[2] + n_cmp[3] == antes) sin_avance++; else sin_avance = 0;
      if (sin_avance > 20000) error($sformatf("no se completan instrucciones (comparadas %0d, %0d, %0d y %0d)", n_cmp[0], n_cmp[1], n_cmp[2], n_cmp[3]));
    end

    comparar_memoria(iguales, en_vuelo);

    for (int t = 0; t < 4; t++)
      $display("HILO %0d: %0d instrucciones comparadas (%0d escrituras de registro, %0d stores, %0d loads, %0d saltos, %0d accesos a SPI y perifericos, de ellos %0d al SPI, %0d lecturas de STATUS con precio nuevo, %0d de lazo vacio, %0d distintas)%s",
               t, n_cmp[t], n_rf[t], n_st[t], n_ld[t], n_salto[t], n_mmio[t], n_spi[t], n_bandera[t], n_lazo[t], n_dist[t],
               fuera[t] ? " FUERA: el programa salio de la memoria" : "");
    $display("PASS verif: %0d instrucciones comparadas una por una (hilos: %0d %0d %0d %0d); memoria final: %0d palabras iguales y %0d sin comparar por stores en vuelo; precios nuevos puestos por el testbench: %0d; ciclos del barrel: %0d",
             n_cmp[0] + n_cmp[1] + n_cmp[2] + n_cmp[3], n_cmp[0], n_cmp[1], n_cmp[2], n_cmp[3],
             iguales, en_vuelo, precios, ciclo);
    $finish;
  end

endmodule
