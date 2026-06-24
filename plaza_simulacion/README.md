# Simulación PLAZA 

TP5 · Simulación UTN FRC 4K1 2026 · Investigación de mercado en Plaza San Martín de Córdoba.

## Estructura

```
plaza_simulacion/
├── app.py                       # Punto de entrada Streamlit (orquesta sidebar + tabs)
├── config.py                    # DEFAULT_PARAMS
├── requirements.txt
├── core/                        # Lógica pura, sin Streamlit
│   ├── __init__.py
│   ├── runge_kutta.py           # f_ode, runge_kutta_tiempo_info
│   ├── variables_aleatorias.py  # gen_exponencial, gen_uniforme, gen_decision
│   ├── modelos.py                # dataclasses Servidor, Transeunte
│   └── simulacion.py            # clase SimulacionPlaza (motor de eventos discretos)
└── ui/                           # Todo lo que dibuja la interfaz
    ├── __init__.py
    ├── sidebar.py                # Panel de parámetros (devuelve params/ejecutar/semilla)
    ├── tab_vector_estado.py      # Pestaña "Vector de Estado"
    ├── tab_metricas.py           # Pestaña "Métricas"
    ├── tab_graficos.py           # Pestaña "Gráficos"
    ├── tab_runge_kutta.py        # Pestaña "Tablas Runge-Kutta"
    └── descripcion.py            # Texto inicial (cuando no se ejecutó la simulación)
```

## Criterio de separación

- **`core/`**: todo lo que es lógica de negocio / matemática, sin ningún `import streamlit`.
  Se puede testear o reutilizar (por ejemplo, en un script de línea de comandos o un notebook)
  sin levantar la UI.
- **`ui/`**: cada pestaña de Streamlit en su propio archivo con una función `render(...)`,
  para que cada una se pueda editar o ampliar sin tocar el resto.
- **`app.py`**: sólo orquesta — arma la página, llama al sidebar, corre la simulación y
  reparte el resultado a cada pestaña. No tiene lógica propia.
- **`config.py`**: parámetros por defecto, separados para que se puedan importar desde
  cualquier lado (tests, otro front, etc.) sin arrastrar el resto del paquete.

## Cómo correr

```bash
cd plaza_simulacion
pip install -r requirements.txt
streamlit run app.py
```


