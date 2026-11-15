// propiedades.vh: propiedades formales del Espino barrel.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// tools/barrel/formal.sh copia este texto dentro del módulo espino_barrel_core (en
// una copia: el archivo de rtl/ no se toca) y lo prueba con SymbiYosys. La
// instrucción que entrega la memoria, el dato del bus y lo que entrega el
// banco de registros quedan libres: las propiedades valen para cualquier
// programa y cualquier contenido de memoria.
//
// Son propiedades de estructura: dicen que los cuatro hilos no se pisan y que
// el arranque deja a cada hilo en su entrada. No dicen que cada instrucción
// calcule lo que debe (eso se comprueba por simulación contra el Espino base,
// tools/barrel/verif.sh).
//
// Tres tareas (tools/barrel/formal.sh):
//   invariantes  P1 a P8, por inducción, con el banco entregando cualquier
//                valor (formal/regfile_abstracto.v).
//   arranque     con -DFORMAL_ARRANQUE se agrega P9, que cuenta ciclos desde
//                el reset y por eso se prueba con profundidad acotada.
//   operandos    con -DFORMAL_ESPIA se agregan P10 y P11, por inducción, con
//                un banco que devuelve las direcciones que vio en sus puertos
//                (formal/regfile_espia.v).

  reg        f_past = 1'b0;          // ya hubo un flanco
  reg  [3:0] f_ciclo = 4'd0;         // flancos desde que se soltó el reset (satura en 15)
  reg  [1:0] f_tid_x_q, f_tid_x_qq;
  reg        f_valid_x_q;
  reg  [PcW-1:1] f_pc_next_q, f_pc_next_qq;
  reg  [3:0] f_rd_x_q, f_rd_x_qq;
  reg        f_we_x_q, f_we_x_qq;

  // El reset está activo solo antes del primer flanco
  initial assume (!rst_ni);
  always @(posedge clk_i) begin
    f_past  <= 1'b1;
    if (rst_ni && f_ciclo != 4'd15) f_ciclo <= f_ciclo + 4'd1;
    f_tid_x_q    <= tid_x;
    f_tid_x_qq   <= f_tid_x_q;
    f_valid_x_q  <= tb_valid_x;
    f_pc_next_q  <= pc_next[PcW-1:1];
    f_pc_next_qq <= f_pc_next_q;
    f_rd_x_q     <= instr_x[10:7];
    f_rd_x_qq    <= f_rd_x_q;
    f_we_x_q     <= rf_we_x;
    f_we_x_qq    <= f_we_x_q;
  end
  always @* if (f_past) assume (rst_ni);

  always @(posedge clk_i) begin
    if (rst_ni) begin
      // P1. El hilo que lee el banco (el de R) nunca es el que lo escribe (el de M).
      assert (tid_r != tid_m);
      // P2. x0 nunca se escribe.
      if (rf_we_m) assert (rd_m != 4'd0);
      // P3. Una burbuja no pide el bus, no salta y no escribe el banco.
      if (!tb_valid_x) assert (!data_req_o && !taken && !rf_we_x);
      // P4. No hay escritura al bus sin petición.
      if (data_we_o) assert (data_req_o);
      // (auxiliar de P7, para la inducción) Si X tiene una instrucción de
      // verdad, R también.
      if (tb_valid_x) assert (valid_r);
    end
    // Las propiedades que miran el ciclo anterior valen desde el segundo
    // ciclo sin reset, y las que miran dos ciclos atrás desde el tercero.
    if (rst_ni && f_ciclo >= 4'd1) begin
      // P5. Los hilos rotan: en X hay un hilo distinto en cada ciclo, en orden.
      assert (tid_x == f_tid_x_q + 2'd1);
      // P6. La instrucción que escribe el banco es la que estuvo en X en el
      //     ciclo anterior, y escribe en el contexto de ese hilo.
      assert (tid_m == f_tid_x_q);
      if (rf_we_m) assert (f_valid_x_q);
      // P7. Una vez que hay instrucciones de verdad en X, no vuelve a haber burbujas.
      if (f_valid_x_q) assert (tb_valid_x);
    end
    if (rst_ni && f_ciclo >= 4'd2) begin
      // P8. El contador de programa que entra a F es el próximo contador que
      //     calculó ese mismo hilo dos ciclos antes, cuando estaba en X.
      assert (tid_f == f_tid_x_qq);
      assert (pc_f_q == f_pc_next_qq);
    end
`ifdef FORMAL_ESPIA
    // Con formal/regfile_espia.v el banco devuelve, en algunos bits del dato
    // leído, las direcciones que vio en sus puertos en el flanco anterior. Así
    // se comprueba lo que de verdad llega al banco, y no solo las señales del
    // core que deberían llegar.
    if (rst_ni && f_ciclo >= 4'd1) begin
      // P10. Los operandos que llegan a X se leyeron del contexto del hilo que
      //      está en X y de los registros rs1 y rs2 de su instrucción.
      assert (rf_rdata_a[5:0] == {tid_x, instr_x[18:15]});
      assert (rf_rdata_b[5:0] == {tid_x, instr_x[23:20]});
    end
    if (rst_ni && f_ciclo >= 4'd2) begin
      // P11. Lo que el banco escribió en el flanco anterior es el registro
      //      destino de la instrucción que estuvo en X dos ciclos antes, en el
      //      contexto de ese hilo, y solo si esa instrucción escribía y su
      //      destino no era x0.
      assert (rf_rdata_a[14] == (f_we_x_qq && f_rd_x_qq != 4'd0));
      if (rf_rdata_a[14]) assert (rf_rdata_a[13:8] == {f_tid_x_qq, f_rd_x_qq});
    end
`endif
`ifdef FORMAL_ARRANQUE
    // P9. Arranque, para cualquier contenido de la memoria: el hilo t busca su
    //     primera instrucción en BootAddr + BootPaso t, en el ciclo t + 1, y la
    //     ejecuta en el ciclo t + 3. Antes de eso en X solo hay burbujas.
    if (rst_ni) begin
      if (f_ciclo == 4'd0) assert (tid_f == 2'd0 && pc_f == BootAddr[PcW-1:0]);
      if (f_ciclo == 4'd1) assert (tid_f == 2'd1 && pc_f == BootAddr[PcW-1:0] + BootPaso);
      if (f_ciclo == 4'd2) assert (tid_f == 2'd2 && pc_f == BootAddr[PcW-1:0] + 2 * BootPaso);
      if (f_ciclo == 4'd3) assert (tid_f == 2'd3 && pc_f == BootAddr[PcW-1:0] + 3 * BootPaso);
      if (f_ciclo <= 4'd1) assert (!tb_valid_x);
      if (f_ciclo == 4'd2) assert (tb_valid_x && tid_x == 2'd0 && pc_x == BootAddr[PcW-1:0]);
      if (f_ciclo == 4'd3) assert (tb_valid_x && tid_x == 2'd1 && pc_x == BootAddr[PcW-1:0] + BootPaso);
      if (f_ciclo == 4'd4) assert (tb_valid_x && tid_x == 2'd2 && pc_x == BootAddr[PcW-1:0] + 2 * BootPaso);
      if (f_ciclo == 4'd5) assert (tb_valid_x && tid_x == 2'd3 && pc_x == BootAddr[PcW-1:0] + 3 * BootPaso);
    end
    // Que la prueba no sea vacía: se llega al ciclo 6 con una escritura al banco
    cover (rst_ni && f_ciclo == 4'd6 && rf_we_m);
`endif
  end
