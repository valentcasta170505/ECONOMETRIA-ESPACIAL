[README (1).md](https://github.com/user-attachments/files/33996033/README.1.md)
# Colombia · Spatial VAR Lab (Streamlit)

Aplicación web didáctica de econometría espacial: explorador territorial 2D/3D, índice de Moran global y LISA, laboratorio dinámico de transmisión de shocks en un sistema de tres ecuaciones interconectadas.

> **Importante:** las **geometrías territoriales** se descargan de servicios públicos, pero los **indicadores económicos son sintéticos** y los parámetros del modelo fueron elegidos para la simulación. No son cifras oficiales, no se estima un VAR con datos observados y ningún resultado debe interpretarse como evidencia causal o pronóstico económico.

## Archivos

```text
spatial_var_streamlit/
├── app.py                  # Interfaz web y controles Streamlit
├── engine.py               # Cartografía, W, panel sintético, Moran, LISA y shocks
├── charts.py               # Mapas, figuras y animaciones Plotly
├── requirements.txt        # Dependencias Python
├── .streamlit/
│   └── config.toml         # Tema claro y configuración segura
├── tests/
│   └── test_engine.py      # Pruebas sin Internet y con datos de juguete
└── README.md
```

## Publicar en Streamlit Community Cloud

1. Crea un repositorio en **GitHub**, por ejemplo `spatial-var-colombia`.
2. Sube **el contenido de esta carpeta** al nivel raíz del repositorio. Conserva el directorio `.streamlit` y los nombres originales. No subas el `.zip` sin extraer.
3. Abre [share.streamlit.io](https://share.streamlit.io/) e inicia sesión con GitHub.
4. Selecciona **Create app** → **Yup, I have an app**.
5. Selecciona el repositorio, la rama `main` y **Main file path: `app.py`**.
6. En **Advanced settings**, selecciona **Python 3.12** y guarda los cambios.
7. Haz clic en **Deploy**. Streamlit instala los paquetes desde `requirements.txt` automáticamente.
8. La aplicación tendrá una dirección pública similar a `https://tu-nombre.streamlit.app/`.

**No necesitas API Keys ni secretos.** La aplicación necesita acceso a Internet para descargar los límites administrativos la primera vez. El resultado se almacena en caché por 24 horas mientras continúe activo el entorno. Si falla el servicio cartográfico, puedes subir en la barra lateral un GeoJSON válido con 30–34 entidades administrativas de Colombia.

## Ejecutar en el computador

Abre una terminal dentro del directorio que contiene `app.py`:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
# source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

El navegador abrirá el servidor local (normalmente `http://localhost:8501`).

## Dependencias

Se eliminaron Gradio, `spreg`, `libpysal`, `esda` y `geopandas` porque para este laboratorio didáctico se implementan operaciones focalizadas con NumPy, SciPy, Shapely y PyProj. Esto reduce dependencias de despliegue. La aplicación **no** contiene `pip install` automático dentro del código.

## Funcionalidades

| Sección | Qué hace |
| --- | --- |
| Explorador territorial | Coropleta 2D, vista 3D, paleta, período e indicador; evolución por departamento y descarga CSV |
| Moran y LISA | Queen o KNN-4, Moran global con 999 permutaciones, dispersión de Moran, mapa de clústeres LISA y corrección FDR opcional |
| Policy Lab 3D | Shock único en cualquier variable y departamento, 9 horizontes, propagación 3D animada, tres respuestas impulso–respuesta, comparación Queen/KNN |
| Metodología y datos | Fórmulas, matrices de parámetros, licencias y fuentes, descarga del panel y metadatos JSON |

### Modelo matemático

Para cada indicador \(j\) y período \(t\):

\[
\Delta \mathbf{y}^{(j)}_t = (I - \rho_j W)^{-1}
\left(\sum_{k=1}^{3} A_{jk} \Delta\mathbf{y}^{(k)}_{t-1} + \mathbf{s}^{(j)}_t\right)
\]

- **A**: transmisión temporal y entre indicadores (**coeficientes asumidos**).
- **ρ**: parámetro de difusión espacial por indicador (**asumido**).
- **W**: matriz de pesos espaciales estandarizada por filas.
- **Queen**: contigüidad entre polígonos; las islas se dejan sin vecinos.
- **KNN-4**: cuatro centroides más próximos calculados en EPSG:6933; la relación KNN puede ser dirigida.
- **Directo**: respuesta en el departamento de origen.
- **Indirecto**: suma sin ponderar de las respuestas en otros departamentos.
- **Total territorial**: suma de respuestas, **no** una tasa de Colombia.

**Moran:** valor p bilateral por 999 permutaciones de la distribución global. **LISA:** permutaciones condicionales por unidad (499), con opción de controlar descubrimientos falsos (Benjamini–Hochberg). Son medidas exploratorias sobre cifras **simuladas**.

### Fuentes de cartografía

La aplicación intenta, en orden:

1. [Servicio ArcGIS DANE – Marco Geoestadístico Nacional 2025](https://geoportal.dane.gov.co/).
2. [Repositorio abierto de mapas de Colombia](https://github.com/ytolosa/mapas-colombia).
3. [geoBoundaries – Colombia ADM1](https://www.geoboundaries.org/) como respaldo (esquema simplificado; revisar los términos de licencia y atribución de esa fuente).

La fuente concreta utilizada se muestra en la aplicación. El servicio remoto puede cambiar y afectar la disponibilidad. Un archivo subido por el usuario se indica como **no verificado**.

## Validación

Las pruebas offline usan exclusivamente polígonos artificiales; no se confunden con la cartografía de producción. Ejecutar desde la raíz:

```bash
python -m unittest discover -s tests -v
python -m py_compile app.py engine.py charts.py
```

## Posibles ampliaciones

Para obtener un **Spatial VAR realmente estimado**, será necesario incorporar un panel departamental verificable y suficientemente largo, documentar las fuentes, hacer pruebas de estacionariedad y estabilidad, estimar los parámetros y construir respuestas impulso–respuesta con incertidumbre. Esta versión es un simulador, no un estimador empírico.
