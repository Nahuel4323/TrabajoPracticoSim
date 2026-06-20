"""
Pestaña "Vector de Estado": tabla cruda de eventos de la simulación.

La última fila generada por la simulación siempre se incluye en la vista,
exista o no dentro del rango [j, j+i) elegido por el usuario.
"""

import pandas as pd
import streamlit as st

# Paleta de colores pastel para los encabezados de columna.
# Son tonos muy próximos entre sí (misma saturación/luminosidad, distinto matiz)
# para que el contraste entre una columna y la siguiente sea suave y no "salte".
_PALETA_PASTEL = [
    "#FBE3E4",  # rosa pastel
    "#FCEFE3",  # damasco pastel
    "#FCF6E3",  # amarillo pastel
    "#EAF4E3",  # verde pastel
    "#E3F2F1",  # turquesa pastel
    "#E3EEFC",  # celeste pastel
    "#EAE3FC",  # lila pastel
    "#F4E3EE",  # malva pastel
]


def _tabla_html_con_encabezados_pastel(df: pd.DataFrame, height: int = 500) -> str:
    """Genera una tabla HTML que imita la apariencia oscura nativa de
    st.dataframe (mismo fondo, tipografía, bordes y fila de índice),
    pero coloreando el encabezado de cada columna con un pastel propio
    (cíclico) para diferenciarlas suavemente entre sí."""

    columnas = list(df.columns)
    n_colores = len(_PALETA_PASTEL)

    # +2 porque la 1ra celda del thead es la del índice de fila (vacía),
    # que se deja con el estilo oscuro original.
    estilos_columnas = "\n".join(
        f".tabla-vector-estado thead th:nth-child({idx + 2}) "
        f"{{ background-color: {_PALETA_PASTEL[idx % n_colores]}; }}"
        for idx in range(len(columnas))
    )

    estilo = f"""
    <style>
    .tabla-vector-estado-contenedor {{
        max-height: {height}px;
        overflow: auto;
        border: 1px solid rgba(250, 250, 250, 0.12);
        border-radius: 6px;
        background-color: #0e1117;
    }}
    .tabla-vector-estado {{
        border-collapse: collapse;
        width: 100%;
        font-size: 0.82rem;
        font-family: "Source Sans Pro", sans-serif;
        color: #fafafa;
        background-color: #0e1117;
    }}
    .tabla-vector-estado thead th {{
        position: sticky;
        top: 0;
        z-index: 1;
        color: #0e1117;
        font-weight: 600;
        text-align: right;
        padding: 8px 12px;
        border-bottom: 1px solid rgba(250, 250, 250, 0.2);
        white-space: nowrap;
        background-color: #262730;
    }}
    .tabla-vector-estado thead th:first-child {{
        background-color: #0e1117;
        color: #fafafa;
    }}
    .tabla-vector-estado tbody th {{
        text-align: right;
        padding: 6px 12px;
        color: rgba(250, 250, 250, 0.5);
        font-weight: 400;
        white-space: nowrap;
    }}
    .tabla-vector-estado tbody td {{
        padding: 6px 12px;
        text-align: right;
        border-bottom: 1px solid rgba(250, 250, 250, 0.08);
        white-space: nowrap;
    }}
    .tabla-vector-estado tbody td:nth-child(3) {{
        text-align: left;
    }}
    .tabla-vector-estado tbody tr:hover td,
    .tabla-vector-estado tbody tr:hover th {{
        background-color: rgba(250, 250, 250, 0.06);
    }}
    {estilos_columnas}
    </style>
    """

    cuerpo_html = df.to_html(
        index=True,
        classes="tabla-vector-estado",
        border=0,
        na_rep="",
    )

    html_final = f"{estilo}<div class='tabla-vector-estado-contenedor'>{cuerpo_html}</div>"

    # Streamlit (markdown) interpreta cualquier línea que empiece con 4+
    # espacios como un bloque de código, por lo que hay que "desindentar"
    # todo el bloque antes de pasarlo con unsafe_allow_html=True.
    html_final = "\n".join(linea.lstrip() for linea in html_final.splitlines())

    return html_final


def render(vector: list[dict], sim, params: dict):
    st.subheader("Vector de Estado")

    j = params["iter_desde_j"]
    i = params["iter_mostrar_i"]

    # Rango [j, j+i) elegido por el usuario
    filas_rango = [f for f in vector if isinstance(f.get("N°"), int) and j <= f["N°"] < j + i]

    # La última fila generada por la simulación se incluye siempre,
    # esté o no dentro del rango seleccionado.
    fila_final_n = None
    if vector:
        ultima = vector[-1]
        if isinstance(ultima.get("N°"), int):
            fila_final_n = ultima["N°"]
            if not any(f["N°"] == fila_final_n for f in filas_rango):
                filas_rango = filas_rango + [ultima]

    if filas_rango:
        df = pd.DataFrame(filas_rango)
        st.markdown(f"**Mostrando iteraciones {j} a {j + i - 1}** ({len(filas_rango)} filas)")
        st.markdown(_tabla_html_con_encabezados_pastel(df, height=500), unsafe_allow_html=True)

        if fila_final_n is not None and not (j <= fila_final_n < j + i):
            st.caption(
                f"ℹ️ Se agregó también la última fila generada por la simulación (N° {fila_final_n}), "
                "que estaba fuera del rango de iteraciones seleccionado."
            )
    else:
        st.info(f"No hay iteraciones en el rango [{j}, {j+i}). "
                f"La simulación generó {sim.iter} iteraciones.")

    # Fila de inicio separada
    fila_inicio = [f for f in vector if f.get("Evento") == "Inicio"]
    if fila_inicio and j <= 0:
        st.markdown("**Fila de Inicio (iteración 0):**")
        st.markdown(
            _tabla_html_con_encabezados_pastel(pd.DataFrame(fila_inicio), height=150),
            unsafe_allow_html=True,
        )
