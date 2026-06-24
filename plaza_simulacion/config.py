"""
Simulación "PLAZA" - TP5 Simulación UTN FRC 4K1 2026
Parámetros por defecto del sistema.
"""

DEFAULT_PARAMS = {
    "media_llegada_min": 60 / 90,       # 0.6667 min entre llegadas
    "media_entrevista_min": 3.0,        # 3 min por entrevista
    "prob_acepta_entrevista": 0.85,
    "prob_vuelve_tarde": 0.25,
    "edad_min": 20,
    "edad_max": 85,
    "n_contactos": 2,
    "n_entrevistadores": 4,
    "tiempo_inicio_min": 0.0,           # reloj arranca en 0 (= 10 AM)
    "duracion_jornada_min": 360.0,      # 6 horas
    "rk_h": 0.1,                        # paso Runge-Kutta
    "segundos_por_unidad_t": 8,         # 1 unidad t = 8 segundos
    "max_iter": 100_000,
    "iter_desde_j": 1,
    "iter_mostrar_i": 50,
}
