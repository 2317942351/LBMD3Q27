ADJOINT=0
TEST=FALSE

# Stage18 clean baseline compile matrix.
#
# Keep the first baseline narrow. Old upstream options such as thermo,
# geometric, staircaseimp, isograd, and tprec are deliberately not exposed here
# because Stage18 reintroduces geometry/wetting through explicit settings and
# clean stages rather than compile-time branches inherited from the old model.
#
# q27 is required for the target D3Q27 phase population. autosym is harmless and
# follows standard TCLB model practice.
OPT="q27*autosym"
