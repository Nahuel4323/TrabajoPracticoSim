"""
Pestaña "Gráficos": ocupación de servidores, embudo de conversión, motivos de
pérdida, distribución de edades y evolución acumulada de la jornada.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render(sim, metricas: dict, vector: list[dict]):
    st.subheader("📊 Gráficos de apoyo a la toma de decisiones")

    colA, colB = st.columns(2)

    # 1) Ocupación de servidores
    with colA:
        _grafico_ocupacion(metricas)

    # 2) Embudo de conversión
    with colB:
        _grafico_embudo(sim)

    colC, colD = st.columns(2)

    # 3) Motivos de pérdida
    with colC:
        _grafico_motivos(sim)

    # 4) Distribución de edades
    with colD:
        _grafico_edades(sim, metricas)

    # 5) Evolución temporal acumulada
    _grafico_evolucion(vector)


def _grafico_ocupacion(metricas: dict):
    st.markdown("**Ocupación promedio de servidores**")
    ocup_contactos = metricas["1. % Ocupación Promedio Contactos"]
    ocup_entrev = metricas["2. % Ocupación Promedio Entrevistadores"]
    fig_ocup = go.Figure(data=[
        go.Bar(
            x=["Contactos", "Entrevistadores"],
            y=[ocup_contactos, ocup_entrev],
            text=[f"{ocup_contactos}%", f"{ocup_entrev}%"],
            textposition="auto",
            marker_color=["#1f77b4", "#ff7f0e"],
        )
    ])
    fig_ocup.update_layout(yaxis_title="% Ocupación", yaxis_range=[0, 100], height=380)
    st.plotly_chart(fig_ocup, use_container_width=True)
    st.caption("Si un recurso está cerca del 100%, es un cuello de botella: "
               "considerar sumar más contactos o entrevistadores.")


def _grafico_embudo(sim):
    st.markdown("**Embudo de conversión de personas**")
    fig_funnel = go.Figure(go.Funnel(
        y=["Pasaron por la plaza", "Fueron informados", "Aceptaron entrevista", "Entrevista finalizada"],
        x=[
            sim.contador_transeuntes_totales,
            sim.contador_informados,
            sim.contador_entrevistas_aceptadas,
            sim.contador_entrevistas_finalizadas,
        ],
        textinfo="value+percent initial",
    ))
    fig_funnel.update_layout(height=380)
    st.plotly_chart(fig_funnel, use_container_width=True)
    st.caption("Muestra en qué etapa se pierden más personas potencialmente entrevistables.")


def _grafico_motivos(sim):
    st.markdown("**¿Por qué no se concretaron entrevistas?**")
    motivos = {
        "Contactos ocupados (no volvió)":
            sim.contador_abandonos_contactos_ocupados - sim.contador_volvieron_preguntar,
        "Contactos ocupados (volvió a preguntar)": sim.contador_volvieron_preguntar,
        "Rechazó la entrevista": sim.contador_rechazo_entrevista,
        "Entrevistadores ocupados": sim.contador_se_fue_puestos_llenos,
    }
    if sum(motivos.values()) > 0:
        fig_motivos = go.Figure(data=[go.Pie(
            labels=list(motivos.keys()),
            values=list(motivos.values()),
            hole=0.4,
        )])
        fig_motivos.update_layout(height=380)
        st.plotly_chart(fig_motivos, use_container_width=True)
        st.caption("Identifica la causa principal de pérdida de potenciales entrevistados.")
    else:
        st.info("No hubo pérdidas que graficar en esta simulación.")


def _grafico_edades(sim, metricas: dict):
    st.markdown("**Distribución de edades de entrevistados (finalizados)**")
    if sim.edades_entrevista_completada:
        fig_edad = px.histogram(
            x=sim.edades_entrevista_completada,
            nbins=15,
            labels={"x": "Edad"},
        )
        fig_edad.add_vline(
            x=metricas["7. Edad Promedio de Entrevistados Completos"],
            line_dash="dash", line_color="red",
            annotation_text="Promedio",
        )
        fig_edad.update_layout(height=380, yaxis_title="Cantidad de personas")
        st.plotly_chart(fig_edad, use_container_width=True)
        st.caption("Ayuda a entender qué franja etaria responde mejor a la encuesta.")
    else:
        st.info("No hubo entrevistas finalizadas para graficar.")


def _grafico_evolucion(vector: list[dict]):
    st.markdown("**Evolución acumulada durante la jornada**")
    filas_validas = [f for f in vector if isinstance(f.get("N°"), int)]
    if filas_validas:
        df_evol = pd.DataFrame(filas_validas)[
            ["Reloj", "Cnt Transeuntes Totales", "Cnt Entrevistas Aceptadas", "Cnt Entrevistas Finalizadas"]
        ]
        fig_evol = go.Figure()
        fig_evol.add_trace(go.Scatter(
            x=df_evol["Reloj"], y=df_evol["Cnt Transeuntes Totales"],
            mode="lines", name="Transeúntes totales"))
        fig_evol.add_trace(go.Scatter(
            x=df_evol["Reloj"], y=df_evol["Cnt Entrevistas Aceptadas"],
            mode="lines", name="Entrevistas aceptadas"))
        fig_evol.add_trace(go.Scatter(
            x=df_evol["Reloj"], y=df_evol["Cnt Entrevistas Finalizadas"],
            mode="lines", name="Entrevistas finalizadas"))
        fig_evol.update_layout(height=420, xaxis_title="Tiempo (min)", yaxis_title="Cantidad acumulada")
        st.plotly_chart(fig_evol, use_container_width=True)
        st.caption("Permite comparar el ritmo de llegada vs. el ritmo de atención a lo largo de la "
                   "jornada, útil para decidir si conviene reforzar personal en ciertos horarios.")
    else:
        st.info("No hay datos suficientes para graficar la evolución temporal.")
