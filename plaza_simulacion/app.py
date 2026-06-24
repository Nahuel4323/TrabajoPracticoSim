"""
Simulación "PLAZA" - TP5 Simulación UTN FRC 4K1 2026
Sistema: Investigación de mercado en Plaza San Martín de Córdoba.

Punto de entrada de la aplicación Streamlit.
Ejecutar con: streamlit run app.py
"""

import random

import streamlit as st

from core.simulacion import SimulacionPlaza
from ui import (
    sidebar,
    tab_vector_estado,
    tab_metricas,
    tab_graficos,
    tab_runge_kutta,
    descripcion,
)


def main():
    st.set_page_config(
        page_title="Simulación Plaza SM - G23",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Simulación Plaza San Martín, Grupo 23")
    st.subheader("4K1 - UTN FRC - 2026")
    st.markdown("**TP5 · Simulación por Eventos Discretos + Runge-Kutta**")

    # ── Sidebar: Parámetros ──────────────────────────────────────────────────
    config = sidebar.render_sidebar()
    params = config["params"]
    ejecutar = config["ejecutar"]
    semilla = config["semilla"]

    # ── Ejecución ────────────────────────────────────────────────────────────
    if not ejecutar:
        descripcion.render()
        return

    if semilla > 0:
        random.seed(semilla)

    sim = SimulacionPlaza(params)

    with st.spinner("Simulando..."):
        vector = sim.run()
        metricas = sim.calcular_metricas()

    st.success(f"✅ Simulación completada — {sim.iter} iteraciones / Reloj final: {round(sim.reloj, 2)} min")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧮 Vector de Estado",
        "📈 Métricas",
        "📊 Gráficos",
        "🔢 Tablas Runge-Kutta",
    ])

    with tab1:
        tab_vector_estado.render(vector, sim, params)

    with tab2:
        tab_metricas.render(metricas)

    with tab3:
        tab_graficos.render(sim, metricas, vector)

    with tab4:
        tab_runge_kutta.render(sim, params["rk_h"])


if __name__ == "__main__":
    main()
