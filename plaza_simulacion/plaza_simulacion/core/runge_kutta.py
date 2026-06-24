"""
Runge-Kutta para calcular el tiempo de información de cada transeúnte.
"""


def f_ode(t: float, E: float, h: float) -> float:
    """dE/dt = (t^2 - E) * h^2"""
    return (t ** 2 - E) * h ** 2


def runge_kutta_tiempo_info(edad: float, h: float, seg_por_unidad: int) -> tuple[float, float, list[dict]]:
    """
    Integra dE/dt = (t^2 - E)*h^2 con E(0)=edad hasta que dE/dt > 0.
    Devuelve (t_final_unidades, t_final_minutos, tabla_rk_pasos).
    """
    t = 0.0
    E = edad
    tabla = []

    max_steps = 100_000
    steps = 0
    t_final = None

    while steps < max_steps:
        k1 = f_ode(t, E, h)
        k2 = f_ode(t + h / 2, E + h / 2 * k1, h)
        k3 = f_ode(t + h / 2, E + h / 2 * k2, h)
        k4 = f_ode(t + h, E + h * k3, h)

        t_new = round(t + h, 10)
        E_new = E + (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

        tabla.append({
            "t": round(t, 4),
            "E": round(E, 6),
            "K1": round(k1, 6),
            "K2": round(k2, 6),
            "K3": round(k3, 6),
            "K4": round(k4, 6),
            "t(i+1)": round(t_new, 4),
            "E(i+1)": round(E_new, 6),
        })

        t = t_new
        E = E_new

        # Velocidad de crecimiento ACTUAL (ya en el nuevo punto)
        dE_new = f_ode(t, E, h)
        if dE_new > 0:
            t_final = t
            # Agregar la fila final donde K1 ya es positivo (la que disparó el corte)
            k1_f = dE_new
            k2_f = f_ode(t + h / 2, E + h / 2 * k1_f, h)
            k3_f = f_ode(t + h / 2, E + h / 2 * k2_f, h)
            k4_f = f_ode(t + h, E + h * k3_f, h)
            t_new_f = round(t + h, 10)
            E_new_f = E + (h / 6) * (k1_f + 2 * k2_f + 2 * k3_f + k4_f)
            tabla.append({
                "t": round(t, 4),
                "E": round(E, 6),
                "K1": round(k1_f, 6),
                "K2": round(k2_f, 6),
                "K3": round(k3_f, 6),
                "K4": round(k4_f, 6),
                "t(i+1)": round(t_new_f, 4),
                "E(i+1)": round(E_new_f, 6),
                "_k1_positivo": True,
            })
            break
        steps += 1

    if t_final is None:
        t_final = t  # fallback

    t_segundos = t_final * seg_por_unidad
    t_minutos = t_segundos / 60.0
    return t_final, t_minutos, tabla
