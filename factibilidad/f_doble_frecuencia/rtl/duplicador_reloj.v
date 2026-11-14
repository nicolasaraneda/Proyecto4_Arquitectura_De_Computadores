// duplicador_reloj.v: duplicador de reloj por lógica, sin PLL.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Experimento de factibilidad (pieza F). No forma parte del SoC de
// competencia.
//
//   ret      = clk_i retardado por una cadena de N LUT
//   clk2x_o  = clk_i XOR ret, por un buffer global SB_GB
//
// Cada flanco de clk_i (de subida y de bajada) produce un pulso de ancho
// igual al retardo de la cadena. La salida tiene dos flancos de subida por
// período de clk_i: uno al subir clk_i y otro al bajar. Por eso los períodos
// del reloj doblado alternan entre el semiperíodo alto y el semiperíodo bajo
// de clk_i, y el ciclo de trabajo del oscilador pasa directo al período.
//
// Cómo se evita que las herramientas se lleven la cadena:
//   - Las LUT se instancian como primitivas SB_LUT4 con el atributo keep.
//     Qué flujos de Yosys la conservan y cuáles no está medido en
//     mediciones/sintesis_cadena.txt. Con CADENA_RTL definido la cadena se
//     escribe como asignaciones comunes, solo para mostrar que así
//     desaparece. Con SIN_KEEP se quita el atributo.
//   - La ubicación se fija en nextpnr con scripts/fijar_cadena.py
//     (--pre-pack), que pone el atributo BEL en cada LUT de la cadena. Un
//     atributo BEL escrito aquí tendría que ser un texto constante por
//     instancia, y Yosys no acepta armarlo dentro de un generate.
//   - nextpnr elige además por cuál de las cuatro entradas físicas de la LUT
//     entra la señal (permuta las entradas al rutear), y cada entrada tiene
//     un retardo distinto. Con Modo = 1 cada etapa usa las cuatro entradas
//     con la misma señal y alterna AND y OR: el retardo ya no depende de esa
//     elección y los flancos de subida y de bajada quedan parejos.
//
// En simulación las primitivas no tienen retardo. Con SIM_RETARDO definido se
// reemplaza la cadena por un retardo de transporte, distinto para el flanco
// de subida y el de bajada, y se agrega el retardo común del XOR y del buffer
// global. Los valores salen de las mediciones (mediciones/cadena.txt).

`timescale 1ns/1ps

module duplicador_reloj #(
  parameter N             = 8,     // LUT de retardo
  parameter Modo          = 0,     // 0: buffer por una entrada. 1: AND y OR de 4 entradas, alternados
  // Solo con SIM_RETARDO, en picosegundos:
  parameter RetSubePs     = 9000,  // retardo de la cadena para el flanco de subida
  parameter RetBajaPs     = 9000,  // retardo de la cadena para el flanco de bajada
  parameter RetComunPs    = 2000   // XOR, ruta al buffer global y red global
) (
  input  wire clk_i,
  output wire clk2x_o,             // reloj doblado, en la red global
  output wire pulso_o,             // el mismo pulso antes del buffer global
  output wire ret_o,               // clk_i retardado (salida de la cadena)
  output wire [N:0] toma_o         // tomas intermedias de la cadena (toma_o[0] = clk_i)
);

`ifdef SIM_RETARDO
  reg ret_q   = 1'b0;
  reg pulso_q = 1'b0;
  always @(clk_i) begin
    if (clk_i) ret_q <= #(RetSubePs / 1000.0) 1'b1;
    else       ret_q <= #(RetBajaPs / 1000.0) 1'b0;
  end
  wire pulso_ideal = clk_i ^ ret_q;
  always @(pulso_ideal) pulso_q <= #(RetComunPs / 1000.0) pulso_ideal;
  assign ret_o   = ret_q;
  assign pulso_o = pulso_q;
  assign clk2x_o = pulso_q;
  assign toma_o  = {{N{ret_q}}, clk_i};
`else
  `ifdef SIN_KEEP
  wire [N:0] d;
  `else
  (* keep *) wire [N:0] d;
  `endif
  assign d[0]   = clk_i;
  assign toma_o = d;

  genvar i;
  generate
    for (i = 0; i < N; i = i + 1) begin : g_ret
  `ifdef CADENA_RTL
      assign d[i + 1] = d[i];
  `else
      if (Modo == 0) begin : g_buf
    `ifndef SIN_KEEP
        (* keep *)
    `endif
        SB_LUT4 #(.LUT_INIT(16'hAAAA)) u_buf (
          .O(d[i + 1]), .I0(d[i]), .I1(1'b0), .I2(1'b0), .I3(1'b0));
      end else begin : g_buf
        // Etapas pares: AND de las cuatro entradas. Impares: OR.
    `ifndef SIN_KEEP
        (* keep *)
    `endif
        SB_LUT4 #(.LUT_INIT((i % 2) ? 16'hFFFE : 16'h8000)) u_buf (
          .O(d[i + 1]), .I0(d[i]), .I1(d[i]), .I2(d[i]), .I3(d[i]));
      end
  `endif
    end
  endgenerate

  assign ret_o = d[N];

  // XOR del reloj con su copia retardada
  `ifdef CADENA_RTL
  assign pulso_o = clk_i ^ d[N];
  `else
    `ifndef SIN_KEEP
  (* keep *)
    `endif
  SB_LUT4 #(.LUT_INIT(16'h6666)) u_xor (
    .O(pulso_o), .I0(clk_i), .I1(d[N]), .I2(1'b0), .I3(1'b0));
  `endif

  // Buffer global: el reloj doblado se reparte por una de las 8 redes
  // globales, igual que un reloj que entra por un pin.
  SB_GB u_gb (
    .USER_SIGNAL_TO_GLOBAL_BUFFER (pulso_o),
    .GLOBAL_BUFFER_OUTPUT         (clk2x_o)
  );
`endif

endmodule
