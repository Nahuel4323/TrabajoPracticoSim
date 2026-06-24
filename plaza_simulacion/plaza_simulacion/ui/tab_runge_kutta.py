"""
Pestaña "Tablas Runge-Kutta": detalle del cálculo del tiempo de información
por transeúnte, más un resumen de todas las tablas.
"""

import pandas as pd
import streamlit as st


def render(sim, rk_h: float):
    st.subheader("Tablas de Runge-Kutta calculadas")
    tablas = sim.tablas_rk_acumuladas

    if not tablas:
        st.info("No se calcularon tablas RK en esta simulación.")
        return

    st.markdown(f"**Total de tablas calculadas:** {len(tablas)}")

    opciones = [
        f"T{t['id_transeunte']} — Edad: {t['edad']} — RND: {t['rnd_edad']} — "
        f"t={t['t_unidades']} u / {t['t_segundos']} seg / {t['t_minutos']} min"
        for t in tablas
    ]

    seleccion = st.selectbox("Seleccionar tabla:", opciones)
    idx = opciones.index(seleccion)
    tabla_sel = tablas[idx]

    st.markdown(
        f"**Transeunte T{tabla_sel['id_transeunte']}** · "
        f"Edad = `{tabla_sel['edad']}` años · "
        f"RND Edad = `{tabla_sel['rnd_edad']}` · "
        f"Tiempo informando = `{tabla_sel['t_unidades']}` unidades = "
        f"`{tabla_sel['t_segundos']}` seg = `{tabla_sel['t_minutos']}` min"
    )

    df_rk = pd.DataFrame(tabla_sel["tabla"])

    # Columna interna de bandera: sacarla de la vista pero usarla para colorear
    tiene_bandera = "_k1_positivo" in df_rk.columns
    if tiene_bandera:
        idx_final = df_rk[df_rk["_k1_positivo"] == True].index
        df_rk = df_rk.drop(columns=["_k1_positivo"])

    def resaltar_fila_k1(df):
        estilos = pd.DataFrame("", index=df.index, columns=df.columns)
        if tiene_bandera and len(idx_final) > 0:
            estilos.loc[idx_final[0]] = "background-color: #d0f0dc; color: #1a5e35; font-weight: 600"
        return estilos

    styled = df_rk.style.apply(resaltar_fila_k1, axis=None)
    st.dataframe(styled, use_container_width=True, height=400)

    if tiene_bandera and len(idx_final) > 0:
        st.caption("🟢 La última fila (resaltada) es donde K1 se vuelve positivo — condición de corte de la integración.")

    st.caption(
        "**dE/dt = (t² − E) · h²** · "
        f"E(0) = {tabla_sel['edad']} (edad del transeunte) · "
        f"h = {rk_h} · "
        "Se integra hasta que dE/dt > 0 (velocidad de crecimiento positiva)"
    )

    # Mostrar resumen de todas las tablas
    st.divider()
    st.subheader("Resumen de todas las tablas RK")
    resumen = [
        {
            "Transeunte": f"T{t['id_transeunte']}",
            "RND Edad": t["rnd_edad"],
            "Edad (años)": t["edad"],
            "t final (unidades)": t["t_unidades"],
            "t final (segundos)": t["t_segundos"],
            "t final (minutos)": t["t_minutos"],
            "Pasos RK": len(t["tabla"]),
        }
        for t in tablas
    ]
    st.dataframe(pd.DataFrame(resumen), use_container_width=True)
