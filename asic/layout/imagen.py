#!/usr/bin/env python3
"""Imagen del layout final del macro ASIC del barrel, con los bloques coloreados.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Adaptado de asic/layout/anotar.py de nuestro Proyecto 3 (lectura del DEF con los LEF
del PDK y el lienzo de KLayout). La diferencia: el netlist del barrel sale aplanado
y las celdas tienen nombres genéricos (_12345_), así que el bloque de cada celda se
saca del nombre jerárquico de la red que maneja su salida (Q, Z o ZN). Así se ven
los flip-flops de cada bloque y la lógica que los alimenta directamente; el resto de
la lógica combinacional queda en gris.

Corre dentro de la imagen de Docker de LibreLane (klayout con su módulo de Python),
desde la raíz del repositorio:
    asic/layout/imagen.sh asic/runs/barrel_xd3_t40
Escribe asic/mediciones/<tag>/layout.png y layout_bloques.txt (celdas y área por bloque).
"""
import os
import re
import sys

import pya


def _param(nombre, defecto=None):
    g = globals()
    if nombre in g and isinstance(g[nombre], str):
        return g[nombre]
    return defecto


RUN = (_param("run") or "").rstrip("/")
if not RUN:
    print("falta -rd run=asic/runs/<tag>")
    sys.exit(1)
TAG = os.path.basename(RUN)
OUT = _param("out", os.path.join("asic", "mediciones", TAG))
PDK_ROOT = os.environ["PDK_ROOT"]
PDK = "gf180mcuD"
SCL = "gf180mcu_fd_sc_mcu7t5v0"
ANCHO_PX = int(_param("ancho", "2400"))
os.makedirs(OUT, exist_ok=True)

# (prefijo de la red de salida, etiqueta, color). El primero que calza gana.
BLOQUES = [
    ("u_soc.u_core.u_rf.", "BANCO DE REGISTROS, 4 CONTEXTOS (U_RF)", 0x1f77b4),
    ("u_soc.u_core.g_xd", "EXTENSION EMAD Y DEVK (G_XD)", 0xd62728),
    ("u_soc.u_core.", "RESTO DEL CORE: PC, ETAPAS (U_CORE)", 0xff7f0e),
    ("u_soc.u_ram.", "RAM DE DATOS EN FLIP-FLOPS (U_RAM)", 0x2ca02c),
    ("u_soc.u_spi.", "ESCLAVO SPI (U_SPI)", 0x9467bd),
    ("u_soc.u_periph.", "PERIFERICO DE LA PLACA (U_PERIPH)", 0x8c564b),
]
GRIS_CELDA = 0xc8c8c8
GRIS_FILL = 0xf0f0f0
GRIS_TEXTO = 0x303030
SALIDAS = ("Q", "Z", "ZN", "CO", "S")


def archivo_def():
    d = os.path.join(RUN, "final", "def")
    return os.path.join(d, next(f for f in os.listdir(d) if f.endswith(".def")))


def cargar_def(deff):
    base = os.path.join(PDK_ROOT, PDK)
    tech = pya.Technology()
    tech.load(os.path.join(base, "libs.tech/klayout/tech/gf180mcu.lyt"))
    lo = tech.load_layout_options
    cfg = lo.lefdef_config
    cfg.map_file = os.path.join(base, "libs.tech/klayout/tech/gf180mcu.map")
    cfg.macro_resolution_mode = 1
    cfg.read_lef_with_def = False
    cfg.lef_files = [os.path.join(base, f"libs.ref/{SCL}/techlef/{SCL}__nom.tlef"),
                     os.path.join(base, f"libs.ref/{SCL}/lef/{SCL}.lef")]
    with open(deff) as f:
        for linea in f:
            m = re.match(r"\s*UNITS DISTANCE MICRONS (\d+)", linea)
            if m:
                cfg.dbu = 1.0 / int(m.group(1))
                break
    layout = pya.Layout()
    layout.read(deff, lo)
    return layout


def leer_texto(deff):
    """DIEAREA y, para cada instancia, la red con nombre que maneja su salida."""
    texto = open(deff).read()
    u = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", texto).group(1))
    m = re.search(r"DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", texto)
    die = pya.DBox(*(int(m.group(i)) / u for i in range(1, 5)))
    salida = {}
    nets = re.search(r"\nNETS \d+ ;\n(.*?)\nEND NETS", texto, re.S).group(1)
    for net in re.split(r"\n\s*- ", "\n" + nets)[1:]:
        nombre = net.split()[0].replace("\\", "")
        if not nombre.startswith("u_soc."):
            continue
        for inst, pin in re.findall(r"\( (\S+) (\S+) \)", net):
            if pin in SALIDAS:
                salida[inst.replace("\\", "")] = nombre
    return die, salida


def instancias(layout):
    out = []
    for inst in layout.top_cell().each_inst():
        if inst.prop_id == 0:
            continue
        nombre = None
        for k, v in layout.properties(inst.prop_id):
            if str(k) == "1" or k == 1:
                nombre = v
        if nombre is not None:
            out.append((str(nombre).replace("\\", ""), inst.cell.name, inst.dbbox()))
    return out


def es_fill(celda):
    return any(s in celda for s in ("__fill", "__filltie", "__endcap", "__fillcap"))


class Lienzo:
    def __init__(self, dbu):
        self.layout = pya.Layout()
        self.layout.dbu = dbu
        self.top = self.layout.create_cell("figura")
        self.capas = []
        self.tg = pya.TextGenerator.default_generator()

    def capa(self, color):
        idx = self.layout.layer(len(self.capas) + 1, 0)
        self.capas.append((idx, color))
        return idx

    def caja(self, capa, dbox):
        self.top.shapes(capa).insert(pya.DBox(dbox))

    def anillo(self, capa, dbox, grosor):
        ext = pya.Region(pya.DBox(dbox).enlarged(grosor, grosor).to_itype(self.layout.dbu))
        inte = pya.Region(pya.DBox(dbox).to_itype(self.layout.dbu))
        self.top.shapes(capa).insert(ext - inte)

    def texto(self, capa, s, x, y, alto):
        reg = self.tg.text(s, self.layout.dbu, alto / 0.7)
        reg.move(int(x / self.layout.dbu), int(y / self.layout.dbu))
        self.top.shapes(capa).insert(reg)

    def guardar(self, path, caja, ancho_px):
        lv = pya.LayoutView()
        lv.set_config("background-color", "#ffffff")
        lv.set_config("grid-visible", "false")
        lv.set_config("text-visible", "false")
        lv.show_layout(self.layout, False)
        lv.clear_layers()
        for idx, color in self.capas:
            lp = pya.LayerPropertiesNode()
            info = self.layout.get_info(idx)
            lp.source = f"{info.layer}/{info.datatype}@1"
            lp.fill_color = color
            lp.frame_color = color
            lp.dither_pattern = 0
            lp.width = 1
            lp.transparent = False
            lv.insert_layer(lv.end_layers(), lp)
        lv.max_hier()
        alto_px = int(ancho_px * caja.height() / caja.width())
        lv.zoom_box(caja)
        lv.save_image_with_options(path, ancho_px, alto_px, 0, 1, 0, caja, False)
        print(f"escrito {path} ({ancho_px}x{alto_px})")


def main():
    deff = archivo_def()
    layout = cargar_def(deff)
    die, salida = leer_texto(deff)
    insts = instancias(layout)
    lz = Lienzo(layout.dbu)
    c_fill = lz.capa(GRIS_FILL)
    c_cel = lz.capa(GRIS_CELDA)
    c_bl = [lz.capa(color) for _, _, color in BLOQUES]
    c_txt = lz.capa(GRIS_TEXTO)
    n = [0] * len(BLOQUES)
    area = [0.0] * len(BLOQUES)
    area_logica = 0.0
    for nombre, celda, box in insts:
        if es_fill(celda) or "__tap" in celda:
            lz.caja(c_fill, box)
            continue
        area_logica += box.area()
        red = salida.get(nombre, "")
        for i, (prefijo, _, _) in enumerate(BLOQUES):
            if red.startswith(prefijo):
                lz.caja(c_bl[i], box)
                n[i] += 1
                area[i] += box.area()
                break
        else:
            lz.caja(c_cel, box)
    lz.anillo(c_txt, die, 2.0)
    # leyenda a la derecha del dado
    alto = 14.0
    x = die.right + 60
    y = die.top - 30
    lz.texto(c_txt, f"{TAG.upper()}: CELDAS POR BLOQUE (RED DE SALIDA)", x, y, alto + 4)
    y -= 3 * alto
    filas = []
    for i, (prefijo, etiqueta, color) in enumerate(BLOQUES):
        lz.caja(c_bl[i], pya.DBox(x, y, x + 2 * alto, y + alto))
        pct = 100 * area[i] / area_logica if area_logica else 0
        lz.texto(c_txt, f"{etiqueta}: {n[i]} CELDAS, {pct:.1f} %", x + 3 * alto, y, alto)
        filas.append(f"{prefijo:20s} {etiqueta:45s} {n[i]:6d} celdas {area[i]:12.1f} um2 {pct:5.1f} %")
        y -= 2.2 * alto
    lz.caja(c_cel, pya.DBox(x, y, x + 2 * alto, y + alto))
    lz.texto(c_txt, "RESTO DE LA LOGICA (ROM, DECODIFICACION, ALU)", x + 3 * alto, y, alto)
    y -= 2.2 * alto
    lz.caja(c_fill, pya.DBox(x, y, x + 2 * alto, y + alto))
    lz.texto(c_txt, "RELLENO Y TAPS", x + 3 * alto, y, alto)
    y -= 3 * alto
    lz.caja(c_txt, pya.DBox(x, y, x + 200, y + 4))
    lz.texto(c_txt, "200 UM", x + 70, y + 10, alto)
    caja = pya.DBox(die.left - 20, die.bottom - 20, die.right + 1100, die.top + 20)
    lz.guardar(os.path.join(OUT, "layout.png"), caja, ANCHO_PX)
    with open(os.path.join(OUT, "layout_bloques.txt"), "w") as f:
        f.write(f"Celdas por bloque en {RUN}, segun la red de salida (asic/layout/imagen.py)\n")
        f.write(f"Area de celdas logicas (sin relleno ni taps): {area_logica:.1f} um2; dado {die.width():.1f} x {die.height():.1f} um\n")
        f.write("\n".join(filas) + "\n")
    print("\n".join(filas))


main()
