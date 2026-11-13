// tb_paralelo.sv: ejecución en paralelo del Espino base y del segmentado.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Instancia dos SoC completos con el mismo programa: A con el Espino base
// (Pipeline = 0) y B con el pipeline de 3 etapas (Pipeline = 1). Cada vez que
// uno completa una instrucción se anota qué hizo, y la instrucción número k
// de A se compara con la número k de B:
//   - contador de programa e instrucción;
//   - escritura al banco de registros (registro y valor);
//   - escritura a memoria (dirección, bytes y dato);
//   - el contenido real de los 16 registros después de la instrucción, leído
//     de las BRAM del banco (las dos copias, puertos A y B);
//   - la palabra de memoria recién escrita, leída de la RAM.
// Al final se compara la RAM completa, palabra por palabra, y en el segmentado
// además la copia de la memoria que usa el fetch.
//
// El segmentado completa instrucciones más rápido que el base. Para que las
// colas no crezcan, el reloj del que va adelantado se detiene.
//
// El bus SPI queda quieto y los interruptores en cero: así lo que el programa
// lee de los periféricos no depende del ciclo en que lo lee, y los dos cores
// tienen que hacer exactamente lo mismo aunque tarden distinto.
//
// Contador de programa. El base lo tiene de 32 bits y el segmentado de 11,
// que es lo que direcciona la memoria de 512 palabras. Mientras el programa
// se queda dentro de la memoria los dos son iguales. Si un programa aleatorio
// salta fuera (por ejemplo un jalr con una base cualquiera), los dos leen la
// misma palabra, porque la memoria solo mira 9 bits, pero el valor del
// contador ya no coincide. Por eso hay dos configuraciones:
//   - PCW_B = 11 (por defecto): el segmentado tal como se sintetiza. La
//     comparación de un programa termina, sin error, en la primera
//     instrucción que el base ejecuta fuera de la memoria.
//   - PCW_B = 32: el segmentado con el contador completo. Se compara todo,
//     también lo que pasa fuera de la memoria.
//
// Uso (make paralelo, tools/paralelo.sh), con Verilator:
//   sim +hex=programa.hex +instrucciones=100000
// El programa debe traer las 512 palabras (los de tools/prog_aleatorio.py las
// traen).

`timescale 1ns/1ps

`ifndef PCW_B
  `define PCW_B 11
`endif

module tb_paralelo;

  localparam int COLA = 16;

  logic clk_a = 0, clk_b = 0;

  pochoco_soc #(.MemFile(""), .PorBits(4), .Pipeline(0)) a (
    .i_Clk(clk_a), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  pochoco_soc #(.MemFile(""), .PorBits(4), .Pipeline(1), .PcW(`PCW_B)) b (
    .i_Clk(clk_b), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  // Lo que hizo una instrucción completada
  typedef struct packed {
    logic [31:0]  pc, instr;
    logic         rf_we;
    logic [3:0]   rf_wa;
    logic [31:0]  rf_wd;
    logic         st;
    logic [31:0]  st_addr, st_data;
    logic [3:0]   st_be;
    logic [511:0] regs_a, regs_b;   // banco real después de la instrucción (copias A y B)
    logic [31:0]  mem_word;         // palabra escrita, leída de la RAM después
  } ev_t;

  ev_t cola_a [COLA], cola_b [COLA];
  longint n_a = 0, n_b = 0;          // instrucciones anotadas y completas (con su foto del banco)
  longint n_cmp = 0;                 // instrucciones comparadas
  longint n_rf = 0, n_st = 0, n_ld = 0, n_salto = 0;
  bit     pend_a = 0, pend_b = 0;    // falta la foto del estado de la última instrucción
  ev_t    ult_a, ult_b;
  longint objetivo = 100000;
  longint ciclos_a = 0, ciclos_b = 0, sin_avance = 0;
  bit     fuera = 0;                 // el programa salió de la memoria (solo con PCW_B < 32)
  string  hex;

  // Estado real del banco de registros: {mitad alta, mitad baja} de cada copia
  `define FOTO(soc, banco) \
    for (int r = 0; r < 16; r++) \
      foto[32*r +: 32] = {soc.u_core.u_rf.banco.u_hi.memory[r], soc.u_core.u_rf.banco.u_lo.memory[r]};

  function automatic logic [511:0] foto_a_A(); logic [511:0] foto; `FOTO(a, u_bankA) return foto; endfunction
  function automatic logic [511:0] foto_a_B(); logic [511:0] foto; `FOTO(a, u_bankB) return foto; endfunction
  function automatic logic [511:0] foto_b_A(); logic [511:0] foto; `FOTO(b, u_bankA) return foto; endfunction
  function automatic logic [511:0] foto_b_B(); logic [511:0] foto; `FOTO(b, u_bankB) return foto; endfunction

  // --- Core A: Espino base -----------------------------------------------------
  always @(posedge clk_a) begin
    ciclos_a++;
    if (pend_a) begin
      ult_a.regs_a   = foto_a_A();
      ult_a.regs_b   = foto_a_B();
      ult_a.mem_word = a.u_ram.mem[ult_a.st_addr[10:2]];
      cola_a[n_a % COLA] = ult_a;
      n_a++;
      pend_a = 0;
    end
    if (a.u_core.u_id.commit) begin
      ult_a.pc      = a.u_core.pc_id;
      ult_a.instr   = a.u_core.instr_ex;
      ult_a.rf_we   = a.u_core.rf_we && a.u_core.rf_waddr != 0;
      ult_a.rf_wa   = a.u_core.rf_waddr;
      ult_a.rf_wd   = a.u_core.rf_wdata;
      ult_a.st      = a.u_core.data_req_o && a.u_core.data_we_o;
      ult_a.st_addr = a.u_core.data_addr_o;
      ult_a.st_data = a.u_core.data_wdata_o;
      ult_a.st_be   = a.u_core.data_be_o;
      pend_a = 1;
    end
  end

  // --- Core B: pipeline de 3 etapas -------------------------------------------
  always @(posedge clk_b) begin
    ciclos_b++;
    if (pend_b) begin
      ult_b.regs_a   = foto_b_A();
      ult_b.regs_b   = foto_b_B();
      ult_b.mem_word = b.u_ram.mem[ult_b.st_addr[10:2]];
      cola_b[n_b % COLA] = ult_b;
      n_b++;
      pend_b = 0;
    end
    if (b.u_core.u_id.commit) begin
      ult_b.pc      = b.u_core.pc_id;
      ult_b.instr   = b.u_core.instr_ex;
      ult_b.rf_we   = b.u_core.rf_we && b.u_core.rf_waddr != 0;
      ult_b.rf_wa   = b.u_core.rf_waddr;
      ult_b.rf_wd   = b.u_core.rf_wdata;
      ult_b.st      = b.u_core.data_req_o && b.u_core.data_we_o;
      ult_b.st_addr = b.u_core.data_addr_o;
      ult_b.st_data = b.u_core.data_wdata_o;
      ult_b.st_be   = b.u_core.data_be_o;
      pend_b = 1;
    end
  end

  // --- Comparación -------------------------------------------------------------
  task automatic falla(input string que, input ev_t ea, input ev_t eb);
    $display("FAIL paralelo: difieren en la instruccion %0d (%s)", n_cmp + 1, que);
    $display("  base:       pc=%08x instr=%08x rf_we=%0d x%0d=%08x store=%0d addr=%08x be=%04b dato=%08x mem=%08x",
             ea.pc, ea.instr, ea.rf_we, ea.rf_wa, ea.rf_wd, ea.st, ea.st_addr, ea.st_be, ea.st_data, ea.mem_word);
    $display("  segmentado: pc=%08x instr=%08x rf_we=%0d x%0d=%08x store=%0d addr=%08x be=%04b dato=%08x mem=%08x",
             eb.pc, eb.instr, eb.rf_we, eb.rf_wa, eb.rf_wd, eb.st, eb.st_addr, eb.st_be, eb.st_data, eb.mem_word);
    for (int r = 1; r < 16; r++)
      if (ea.regs_a[32*r +: 32] !== eb.regs_a[32*r +: 32] || ea.regs_b[32*r +: 32] !== eb.regs_b[32*r +: 32])
        $display("  x%0d: base %08x/%08x, segmentado %08x/%08x (copias A/B del banco)", r,
                 ea.regs_a[32*r +: 32], ea.regs_b[32*r +: 32], eb.regs_a[32*r +: 32], eb.regs_b[32*r +: 32]);
    $fatal(1);
  endtask

  task automatic comparar;
    ev_t ea, eb;
    while (n_cmp < n_a && n_cmp < n_b && n_cmp < objetivo) begin
      ea = cola_a[n_cmp % COLA];
      eb = cola_b[n_cmp % COLA];
      if (`PCW_B < 32 && (ea.pc >> `PCW_B) != 0) begin
        fuera = 1;
        objetivo = n_cmp;
        break;
      end
      if (ea.pc !== eb.pc || ea.instr !== eb.instr) falla("contador de programa o instruccion", ea, eb);
      if (ea.rf_we !== eb.rf_we || (ea.rf_we && (ea.rf_wa !== eb.rf_wa || ea.rf_wd !== eb.rf_wd)))
        falla("escritura al banco de registros", ea, eb);
      if (ea.st !== eb.st || (ea.st && (ea.st_addr !== eb.st_addr || ea.st_be !== eb.st_be || ea.st_data !== eb.st_data)))
        falla("escritura a memoria", ea, eb);
      if (ea.regs_a !== eb.regs_a || ea.regs_b !== eb.regs_b || ea.regs_a !== ea.regs_b)
        falla("contenido del banco de registros", ea, eb);
      if (ea.st && !ea.st_addr[31] && ea.mem_word !== eb.mem_word) falla("palabra de memoria escrita", ea, eb);
      if (ea.rf_we) n_rf++;
      if (ea.st)    n_st++;
      if (ea.instr[6:0] == 7'h03) n_ld++;
      if (ea.instr[6:0] == 7'h63 || ea.instr[6:0] == 7'h6f || ea.instr[6:0] == 7'h67) n_salto++;
      n_cmp++;
      sin_avance = 0;
    end
  endtask

  // --- Relojes: se detiene al que va más de COLA/2 instrucciones adelante ------
  initial begin
    if (!$value$plusargs("hex=%s", hex)) begin $display("falta +hex=ARCHIVO"); $fatal(1); end
    void'($value$plusargs("instrucciones=%d", objetivo));
    for (int i = 0; i < 512; i++) begin a.u_ram.mem[i] = 0; b.u_ram.mem[i] = 0; b.u_ram.g_neg.mem_f[i] = 0; end
    $readmemh(hex, a.u_ram.mem);
    $readmemh(hex, b.u_ram.mem);
    $readmemh(hex, b.u_ram.g_neg.mem_f);

    while (n_cmp < objetivo) begin
      #20;
      if (n_a + pend_a - n_cmp < COLA / 2) clk_a = 1;
      if (n_b + pend_b - n_cmp < COLA / 2) clk_b = 1;
      #20;
      clk_a = 0; clk_b = 0;
      comparar();
      sin_avance++;
      if (sin_avance > 20000) begin
        $display("FAIL paralelo: ninguno de los dos cores completa instrucciones (comparadas %0d)", n_cmp);
        $fatal(1);
      end
    end

    // RAM completa. Los dos cores pueden llevar instrucciones completadas de
    // más (hasta COLA/2), así que solo se exige igualdad si ninguno de los
    // dos escribió memoria después de la última instrucción comparada.
    begin
      int dif = 0, dif_f = 0;
      bit store_extra = 0;
      for (longint k = n_cmp; k < n_a; k++) store_extra |= cola_a[k % COLA].st;
      for (longint k = n_cmp; k < n_b; k++) store_extra |= cola_b[k % COLA].st;
      store_extra |= (pend_a && ult_a.st) || (pend_b && ult_b.st);
      for (int i = 0; i < 512; i++) begin
        if (a.u_ram.mem[i] !== b.u_ram.mem[i]) dif++;
        if (b.u_ram.mem[i] !== b.u_ram.g_neg.mem_f[i]) dif_f++;
      end
      if (dif_f != 0) begin
        $display("FAIL paralelo: la copia de la memoria para el fetch difiere de la RAM en %0d palabras", dif_f);
        $fatal(1);
      end
      if (dif != 0 && !store_extra) begin
        $display("FAIL paralelo: la RAM de los dos cores difiere en %0d palabras al terminar", dif);
        $fatal(1);
      end
      $display("PASS paralelo: %0d instrucciones comparadas (%0d escrituras de registro, %0d stores, %0d loads, %0d saltos); RAM final %s. Ciclos: base %0d, segmentado %0d.%s",
               n_cmp, n_rf, n_st, n_ld, n_salto,
               store_extra ? "no comparada entera (habia un store en vuelo)" : "identica en las 512 palabras",
               ciclos_a, ciclos_b,
               fuera ? " FUERA: el programa salio de la memoria y la comparacion termino ahi" : "");
    end
    $finish;
  end

endmodule
