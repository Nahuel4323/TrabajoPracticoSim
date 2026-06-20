# Simulación PLAZA

Aplicación web en Python (Streamlit) para simular el sistema de investigación de
mercado del TP5 — Simulación UTN FRC 4K1 2026, en la Plaza San Martín de Córdoba.

## Cómo ejecutar

Desde esta carpeta

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```
Esto abre la app en el navegador (por defecto `http://localhost:8501`).

No requiere instalar nada más allá de lo que está en `requirements.txt`
(`streamlit`, `pandas`, `plotly`).

## Estructura del código

- `app.py`: punto de entrada de la aplicación (orquesta sidebar + pestañas).
- `config.py`: parámetros por defecto (`DEFAULT_PARAMS`).
- `core/`: lógica de la simulación, sin ningún `import streamlit`.
- `core/runge_kutta.py`: integración de Runge-Kutta para el tiempo de información.
- `core/variables_aleatorias.py`: generadores `gen_exponencial`, `gen_uniforme`, `gen_decision`.
- `core/modelos.py`: dataclasses `Servidor` y `Transeunte`.
- `core/simulacion.py`: clase `SimulacionPlaza`, motor de eventos discretos.
- `ui/`: pantallas hechas con `streamlit`.
- `ui/sidebar.py`: panel de parámetros configurables.
- `ui/tab_vector_estado.py`: pestaña "Vector de Estado" (tabla de eventos).
- `ui/tab_metricas.py`: pestaña "Métricas".
- `ui/tab_graficos.py`: pestaña "Gráficos".
- `ui/tab_runge_kutta.py`: pestaña "Tablas Runge-Kutta".
- `ui/descripcion.py`: texto inicial (cuando todavía no se ejecutó la simulación).

## Qué permite modificar

- Tasa de llegada de transeúntes (λ, en personas/minuto).
- Media de duración de la entrevista.
- Probabilidad de aceptar la entrevista.
- Probabilidad de volver a preguntar si los contactos están ocupados.
- Rango de edades (mínima y máxima) de los transeúntes.
- Cantidad de contactos y de entrevistadores.
- Hora de inicio y duración de la jornada.
- Paso `h` de Runge-Kutta y segundos por unidad de tiempo `t`.
- Máximo de iteraciones de la simulación, hasta 100000.
- Semilla aleatoria (0 = aleatoria).
- Iteración inicial `j` y cantidad de iteraciones `i` a mostrar en el vector de estado.

El vector muestra las `i` iteraciones solicitadas desde `j` hasta `j + i - 1` y,
además, agrega siempre la última fila generada por la simulación. Por eso, si la
fila final está fuera del rango pedido, se verá como una fila adicional.

## Decisiones de modelado

- Cada transeúnte que llega decide, según una probabilidad configurable, si
  acepta o no la entrevista una vez informado.
- Si los contactos están ocupados, el transeúnte puede decidir volver a
  preguntar más tarde según otra probabilidad configurable.
- El tiempo de información de cada transeúnte se calcula integrando una
  ecuación diferencial con Runge-Kutta de 4° orden, usando la edad del
  transeúnte como condición inicial.
- Las llegadas de transeúntes siguen una distribución exponencial negativa,
  con la media derivada de la tasa λ ingresada en personas por minuto.
- Las edades se generan con una distribución uniforme entre la edad mínima
  y la edad máxima configuradas.
- La cantidad de contactos y de entrevistadores son servidores independientes
  y configurables; un transeúnte solo pasa a entrevista si hay un
  entrevistador libre.

## Runge-Kutta

La ecuación diferencial usada para el tiempo de información es:

```
dE/dt = (t² - E) * h²
```

con `E(0) = edad` del transeúnte y paso `h` configurable desde la interfaz.
La integración corre hasta que `dE/dt > 0`, momento en el que se toma `t` como
el tiempo de información (luego convertido a segundos y minutos usando el
parámetro "segundos por unidad t").

## Estadísticas calculadas

La aplicación muestra más de 8 estadísticas, entre ellas:

- % de Ocupación Promedio de Contactos.
- % de Ocupación Promedio de Entrevistadores.
- % de Personas que Aceptaron la Entrevista.
- % de Rechazo por Contactos Ocupados.
- Cantidad de Personas que Volvieron a Preguntar.
- % de Informados que No Fueron a Entrevista.
- Edad Promedio de Entrevistados Completos.
- % de Personas Entrevistadas sobre el Total que Pasó por la Plaza.

## Notas

- No se modificó ninguna fórmula, probabilidad ni el orden de eventos de la
  simulación; el código está reorganizado en módulos, no reescrito.
- Si en el futuro se agrega una nueva pestaña o gráfico, alcanza con crear un
  archivo nuevo en `ui/` con su propio `render(...)` e importarlo en `app.py`.
