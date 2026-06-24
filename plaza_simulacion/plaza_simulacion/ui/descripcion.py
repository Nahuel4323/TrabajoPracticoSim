"""
Descripción del sistema, mostrada antes de ejecutar la simulación.
"""

import streamlit as st


def render():
    st.info("👈 Configurá los parámetros en el panel lateral y presioná **Ejecutar Simulación**.")

    with st.expander("ℹ️ Descripción del sistema"):
        st.markdown("""
### Sistema "PLAZA"
- **4 entrevistadores** en la Plaza San Martín de Córdoba.
- **2 contactos** que informan a los transeúntes.
- Llegada de transeúntes: **Exponencial(λ)**, con λ ingresado directamente en **personas/minuto**.
- Si los 2 contactos están ocupados: el **25%** vuelve más tarde, el **75%** se va definitivamente.
- Tiempo de información: calculado con **Runge-Kutta (dE/dt = (t²−E)·h²)**, E(0)=Edad~Uniforme[20,85].
  - Se integra hasta que dE/dt > 0. Ese `t` (en unidades, 1 unidad = 8 seg) es el tiempo de información.
- El **85%** acepta la entrevista. Si todos los puestos están ocupados → la persona se va.
- Duración entrevista: **Exponencial(media=3 min)**.
- Horario: **10:00 AM a 16:00 PM** (360 minutos por jornada).

### 8 Métricas calculadas
1. **% Ocupación promedio Contactos**
2. **% Ocupación promedio Entrevistadores**
3. **% Personas que aceptaron entrevista** (de las informadas)
4. **% Rechazo por contactos ocupados** (sobre total de transeúntes)
5. **Cantidad de personas que volvieron a preguntar**
6. **% Informados que no fueron a entrevista**
7. **Edad promedio de entrevistados que completaron** la entrevista
8. **% de personas entrevistadas sobre el total que pasó por la plaza** (entrevistas finalizadas / transeúntes totales)

### 📊 Gráficos
En la pestaña **Gráficos** vas a encontrar visualizaciones para apoyar decisiones: ocupación de
servidores, embudo de conversión, motivos de pérdida de entrevistas, distribución de edades y
evolución acumulada de llegadas vs. entrevistas a lo largo de la jornada.
        """)
