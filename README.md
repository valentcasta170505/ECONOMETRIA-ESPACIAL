# Spatial VAR Colombia — aplicación Streamlit

## Entrega

Esta versión convierte el archivo de Google Colab/Gradio **a Streamlit** y conserva:

- Los 3 módulos originales: explorador 3D, Moran global, y Policy Lab 3D animado.
- Las 3 variables originales: crecimiento, desempleo y luces nocturnas.
- Sus 4 períodos de ejemplo: P1, P2, P3, P4.
- **Exactamente** los coeficientes A y ρ y las ecuaciones de propagación espacial.
- Las matrices Queen/KNN 4, el análisis de Moran de 999 permutaciones.
- Respuestas impulso–respuesta en h=0,...,8, interpretación local/externa.
- La cartografía real desde DANE, GitHub o geoBoundaries con respaldo; carga opcional de GeoJSON.

**Transparencia metodológica:** los indicadores económicos son SINTÉTICOS. El programa NO estima un VAR espacial a partir de datos del DANE, ni estima efectos causales.

## ¿Qué archivos subir a GitHub?

Selecciona solamente los tres archivos incluidos en este ZIP, directamente en la raíz de tu repositorio:

```
mi-repositorio/
├── app.py
├── requirements.txt
└── README.md
```

**NO subas el ZIP comprimido** como sustituto de los tres archivos. Si GitHub no muestra los archivos al buscarlos, entra a la carpeta descomprimida, selecciona los tres archivos con `Ctrl + A`, y pulsa **Abrir**. Alternativamente, arrastra los tres archivos a **Add file → Upload files** y confirma con **Commit changes**. Evita crear una carpeta de más.

## Desplegar en Streamlit Community Cloud

1. En GitHub, crea un repositorio público o abre uno existente.
2. Sube `app.py`, `requirements.txt` y `README.md` a la raíz del repositorio.
3. Ve a https://share.streamlit.io y selecciona **Create app**.
4. Configura **Repository** (usuario/repositorio), **Branch** (`main`) y **Main file path** (`app.py`).
5. En ajustes avanzados, si se ofrece selección de Python, elige **Python 3.12**.
6. Pulsa **Deploy**. Streamlit instala las dependencias de `requirements.txt`.
7. Si una descarga cartográfica falla, el panel lateral permite subir un GeoJSON departamental válido.

La aplicación requiere acceso a Internet al iniciar para obtener GeoJSON real, salvo que se cargue manualmente un GeoJSON. Puede tardar durante el primer inicio. La instancia gratuita puede reiniciarse y reconstruir caché; es normal.

## Ejecutarla en tu equipo

Con Python 3.12 instalado, desde la carpeta de los tres archivos:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

En Windows también puedes usar `py -3.12 -m pip ...`.

## Cambios respecto al código que enviaste

- Se eliminaron solamente los bloques `pip install` en ejecución y el servidor Gradio, ya que Streamlit instala dependencias desde `requirements.txt`.
- Los controles `gr.Dropdown`, `gr.Slider`, `gr.Plot`, `gr.Dataframe` y `gr.HTML` se reemplazaron por los correspondientes de Streamlit.
- Los métodos econométricos, valores de A, RHO y horizonte del shock se mantienen.
- Se agregó `st.cache_data` únicamente a la descarga/preparación del mapa, para no repetir solicitudes en cada interacción.
- Se añade descarga CSV de resultados, fuente del GeoJSON y manejo amigable de errores.

**Nota:** la descarga de archivos y la visualización integral en Streamlit Cloud no se pudieron probar dentro del entorno de creación (sin conexión externa y sin librerías Streamlit/libpysal/esda). Se verificó la compilación, se compararon 10 funciones originales sin diferencias y se ejecutaron pruebas locales del núcleo (panel, respuesta al impulso, red 3D, curvas y tabla). No se comprobó el servicio Streamlit completo. Si Community Cloud muestra un error, revisa **Manage app → Logs** y compártelo para corregirlo.
