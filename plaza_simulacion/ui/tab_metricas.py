"""
Pestaña "Métricas": métricas principales + tabla completa.

Algunas métricas se siguen calculando en `core/simulacion.py` (porque las usa,
por ejemplo, la pestaña de Gráficos) pero se ocultan de esta vista a pedido.
"""

import pandas as pd
import streamlit as st

# Métricas que se calculan pero NO se muestran en esta pestaña.
METRICAS_OCULTAS = {
    "7. Edad Promedio de Entrevistados Completos",
    "8. % de Personas Entrevistadas sobre el Total que Pasó por la Plaza",
    "Total Abandonos Contactos Ocupados",
    "Total Volvieron Preguntar",
    "Total Informados No Entrevistados",
    "Total Rechazaron la Entrevista",
    "Total Se Fueron (Entrevistadores Llenos)",
    "Reloj Final (min)",
    "Iteraciones",
}


def render(metricas: dict):
    st.subheader("📈 Métricas de la Simulación")

    metricas_visibles = {k: v for k, v in metricas.items() if k not in METRICAS_OCULTAS}
    metricas_principales = {k: v for k, v in metricas_visibles.items() if not k.startswith("──")}

    col1, col2 = st.columns(2)
    items = [(k, v) for k, v in metricas_principales.items()]
    mid = len(items) // 2

    for idx, (k, v) in enumerate(items):
        col = col1 if idx < mid else col2
        if isinstance(v, float) and "%" in k:
            col.metric(k, f"{v}%")
        else:
            col.metric(k, v)

    st.divider()
    st.subheader("Tabla de métricas completa")
    df_met = pd.DataFrame(list(metricas_visibles.items()), columns=["Métrica", "Valor"])
    st.dataframe(df_met, use_container_width=True)
