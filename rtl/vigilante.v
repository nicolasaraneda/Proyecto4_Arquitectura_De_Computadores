// vigilante.v: dispara el cambio a la imagen de respaldo si el programa deja
// de responder.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Viene del estudio de factibilidad del respaldo por reconfiguración (rama
// factibilidad-fondo, factibilidad/e_warmboot), sin cambios en la lógica.
// Documento de estudio: docs/tabla_vigilante.md. Pruebas: make vig-tb y
// make vig-formal.
//
// Regla: el módulo cuenta los precios recibidos desde la última escritura en
// DECISION. En un programa sano esa cuenta va de 0 a 1 y vuelve a 0 en cada
// tick. Si llega a N + 1 (N precios quedaron sin respuesta y ya llegó otro
// más), se pide a la FPGA que se reconfigure con la imagen Destino
// (SB_WARMBOOT, S1 S0).
//
// Lo que cuenta son precios completos (byte_done del esclavo SPI), no tiempo
// ni flancos de CS_n. Por eso:
//
//   - Con la maestra detenida no pasa nada: sin precios no hay cuenta.
//   - Durante el reset del SoC no pasa nada: el esclavo no entrega precios y
//     este módulo está en reset.
//   - Un rebote de CS_n al conectar el cable no cuenta, porque no completa un
//     byte. Si el ruido llegara a completar uno, el programa lo lee como un
//     precio y responde, y la cuenta vuelve a cero.
//   - Funciona igual con cualquier período, de 10 ms a 0,1 ms.
//
// El disparo espera a que CS_n esté en alto. El precio que completa la cuenta
// llega con CS_n todavía en bajo; BOOT sube cuando la transacción termina. Así
// la maestra nunca ve el pin MISO soltarse a mitad de un byte, y queda todo el
// período libre antes de la transacción siguiente. Si el programa alcanza a
// escribir DECISION antes de que CS_n suba, la cuenta vuelve a cero y no hay
// disparo.
//
// BOOT no se baja: queda en alto hasta que la FPGA se reconfigura. La imagen
// de respaldo no lleva vigilante, de modo que no puede haber un ciclo de
// reinicios.
//
// Entradas, todas síncronas con clk_i:
//   precio_i       pulso de un ciclo por cada precio recibido
//   decision_wr_i  pulso de un ciclo cuando el core escribe DECISION
//   cs_activo_i    CS_n en bajo, ya sincronizado
//   forzar_i       disparo manual. En 0 si no se usa.

module vigilante #(
  parameter       N       = 4,
  parameter [1:0] Destino = 2'b01
) (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       precio_i,
  input  wire       decision_wr_i,
  input  wire       cs_activo_i,
  input  wire       forzar_i,
  output wire       boot_o,
  output wire [1:0] sel_o
);

  localparam W = $clog2(N + 2);

  reg [W-1:0] sin_resp;  // precios recibidos desde la última escritura en DECISION
  reg         boot_q;

  wire lleno = (sin_resp == N + 1);

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      sin_resp <= {W{1'b0}};
      boot_q   <= 1'b0;
    end else begin
      if (precio_i) begin
        // Una escritura en el mismo ciclo responde al precio anterior: queda
        // pendiente solo el que acaba de llegar.
        if (decision_wr_i) sin_resp <= {{(W-1){1'b0}}, 1'b1};
        else if (!lleno)   sin_resp <= sin_resp + 1'b1;
      end else if (decision_wr_i) begin
        sin_resp <= {W{1'b0}};
      end

      if ((lleno | forzar_i) & ~cs_activo_i) boot_q <= 1'b1;
    end
  end

  assign boot_o = boot_q;
  assign sel_o  = Destino;

`ifdef FORMAL
  // Propiedades para SymbiYosys (formal/vigilante/vigilante.sby).
  //
  // El monitor lleva la misma historia con otra codificación: un registro de
  // desplazamiento con un 1 por cada precio recibido desde la última
  // escritura en DECISION. El bit N en 1 significa N + 1 precios.
  reg         f_pasado     = 1'b0;
  reg [N:0]   f_hist       = 0;
  reg         f_forzado    = 1'b0;   // hubo un disparo manual con CS_n en alto
  reg         f_boot_ant   = 1'b0;
  reg         f_cs_ant     = 1'b0;
  reg         f_lleno_ant  = 1'b0;
  reg         f_forzar_ant = 1'b0;
  integer     f_i;

  initial assume (!rst_ni);
  always @(posedge clk_i) begin
    f_pasado <= 1'b1;
    if (f_pasado) assume (rst_ni);     // un solo reset, al comienzo
  end

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      f_hist       <= 0;
      f_forzado    <= 1'b0;
      f_boot_ant   <= 1'b0;
      f_cs_ant     <= 1'b0;
      f_lleno_ant  <= 1'b0;
      f_forzar_ant <= 1'b0;
    end else begin
      if (precio_i)           f_hist <= decision_wr_i ? 1 : {f_hist[N-1:0], 1'b1};
      else if (decision_wr_i) f_hist <= 0;
      if (forzar_i & ~cs_activo_i) f_forzado <= 1'b1;
      f_boot_ant   <= boot_q;
      f_cs_ant     <= cs_activo_i;
      f_lleno_ant  <= lleno;
      f_forzar_ant <= forzar_i;
    end
  end

  always @(posedge clk_i) begin
    if (f_pasado && rst_ni) begin
      // Relación entre el contador del módulo y la historia del monitor
      // (sirve además de invariante para la inducción).
      for (f_i = 0; f_i <= N; f_i = f_i + 1)
        assert (f_hist[f_i] == (sin_resp > f_i));
      assert (sin_resp <= N + 1);

      // 1. BOOT solo sube con CS_n en alto en el ciclo anterior.
      if (boot_q && !f_boot_ant) assert (!f_cs_ant);
      // 2. BOOT solo sube por la cuenta completa o por el disparo manual.
      if (boot_q && !f_boot_ant) assert (f_lleno_ant || f_forzar_ant);
      // 3. BOOT no vuelve a bajar.
      if (f_boot_ant) assert (boot_q);
      // 4. Sin disparo manual, BOOT solo sube si en el ciclo anterior la
      //    historia tenía N + 1 precios seguidos sin escritura.
      if (boot_q && !f_boot_ant && !f_forzar_ant) assert ($past(f_hist[N]));
      // 5. El destino es constante.
      assert (sel_o == Destino);
    end
  end

  // Alcanzable: el disparo por cuenta (sin ningún disparo manual) y el
  // programa sano que responde muchos precios sin que BOOT suba.
  reg [3:0] f_respuestas = 0;
  always @(posedge clk_i) begin
    if (f_pasado && rst_ni) begin
      if (decision_wr_i && !precio_i && sin_resp == 1 && !(&f_respuestas))
        f_respuestas <= f_respuestas + 1'b1;
      cover (boot_q && !f_forzado);
      cover (f_respuestas == 4'd8 && !boot_q);
    end
  end
`endif

endmodule
