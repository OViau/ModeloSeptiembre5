# Frontera Eficiente — Portafolio de Proveedores

Dashboard en Streamlit que aplica el modelo de **Frontera Eficiente de Markowitz**
a la gestión de proveedores: cada proveedor se trata como un "activo" con una
utilidad esperada y tres dimensiones de riesgo (ejecución, comercial, financiero).

## Estructura del repositorio

```
.
├── app.py                  # Interfaz de Streamlit
├── optimizer.py             # Lógica cuantitativa (carga de datos, estadísticos, optimización)
├── data/
│   └── BD_Gestion_Proveedores_Markowitz.xlsx   # Base de datos de ejemplo (sintética)
├── .streamlit/
│   └── config.toml          # Tema visual (dark, azul/negro)
├── requirements.txt
└── README.md
```

Estructura deliberadamente plana (sin subcarpetas de código) para evitar errores de
`ModuleNotFoundError` cuando el repositorio se sube a GitHub arrastrando archivos
desde la interfaz web, que a veces no preserva subcarpetas correctamente.

## Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Desplegar en Streamlit Community Cloud

1. Sube este repositorio a GitHub (público o privado, según tu plan).
2. En [share.streamlit.io](https://share.streamlit.io), selecciona "New app".
3. Elige el repositorio, la rama (`main`) y el archivo de entrada `app.py`.
4. Deploy. Streamlit instalará automáticamente `requirements.txt`.

## Supuestos del modelo (léelos antes de usar los resultados)

- **Fuente del riesgo de mercado**: la matriz de covarianza se calcula a partir de
  la hoja `Rendimientos_Historicos` (retornos mensuales simulados). El riesgo de
  ejecución/comercial/financiero **no** se mezcla dentro de la covarianza: se
  usa como **filtro de exclusión** (umbral máximo tolerado, configurable en la barra lateral).
- **Función objetivo** (seleccionable en la app): máximo Sharpe, mínimo riesgo, o máximo retorno.
- **Restricciones**: peso máximo y mínimo por proveedor, ambos configurables. La
  suma de pesos siempre es 100%.
- **Optimización**: `scipy.optimize.minimize` (SLSQP). No se usan librerías de
  optimización externas (cvxpy, PyPortfolioOpt) para minimizar dependencias en el despliegue.
- **Datos de ejemplo**: el archivo `.xlsx` incluido contiene datos **sintéticos**,
  generados únicamente para probar el modelo. Reemplázalo por tu propia base
  (mismo formato de columnas) usando el cargador de archivos de la barra lateral,
  o sustituyendo el archivo en `data/`.

## Parámetros dinámicos disponibles en la app

| Parámetro | Tipo | Descripción |
|---|---|---|
| Función objetivo | Selector | Sharpe / mínimo riesgo / máximo retorno |
| Ventana histórica | Slider | Meses de historia usados para estimar media y covarianza |
| Peso máximo/mínimo por proveedor | Slider | Restricciones de concentración |
| Tasa libre de riesgo | Input | Usada para el cálculo de Sharpe |
| Presupuesto total | Input | Para traducir pesos (%) a montos (MXN) |
| Umbrales de riesgo cualitativo | Sliders | Excluye proveedores por encima del umbral |
| Categorías incluidas | Multiselect | Filtra el universo de proveedores |
| Archivo de datos | Uploader | Permite sustituir la base de ejemplo |

## Extender el modelo

- Para incorporar el riesgo cualitativo directamente en la covarianza (en vez de
  como filtro), modifica `calcular_estadisticos` en `optimizer.py`.
- Para agregar restricciones por categoría (ej. máx. 40% en un giro), añade
  restricciones adicionales dentro de `optimizar_portafolio`.
- Para portafolios con posiciones mixtas-enteras (proveedor entra/no entra como
  variable binaria), se requeriría un solver de programación mixta-entera
  (ej. `PuLP`, `mip`), no incluido aquí para mantener el despliegue ligero.
