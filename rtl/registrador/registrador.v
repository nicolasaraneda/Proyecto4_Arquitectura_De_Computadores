// registrador.v: registra por la UART cada precio que manda la maestra SPI.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Herramienta para la prueba con la maestra real del 26/11 (docs/checklist_26nov.md,
// docs/registrador.md). No es parte del diseño de competencia y no guarda ninguna
// serie: escucha las líneas del SPI, arma un registro por transacción y lo manda por
// la UART de la Go Board al computador, donde tools/registrador.py lo guarda como CSV.
//
// Hay dos módulos:
//   registrador      el núcleo: escucha SCLK, MOSI, CS_n y MISO (sin manejarlos) y
//                    entrega los bytes por un transmisor UART 8N1.
//   registrador_top  el bitstream: el núcleo con los pines de goboard.pcf. Responde
//                    0x00 por MISO (mantener), igual que el medidor del SPI, y muestra
//                    en los 7 segmentos cuántos precios registró.
//
// Muestreo, igual que pochoco_spi_slave: tres flip-flops de sincronización en cada
// línea, flanco de subida de SCLK con CS_n en bajo, MOSI y MISO tomados en ese flanco,
// el primer bit es el más significativo. La transacción termina cuando CS_n sube.
//
// Registro de una transacción: 5 bytes, el primero con el bit 7 en 1 y los otros en 0,
// para que el computador se pueda sincronizar en cualquier momento.
//   b0 = {1, sec[6:0]}                    número de registro, módulo 128
//   b1 = {0, precio[7:1]}
//   b2 = {0, miso[7:1]}                   lo que la maestra leyó por MISO
//   b3 = {0, precio[0], miso[0], err, dt[10:7]}
//   b4 = {0, dt[6:0]}
// err: la transacción no tuvo exactamente 8 flancos de subida de SCLK.
// dt: tiempo desde la bajada de CS_n de la transacción anterior, en unidades de
//     128 ciclos (5,12 us), saturado en 2047 (10,48 ms). Es 2047 en la primera.
//
// A 1 Mbaud (25 ciclos por bit) un registro tarda 50 us en salir. La cola tiene 4
// registros: alcanza para precios cada 50 us sostenidos y ráfagas más rápidas. Si
// se llena, el registro nuevo se descarta y el número de secuencia lo delata (y LED3
// queda encendido).
//
// Botones: SW3 borra la cuenta, la secuencia y las alarmas (empezar una ronda nueva).
// SW4 mantenido muestra el byte alto de la cuenta.
// LED1: cambia con cada registro. LED2: la UART está transmitiendo. LED3: hubo una
// transacción con err. LED4: se perdió un registro por cola llena.

module registrador #(
  parameter integer CICLOS_BIT = 25,       // 25 MHz / 1 Mbaud
  parameter integer PROF_LOG2  = 2          // cola de 2^PROF_LOG2 registros
) (
  input  wire        clk,
  input  wire        borrar_i,             // pulso: cuenta, secuencia y alarmas a cero
  input  wire        sclk_i,
  input  wire        mosi_i,
  input  wire        cs_n_i,
  input  wire        miso_i,
  output wire        tx_o,
  output reg  [15:0] cuenta_o = 16'd0,     // registros encolados desde el último borrado
  output reg         alarma_err_o = 1'b0,
  output reg         alarma_cola_o = 1'b0,
  output reg         latido_o = 1'b0,
  output wire        ocupado_o
);

  // --- Sincronización y flancos --------------------------------------------------
  reg [2:0] sclk_s = 3'b000, cs_s = 3'b111, mosi_s = 3'b000, miso_s = 3'b000;
  always @(posedge clk) begin
    sclk_s <= {sclk_s[1:0], sclk_i};
    cs_s   <= {cs_s[1:0], cs_n_i};
    mosi_s <= {mosi_s[1:0], mosi_i};
    miso_s <= {miso_s[1:0], miso_i};
  end
  wire sclk_sube = sclk_s[1] & ~sclk_s[2];
  wire cs_baja   = ~cs_s[1] & cs_s[2];
  wire cs_sube   = cs_s[1] & ~cs_s[2];
  wire cs_activo = ~cs_s[1];

  // --- Una transacción -------------------------------------------------------------
  reg [7:0]  rx = 8'd0, mx = 8'd0;
  reg [3:0]  bits = 4'd0;
  reg [17:0] t_per = 18'h3FFFF;            // ciclos desde la bajada anterior de CS_n
  reg [10:0] dt_tx = 11'h7FF;              // dt de la transacción en curso
  reg        hubo = 1'b0;
  reg [6:0]  sec = 7'd0;

  localparam integer ANCHO = 7 + 8 + 8 + 1 + 11;   // sec, precio, miso, err, dt
  reg  [ANCHO-1:0] cola [0:(1<<PROF_LOG2)-1];
  reg  [PROF_LOG2:0] esc = 0, lec = 0;
  // La resta se guarda en PROF_LOG2 + 1 bits: comparada directamente con un entero se
  // haría en 32 bits y, cuando los punteros dan la vuelta, la cola llena no se vería
  // (lo encontró un control negativo de tools/registrador.sh; ver docs/registrador.md).
  wire [PROF_LOG2:0] ocupados = esc - lec;
  wire llena = ocupados[PROF_LOG2];
  wire vacia = esc == lec;
  wire [ANCHO-1:0] nuevo = {sec, rx, mx, bits != 4'd8, dt_tx};

  always @(posedge clk) begin
    t_per <= (t_per == 18'h3FFFF) ? t_per : t_per + 18'd1;
    if (cs_baja) begin
      bits  <= 4'd0;
      t_per <= 18'd0;
      dt_tx <= hubo ? t_per[17:7] : 11'h7FF;   // t_per satura en 2^18 - 1: dt queda en 2047
      hubo  <= 1'b1;
    end
    if (sclk_sube && cs_activo) begin
      rx   <= {rx[6:0], mosi_s[1]};
      mx   <= {mx[6:0], miso_s[1]};
      bits <= (bits == 4'hF) ? bits : bits + 4'd1;
    end
    if (cs_sube) begin
      if (bits != 4'd8) alarma_err_o <= 1'b1;
      if (llena) alarma_cola_o <= 1'b1;
      else begin
        cola[esc[PROF_LOG2-1:0]] <= nuevo;
        esc      <= esc + 1'b1;
        cuenta_o <= cuenta_o + 16'd1;
        latido_o <= ~latido_o;
      end
      sec <= sec + 7'd1;                    // avanza aunque se pierda: la pérdida se ve
    end
    if (borrar_i) begin
      cuenta_o      <= 16'd0;
      sec           <= 7'd0;
      alarma_err_o  <= 1'b0;
      alarma_cola_o <= 1'b0;
      hubo          <= 1'b0;
    end
  end

  // --- Transmisión: 5 bytes por registro ---------------------------------------------
  wire [ANCHO-1:0] r = cola[lec[PROF_LOG2-1:0]];
  wire [6:0]  r_sec = r[34:28];
  wire [7:0]  r_pre = r[27:20];
  wire [7:0]  r_mis = r[19:12];
  wire        r_err = r[11];
  wire [10:0] r_dt  = r[10:0];
  reg  [2:0]  nbyte = 3'd0;                // 0 a 4 dentro del registro
  reg  [7:0]  dato;
  always @(*) begin
    case (nbyte)
      3'd0: dato = {1'b1, r_sec};
      3'd1: dato = {1'b0, r_pre[7:1]};
      3'd2: dato = {1'b0, r_mis[7:1]};
      3'd3: dato = {1'b0, r_pre[0], r_mis[0], r_err, r_dt[10:7]};
      default: dato = {1'b0, r_dt[6:0]};
    endcase
  end

  reg [9:0] sh = 10'h3FF;                  // {parada, dato, inicio}, sale el bit 0
  reg [3:0] nbit = 4'd0;
  reg [$clog2(CICLOS_BIT+1)-1:0] div = 0;
  reg       enviando = 1'b0;
  assign tx_o = enviando ? sh[0] : 1'b1;
  assign ocupado_o = enviando;
  always @(posedge clk) begin
    if (!enviando) begin
      if (!vacia) begin
        sh       <= {1'b1, dato, 1'b0};
        nbit     <= 4'd0;
        div      <= 0;
        enviando <= 1'b1;
      end
    end else if (div == CICLOS_BIT - 1) begin
      div <= 0;
      if (nbit == 4'd9) begin
        enviando <= 1'b0;
        if (nbyte == 3'd4) begin
          nbyte <= 3'd0;
          lec   <= lec + 1'b1;
        end else nbyte <= nbyte + 3'd1;
      end else begin
        sh   <= {1'b1, sh[9:1]};
        nbit <= nbit + 4'd1;
      end
    end else div <= div + 1'b1;
  end
endmodule


// Antirrebote: el botón tiene que quedar estable REBOTE ciclos. pulso_o dura un ciclo.
module registrador_boton #(parameter integer REBOTE = 250000) (
  input  wire clk_i,
  input  wire boton_i,
  output reg  estable_o = 1'b0,
  output wire pulso_o
);
  reg [1:0] s = 2'b00;
  reg [17:0] n = 18'd0;
  reg anterior = 1'b0;
  always @(posedge clk_i) begin
    s <= {s[0], boton_i};
    if (s[1] == estable_o) n <= 18'd0;
    else if (n == REBOTE - 1) begin estable_o <= s[1]; n <= 18'd0; end
    else n <= n + 18'd1;
    anterior <= estable_o;
  end
  assign pulso_o = estable_o & ~anterior;
endmodule


module registrador_top #(
  parameter integer CICLOS_BIT = 25,
  parameter integer REBOTE     = 250000
) (
  input  wire       i_Clk,
  input  wire [3:0] i_Switch,
  output wire [3:0] o_LED,
  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,
  input  wire       i_SPI_SCLK,
  input  wire       i_SPI_MOSI,
  input  wire       i_SPI_CS_n,
  output wire       o_SPI_MISO,
  input  wire       i_UART_RX,
  output wire       o_UART_TX
);
  assign o_SPI_MISO = 1'b0;                // la maestra lee 0x00: mantener

  wire [3:0] apretado, pulso;
  genvar b;
  generate
    for (b = 0; b < 4; b = b + 1) begin : g_boton
      registrador_boton #(.REBOTE(REBOTE)) u_b (.clk_i(i_Clk), .boton_i(i_Switch[b]), .estable_o(apretado[b]), .pulso_o(pulso[b]));
    end
  endgenerate

  wire [15:0] cuenta;
  wire err, perdida, latido, ocupado;
  registrador #(.CICLOS_BIT(CICLOS_BIT)) u_reg (
    .clk(i_Clk), .borrar_i(pulso[2]), .sclk_i(i_SPI_SCLK), .mosi_i(i_SPI_MOSI), .cs_n_i(i_SPI_CS_n),
    .miso_i(o_SPI_MISO), .tx_o(o_UART_TX), .cuenta_o(cuenta), .alarma_err_o(err), .alarma_cola_o(perdida),
    .latido_o(latido), .ocupado_o(ocupado));

  assign o_LED = {perdida, err, ocupado, latido};

  wire [7:0] muestra = apretado[3] ? cuenta[15:8] : cuenta[7:0];
  function [6:0] hex2seg;                  // el mismo decodificador de pochoco_periph.v
    input [3:0] h;
    begin
      case (h)
        4'h0: hex2seg = 7'b0111111; 4'h1: hex2seg = 7'b0000110; 4'h2: hex2seg = 7'b1011011;
        4'h3: hex2seg = 7'b1001111; 4'h4: hex2seg = 7'b1100110; 4'h5: hex2seg = 7'b1101101;
        4'h6: hex2seg = 7'b1111101; 4'h7: hex2seg = 7'b0000111; 4'h8: hex2seg = 7'b1111111;
        4'h9: hex2seg = 7'b1101111; 4'hA: hex2seg = 7'b1110111; 4'hB: hex2seg = 7'b1111100;
        4'hC: hex2seg = 7'b0111001; 4'hD: hex2seg = 7'b1011110; 4'hE: hex2seg = 7'b1111001;
        default: hex2seg = 7'b1110001;
      endcase
    end
  endfunction
  wire [6:0] s1 = hex2seg(muestra[7:4]), s2 = hex2seg(muestra[3:0]);
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D, o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~s1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D, o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~s2;
endmodule
