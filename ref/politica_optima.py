#!/usr/bin/env python3
"""politica_optima.py: filtro de Kalman en estado estacionario y política óptima del modelo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Con el modelo ajustado en ref/generador.py (nivel lento más transitoria más
redondeo) se responden dos preguntas:

1. Cuál es el mejor estimador de la componente transitoria. Es el filtro de
   Kalman de dos estados. En estado estacionario sus ganancias son constantes
   y la actualización es un producto de una matriz de 2x2 por el vector de
   estado más una ganancia por el precio:

       [nivel']   [ 1-K1     -K1*phi   ] [nivel]   [K1]
       [trans'] = [ -K2    (1-K2)*phi  ] [trans] + [K2] * precio

   `kalman` calcula K1 y K2 iterando la ecuación de Riccati. `matriz` entrega
   la matriz con los coeficientes aproximados por sumas de potencias de dos,
   que es la forma que se puede calcular sin multiplicador.

2. Cuánto se puede ganar como máximo. Como la decisión se ejecuta un tick
   después, lo único que sirve para predecir es la transitoria estimada z. Con
   z como estado (un AR(1)) se resuelve por programación dinámica la política
   que maximiza la ganancia esperada, con comisión por orden, límite de 63
   acciones por orden y ejecución al tick siguiente. Sale una política de
   bandas: entrar bajo un umbral, salir sobre otro.

    python3 ref/politica_optima.py            # ganancias, matriz, bandas y cota de ganancia

La política óptima es una cota y una guía. Supone que el modelo es exacto y
que se conoce el régimen de volatilidad. Lo que opera en la placa es una regla
de bandas con umbrales fijos, y se evalúa con el protocolo.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibracion as cal     # noqa: E402

# Coeficientes en punto fijo del filtro (los que usa candidatos.Trader con est=1)
PHI_FIJO = 1 - 1 / 32 - 1 / 128       # 0,9609375  (ka = 5, kb = 7)
K1_FIJO = 1 / 2 + 1 / 8               # 0,625      (k1a = 1, k1b = 3)
K2_FIJO = 1 / 8 + 1 / 16              # 0,1875     (k2a = 3, k2b = 4)


def kalman(q_nivel, q_trans, phi, r=cal.R_REDONDEO, iteraciones=5000):
    """Ganancias en estado estacionario. Devuelve (K1, K2, S, P).

    S es la varianza de la innovación y P = (p11, p12, p22) la covarianza del
    error después de actualizar.
    """
    p11, p12, p22 = 1.0, 0.0, q_trans / (1 - phi * phi)
    k1 = k2 = s = 0.0
    for _ in range(iteraciones):
        p11, p12, p22 = p11 + q_nivel, phi * p12, phi * phi * p22 + q_trans
        s = p11 + 2 * p12 + p22 + r
        k1, k2 = (p11 + p12) / s, (p12 + p22) / s
        p11, p12, p22 = p11 - k1 * (p11 + p12), p12 - k1 * (p12 + p22), p22 - k2 * (p12 + p22)
    return k1, k2, s, (p11, p12, p22)


def matriz(k1=K1_FIJO, k2=K2_FIJO, phi=PHI_FIJO):
    """Matriz A de 2x2 y vector de ganancias K de la actualización x' = A x + K p."""
    return [[1 - k1, -k1 * phi], [-k2, (1 - k2) * phi]], [k1, k2]


def politica(q_nivel, q_trans, phi, precio=128.0, caja=10000.0, comision=5.0, iteraciones=400, puntos=101):
    """Programación dinámica sobre la transitoria estimada z.

    Estado: (z, acciones). Decisión: con cuántas acciones quedar, a no más de
    63 de distancia por tick. Una orden cuesta `comision`. La ganancia
    esperada de tener q acciones durante el tick siguiente a la ejecución es
    q * (-phi * (1 - phi) * z). Devuelve un diccionario con las ganancias, la
    ganancia óptima por tick (en pesos) y los umbrales de la política.
    """
    k1, k2, s, _ = kalman(q_nivel, q_trans, phi)
    sd_z = math.sqrt(k2 * k2 * s / (1 - phi * phi))
    z_max = 5 * sd_z
    dz = 2 * z_max / (puntos - 1)
    zs = [-z_max + i * dz for i in range(puntos)]
    sd_e = k2 * math.sqrt(s)
    filas = []
    for z in zs:
        pesos = [(j, math.exp(-0.5 * ((z2 - phi * z) / sd_e) ** 2)) for j, z2 in enumerate(zs)
                 if abs(z2 - phi * z) < 5 * sd_e]
        total = sum(w for _, w in pesos)
        filas.append([(j, w / total) for j, w in pesos])
    lleno = int((caja - comision) // precio)
    qs = sorted({0, min(63, lleno), lleno})
    deriva = [-phi * (1 - phi) * z for z in zs]
    valor = [[0.0] * puntos for _ in qs]
    ganancia, pol = 0.0, None
    for _ in range(iteraciones):
        esperado = [[sum(w * v[j] for j, w in filas[i]) for i in range(puntos)] for v in valor]
        nuevo, pol = [], []
        for q in qs:
            fila, eleccion = [], []
            for i in range(puntos):
                mejor, cual = -1e18, 0
                for b, q2 in enumerate(qs):
                    if abs(q2 - q) > 63:
                        continue
                    v = (0.0 if q2 == q else -comision) + q2 * deriva[i] + esperado[b][i]
                    if v > mejor + 1e-12:
                        mejor, cual = v, b
                fila.append(mejor)
                eleccion.append(cual)
            nuevo.append(fila)
            pol.append(eleccion)
        ganancia = nuevo[0][puntos // 2] - valor[0][puntos // 2]
        valor = nuevo
    # umbrales: desde 0 acciones, el mayor z en que todavía compra; desde lleno, el menor z en que vende
    compra = max((zs[i] for i in range(puntos) if pol[0][i] != 0), default=float("nan"))
    vende = min((zs[i] for i in range(puntos) if pol[-1][i] != len(qs) - 1), default=float("nan"))
    segunda = max((zs[i] for i in range(puntos) if len(qs) == 3 and pol[1][i] == 2), default=float("nan"))
    return dict(k1=k1, k2=k2, s=s, sd_z=sd_z, sd_trans=math.sqrt(q_trans / (1 - phi * phi)), acciones=qs,
                ganancia_tick=ganancia, compra=compra, segunda=segunda, vende=vende)


def main():
    print("1. Filtro de Kalman en estado estacionario (redondeo como ruido de varianza 1/12)")
    regimenes = (("tranquilo", 1.0), ("ruidoso", cal.RAZON_RUIDOSO))
    for nombre, razon in regimenes:
        k1, k2, s, p = kalman(cal.Q_NIVEL * razon, cal.Q_TRANS * razon, cal.PHI)
        print(f"   regimen {nombre:9s}: K1 = {k1:.4f}, K2 = {k2:.4f}, varianza de la innovacion {s:.3f}, "
              f"error de la transitoria {math.sqrt(p[2]):.2f} (su desviacion estandar es "
              f"{math.sqrt(cal.Q_TRANS * razon / (1 - cal.PHI ** 2)):.2f})")
    print(f"   En punto fijo: phi = 1 - 1/32 - 1/128 = {PHI_FIJO}, K1 = 1/2 + 1/8 = {K1_FIJO}, K2 = 1/8 + 1/16 = {K2_FIJO}")

    print("\n2. Actualizacion como producto de matriz 2x2 por vector: x' = A x + K p, con x = [nivel, transitoria]")
    a, k = matriz()
    print(f"   A = [[{a[0][0]:.7f}, {a[0][1]:.7f}], [{a[1][0]:.7f}, {a[1][1]:.7f}]]   K = [{k[0]}, {k[1]}]")
    print(f"   En Q8 (por 256): A = [[{round(a[0][0] * 256)}, {round(a[0][1] * 256)}], "
          f"[{round(a[1][0] * 256)}, {round(a[1][1] * 256)}]]   K = [{round(k[0] * 256)}, {round(k[1] * 256)}]")
    print("   Forma con sumas y desplazamientos (la de candidatos.Trader, estado en Q8):")
    print("      Tp = T - (T >> 5) - (T >> 7)")
    print("      e  = (p << 8) - L - Tp")
    print("      L  = L + (e >> 1) + (e >> 3)")
    print("      T  = Tp + (e >> 3) + (e >> 4)")

    print("\n3. Politica optima por programacion dinamica (precio 128, caja 10 000, comision 5, 63 acciones por orden)")
    total = 0.0
    frac = cal.DUR_RUIDOSO / (cal.DUR_TRANQUILO + cal.DUR_RUIDOSO)
    for nombre, razon in regimenes:
        r = politica(cal.Q_NIVEL * razon, cal.Q_TRANS * razon, cal.PHI)
        peso = frac if razon != 1.0 else 1 - frac
        total += peso * r["ganancia_tick"]
        print(f"   regimen {nombre:9s}: desv. est. de z {r['sd_z']:.2f}. Primera orden si z < {r['compra']:+.2f}, "
              f"segunda si z < {r['segunda']:+.2f}, vende si z > {r['vende']:+.2f}. "
              f"Ganancia optima {2000 * r['ganancia_tick']:.0f} por 2000 ticks")
    print(f"   Mezcla de regimenes ({100 * (1 - frac):.0f} % tranquilo): {2000 * total:.0f} por 2000 ticks "
          f"({100 * 2000 * total / 10000:.1f} % de la caja)")
    r0 = politica(cal.Q_NIVEL, cal.Q_TRANS, cal.PHI, comision=0.0)
    print(f"   Sin comision, regimen tranquilo: {2000 * r0['ganancia_tick']:.0f} por 2000 ticks, "
          f"compra si z < {r0['compra']:+.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
