// placa_x2.v: prueba mínima del duplicador de reloj en la Go Board.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Un contador en el reloj original de 25 MHz y otro en el reloj doblado,
// con sus bits altos en los dos displays de 7 segmentos. Si el duplicador
// funciona, el display derecho avanza al doble de velocidad que el
// izquierdo. Además un comparador cuenta cuántos ciclos del reloj doblado
// caben en una ventana fija del reloj original y enciende un LED de error si
// alguna vez no son exactamente el doble (con tolerancia de un ciclo por el
// cruce de dominios).
//
// La prueba trae también un oscilador en anillo hecho con las mismas LUT de
// la cadena. Mide cuánto demoran de verdad en este chip, sin osciloscopio:
// con SW4 presionado los displays muestran un número D de dos dígitos
// hexadecimales, y el período del anillo es 1280 / D ns (D en decimal).
//
// Qué se ve en la placa:
//   Display izquierdo   bits altos del contador de 25 MHz. Con ContBits = 28
//                       cambia cada 0,67 s.
//   Display derecho     los mismos bits del contador del reloj doblado.
//                       Cambia cada 0,34 s si el reloj es de 50 MHz.
//   LED1 (o_LED[0])     encendido: la última ventana midió el doble exacto.
//   LED2 (o_LED[1])     error retenido: alguna ventana no midió el doble, o
//                       el reloj doblado está detenido. Se borra con SW4.
//   LED3 (o_LED[2])     parpadeo del reloj original (bit ContBits-3).
//   LED4 (o_LED[3])     parpadeo del reloj doblado (el mismo bit: va al doble).
//
// Botones (activos en alto en la Go Board):
//   sin presionar       cadena completa (NRet LUT)
//   SW1 presionado      sin cadena: el retardo es solo el del multiplexor
//   SW2 presionado      toma después de 1 LUT
//   SW3 presionado      toma después de 2 LUT
//   SW4 presionado      borra el error retenido, enciende el anillo, muestra
//                       su medición en los dos displays y saca el pulso crudo
//                       por el pin de prueba
// El multiplexor que elige la toma agrega su propio retardo al pulso: el
// ancho que queda con cada botón está en mediciones/placa_x2.txt. Con una
// toma muy corta el pulso puede ser demasiado angosto para la red global y
// el contador del reloj doblado pierde ciclos o se detiene: es la forma de
// buscar en la placa el pulso mínimo utilizable. Las tres tomas cortas
// quedan a propósito cerca del mínimo de la hoja de datos (0,88 ns).
//
// Pin de prueba (pin 63, el MISO del conector PMOD, que en el SoC también
// es salida): el reloj doblado dividido por 2. Es una onda de 25 MHz cuyo
// tiempo en alto dura un período del reloj doblado y cuyo tiempo en bajo
// dura el siguiente: con un osciloscopio se leen directamente los dos
// períodos que alternan, o sea el ciclo de trabajo del oscilador. Con SW4
// presionado sale el pulso sin dividir.
//
// Los demás pines del PMOD no se usan: son entradas en el SoC y aquí quedan
// sin conectar, para que este bitstream no pelee con la maestra si la placa
// quedara conectada por error.
//
// En simulación las primitivas no tienen retardo. Con SIM_RETARDO definido
// cada LUT de la cadena se reemplaza por un retardo de transporte, el buffer
// global por un filtro que se traga los pulsos más angostos que PulsoMinPs
// seguido del retardo común, y el anillo por un oscilador ideal.

`timescale 1ns/1ps

module placa_x2 #(
  parameter NRet       = 8,    // LUT de la cadena completa (3 o más)
  parameter ContBits   = 28,   // bits de los contadores (se acorta en simulación)
  parameter VentBits   = 22,   // la ventana del comparador dura 2^VentBits ciclos de 25 MHz
  parameter ConAnillo  = 1,    // 0: sin el oscilador en anillo (para medir restricciones sin lazos)
  parameter NAnillo    = 8,    // LUT de retardo del anillo (más la compuerta que lo habilita)
  parameter VentAniBits = 16,  // la ventana del anillo dura 2^VentAniBits ciclos de 25 MHz
  // Modelo de simulación (SIM_RETARDO), en picosegundos
  parameter RetSubePs   = 9000,  // cadena completa, flanco de subida
  parameter RetBajaPs   = 9000,  // cadena completa, flanco de bajada
  parameter RetMuxPs    = 0,     // multiplexor de tomas
  parameter RetComunPs  = 2000,  // XOR, ruta al buffer global y red global
  parameter PulsoMinPs  = 880,   // pulso mínimo que pasa por la red global
  parameter RetAnilloPs = 8400   // una vuelta del anillo (medio período)
) (
  input  wire       i_Clk,
  input  wire [3:0] i_Switch,
  output wire [3:0] o_LED,
  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,
  output wire       o_Prueba
);

  // ---- Reloj doblado, con largo de cadena elegible -------------------------
  wire          clk2x;
  wire          pulso;
  wire [NRet:0] d;
  wire          ret_sel;
  genvar        i;

`ifdef SIM_RETARDO
  reg [NRet:1] d_r = {NRet{1'b0}};
  assign d = {d_r, i_Clk};
  generate
    for (i = 0; i < NRet; i = i + 1) begin : g_ret
      always @(d[i]) begin
        if (d[i]) d_r[i + 1] <= #(RetSubePs / 1000.0 / NRet) 1'b1;
        else      d_r[i + 1] <= #(RetBajaPs / 1000.0 / NRet) 1'b0;
      end
    end
  endgenerate
  wire ret_mux = i_Switch[0] ? d[0] :
                 i_Switch[1] ? d[1] :
                 i_Switch[2] ? d[2] : d[NRet];
  reg  ret_mux_q = 1'b0;
  always @(ret_mux) ret_mux_q <= #(RetMuxPs / 1000.0) ret_mux;
  assign ret_sel = ret_mux_q;

  wire pulso_ideal = i_Clk ^ ret_sel;
  // Retardo inercial: un pulso (o un hueco) más angosto que PulsoMinPs no pasa.
  wire #(PulsoMinPs / 1000.0) pulso_filtrado = pulso_ideal;
  reg  pulso_q = 1'b0;
  always @(pulso_filtrado) pulso_q <= #((RetComunPs - PulsoMinPs) / 1000.0) pulso_filtrado;
  assign pulso = pulso_q;
  assign clk2x = pulso_q;
`else
  // La cadena es la de duplicador_reloj (modo 0), pero el XOR y el buffer
  // global se instancian aquí para poder elegir la toma con los botones.
  (* keep *) wire [NRet:0] d_k;
  assign d_k[0] = i_Clk;
  assign d = d_k;
  generate
    for (i = 0; i < NRet; i = i + 1) begin : g_ret
      (* keep *)
      SB_LUT4 #(.LUT_INIT(16'hAAAA)) u_buf (
        .O(d_k[i + 1]), .I0(d_k[i]), .I1(1'b0), .I2(1'b0), .I3(1'b0));
    end
  endgenerate

  // Los botones entran sin sincronizar: son parte de la red de reloj a
  // propósito. Cambiar de toma en marcha produce un pulso irregular, y por
  // eso después de soltar el botón se borra el error con SW4.
  assign ret_sel = i_Switch[0] ? d[0] :
                   i_Switch[1] ? d[1] :
                   i_Switch[2] ? d[2] : d[NRet];

  (* keep *)
  SB_LUT4 #(.LUT_INIT(16'h6666)) u_xor (
    .O(pulso), .I0(i_Clk), .I1(ret_sel), .I2(1'b0), .I3(1'b0));

  SB_GB u_gb (
    .USER_SIGNAL_TO_GLOBAL_BUFFER (pulso),
    .GLOBAL_BUFFER_OUTPUT         (clk2x)
  );
`endif

  // ---- Contador en el reloj original ---------------------------------------
  reg [ContBits-1:0] cnt1_q = {ContBits{1'b0}};
  always @(posedge i_Clk) cnt1_q <= cnt1_q + 1'b1;

  // Ventana: un bit que cambia cada 2^VentBits ciclos de 25 MHz
  wire vent = cnt1_q[VentBits];

  // ---- Contador en el reloj doblado ----------------------------------------
  reg [ContBits-1:0] cnt2_q = {ContBits{1'b0}};
  always @(posedge clk2x) cnt2_q <= cnt2_q + 1'b1;

  // ---- Comparador, en el dominio del reloj doblado -------------------------
  // La ventana cruza de dominio por un sincronizador de dos flip-flops. Entre
  // dos cambios de la ventana deben caber 2^(VentBits+1) ciclos del reloj
  // doblado, más o menos uno por la incertidumbre del sincronizador.
  reg [2:0]          vent_s = 3'b000;
  reg [VentBits+2:0] med_q = {(VentBits+3){1'b0}};
  reg                ok_q = 1'b0, error_q = 1'b0, primera_q = 1'b1;
  wire               cambio = vent_s[2] ^ vent_s[1];
  wire [VentBits+2:0] esperado = {2'b01, {(VentBits+1){1'b0}}};   // 2^(VentBits+1)
  wire               justo = (med_q == esperado) || (med_q == esperado - 1'b1) || (med_q == esperado + 1'b1);

  // SW4 borra el error. Pasa por su propio sincronizador.
  reg [1:0] borra_s = 2'b00;

  always @(posedge clk2x) begin
    vent_s  <= {vent_s[1:0], vent};
    borra_s <= {borra_s[0], i_Switch[3]};
    if (cambio) begin
      med_q     <= {{(VentBits+2){1'b0}}, 1'b1};
      primera_q <= 1'b0;
      if (!primera_q) begin
        ok_q <= justo;
        if (!justo) error_q <= 1'b1;
      end
    end else if (!med_q[VentBits+2]) begin
      med_q <= med_q + 1'b1;                 // satura para no dar la vuelta
    end
    if (borra_s[1]) error_q <= 1'b0;
  end

  // Si el reloj doblado se detiene, el comparador también: el LED de la
  // última ventana quedaría pegado en su valor. Para verlo desde el reloj
  // original se mira si el contador doblado avanzó en la ventana.
  reg [1:0] vivo_s = 2'b00;
  reg       vivo_ant = 1'b0, visto_q = 1'b0, vivo_q = 1'b0, vent_ant = 1'b0;
  always @(posedge i_Clk) begin
    vivo_s   <= {vivo_s[0], cnt2_q[VentBits-2]};
    vivo_ant <= vivo_s[1];
    vent_ant <= vent;
    if (vent ^ vent_ant) begin
      vivo_q  <= visto_q;                    // ¿avanzó en la ventana que termina?
      visto_q <= 1'b0;
    end else if (vivo_s[1] ^ vivo_ant) begin
      visto_q <= 1'b1;
    end
  end

  assign o_LED[0] = ok_q & vivo_q;
  assign o_LED[1] = error_q | ~vivo_q;
  assign o_LED[2] = cnt1_q[ContBits-3];
  assign o_LED[3] = cnt2_q[ContBits-3];

  // ---- Oscilador en anillo y su medición ------------------------------------
  // Una compuerta NAND que lo habilita y NAnillo LUT iguales a las de la
  // cadena. Corre solo con SW4 presionado, para que no meta ruido en la
  // prueba del duplicador. Su salida va por otro buffer global a un contador.
  wire clk_ani;
  wire ani_en = i_Switch[3];

`ifdef SIM_RETARDO
  reg ani_q = 1'b0;
  always begin
    wait (ani_en && ConAnillo != 0);
    #(RetAnilloPs / 1000.0) ani_q = ~ani_q;
  end
  assign clk_ani = ani_q;
`else
  generate
    if (ConAnillo != 0) begin : g_anillo
      (* keep *) wire [NAnillo:0] a;
      (* keep *)
      SB_LUT4 #(.LUT_INIT(16'h7777)) u_ani_nand (       // O = ~(I0 & I1)
        .O(a[0]), .I0(a[NAnillo]), .I1(ani_en), .I2(1'b0), .I3(1'b0));
      for (i = 0; i < NAnillo; i = i + 1) begin : g_ani
        (* keep *)
        SB_LUT4 #(.LUT_INIT(16'hAAAA)) u_buf (
          .O(a[i + 1]), .I0(a[i]), .I1(1'b0), .I2(1'b0), .I3(1'b0));
      end
      SB_GB u_gb_ani (
        .USER_SIGNAL_TO_GLOBAL_BUFFER (a[NAnillo]),
        .GLOBAL_BUFFER_OUTPUT         (clk_ani)
      );
    end else begin : g_sin_anillo
      assign clk_ani = 1'b0;
    end
  endgenerate
`endif

  // Cuenta los períodos del anillo que caben en 2^VentAniBits ciclos de
  // 25 MHz. Lo que se muestra es la cuenta dividida por 2^(VentAniBits-5):
  //   D = 32 x 40 ns / período del anillo = 1280 / período en ns
  // Con SW4 suelto el anillo se detiene y queda la última medición.
  wire               vent_ani = cnt1_q[VentAniBits];
  reg [2:0]          vani_s = 3'b000;
  reg [VentAniBits+3:0] cani_q = {(VentAniBits+4){1'b0}};   // el bit alto marca fuera de rango
  reg [7:0]          dani_q = 8'h00;
  always @(posedge clk_ani) begin
    vani_s <= {vani_s[1:0], vent_ani};
    if (vani_s[2] ^ vani_s[1]) begin
      dani_q <= cani_q[VentAniBits+3] ? 8'hFF : cani_q[VentAniBits+2:VentAniBits-5];
      cani_q <= {{(VentAniBits+3){1'b0}}, 1'b1};
    end else if (!cani_q[VentAniBits+3]) begin
      cani_q <= cani_q + 1'b1;               // se detiene al pasarse: D = FF es fuera de rango
    end
  end

  // ---- Displays ------------------------------------------------------------
  function [6:0] hex2seg;
    input [3:0] hex;
    begin
      case (hex)
        4'h0: hex2seg = 7'b0111111;
        4'h1: hex2seg = 7'b0000110;
        4'h2: hex2seg = 7'b1011011;
        4'h3: hex2seg = 7'b1001111;
        4'h4: hex2seg = 7'b1100110;
        4'h5: hex2seg = 7'b1101101;
        4'h6: hex2seg = 7'b1111101;
        4'h7: hex2seg = 7'b0000111;
        4'h8: hex2seg = 7'b1111111;
        4'h9: hex2seg = 7'b1101111;
        4'hA: hex2seg = 7'b1110111;
        4'hB: hex2seg = 7'b1111100;
        4'hC: hex2seg = 7'b0111001;
        4'hD: hex2seg = 7'b1011110;
        4'hE: hex2seg = 7'b1111001;
        4'hF: hex2seg = 7'b1110001;
        default: hex2seg = 7'b0000000;
      endcase
    end
  endfunction

  // SW4 pasa por un sincronizador antes de elegir qué se muestra
  reg [1:0] ver_s = 2'b00;
  always @(posedge i_Clk) ver_s <= {ver_s[0], i_Switch[3]};

  wire [3:0] izq = ver_s[1] ? dani_q[7:4] : cnt1_q[ContBits-1:ContBits-4];
  wire [3:0] der = ver_s[1] ? dani_q[3:0] : cnt2_q[ContBits-1:ContBits-4];
  wire [6:0] seg1 = hex2seg(izq);
  wire [6:0] seg2 = hex2seg(der);

  // Los segmentos son activos en bajo en la placa
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~seg2;

  // ---- Pin de prueba -------------------------------------------------------
  reg div2_q = 1'b0;
  always @(posedge clk2x) div2_q <= ~div2_q;
  assign o_Prueba = i_Switch[3] ? pulso : div2_q;

endmodule
