#!/usr/bin/env python3
"""casos_tb.py: casos del testbench del duplicador, a partir de una medición.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee el JSON de scripts/sta_icestorm.py de un diseño con duplicador y escribe
una línea por caso: nombre, resultado esperado, semiperíodo alto y bajo
efectivos, retardo de la cadena para el flanco de subida y de bajada, y
retardo común, todo en picosegundos. El semiperíodo efectivo incluye la
diferencia de latencia entre el flanco de bajada y el de subida.

Uso: casos_tb.py STA.json [PERIODO_PS]
"""
import json
import sys


def main():
    sta = json.load(open(sys.argv[1]))
    T = int(sys.argv[2]) if len(sys.argv) > 2 else 40000
    esq = sta["reloj"][0]["esquinas"]
    for cn in ("min", "tip", "max"):
        e = esq[cn]
        a = e["baja"]["latencia_ps"] - e["sube"]["latencia_ps"]
        for duty in (45, 50, 55):
            alto = round(T * duty / 100 + a)
            bajo = T - alto
            print("%s_duty%d PASS %d %d %d %d %d" % (
                cn, duty, alto, bajo, round(e["sube"]["ancho_ps"]), round(e["baja"]["ancho_ps"]),
                round(e["sube"]["latencia_ps"])))
    # Controles negativos
    print("control_cadena_larga FAIL %d %d %d %d %d" % (T // 2, T // 2, T // 2 + 500, T // 2 + 500, 2000))
    print("control_cadena_corta FAIL %d %d %d %d %d" % (T // 2, T // 2, 300, 300, 2000))


if __name__ == "__main__":
    main()
