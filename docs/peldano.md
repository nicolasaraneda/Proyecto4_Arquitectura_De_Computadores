# El diseño por defecto: el peldaño que compite

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

## Qué hay que lograr

El encabezado de `tb/tb_proyecto_4.sv` dice cómo se corre el testbench del curso:

```
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex
iverilog -g2012 -s tb_proyecto_4 -o /tmp/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv
vvp -n /tmp/tb_p4
```

Sin ninguna definición. Hoy eso da R0: el Espino base con `max_media`. Si compite R1 o R2, el profesor tiene que poder correr exactamente esos comandos y obtener el diseño que compite, con 4/4. El cambio queda preparado y probado; se ejecuta después del 26/11, cuando se sepa qué peldaño compite.

## Cómo se hace

`make peldano-fijar PELDANO=r1` (o `r2`) corre `tools/peldano.py fijar`, que hace cuatro cosas en el árbol de trabajo, sin commit:

1. **`rtl/00_peldano.v`**, un archivo sin lógica con las definiciones del peldaño (`ESPINO_BARREL`, `ESPINO_XD_EMAD`, `ESPINO_XD_DEVK`, `ESPINO_TABLA` y, para R2, `ESPINO_VIGILANTE`). El comando oficial compila `rtl/*.v` en orden alfabético, así que este archivo va primero y sus definiciones valen para `pochoco_soc.v` y el resto.
2. **El programa de R0 pasa a `sw/max_media.s`** (`git mv`), y las referencias a `sw/trade.s` y `sw/trade.hex` del `Makefile`, la integración continua, `tools/`, `ref/`, `tb/` y `formal/` pasan a `sw/max_media.*`. `tb/tb_proyecto_4.sv` no se toca, y los programas de `sw/` quedan byte por byte.
3. **`sw/trade.s` pasa a ser una copia exacta de `sw/fondo.s`**, y `sw/trade.hex` su ensamblado.
4. **Comprueba**: corre el comando oficial tal cual en una copia y exige 4/4 y `decisiones.csv` igual al de `ref/fondo.py`.

¿Por qué no se rompe todo lo demás? Porque desde el 16/11 **ningún flujo propio del repositorio lee los `rtl/00_*`**: todos arman su lista de fuentes sin ellos (el `Makefile` con `filter-out`, los scripts con `grep -v '^rtl/00_'`, los de Python con `startswith("00_")`) y eligen la variante con sus propias definiciones, como siempre. Sin definiciones, para ellos sigue siendo el Espino base. Los únicos que ven `rtl/00_peldano.v` son el comando oficial y `make tb`, que es ese mismo comando, y son justamente los que tienen que verlo. R0 con el testbench del curso queda en `make tb-param`, que usa una copia parametrizada con el programa de R0.

## Cómo se sabe que funciona, hoy

- `make peldano-oficial` corre el comando oficial con el diseño que hoy es el de por defecto y compara con su referencia. Hoy: R0, 4/4, patrimonio 9 661 y `decisiones.csv` idéntico al de `ref/trader.py`. Corre en la integración continua, así que también vigila que nadie rompa el comando oficial.
- `make peldano-probar PELDANO=r1` hace el cambio en una copia del repositorio (un `git worktree` en `build/peldano/`), sin tocar el árbol de trabajo, y corre ahí el comando oficial y ocho objetivos propios: `test-ref`, `tb` (que es el comando oficial y por eso pasa a probar R1), `tb-param` (la copia parametrizada del testbench, que sigue probando R0 con `sw/max_media.hex`), `equiv-gemelo`, `fondo-oficial`, `retune-control`, `check-tabla` y `test-fondo`. Resultado en `docs/mediciones/peldano_probar_r1.txt`.

## Qué hacer después del 26/11

```
git checkout main && git pull
make peldano-probar PELDANO=r1         # otra vez, con el main de ese día
make peldano-fijar PELDANO=r1          # el cambio de verdad
git status                             # revisar: rtl/00_peldano.v, sw/trade.s, sw/max_media.s y las referencias
make check                             # todo en verde
git commit -m "El diseño por defecto es R1"
```

Empujar a una rama, esperar la integración continua y recién entonces avanzar `main`. Para deshacer antes del commit: `git checkout -- . && git clean -fd rtl/ sw/`.

Si compite R0 no hay nada que hacer: ya es el diseño por defecto.

## Qué queda distinto después del cambio

- Los documentos que hablan de `sw/trade.s` como el programa de R0 quedan con el nombre viejo: el script no toca `docs/`. El README hay que actualizarlo a mano (sección de ensamblar).
- Los comentarios de los programas de `sw/` que citan `sw/trade.s` tampoco cambian, para que sus hashes sigan siendo los de las mediciones.
