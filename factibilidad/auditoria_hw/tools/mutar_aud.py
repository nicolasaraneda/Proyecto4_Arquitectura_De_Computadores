#!/usr/bin/env python3
"""mutar_aud.py: copias del RTL auditado con un error puesto a propósito.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    mutar_aud.py --tabla              nombre | área | archivo | descripción
    mutar_aud.py NOMBRE CARPETA       escribe en CARPETA las copias de
                                      espino_barrel_core.v, pochoco_soc.v,
                                      tabla_mmio.v, tabla_ram.v (i_integrado),
                                      vigilante.v (e_warmboot) y xd_opa.v
                                      (d_isa), con esa mutación en una de ellas
    mutar_aud.py referencia CARPETA   las mismas copias sin mutar

Las mutaciones de esta lista son distintas de las 18 de
factibilidad/i_integrado/tools/mutar.py: sirven para ver si las pruebas de la
pieza detectan errores que quien las escribió no tenía en mente. Cada una es
un reemplazo de texto que tiene que aparecer exactamente una vez. Ningún
archivo original se toca.
"""
import sys
from pathlib import Path

FACT = Path(__file__).resolve().parent.parent.parent
ORIGEN = {
    "espino_barrel_core.v": FACT / "i_integrado/rtl/espino_barrel_core.v",
    "pochoco_soc.v": FACT / "i_integrado/rtl/pochoco_soc.v",
    "tabla_mmio.v": FACT / "i_integrado/rtl/tabla_mmio.v",
    "tabla_ram.v": FACT / "i_integrado/rtl/tabla_ram.v",
    "vigilante.v": FACT / "e_warmboot/rtl/vigilante.v",
    "xd_opa.v": FACT / "d_isa/rtl/xd_opa.v",
}
CORE, SOC, VIG, OPA = "espino_barrel_core.v", "pochoco_soc.v", "vigilante.v", "xd_opa.v"

# nombre: (área, archivo, descripción, texto original, texto mutado)
MUTACIONES = {
    "opa_con_rs2": ("isa", CORE,
        "el operando desplazado de emad, devk y mulstep se calcula con rs2 en vez de rs1",
        "        .rs1_i    (rf_rdata_a),\n        .funct3_i (instr_x[14:12]),\n        .funct7_i (instr_x[31:25]),\n        .a_o      (xd_opa_a),",
        "        .rs1_i    (rf_rdata_b),\n        .funct3_i (instr_x[14:12]),\n        .funct7_i (instr_x[31:25]),\n        .a_o      (xd_opa_a),"),
    "emad_sin_decodificar": ("isa", CORE,
        "el decodificador se instancia sin emad: la instrucción queda como no reconocida",
        ".XdEmad(XdEmadKb >= 0), .XdDevk(XdDevkKb >= 0)",
        ".XdEmad(0), .XdDevk(XdDevkKb >= 0)"),
    "anula_b_siempre": ("isa", CORE,
        "el operando B se anula en todas las instrucciones que usan el operando desplazado, no solo en mulstep con rs1[31] = 0",
        "  wire mul_anula = (XdOpa != 0) & (alu_op_a_sel_x == OP_A_XD) & xd_opa_b_cero;",
        "  wire mul_anula = (XdOpa != 0) & (alu_op_a_sel_x == OP_A_XD);"),
    "carriles_pegados": ("isa", CORE,
        "el corte de acarreos de los carriles no se suelta: después de una instrucción de carriles de cualquier hilo, las sumas de todos quedan cortadas cada 8 bits",
        "    lane_op_x      <= lane_op_d;",
        "    lane_op_x      <= lane_op_x | lane_op_d;"),
    "k_de_otro_hilo": ("isa", CORE,
        "xd_opa recibe el funct7 (el k del desplazamiento) de la instrucción que sale de la memoria, que es de otro hilo",
        "        .funct3_i (instr_x[14:12]),\n        .funct7_i (instr_x[31:25]),\n        .a_o      (xd_opa_a),",
        "        .funct3_i (instr_x[14:12]),\n        .funct7_i (instr_rdata_i[31:25]),\n        .a_o      (xd_opa_a),"),
    "mulstep_bit_30": ("isa", OPA,
        "mulstep decide si suma con rs1[30] en vez de rs1[31] (error dentro de xd_opa, visto desde la integración)",
        "  assign b_cero_o = (MULSTEP != 0) && (funct3_i == 3'b010) && ~rs1_i[31];",
        "  assign b_cero_o = (MULSTEP != 0) && (funct3_i == 3'b010) && ~rs1_i[30];"),
    "vig_cuenta_cs": ("vigilante", SOC,
        "el vigilante cuenta ciclos con CS_n en bajo en vez de precios completos",
        "        .precio_i      (spi_precio),",
        "        .precio_i      (spi_cs_activo),"),
    "vig_un_precio_tarde": ("vigilante", VIG,
        "el disparo ocurre con un precio más de los debidos (cuenta N + 2)",
        "  wire lleno = (sin_resp == N + 1);",
        "  wire lleno = (sin_resp == N + 2);"),
    "vig_boot_sin_enganche": ("vigilante", VIG,
        "BOOT no queda enganchado: baja cuando CS_n vuelve a bajar",
        "      if ((lleno | forzar_i) & ~cs_activo_i) boot_q <= 1'b1;",
        "      boot_q <= (lleno | forzar_i) & ~cs_activo_i;"),
    "vig_mismo_ciclo": ("vigilante", VIG,
        "si un precio llega en el mismo ciclo que una escritura en DECISION, la cuenta queda en 0 y ese precio no se cuenta",
        "        if (decision_wr_i) sin_resp <= {{(W-1){1'b0}}, 1'b1};",
        "        if (decision_wr_i) sin_resp <= {W{1'b0}};"),
    "warmboot_pines": ("vigilante", SOC,
        "S1 y S0 llegan cruzados a la primitiva SB_WARMBOOT: la FPGA cargaría la imagen 2 en vez de la 1",
        "        .S1   (sel[1]),\n        .S0   (sel[0])",
        "        .S1   (sel[0]),\n        .S0   (sel[1])"),
    "warmboot_sin_boot": ("vigilante", SOC,
        "la entrada BOOT de la primitiva queda en 0: el vigilante dispara y la FPGA no se reconfigura",
        "        .BOOT (boot),",
        "        .BOOT (1'b0),"),
}


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--tabla":
        for n, (area, arch, desc, _, _) in MUTACIONES.items():
            print(f"{n}|{area}|{arch}|{desc}")
        return
    if len(sys.argv) != 3 or (sys.argv[1] not in MUTACIONES and sys.argv[1] != "referencia"):
        sys.exit(__doc__)
    nombre, destino = sys.argv[1], Path(sys.argv[2])
    _, arch, desc, viejo, nuevo = MUTACIONES.get(nombre, ("", None, "sin mutación", "", ""))
    destino.mkdir(parents=True, exist_ok=True)
    for f, origen in ORIGEN.items():
        texto = origen.read_text(encoding="utf-8")
        if f == arch:
            if texto.count(viejo) != 1:
                sys.exit(f"mutar_aud.py: el texto de la mutación {nombre} aparece {texto.count(viejo)} veces en {f}")
            texto = texto.replace(viejo, nuevo)
        (destino / f).write_text(texto, encoding="utf-8", newline="\n")
    print(f"{nombre}: {desc} ({arch})")


if __name__ == "__main__":
    main()
