// espino_xd.v: extensión de la ISA en custom-0 para el Espino barrel
// (docs/extension_isa.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Tres instrucciones de formato R en el opcode custom-0 (0001011). Las tres
// son "un desplazamiento por una constante y una suma", así que usan el
// sumador de la ALU del Espino: no agregan un sumador ni una entrada al
// multiplexor de escritura. Son combinacionales, de un ciclo y sin estado.
//
//   instrucción           funct3  funct7   resultado
//   emad rd, rs1, rs2, 5  100     0000101  rd = rs2 + (rs1 >>> 5)
//   devk rd, rs1, rs2, 5  101     0000101  rd = (rs1 << 5) - rs2
//   mulstep rd, rs1, rs2  010     0000000  rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)
//
// Cualquier otra palabra de custom-0 no es una instrucción: el decodificador
// del Espino la marca como ilegal y el core no hace nada con ella, igual que
// sin la extensión. En particular emad y devk con k distinto de 5.
//
// Este archivo tiene los dos bloques que el core instancia:
//   espino_xd_dec  etapa R. Reconoce las tres codificaciones.
//   espino_xd_opa  etapa X. Entrega el operando A desplazado y avisa cuando
//                  mulstep necesita el operando B en cero.
// El parámetro Xd de los dos es una máscara con las instrucciones presentes:
// bit 0 emad, bit 1 devk, bit 2 mulstep. Con Xd = 0 no queda lógica.
//
// Modelo de referencia: ref/xd.py. Prueba formal contra la especificación:
// formal/xd/ (make xd-formal). Testbench de los dos módulos: tb/xd/tb_xd_mod.sv.
//
// Los bloques `ifdef MUTA_XD_* son errores puestos a propósito, que solo se
// activan desde la línea de comandos para comprobar que las pruebas los
// detectan (tools/xd/mutaciones.sh). No se sintetizan nunca.

module espino_xd_dec #(
  parameter [2:0] Xd = 3'b000
) (
  input  wire [31:0] instr_i,
  output wire        emad_o,      // la instrucción es emad con k = 5
  output wire        devk_o,      // la instrucción es devk con k = 5
  output wire        mulstep_o    // la instrucción es mulstep
);

  localparam [6:0] OPCODE_CUSTOM0 = 7'h0b;
  localparam [6:0] F7_K5          = 7'b0000101;   // k = 5 en los bits 4:0

  wire        custom0 = (instr_i[6:0] == OPCODE_CUSTOM0);
  wire [2:0]  funct3  = instr_i[14:12];
  wire [6:0]  funct7  = instr_i[31:25];

`ifdef MUTA_XD_K
  // MUTACIÓN (solo para las pruebas): no se revisa k, y emad y devk con
  // cualquier k se ejecutan con k = 5.
  wire        k5 = (funct7[6:5] == 2'b00);
`else
  wire        k5 = (funct7 == F7_K5);
`endif

`ifdef MUTA_XD_F7MUL
  // MUTACIÓN (solo para las pruebas): mulstep no revisa funct7.
  wire        f7_cero = 1'b1;
`else
  wire        f7_cero = (funct7 == 7'b0);
`endif

  assign emad_o    = Xd[0] & custom0 & (funct3 == 3'b100) & k5;
  assign devk_o    = Xd[1] & custom0 & (funct3 == 3'b101) & k5;
  assign mulstep_o = Xd[2] & custom0 & (funct3 == 3'b010) & f7_cero;

  wire _unused = &{1'b0, instr_i[24:15], instr_i[11:7]};

endmodule


module espino_xd_opa #(
  parameter [2:0] Xd = 3'b000
) (
  input  wire [31:0] rs1_i,
  input  wire [2:0]  funct3_i,    // de la instrucción que está en ejecución
  output reg  [31:0] a_o,         // operando A de la ALU
  output wire        b_cero_o     // mulstep: el operando B debe valer cero
);

  // El core solo usa a_o cuando la instrucción en ejecución es una de las
  // tres, así que con funct3 basta para elegir: 100 emad, 101 devk y 010
  // mulstep. El bit 2 separa a mulstep de las otras dos y el bit 0 a emad de
  // devk. Si una instrucción no está en Xd su rama desaparece.
`ifdef MUTA_XD_SRL
  // MUTACIÓN (solo para las pruebas): el desplazamiento a la derecha es lógico.
  wire [31:0] emad_a    = {5'b0, rs1_i[31:5]};
`else
  wire [31:0] emad_a    = {{5{rs1_i[31]}}, rs1_i[31:5]};    // rs1 >>> 5
`endif
`ifdef MUTA_XD_K4
  // MUTACIÓN (solo para las pruebas): devk desplaza 4 en vez de 5.
  wire [31:0] devk_a    = {rs1_i[27:0], 4'b0};
`else
  wire [31:0] devk_a    = {rs1_i[26:0], 5'b0};              // rs1 << 5
`endif
  wire [31:0] mulstep_a = {rs1_i[30:0], 1'b0};              // rs1 << 1

  // emad o devk, según el bit 0. Con una sola de las dos no hay multiplexor.
  wire [31:0] media_a = (Xd[1:0] == 2'b11) ? (funct3_i[0] ? devk_a : emad_a) :
                        Xd[1]              ? devk_a : emad_a;
  wire        hay_media = (Xd[1:0] != 2'b00);

  always @* begin
    if (Xd[2] && hay_media) a_o = funct3_i[2] ? media_a : mulstep_a;
    else if (Xd[2])         a_o = mulstep_a;
    else                    a_o = media_a;
  end

`ifdef MUTA_XD_BCERO
  // MUTACIÓN (solo para las pruebas): mulstep suma rs2 siempre.
  assign b_cero_o = 1'b0;
`else
  assign b_cero_o = Xd[2] & (~funct3_i[2] | ~hay_media) & ~rs1_i[31];
`endif

  wire _unused = &{1'b0, funct3_i[1], emad_a, devk_a, mulstep_a};

endmodule
