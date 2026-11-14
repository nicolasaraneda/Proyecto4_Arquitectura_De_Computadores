# reloj_x2.py: restricción del reloj doblado en nextpnr (--pre-pack).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El reloj doblado no entra por un pin: sale de un SB_GB dentro del diseño, y
# la red se llama "clk" en pochoco_soc. ctx.addClock fija su frecuencia por
# nombre de red. La frecuencia se pasa por la variable de entorno
# RELOJ_X2_MHZ (por defecto 50) y el nombre de la red por RELOJ_X2_RED.
# RELOJ_EXTRA permite restringir más redes: "red=MHz,red=MHz".
#
# Lo que esta restricción NO le dice a nextpnr: que los períodos alternan
# entre el semiperíodo alto y el bajo del oscilador, que el tiempo en alto es
# el retardo de la cadena y no medio período, ni la fase respecto de i_Clk.
import os

_mhz = float(os.environ.get("RELOJ_X2_MHZ", "50"))
_red = os.environ.get("RELOJ_X2_RED", "clk")
ctx.addClock(_red, _mhz)
print("reloj_x2: red '%s' restringida a %.2f MHz" % (_red, _mhz))
for _par in os.environ.get("RELOJ_EXTRA", "").split(","):
    if "=" in _par:
        _r, _f = _par.split("=")
        ctx.addClock(_r, float(_f))
        print("reloj_x2: red '%s' restringida a %.2f MHz" % (_r, float(_f)))
