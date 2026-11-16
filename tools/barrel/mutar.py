#!/usr/bin/env python3
"""mutar.py: copias del Espino barrel con un error puesto a propósito.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 mutar.py --lista                 nombres de las mutaciones
    python3 mutar.py --tabla                 nombre, archivo y descripción
    python3 mutar.py NOMBRE CARPETA          escribe en CARPETA las copias de
                                             espino_barrel_core.v,
                                             espino_barrel_regfile.v y
                                             pochoco_soc.v con esa mutación

Cada mutación es un reemplazo de texto en uno de los tres archivos del barrel
(rtl/espino_core/espino_barrel_core.v, rtl/espino_core/espino_barrel_regfile.v
y rtl/pochoco_soc.v). El texto original tiene que aparecer exactamente una
vez: si el RTL cambia y deja de aparecer, el script falla en vez de entregar
una copia sin mutar. Los archivos de rtl/ no se tocan. Lo usa
tools/barrel/mutaciones.sh, que compila tb/barrel/tb_verif.sv con cada copia y exige
que la comparación contra el Espino base la detecte. El método viene del
tb/revision_a_mutaciones.sh de nuestro Proyecto 3.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
CORE, RF, SOC = "espino_barrel_core.v", "espino_barrel_regfile.v", "pochoco_soc.v"
ORIGEN = {CORE: RAIZ / "rtl/espino_core" / CORE, RF: RAIZ / "rtl/espino_core" / RF, SOC: RAIZ / "rtl" / SOC}

# nombre: (archivo, descripción, texto original, texto mutado)
MUTACIONES = {
    "ctx_escritura": (CORE,
        "El resultado se escribe en el contexto del hilo que esta en X, no en el del que esta en M",
        "    .waddr_i   ({tid_m, rd_m}),",
        "    .waddr_i   ({tid_x, rd_m}),"),
    "ctx_lectura_rs1": (CORE,
        "rs1 se lee del contexto del hilo que esta en F",
        "    .raddr_a_i ({tid_r, instr_rdata_i[18:15]}),",
        "    .raddr_a_i ({tid_f, instr_rdata_i[18:15]}),"),
    "ctx_lectura_rs2": (CORE,
        "rs2 se lee del contexto del hilo que esta en X",
        "    .raddr_b_i ({tid_r, instr_rdata_i[23:20]}),",
        "    .raddr_b_i ({tid_x, instr_rdata_i[23:20]}),"),
    "escritura_sin_hilo": (RF,
        "La escritura al banco ignora el numero de hilo: todos escriben el contexto 0",
        "  wire [10:0] wa = {5'b0, waddr_i};",
        "  wire [10:0] wa = {7'b0, waddr_i[3:0]};"),
    "pc_otro_hilo": (CORE,
        "El hilo que entra a F busca con el proximo contador del hilo que esta en X",
        "      pc_f_q      <= pc_m_q;",
        "      pc_f_q      <= pc_next[PcW-1:1];"),
    "enlace_otro_hilo": (CORE,
        "El enlace de jal y jalr guarda el contador del hilo que esta en F",
        "    res_m      <= (rf_wd_sel_x == WD_PC4) ? pc_plus_4 : alu_result;",
        "    res_m      <= (rf_wd_sel_x == WD_PC4) ? (pc_f + 32'd4) : alu_result;"),
    "x0": (CORE,
        "Se permite escribir x0",
        "      rf_we_m     <= rf_we_x & (instr_x[10:7] != 4'd0);",
        "      rf_we_m     <= rf_we_x;"),
    "rd_otro_hilo": (CORE,
        "El registro destino sale de la instruccion que esta en R",
        "    rd_m       <= instr_x[10:7];",
        "    rd_m       <= instr_rdata_i[10:7];"),
    "be_ram": (SOC,
        "Los bytes habilitados llegan rotados a la memoria",
        "    .b_be_i    (data_be),",
        "    .b_be_i    ({data_be[2:0], data_be[3]}),"),
    "tamano_store": (CORE,
        "El tamano del store sale de la instruccion que esta en R",
        "    .type_i       (lsu_type_x),",
        "    .type_i       (lsu_type_d),"),
    "desplazamiento_load": (CORE,
        "El dato del load se alinea con la direccion de la instruccion que esta en X",
        "    .addr_i       ({30'b0, boff_m}),",
        "    .addr_i       ({30'b0, alu_result[1:0]}),"),
    "signo_load": (CORE,
        "La extension de signo del load sale de la instruccion que esta en R",
        "    lsu_sign_m <= lsu_sign_x;",
        "    lsu_sign_m <= lsu_sign_d;"),
    "mux_lectura": (SOC,
        "El multiplexor de lectura (memoria, SPI o perifericos) elige con la direccion de la instruccion que esta en X",
        "  assign data_rdata = rd_is_per ? per_rdata :\n                      rd_is_spi ? spi_rdata :\n                      rd_is_tab ? tab_rdata : ram_b_rdata;",
        "  assign data_rdata = per_sel ? per_rdata :\n                      spi_sel ? spi_rdata :\n                      tab_sel ? tab_rdata : ram_b_rdata;"),
    "peticion_bus": (CORE,
        "La peticion al bus sale con la instruccion que esta en R",
        "  assign data_req_o = lsu_req_x;",
        "  assign data_req_o = lsu_req_d & valid_r;"),
    "burbuja_salta": (CORE,
        "La burbuja del arranque no anula el jal que quedo a la salida de la memoria",
        "      is_jal_x    <= is_jal_d    & valid_r;",
        "      is_jal_x    <= is_jal_d;"),
    "hilo_desfasado": (CORE,
        "El contador de hilos sale del reset en 1",
        "      tid_f       <= 2'd0;",
        "      tid_f       <= 2'd1;"),
    "jalr_no_salta": (CORE,
        "jalr no salta",
        "  wire           taken       = (is_branch_x & alu_cmp_result) | is_jal_x | is_jalr_x;",
        "  wire           taken       = (is_branch_x & alu_cmp_result) | is_jal_x;"),
    "dato_store": (CORE,
        "El dato del store sale de rs1 en vez de rs2",
        "    .wdata_i      (rf_rdata_b),",
        "    .wdata_i      (rf_rdata_a),"),
}


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--lista":
        print("\n".join(MUTACIONES))
        return
    if len(sys.argv) == 2 and sys.argv[1] == "--tabla":
        for n, (arch, desc, _, _) in MUTACIONES.items():
            print(f"{n}|{arch}|{desc}")
        return
    if len(sys.argv) != 3 or sys.argv[1] not in MUTACIONES:
        sys.exit(__doc__)
    nombre, destino = sys.argv[1], Path(sys.argv[2])
    arch, desc, viejo, nuevo = MUTACIONES[nombre]
    destino.mkdir(parents=True, exist_ok=True)
    for f in (CORE, RF, SOC):
        texto = ORIGEN[f].read_text(encoding="utf-8")
        if f == arch:
            if texto.count(viejo) != 1:
                sys.exit(f"mutar.py: el texto de la mutacion {nombre} aparece {texto.count(viejo)} veces en {f}")
            texto = texto.replace(viejo, nuevo)
        (destino / f).write_text(texto, encoding="utf-8", newline="\n")
    print(f"{nombre}: {desc} ({arch})")


if __name__ == "__main__":
    main()
