# potencia.tcl: potencia de una corrida del macro ASIC con OpenSTA.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Viene de asic/potencia/potencia.tcl de nuestro Proyecto 3. Lo llama
# scripts/potencia.sh con el sta de la imagen de LibreLane 3.0.16. Variables
# de entorno:
#   CORRIDA  carpeta final de la corrida (factibilidad/g_asic/runs/TAG/final)
#   ESQUINA  <rc>_<pvt>, por ejemplo nom_tt_025C_5v00: <rc> elige el SPEF
#            (min, nom, max) y <pvt> el liberty
#   MODO     defecto: sin actividad anotada, lo que hace el flujo
#            cero:    actividad 0 en todo el diseño, solo conmuta el reloj
#            vcd:     actividad leída de un VCD (read_vcd -scope $SCOPE $VCD)
#   VCD, SCOPE   solo con MODO=vcd
#   PDK_ROOT
# Carga liberty, netlist, SDC y SPEF igual que el STA del flujo, con los
# archivos que la corrida dejó en final/. El período del reloj es el de la
# SDC de la corrida.

set esquina $::env(ESQUINA)
set modo    $::env(MODO)
set corrida $::env(CORRIDA)
set rc      [string range $esquina 0 2]
set pvt     [string range $esquina 4 end]
set pdk_root $::env(PDK_ROOT)
set scl  gf180mcu_fd_sc_mcu7t5v0
set lib  $pdk_root/gf180mcuD/libs.ref/$scl/lib/${scl}__$pvt.lib
set nl   $corrida/nl/asic_top.nl.v
set sdc  $corrida/sdc/asic_top.sdc
set spef $corrida/spef/$rc/asic_top.$rc.spef

puts "potencia.tcl: esquina $esquina, modo $modo"
puts "  liberty: $lib"
puts "  netlist: $nl"
puts "  sdc:     $sdc"
puts "  spef:    $spef"

set_cmd_units -time ns -capacitance pF -current mA -voltage V -resistance kOhm -distance um
set sta_report_default_digits 6

define_corners $esquina
read_liberty -corner $esquina $lib
read_verilog $nl
link_design asic_top
read_sdc $sdc
read_spef -corner $esquina $spef

puts "\n=== clocks ==="
foreach clk [all_clocks] {
    puts "clock [get_property $clk name]: periodo [get_property $clk period], propagado [get_property $clk is_propagated]"
}

switch $modo {
    defecto {
        puts "\nMODO defecto: sin actividad anotada (actividad por defecto de OpenSTA en las entradas, propagada)"
    }
    cero {
        puts "\nMODO cero: set_power_activity -global -activity 0 -duty 0.5 (solo conmuta el reloj)"
        set_power_activity -global -activity 0 -duty 0.5
    }
    vcd {
        set vcd   $::env(VCD)
        set scope $::env(SCOPE)
        puts "\nMODO vcd: read_vcd -scope $scope $vcd"
        read_vcd -scope $scope $vcd
    }
    default {
        puts "MODO desconocido: $modo"
        exit 1
    }
}

puts "\n=== report_activity_annotation ==="
report_activity_annotation
if { $modo == "vcd" } {
    puts "\n=== report_activity_annotation -report_unannotated ==="
    report_activity_annotation -report_unannotated
}

puts "\n=== report_power -corner $esquina ==="
report_power -corner $esquina

# Sonda: actividad de algunos puertos (densidad en 1/s, duty y origen), para
# comprobar que OpenSTA leyó el VCD: el origen debe decir vcd y el reloj debe
# tener 2 transiciones por período.
puts "\n=== sonda: actividad de puertos (densidad 1/s, duty, origen) ==="
foreach puerto {clk rst_n spi_sclk spi_cs_n spi_miso} {
    puts "sonda puerto $puerto: [get_property [get_ports $puerto] activity]"
}

set p [sta::design_power [sta::find_corner $esquina]]
lassign [lrange $p 0 3] p_int p_sw p_leak p_tot
puts "\n=== design_power (W): interna $p_int conmutacion $p_sw fuga $p_leak total $p_tot ==="
