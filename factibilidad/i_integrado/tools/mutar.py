#!/usr/bin/env python3
"""mutar.py: copias del RTL del diseño integrado con un error puesto a propósito.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 mutar.py --lista                 nombres de las mutaciones
    python3 mutar.py --tabla                 nombre, archivo y descripción
    python3 mutar.py NOMBRE CARPETA          escribe en CARPETA las copias de
                                             espino_barrel_core.v, pochoco_soc.v,
                                             tabla_mmio.v y tabla_ram.v con esa
                                             mutación

Es el método de factibilidad/a_barrel/tools/mutar.py. Cada mutación es un
reemplazo de texto en uno de los cuatro archivos propios de esta carpeta
(rtl/). El texto original tiene que aparecer exactamente una vez: si el RTL
cambia y deja de aparecer, el script falla en vez de entregar una copia sin
mutar. Los archivos de rtl/ no se tocan. Lo usa tools/mutaciones.sh.

Todas las mutaciones son de lo que este estudio agregó: la integración de la
extensión en la etapa X del barrel, la conexión del vigilante y la memoria de
la tabla. Las del barrel mismo están en el estudio del barrel (21 de 21).
"""
import sys
from pathlib import Path

RTL = Path(__file__).resolve().parent.parent / "rtl"
CORE, SOC, TMM, TRAM = "espino_barrel_core.v", "pochoco_soc.v", "tabla_mmio.v", "tabla_ram.v"

# nombre: (archivo, descripción, texto original, texto mutado)
MUTACIONES = {
    "f3_otro_hilo": (CORE,
        "xd_opa recibe el funct3 de la instruccion que sale de la memoria (etapa R, otro hilo) y no el de la que esta en X",
        "        .rs1_i    (rf_rdata_a),\n        .funct3_i (instr_x[14:12]),\n        .funct7_i (instr_x[31:25]),\n        .a_o      (xd_opa_a),",
        "        .rs1_i    (rf_rdata_a),\n        .funct3_i (instr_rdata_i[14:12]),\n        .funct7_i (instr_x[31:25]),\n        .a_o      (xd_opa_a),"),
    "sin_anular_b": (CORE,
        "mulstep no anula el operando B cuando rs1[31] = 0",
        "  wire mul_anula = (XdOpa != 0) & (alu_op_a_sel_x == OP_A_XD) & xd_opa_b_cero;",
        "  wire mul_anula = 1'b0;"),
    "anula_sin_seleccion": (CORE,
        "El operando B se anula sin mirar si la instruccion es de la extension: afecta a slti, slt, lw y sw (funct3 = 010) con rs1[31] = 0",
        "  wire mul_anula = (XdOpa != 0) & (alu_op_a_sel_x == OP_A_XD) & xd_opa_b_cero;",
        "  wire mul_anula = (XdOpa != 0) & xd_opa_b_cero;"),
    "opa_sin_conectar": (CORE,
        "La seleccion 3 del operando A entrega rs1 sin desplazar",
        "      OP_A_XD:   operand_a = (XdOpa != 0) ? xd_opa_a : rf_rdata_a;",
        "      OP_A_XD:   operand_a = rf_rdata_a;"),
    "lane_op_otro_hilo": (CORE,
        "La ALU corta los acarreos segun la instruccion que esta en R (otro hilo): rompe las sumas de RV32E de los demas hilos",
        "        .lane_op_i    (lane_op_x),",
        "        .lane_op_i    (lane_op_d),"),
    "is_xd_otro_hilo": (CORE,
        "El resultado de xd_unit se elige con la marca de la instruccion que esta en R (otro hilo)",
        "  wire [31:0] ex_result = is_xd_x ? xd_result : alu_result;",
        "  wire [31:0] ex_result = is_xd_d ? xd_result : alu_result;"),
    "xd_operandos": (CORE,
        "xd_unit recibe rs1 en lugar de rs2",
        "        .rs2_i    (rf_rdata_b),",
        "        .rs2_i    (rf_rdata_a),"),
    "enlace_sin_pc4": (CORE,
        "El registro entre X y M guarda siempre el resultado de la etapa X: jal y jalr escriben el resultado de la ALU en vez del enlace",
        "    res_m      <= (rf_wd_sel_x == WD_PC4) ? pc_plus_4 : ex_result;",
        "    res_m      <= ex_result;"),
    "vig_sin_latido": (SOC,
        "El vigilante no ve las escrituras en DECISION: dispara con el programa sano",
        "        .decision_wr_i (spi_decision_wr),",
        "        .decision_wr_i (1'b0),"),
    "vig_cualquier_store": (SOC,
        "El vigilante toma cualquier escritura al bus, de cualquier hilo, como respuesta: no dispara si los otros hilos siguen vivos",
        "        .decision_wr_i (spi_decision_wr),",
        "        .decision_wr_i (data_req & data_we),"),
    "vig_sin_cs": (SOC,
        "El vigilante no espera a que CS_n suba para disparar",
        "        .cs_activo_i   (spi_cs_activo),",
        "        .cs_activo_i   (1'b0),"),
    "tabla_sin_seleccion": (SOC,
        "Todo acceso al bus llega a la memoria de la tabla",
        "  assign tab_req   = data_req &  tab_sel;",
        "  assign tab_req   = data_req;"),
    "tabla_mux": (SOC,
        "El multiplexor de lectura nunca elige la tabla",
        "      rd_is_tab <= tab_sel;",
        "      rd_is_tab <= 1'b0;"),
    "tabla_y_perifericos": (SOC,
        "Un acceso a la tabla por MMIO tambien selecciona los perifericos (forma 1)",
        "  assign per_sel  = is_mmio & ~data_addr[16] & ~tab_mmio;",
        "  assign per_sel  = is_mmio & ~data_addr[16];"),
    "tabla_alias": (SOC,
        "Una escritura en las 512 palabras nuevas tambien escribe la memoria de programa (forma 2)",
        "  assign ram_b_req = data_req & ~is_mmio & ~tab_ram;",
        "  assign ram_b_req = data_req & ~is_mmio;"),
    "tabla_indice": (SOC,
        "La tabla por MMIO se direcciona con los bits 8 a 1 en vez de 9 a 2 (forma 1)",
        "        .idx_i   (data_addr[9:2]),",
        "        .idx_i   (data_addr[8:1]),"),
    "tabla_byte_alto": (TMM,
        "tabla_mmio escribe el byte alto con la habilitacion del byte bajo",
        "      if (be_i[1]) mem[idx_i][15:8] <= wdata_i[15:8];",
        "      if (be_i[0]) mem[idx_i][15:8] <= wdata_i[15:8];"),
    "tabla_ram_byte": (TRAM,
        "tabla_ram escribe el byte 1 con el dato del byte 0",
        "      if (be_i[1]) mem[idx_i][15:8]  <= wdata_i[15:8];",
        "      if (be_i[1]) mem[idx_i][15:8]  <= wdata_i[7:0];"),
}


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--lista":
        print("\n".join(MUTACIONES))
        return
    if len(sys.argv) == 2 and sys.argv[1] == "--tabla":
        for n, (arch, desc, _, _) in MUTACIONES.items():
            print(f"{n}|{arch}|{desc}")
        return
    if len(sys.argv) != 3 or (sys.argv[1] not in MUTACIONES and sys.argv[1] != "referencia"):
        sys.exit(__doc__)
    nombre, destino = sys.argv[1], Path(sys.argv[2])
    arch, desc, viejo, nuevo = MUTACIONES.get(nombre, (None, "sin mutacion", "", ""))
    destino.mkdir(parents=True, exist_ok=True)
    for f in (CORE, SOC, TMM, TRAM):
        texto = (RTL / f).read_text(encoding="utf-8")
        if f == arch:
            if texto.count(viejo) != 1:
                sys.exit(f"mutar.py: el texto de la mutacion {nombre} aparece {texto.count(viejo)} veces en {f}")
            texto = texto.replace(viejo, nuevo)
        (destino / f).write_text(texto, encoding="utf-8", newline="\n")
    print(f"{nombre}: {desc} ({arch})")


if __name__ == "__main__":
    main()
