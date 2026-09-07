"""
optimizer.py
------------
Núcleo cuantitativo del modelo: carga de datos, cálculo de estadísticos
(retorno esperado y matriz de covarianza) y optimización de portafolio
bajo el enfoque de Markowitz (frontera eficiente).

No depende de librerías de optimización pesadas (cvxpy, PyPortfolioOpt):
usa scipy.optimize, que es estable y ligero para desplegar en Streamlit
Community Cloud.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

MESES_POR_ANIO = 12


# ---------------------------------------------------------------------------
# Carga y limpieza de datos
# ---------------------------------------------------------------------------
def cargar_datos(archivo) -> dict:
    """
    Lee el Excel de proveedores y devuelve un diccionario con los DataFrames
    ya limpios. `archivo` puede ser una ruta (str/Path) o un objeto tipo
    archivo (por ejemplo, el que entrega st.file_uploader).
    """
    xls = pd.ExcelFile(archivo)

    proveedores = pd.read_excel(xls, "Proveedores")

    rendimientos = pd.read_excel(xls, "Rendimientos_Historicos")
    # Se descartan filas de nota / vacías al final de la tabla
    rendimientos = rendimientos[rendimientos["Fecha"].astype(str).str.match(r"^\d{4}-\d{2}$", na=False)]
    rendimientos = rendimientos.set_index("Fecha")
    rendimientos.index = pd.to_datetime(rendimientos.index, format="%Y-%m")
    rendimientos = rendimientos.sort_index()

    try:
        evaluaciones = pd.read_excel(xls, "Evaluaciones_Periodicas")
    except Exception:
        evaluaciones = pd.DataFrame()

    try:
        restricciones = pd.read_excel(xls, "Restricciones_Portafolio")
    except Exception:
        restricciones = pd.DataFrame()

    return {
        "proveedores": proveedores,
        "rendimientos": rendimientos,
        "evaluaciones": evaluaciones,
        "restricciones": restricciones,
    }


def filtrar_por_riesgo(
    proveedores: pd.DataFrame,
    max_riesgo_ejecucion: float,
    max_riesgo_comercial: float,
    max_riesgo_financiero: float,
) -> pd.DataFrame:
    """Excluye proveedores que superen los umbrales cualitativos de riesgo definidos por el usuario."""
    df = proveedores.copy()
    mask = (
        (df["Riesgo_Ejecucion_Pct"] <= max_riesgo_ejecucion)
        & (df["Riesgo_Comercial_Pct"] <= max_riesgo_comercial)
        & (df["Riesgo_Financiero_Pct"] <= max_riesgo_financiero)
    )
    return df[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Estadísticos del modelo
# ---------------------------------------------------------------------------
def calcular_estadisticos(
    rendimientos: pd.DataFrame,
    ids_validos: list[str],
    ventana_meses: int,
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Calcula el retorno esperado anualizado y la matriz de covarianza anualizada
    a partir de la serie histórica de rendimientos mensuales, usando solo los
    últimos `ventana_meses` meses y los proveedores en `ids_validos`.
    """
    cols = [c for c in ids_validos if c in rendimientos.columns]
    serie = rendimientos[cols].tail(ventana_meses)

    mu_mensual = serie.mean()
    cov_mensual = serie.cov()

    mu_anual = mu_mensual * MESES_POR_ANIO
    cov_anual = cov_mensual * MESES_POR_ANIO
    return mu_anual, cov_anual


# ---------------------------------------------------------------------------
# Optimización
# ---------------------------------------------------------------------------
def _rendimiento_portafolio(w, mu):
    return float(np.dot(w, mu))


def _riesgo_portafolio(w, cov):
    return float(np.sqrt(np.dot(w.T, np.dot(cov, w))))


def _sharpe_negativo(w, mu, cov, rf):
    ret = _rendimiento_portafolio(w, mu)
    riesgo = _riesgo_portafolio(w, cov)
    if riesgo == 0:
        return 0.0
    return -(ret - rf) / riesgo


def optimizar_portafolio(
    mu: pd.Series,
    cov: pd.DataFrame,
    objetivo: str,
    peso_min: float = 0.0,
    peso_max: float = 0.25,
    rf: float = 0.0,
    retorno_objetivo: float | None = None,
) -> dict:
    """
    Resuelve el problema de optimización de portafolio.

    objetivo: "sharpe" | "min_riesgo" | "max_retorno" | "retorno_objetivo"
    """
    n = len(mu)
    if n == 0:
        raise ValueError("No hay proveedores disponibles con los filtros seleccionados.")

    w0 = np.repeat(1 / n, n)
    bounds = tuple((peso_min, peso_max) for _ in range(n))
    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    mu_arr = mu.values
    cov_arr = cov.values

    if peso_max * n < 1.0:
        raise ValueError(
            f"El peso máximo por proveedor ({peso_max:.0%}) es demasiado bajo para "
            f"{n} proveedores disponibles: no es posible sumar 100%."
        )

    if objetivo == "sharpe":
        res = minimize(
            _sharpe_negativo, w0, args=(mu_arr, cov_arr, rf),
            method="SLSQP", bounds=bounds, constraints=restricciones,
        )
    elif objetivo == "min_riesgo":
        res = minimize(
            lambda w: _riesgo_portafolio(w, cov_arr), w0,
            method="SLSQP", bounds=bounds, constraints=restricciones,
        )
    elif objetivo == "max_retorno":
        res = minimize(
            lambda w: -_rendimiento_portafolio(w, mu_arr), w0,
            method="SLSQP", bounds=bounds, constraints=restricciones,
        )
    elif objetivo == "retorno_objetivo":
        if retorno_objetivo is None:
            raise ValueError("Debes indicar un retorno_objetivo para este modo.")
        restricciones = restricciones + [
            {"type": "eq", "fun": lambda w: _rendimiento_portafolio(w, mu_arr) - retorno_objetivo}
        ]
        res = minimize(
            lambda w: _riesgo_portafolio(w, cov_arr), w0,
            method="SLSQP", bounds=bounds, constraints=restricciones,
        )
    else:
        raise ValueError(f"Objetivo no reconocido: {objetivo}")

    if not res.success:
        raise RuntimeError(f"La optimización no convergió: {res.message}")

    w = res.x
    w[w < 1e-6] = 0.0
    w = w / w.sum()  # renormaliza por errores numéricos

    ret = _rendimiento_portafolio(w, mu_arr)
    riesgo = _riesgo_portafolio(w, cov_arr)
    sharpe = (ret - rf) / riesgo if riesgo > 0 else np.nan

    return {
        "pesos": pd.Series(w, index=mu.index),
        "retorno_esperado": ret,
        "riesgo": riesgo,
        "sharpe": sharpe,
    }


def calcular_frontera_eficiente(
    mu: pd.Series,
    cov: pd.DataFrame,
    peso_min: float = 0.0,
    peso_max: float = 0.25,
    n_puntos: int = 40,
) -> pd.DataFrame:
    """
    Calcula la frontera eficiente: para una malla de retornos objetivo entre
    el mínimo y el máximo alcanzable, encuentra el portafolio de mínima
    varianza correspondiente.

    Solo se conserva el tramo EFICIENTE de la parábola (desde el portafolio
    de mínima varianza hacia arriba). El tramo inferior queda matemáticamente
    definido pero está dominado -- para el mismo riesgo siempre existe un
    portafolio con mayor retorno en el tramo superior -- por lo que no se
    incluye en la frontera eficiente reportada.
    """
    ret_min = mu.min()
    ret_max = mu.max()
    objetivos = np.linspace(ret_min, ret_max, n_puntos)

    puntos = []
    for r_obj in objetivos:
        try:
            resultado = optimizar_portafolio(
                mu, cov, objetivo="retorno_objetivo",
                peso_min=peso_min, peso_max=peso_max, retorno_objetivo=r_obj,
            )
            puntos.append({"retorno": resultado["retorno_esperado"], "riesgo": resultado["riesgo"]})
        except Exception:
            continue

    df = pd.DataFrame(puntos)
    if df.empty:
        return df

    # Conservar solo el tramo eficiente: a partir del punto de mínimo riesgo,
    # y descartando cualquier punto posterior cuyo retorno no supere al anterior
    # (evita el "rulo" hacia abajo típico de una malla de retornos objetivo).
    df = df.sort_values("riesgo").reset_index(drop=True)
    idx_min_riesgo = df["riesgo"].idxmin()
    df_eficiente = df.loc[idx_min_riesgo:].copy()
    df_eficiente = df_eficiente[df_eficiente["retorno"].cummax() == df_eficiente["retorno"]]
    return df_eficiente.reset_index(drop=True)
