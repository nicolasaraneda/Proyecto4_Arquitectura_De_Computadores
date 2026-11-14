# fijar_cadena.py: fija la ubicación de la cadena de retardo en nextpnr.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se pasa a nextpnr con --pre-pack. Pone el atributo BEL en cada LUT de la
# cadena del duplicador (celdas "...g_ret[i].g_buf.u_buf" en
# duplicador_reloj y "g_ret[i].u_buf" en placa_x2, más "...u_xor"): 8 LUT
# por bloque lógico, partiendo de la columna X y la fila Y, y subiendo de
# fila. El XOR queda en la celda que sigue a la última LUT de la cadena. El
# empaquetador de nextpnr copia el atributo a la celda lógica y el colocador
# no la mueve.
#
# Si el diseño tiene además el oscilador en anillo de placa_x2 (celdas
# "u_ani_nand" y "g_ani[i].u_buf"), lo fija de la misma forma en otra
# columna.
#
# La posición se elige con variables de entorno:
#   CADENA_X, CADENA_Y   bloque lógico de partida de la cadena (por defecto 1
#                        y 8, al lado del pin del reloj, que está en X0/Y8)
#   ANILLO_X, ANILLO_Y   bloque lógico de partida del anillo (por defecto 6 y 9)
# Columnas válidas en la HX1K: 1, 2, 4 a 9, 11 y 12 (la 3 y la 10 son BRAM).
import os
import re

_x = int(os.environ.get("CADENA_X", "1"))
_y = int(os.environ.get("CADENA_Y", "8"))
_ax = int(os.environ.get("ANILLO_X", "6"))
_ay = int(os.environ.get("ANILLO_Y", "9"))

_cadena = {}
_anillo = {}
_xor = None
_nand = None
for _nombre, _celda in ctx.cells:
    _m = re.search(r"(^|\.)g_ret\[(\d+)\]\.(g_buf\.)?u_buf$", _nombre)
    _a = re.search(r"(^|\.)g_ani\[(\d+)\]\.u_buf$", _nombre)
    if _m:
        _cadena[int(_m.group(2))] = _celda
    elif _a:
        _anillo[int(_a.group(2))] = _celda
    elif _nombre.endswith("u_ani_nand"):
        _nand = _celda
    elif _nombre.endswith("u_xor"):
        _xor = _celda


def _fijar(celdas, x, y):
    for _i, _celda in enumerate(celdas):
        _celda.setAttr("BEL", "X%d/Y%d/lc%d" % (x, y + _i // 8, _i % 8))


_orden = [_cadena[i] for i in sorted(_cadena)]
if _xor is not None:
    _orden.append(_xor)
_fijar(_orden, _x, _y)
print("fijar_cadena: %d celdas de la cadena fijadas desde X%d/Y%d" % (len(_orden), _x, _y))

_orden_a = ([_nand] if _nand is not None else []) + [_anillo[i] for i in sorted(_anillo)]
if _orden_a:
    _fijar(_orden_a, _ax, _ay)
    print("fijar_cadena: %d celdas del anillo fijadas desde X%d/Y%d" % (len(_orden_a), _ax, _ay))
