# Spatial VAR Colombia | Territorial Analytics Lab

**Laboratorio interactivo de econometría espacial, exploración territorial y simulación de respuestas dinámicas entre departamentos de Colombia.**

> **Alcance de los datos:** la cartografía corresponde a divisiones administrativas reales de Colombia. Los indicadores de crecimiento económico, desempleo y luces nocturnas son **sintéticos**; los coeficientes del modelo son supuestos de simulación. Esta versión **no estima** un VAR espacial con series oficiales y sus resultados **no constituyen evidencia causal ni cifras del DANE**.

## 1. Presentación del proyecto

Spatial VAR Colombia es una aplicación analítica desarrollada con **Python, Streamlit, GeoPandas, PySAL y Plotly**. Su propósito es facilitar la comprensión visual y cuantitativa de las relaciones espaciales y dinámicas entre departamentos colombianos mediante un entorno interactivo.

El proyecto integra límites geográficos reales, matrices de vecindad espacial, pruebas de autocorrelación y un sistema dinámico de **tres ecuaciones interconectadas**. Desde la interfaz, el usuario puede explorar el territorio en tres dimensiones, comparar estructuras de vecindad y observar cómo se propaga un impulso simulado desde un departamento hacia los demás a lo largo de distintos horizontes.

El laboratorio está orientado a la **docencia, experimentación metodológica y divulgación académica** de conceptos de econometría espacial. La aplicación distingue explícitamente las operaciones de **diagnóstico exploratorio** de las de **simulación**, sin presentarlas como estimación econométrica a partir de observaciones oficiales.

## 2. Objetivos

### Objetivo general

Desarrollar un entorno interactivo para explorar la estructura territorial de Colombia y analizar, mediante un modelo espacial multivariante simulado, la dependencia espacial y la transmisión dinámica de perturbaciones entre departamentos.

### Objetivos específicos

- Visualizar indicadores ilustrativos asociados a departamentos reales en un explorador geográfico 3D.
- Construir y contrastar matrices de pesos espaciales basadas en contigüidad **Queen** y en **cuatro vecinos más cercanos (KNN-4)**.
- Calcular el **índice global de Moran** para identificar patrones exploratorios de autocorrelación espacial.
- Simular la interacción temporal y espacial entre crecimiento económico, desempleo y luces nocturnas.
- Representar respuestas impulso–respuesta, efectos en el departamento intervenido y propagación hacia otros territorios.
- Comunicar los resultados mediante gráficos interactivos, tablas y exportaciones en formato CSV.

## 3. Cobertura, variables y datos

**Unidad territorial:** departamentos y entidad territorial de nivel equivalente, según el proveedor cartográfico disponible (normalmente entre 30 y 34 unidades válidas).

**Panel ilustrativo:** cuatro períodos artificiales, identificados como `P1`, `P2`, `P3` y `P4`. **No equivalen a años calendario.**

| Variable | Identificador interno | Interpretación dentro del laboratorio |
|---|---|---|
| Crecimiento económico | `growth` | Indicador sintético mostrado con escala porcentual; sus perturbaciones se expresan en puntos porcentuales. |
| Desempleo | `unemp` | Tasa sintética de desempleo; respuesta dinámica en puntos porcentuales. |
| Luces nocturnas | `nightlights` | Índice sintético de intensidad luminosa, de escala 0 a 100. |

La generación del panel utiliza una semilla fija (`SEED = 20261020`), perturbaciones aleatorias reproducibles y transmisión espacial con parámetros predefinidos. Para la presentación de los indicadores se aplican límites de escala; **no se descargan series de indicadores económicos del DANE**.

### Cartografía

Las geometrías se solicitan en este orden:

1. **DANE — Marco Geoestadístico Nacional 2025**, mediante consulta al servicio geográfico indicado en el código.
2. **Repositorio público de cartografía de Colombia** empleado como fuente de respaldo.
3. **geoBoundaries (COL, ADM1)**, como respaldo adicional.

La aplicación también admite cargar manualmente un archivo **GeoJSON** compatible. Para normalizar las geometrías y obtener centroides se utilizan los sistemas `EPSG:4326` y `EPSG:6933` respectivamente. Los límites se utilizan para las relaciones espaciales; el dibujo 3D es una representación exploratoria, **no una herramienta SIG de precisión cartográfica**.

> Si el servicio principal no está disponible, la aplicación puede utilizar una fuente alternativa. Por ello, conviene revisar la procedencia cartográfica que aparece en pantalla antes de interpretar relaciones de contigüidad.

## 4. Metodología econométrica

### 4.1. Matrices de pesos espaciales

El laboratorio permite seleccionar dos especificaciones de la matriz de pesos espaciales `W`:

- **Queen:** dos unidades se consideran vecinas si comparten al menos un punto de frontera. Las unidades desconectadas conservan filas sin vecinos; no se crean fronteras artificiales.
- **KNN-4:** cada unidad se relaciona con sus cuatro centroides departamentales más cercanos, calculados en una proyección métrica, no directamente sobre grados de latitud y longitud.

Los pesos se **normalizan por fila** (`w.transform = "r"`), excepto las filas correspondientes a unidades sin vecinos en Queen. Estas matrices permiten evaluar cómo influye la estructura territorial elegida en los diagnósticos y en la simulación.

### 4.2. Sistema Spatial VAR simulado

Para cada variable `j`, la regla dinámica implementada es:

$$
\Delta y_{j,t} = (I - \rho_j W)^{-1}
\left(\sum_{k=1}^{3} A_{jk}\,\Delta y_{k,t-1} + s_{j,t}\right)
$$

Donde:

- `W` es la matriz espacial seleccionada.
- `ρⱼ` determina la intensidad de difusión espacial contemporánea de la variable `j`.
- `Aⱼₖ` recoge la transmisión temporal propia y cruzada entre las tres variables.
- `sⱼ,ₜ` es la innovación o perturbación simulada.
- `I` es la matriz identidad y `Δy` representa las respuestas o desviaciones dinámicas simuladas.

Los coeficientes **se fijan en el código**. No proceden de una regresión ni de un procedimiento de identificación causal.

**Matriz de transmisión temporal y cruzada:**

$$
A = \begin{pmatrix}
 0.52 & -0.08 & 0.06 \\
-0.28 & 0.50 & -0.025 \\
 0.22 & -0.07 & 0.47
\end{pmatrix}
$$

**Parámetros de dependencia espacial:**

$$
\rho = (0.26,\ 0.16,\ 0.19)
$$

El sistema contiene tres ecuaciones conectadas: una para crecimiento económico, otra para desempleo y otra para luces nocturnas. Los efectos cruzados de `A` permiten que una perturbación inicial en crecimiento produzca, en horizontes posteriores, respuestas en las otras dos variables.

### 4.3. Autocorrelación espacial

Se calcula el **índice global de Moran** para cada variable en el período seleccionado y con la matriz de pesos elegida. La prueba utiliza **999 permutaciones** para obtener un valor `p` Monte Carlo exploratorio.

El módulo incluye:

- Tabla comparativa de `I` de Moran, valor esperado `E[I]`, valor `p` por simulación y signo de la autocorrelación.
- Diagrama de dispersión de Moran con valores estandarizados (`z`) y su rezago espacial (`Wz`).
- Información sobre la cantidad de unidades sin vecinos en la matriz seleccionada.

**Importante:** una asociación espacial detectada en estas variables generadas artificialmente no permite afirmar que exista ese mismo patrón en los datos reales de Colombia.

### 4.4. Respuesta impulso–respuesta y difusión territorial

El laboratorio aplica **un solo shock de crecimiento económico** al departamento elegido en el horizonte `h = 0`. A partir de ese impulso calcula las respuestas de las tres variables hasta `h = 8`, sin repetir el shock en los períodos siguientes.

La respuesta inicial del crecimiento se resume mediante:

- **Efecto en origen (denominado «directo» en la interfaz):** respuesta del departamento intervenido.
- **Efecto fuera del origen (denominado «indirecto»):** suma de las respuestas de los demás departamentos.
- **Suma territorial:** efecto en origen más efecto fuera del origen.

Esta es una **descomposición de la simulación concreta**, no la estimación de efectos directos e indirectos promedio de un modelo espacial ajustado a datos reales. La suma de variaciones en puntos porcentuales departamentales **no representa una tasa nacional**, puesto que no utiliza ponderadores poblacionales o económicos.

## 5. Módulos de la aplicación

### Módulo 01 — Explorador territorial 3D

Permite elegir una de las tres variables, uno de los cuatro períodos sintéticos y una paleta de colores. Presenta centroides departamentales en un plano de longitud y latitud, con valores del indicador sobre el eje vertical, además de contornos geográficos y consulta por departamento.

**Salidas:** gráfico interactivo, tabla de indicadores y descarga del panel sintético completo en CSV.

### Módulo 02 — Diagnósticos espaciales / ESDA

Permite seleccionar la matriz Queen o KNN-4, el período ilustrativo y la variable para el diagrama de Moran. Reporta la autocorrelación espacial de las tres variables en la configuración elegida.

**Salidas:** tabla de estadísticas globales, diagrama de dispersión, nota metodológica y descarga del diagnóstico en CSV.

### Módulo 03 — Policy Lab / Transmisión 3D

Permite seleccionar el departamento en el que se origina el impulso, la magnitud del shock de crecimiento (entre `-5` y `+5` puntos porcentuales), la matriz de transmisión, la variable representada y el horizonte inicial.

El modelo dibuja una **red 3D animada**: los nodos representan la respuesta de cada territorio y los enlaces ilustran términos de interacción espacial `ρ·W·Δy`. Los enlaces muestran **sensibilidades del modelo**, no flujos económicos observados ni rutas causales individuales.

**Salidas:** indicadores de impacto inicial, red animada (`h = 0…8`), gráficos de respuesta impulso–respuesta para las tres variables, clasificación de las 12 mayores respuestas territoriales en valor absoluto y tabla descargable en CSV.

## 6. Tecnologías y organización del repositorio

| Componente | Función |
|---|---|
| Python | Implementación de los cálculos y la lógica de la aplicación. |
| Streamlit | Interfaz web, controles interactivos y descargas. |
| NumPy y pandas | Operaciones matriciales y organización del panel. |
| GeoPandas y Shapely | Procesamiento de geometrías departamentales. |
| libpysal | Construcción de matrices Queen y KNN. |
| esda | Estadístico global de Moran y permutaciones. |
| Plotly | Visualizaciones 3D, animación y curvas de respuesta. |
| Requests | Consulta de servicios cartográficos. |

```text
ECONOMETRIA-ESPACIAL/
├── app.py             # Aplicación y motor de simulación
├── requirements.txt   # Dependencias de Python
└── README.md          # Presentación y documentación del proyecto
```

## 7. Ejecución de la aplicación

La aplicación está preparada para ejecutarse como proyecto Streamlit. Con Python 3.12 y las dependencias instaladas:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

En **Streamlit Community Cloud**, el archivo de entrada es `app.py`; la plataforma instala las dependencias especificadas en `requirements.txt`. Se requiere conectividad para obtener los límites geográficos, salvo que se cargue un GeoJSON manualmente. La disponibilidad de estos servicios de terceros no está garantizada.

## 8. Reproducibilidad, interpretación y limitaciones

- **Resultados reproducibles:** el generador utiliza una semilla constante; los resultados dependerán también de la cartografía, las versiones de las bibliotecas y las opciones seleccionadas.
- **Panel artificial:** los cuatro períodos no corresponden a 2018–2023 ni a cualquier otra serie anual, trimestral o mensual observada.
- **Parámetros supuestos:** `A` y `ρ` no están estimados; no deben interpretarse como elasticidades o impactos causales comprobados.
- **Inferencia exploratoria:** el valor `p` Monte Carlo corresponde a las variables sintéticas de la simulación.
- **Dependencia del mapa:** cambiar geometrías puede modificar los centroides, las relaciones Queen/KNN y los resultados.
- **Escalas de lectura:** los puntos porcentuales regionales y el índice de luces nocturnas tienen unidades distintas; sus valores no son sumables entre variables.
- **Alcance:** el proyecto es una demostración didáctica de mecanismos espaciales dinámicos y **no constituye un pronóstico económico ni una evaluación de política pública real**.

Para evolucionar hacia un estudio empírico será necesario incorporar series oficiales comparables por territorio y fecha, verificar consistencia geográfica y temporal, definir y estimar la especificación econométrica, realizar diagnósticos y evaluar la estabilidad e identificación de los efectos.

## 9. Fuentes cartográficas y recursos

- [DANE — Geoportal y Marco Geoestadístico Nacional](https://geoportal.dane.gov.co/)
- [Repositorio cartográfico de respaldo: ytolosa/mapas-colombia](https://github.com/ytolosa/mapas-colombia)
- [geoBoundaries — límites administrativos abiertos](https://www.geoboundaries.org/)
- [Documentación de Streamlit](https://docs.streamlit.io/)
- [PySAL — análisis espacial en Python](https://pysal.org/)

---

**Spatial VAR Colombia — Territorial Analytics Lab**  
*Proyecto académico de simulación econométrica espacial. Cartografía real; indicadores y parámetros ilustrativos.*
