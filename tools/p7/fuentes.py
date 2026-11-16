"""fuentes.py: de cada dirección del programa a su línea de assembly y a su fase.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El perfil del gemelo (build/gemelo --perfil) cuenta instrucciones y ciclos por
dirección. Para decir en qué parte del tick se van los ciclos hay que saber qué
línea del .s está en cada dirección y a qué fase pertenece. Este módulo
ensambla el programa con tools/pochoasm.py (el mismo ensamblador, sin copiar
nada) y anota la dirección de cada instrucción. Las fases salen del programa,
no se escriben a mano:

  - sw/trade.s y sw/xd/trade_xd.s tienen la misma forma. Se recorre el lazo
    principal desde la etiqueta `esperar`: las tres instrucciones del sondeo,
    la lectura de PRICE, el cálculo de dev (hasta la instrucción que escribe
    x6 con sub o devk), la decisión (hasta el store a DECISION), el store, la
    actualización de la media S y el salto de vuelta.
  - sw/fondo.s está dividido en secciones con comentarios numerados ("# --- 1.
    Esperar el precio" en el supervisor, "# 1. Esperar el tick siguiente" en
    la rutina de los gestores). La fase es la de la última sección vista.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "tools", "asm"))
import core  # noqa: E402

# Fases del kernel de max_media, en el orden del tick
FASES_TRADE = ["esperar", "leer", "media_dev", "decidir", "escribir", "media_s", "volver"]
NOMBRE_FASE = {
    "esperar": "esperar el precio (sondeo de STATUS)",
    "leer": "leer PRICE",
    "media_dev": "media: dev = 32 p - S",
    "decidir": "decidir y armar el byte",
    "escribir": "escribir DECISION",
    "media_s": "media: S = S + (dev >>> 5)",
    "volver": "volver al sondeo (j)",
    "arranque": "arranque y primer precio",
}


class _Anotador(core.Assembler):
    """El ensamblador del repositorio, que además anota dirección y línea."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.lineas = {}

    def _encode_instruction(self, ln, address, symtab):
        palabras = super()._encode_instruction(ln, address, symtab)
        for i in range(len(palabras)):
            self.lineas[address + 4 * i] = ln
        self.simbolos = symtab
        return palabras


def mapa(ruta):
    """{dirección: (número de línea, nombre, operandos, texto)} y la tabla de símbolos."""
    texto = open(ruta, encoding="utf-8").read()
    a = _Anotador()
    a.assemble(texto)
    m = {d: (ln.lineno, ln.name, [o.lower() for o in ln.operands], ln.raw.strip()) for d, ln in a.lineas.items()}
    return m, a.simbolos


def fases_trade(ruta):
    """Fase de cada dirección de un programa con la forma de sw/trade.s."""
    m, sim = mapa(ruta)
    ini = sim["esperar"]
    fase = {d: "arranque" for d in m}
    estado = "esperar"
    n_sondeo = 0
    d = ini
    while d in m:
        _, nom, ops, _ = m[d]
        if estado == "esperar":
            fase[d] = "esperar"
            n_sondeo += 1
            if n_sondeo == 3:
                estado = "leer"
        elif estado == "leer":
            if not (nom == "lw" and "off_price" in ops[1]):
                raise ValueError(f"{ruta}: se esperaba la lectura de PRICE en {d:#x}")
            fase[d] = "leer"
            estado = "media_dev"
        elif estado == "media_dev":
            fase[d] = "media_dev"
            if nom in ("sub", "devk") and ops[0] == "x6":
                estado = "decidir"
        elif estado == "decidir":
            if nom == "sw" and "off_decision" in ops[1]:
                fase[d] = "escribir"
                estado = "media_s"
            else:
                fase[d] = "decidir"
        elif estado == "media_s":
            if nom == "j" and ops[0] == "esperar":
                fase[d] = "volver"
                break
            fase[d] = "media_s"
        d += 4
    if estado != "media_s":
        raise ValueError(f"{ruta}: no se encontró el lazo principal completo")
    return fase, m


# Secciones de sw/fondo.s: el texto del comentario manda la fase
SECCIONES_FONDO = [
    (r"^# --- Tabla de arranque", "arranque"),
    (r"^supervisor:", "arranque"),
    (r"^# --- 1\. Esperar", "esperar"),
    (r"^# --- 2\. Publicar", "publicar"),
    (r"^# --- 3\. max_media", "regla"),
    (r"^# --- 4\. Recoger", "votos"),
    (r"^# --- 5\. Reparto", "pesos"),
    (r"^# --- 6\. Voto", "voto"),
    (r"^# --- 7\. Telemetr", "telemetria"),
    (r"^# --- Frontera", "pesos"),
    (r"^hilo1:", "arranque"),
    (r"^# --- Rutina", "arranque"),
    (r"^# Primer precio", "arranque"),
    (r"^# 1\. Esperar", "esperar"),
    (r"^# 2\. Puntaje", "puntaje"),
    (r"^# 3\. Regla", "regla"),
    (r"^# 4\. Publicar", "publicar_voto"),
    (r"^# 5\. Actualizar", "regla"),
]
NOMBRE_FASE_FONDO = {
    "arranque": "arranque y primer precio",
    "esperar": "esperar (supervisor: STATUS; gestores: PUB)",
    "leer": "leer PRICE",
    "publicar": "publicar precio y tick (PUB)",
    "regla": "regla max_media (dev, decisión y media)",
    "votos": "recoger los votos (espera a los gestores)",
    "pesos": "ajuste de pesos (frontera de ventana)",
    "voto": "voto ponderado y byte",
    "escribir": "escribir DECISION",
    "telemetria": "telemetría",
    "puntaje": "puntaje en papel",
    "publicar_voto": "publicar puntaje y voto",
}


def fases_fondo(ruta):
    """Fase de cada dirección de sw/fondo.s, por la última sección vista."""
    m, _ = mapa(ruta)
    lineas = open(ruta, encoding="utf-8").read().splitlines()
    fase_linea = {}
    actual = "arranque"
    for i, txt in enumerate(lineas, start=1):
        for patron, f in SECCIONES_FONDO:
            if re.match(patron, txt):
                actual = f
                break
        fase_linea[i] = actual
    fase = {}
    for d, (lineno, nom, ops, _) in m.items():
        f = fase_linea[lineno]
        if nom == "lw" and len(ops) > 1 and "off_price" in ops[1]:
            f = "leer"
        elif nom == "sw" and len(ops) > 1 and "off_decision" in ops[1]:
            f = "escribir"
        fase[d] = f
    return fase, m


def tamano_acceso(palabra):
    """Bytes que mueve una instrucción de memoria (0 si no es load ni store)."""
    op, f3 = palabra & 0x7F, (palabra >> 12) & 7
    if op == 0x03:
        return {0: 1, 1: 2, 2: 4, 4: 1, 5: 2}.get(f3, 4)
    if op == 0x23:
        return {0: 1, 1: 2, 2: 4}.get(f3, 4)
    return 0


def clase(palabra):
    """Clase de la instrucción para el modelo de costo: alu, load, store, salto."""
    op = palabra & 0x7F
    if op == 0x03:
        return "load"
    if op == 0x23:
        return "store"
    if op in (0x63, 0x6F, 0x67):
        return "salto"
    return "alu"
