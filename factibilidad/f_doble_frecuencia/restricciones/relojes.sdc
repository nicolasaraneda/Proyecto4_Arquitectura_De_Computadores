# relojes.sdc: los dos relojes de la prueba de placa, en el SDC que acepta nextpnr.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# nextpnr 0.11 acepta create_clock con -period y -name sobre un puerto o una
# red. No acepta -waveform (ciclo de trabajo), create_generated_clock ni
# set_clock_groups: ver mediciones/restricciones.txt.
create_clock -period 40 -name osc   [get_ports i_Clk]
create_clock -period 20 -name clk2x [get_nets clk2x]
