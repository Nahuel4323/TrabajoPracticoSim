"""
Sidebar de parámetros configurables por el usuario.
"""

import streamlit as st


def render_sidebar() -> dict:
    """
    Dibuja el panel lateral de parámetros y devuelve un dict con:
      - params: dict listo para pasarle a SimulacionPlaza
      - ejecutar: bool (se presionó el botón "Ejecutar Simulación")
      - semilla: int (semilla aleatoria, 0 = aleatoria)
    """
    with st.sidebar:
        st.header("⚙️ Parámetros")

        st.subheader("Sistema")
        lambda_llegada = st.number_input(
            "λ - Tasa de llegada (personas / minuto)",
            value=1.5,
            min_value=0.0001,
            step=0.1,
            format="%.4f",
            help="Tasa media (λ) de la exponencial negativa de llegada de transeúntes, "
                 "expresada directamente en personas por minuto. "
                 "Ej: 90 personas/hora equivale a λ = 1.5 personas/minuto.",
        )
        media_llegada_min = 1.0 / lambda_llegada
        st.caption(
            f"≈ {lambda_llegada * 60:.2f} personas/hora · "
            f"Tiempo medio entre llegadas = {media_llegada_min:.4f} min"
        )

        media_entrevista = st.number_input("Media duración entrevista (min)", value=3.0, min_value=0.1)
        prob_acepta = st.slider("P(acepta entrevista)", 0.0, 1.0, 0.85, 0.01)
        prob_vuelve = st.slider("P(vuelve tarde si contactos ocupados)", 0.0, 1.0, 0.25, 0.01)

        st.subheader("Edades")
        edad_min = st.number_input("Edad mínima", value=20, min_value=0)
        edad_max = st.number_input("Edad máxima", value=85, min_value=1)

        st.subheader("Servidores")
        n_contactos = st.number_input("N° de contactos", value=2, min_value=1, max_value=10)
        n_entrevistadores = st.number_input("N° de entrevistadores", value=4, min_value=1, max_value=20)

        st.subheader("Horario")
        hora_inicio = st.number_input("Hora de inicio (0=10AM)", value=0.0, min_value=0.0)
        duracion_horas = st.number_input("Duración jornada (horas)", value=6.0, min_value=0.1)

        st.subheader("Runge-Kutta")
        rk_h = st.number_input("Paso h (RK)", value=0.1, min_value=0.001, format="%.3f")
        seg_por_unidad = st.number_input("Segundos por unidad t", value=8, min_value=1)

        st.subheader("Simulación")
        max_iter = st.number_input("Máx. iteraciones", value=100_000, min_value=1, max_value=100_000)
        semilla = st.number_input("Semilla aleatoria (0=aleatoria)", value=0, min_value=0)

        st.subheader("Visualización del Vector")
        iter_j = st.number_input("Mostrar desde iteración j", value=1, min_value=0)
        iter_i = st.number_input("Mostrar i iteraciones", value=50, min_value=1, max_value=100000)

        ejecutar = st.button("▶️ Ejecutar Simulación", type="primary", use_container_width=True)

    params = {
        "media_llegada_min": media_llegada_min,
        "media_entrevista_min": media_entrevista,
        "prob_acepta_entrevista": prob_acepta,
        "prob_vuelve_tarde": prob_vuelve,
        "edad_min": edad_min,
        "edad_max": edad_max,
        "n_contactos": int(n_contactos),
        "n_entrevistadores": int(n_entrevistadores),
        "tiempo_inicio_min": hora_inicio,
        "duracion_jornada_min": duracion_horas * 60,
        "rk_h": rk_h,
        "segundos_por_unidad_t": int(seg_por_unidad),
        "max_iter": int(max_iter),
        "iter_desde_j": int(iter_j),
        "iter_mostrar_i": int(iter_i),
    }

    return {
        "params": params,
        "ejecutar": ejecutar,
        "semilla": int(semilla),
    }
