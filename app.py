# -*- coding: utf-8 -*-
"""
=============================================================================
 ARIGAEL — SEMÁFORO DE INVERSIÓN Y SIMULADOR EN VIVO (PAPER TRADING)
 Versión Semipro — Fusión: motor robusto (3 módulos) + licencia real Gumroad
=============================================================================
"""
import time
import base64
import json
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# =============================================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA Y ESTILOS
# =============================================================================
st.set_page_config(
    page_title="Arigael — Semáforo de Inversión y Simulador",
    page_icon="🚦",
    layout="wide",
)

st.markdown("""
    <style>
    div[data-testid="stRadio"] > div { gap: 15px; }
    div[data-testid="stRadio"] label {
        font-size: 20px !important;
        font-weight: 800 !important;
        padding: 12px 24px !important;
        background-color: #1e222d !important;
        border-radius: 10px !important;
        border: 2px solid #363c4e !important;
        color: #ffffff !important;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #2962ff !important;
        background-color: #2a2e3d !important;
    }
    .header-author {
        position: absolute;
        top: 0px;
        right: 10px;
        font-size: 10px !important;
        color: #888888;
        font-family: sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

LOG_FILE = "bitacora_decisiones.csv"
SIMULADOR_FILE = "mi_portafolio_simulador.json"
DCA_FILE = "dca_reminder.json"

# SEC EDGAR requiere un User-Agent identificable con contacto real (política de uso justo).
# CAMBIA esto por tu nombre/producto y un correo real antes de publicar.
SEC_USER_AGENT = "Arigael Terminal contacto@tudominio.com"


# =============================================================================
# LICENCIA — VALIDACIÓN REAL CON GUMROAD (candado que sí detiene la app)
# =============================================================================
def validar_licencia_gumroad(license_key: str) -> bool:
    """Verifica si la clave ingresada por el usuario es válida en Gumroad."""
    url = "https://api.gumroad.com/v2/licenses/verify"
    payload = {
        "product_id": "90wXizqYUDaV85t9R5Tb1Q==",  # product_id exigido por Gumroad para este producto
        "license_key": license_key.strip(),
        "increment_uses_count": "false",
    }
    try:
        response = requests.post(url, data=payload, timeout=5)
        res_data = response.json()
        return res_data.get("success", False) and not res_data.get(
            "purchase", {}
        ).get("refunded", False)
    except Exception:
        return False


with st.sidebar:
    st.markdown("### 🔑 Licencia del Sistema")

    if "licencia_activa" not in st.session_state:
        st.session_state["licencia_activa"] = False

    if not st.session_state["licencia_activa"]:
        st.warning("🔑 Modo Prueba / No Registrado")
        clave_ingresada = st.text_input(
            "Ingrese su License Key de Gumroad:",
            type="password",
            key="key_id_input",
        )

        if st.button("Activar Licencia", use_container_width=True):
            # Clave maestra personal (para que tú entres siempre gratis)
            if clave_ingresada.strip() == "ADMIN123":
                st.session_state["licencia_activa"] = True
                st.success("Licencia de Administrador Activada")
                st.rerun()
            # Validación real con el servidor de Gumroad para el cliente
            elif validar_licencia_gumroad(clave_ingresada):
                st.session_state["licencia_activa"] = True
                st.success("¡Licencia Validada Correctamente!")
                st.rerun()
            else:
                st.error("Clave inválida, no encontrada o reembolsada.")
    else:
        st.success("🟢 Licencia PRO Activa")

# =============================================================================
# CANDADO REAL: detiene la app aquí si no hay licencia activa
# =============================================================================
if not st.session_state.get("licencia_activa", False):
    st.title("🔒 Arigael — Semáforo de Inversión y Simulador")
    st.warning(
        "⚠️ Necesitas una licencia válida para usar esta herramienta. "
        "Ingresa tu clave en la barra lateral izquierda para continuar."
    )
    st.info("¿No tienes clave? Consíguela en tu página de producto de Gumroad.")
    st.stop()


# =============================================================================
# PANTALLA DE BIENVENIDA — disclaimer real, una vez por sesión
# =============================================================================
if "disclaimer_visto" not in st.session_state:
    st.session_state["disclaimer_visto"] = False

if not st.session_state["disclaimer_visto"]:
    st.title("👋 Bienvenido a Arigael")
    st.markdown("""
### Antes de empezar, 3 cosas importantes:

1. **Esto es una herramienta educativa de organización de datos, no un sistema de predicción.**
   Los "scores" y semáforos son heurísticas basadas en reglas que definimos nosotros —
   no son validaciones estadísticas de qué tan bien predicen el futuro.

2. **La protección real de tu capital viene de diversificar, no de encontrar la señal perfecta.**
   Considera mantener la mayoría de tu capital en algo diversificado (ej. un ETF amplio como
   el S&P 500) y usar la porción de acciones individuales como una parte pequeña y acotada
   de tu portafolio total.

3. **Ningún resultado pasado —incluido el historial de precisión que puedes consultar aquí—
   garantiza resultados futuros.** Úsalo para aprender y organizar tu análisis, no como
   una promesa de ganancias.
""")
    if st.button("Entendido, continuar a la aplicación", type="primary", use_container_width=True):
        st.session_state["disclaimer_visto"] = True
        st.rerun()
    st.stop()


# =============================================================================
# FUNCIONES AUXILIARES DE IMAGEN Y LOGO
# =============================================================================
def obtener_base64_imagen(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/jpeg;base64,{encoded_string}"
    return None


# =============================================================================
# FUNCIONES DEL SIMULADOR (PERSISTENCIA DE DATOS)
# =============================================================================
def cargar_simulador():
    if os.path.exists(SIMULADOR_FILE):
        try:
            with open(SIMULADOR_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"efectivo": 100000.0, "posiciones": {}}


def guardar_simulador(data):
    with open(SIMULADOR_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =============================================================================
# BITÁCORA AUTOMÁTICA DE SEÑALES + EVALUACIÓN DE PRECISIÓN HISTÓRICA
# (Evidencia real sobre el propio semáforo, no una promesa de resultados)
# =============================================================================
def cargar_bitacora() -> pd.DataFrame:
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except Exception:
            pass
    return pd.DataFrame(columns=["fecha", "ticker", "señal", "precio"])


def registrar_señal_bitacora(ticker: str, color: str, precio: float):
    """Guarda como máximo una señal por ticker por día (no satura el archivo)."""
    df_log = cargar_bitacora()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    ya_existe = (
        not df_log.empty
        and ((df_log["fecha"] == fecha_hoy) & (df_log["ticker"] == ticker)).any()
    )
    if not ya_existe:
        nueva_fila = pd.DataFrame([{"fecha": fecha_hoy, "ticker": ticker, "señal": color, "precio": precio}])
        df_log = pd.concat([df_log, nueva_fila], ignore_index=True)
        df_log.to_csv(LOG_FILE, index=False)


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_precio_en_fecha(ticker: str, fecha_objetivo_str: str, dias_ventana: int = 5):
    """Busca el precio de cierre más cercano a una fecha específica (±ventana días)."""
    try:
        fecha = pd.to_datetime(fecha_objetivo_str)
        inicio = (fecha - pd.Timedelta(days=dias_ventana)).strftime("%Y-%m-%d")
        fin = (fecha + pd.Timedelta(days=dias_ventana)).strftime("%Y-%m-%d")
        hist = yf.Ticker(ticker).history(start=inicio, end=fin)
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        hist["dif"] = abs((hist.index - fecha).days)
        fila = hist.sort_values("dif").iloc[0]
        return float(fila["Close"])
    except Exception:
        return None


def evaluar_precision_historial(horizonte_dias: int):
    """Compara cada señal registrada (ya 'madura', con suficiente tiempo transcurrido)
    contra lo que el precio realmente hizo después. No inventa datos: si no se puede
    obtener el precio futuro, esa señal simplemente se omite del cálculo."""
    df_log = cargar_bitacora()
    if df_log.empty:
        return None

    df_log["fecha"] = pd.to_datetime(df_log["fecha"])
    hoy = pd.Timestamp(datetime.now().date())
    df_log["dias_transcurridos"] = (hoy - df_log["fecha"]).dt.days
    maduras = df_log[df_log["dias_transcurridos"] >= horizonte_dias].copy()
    if maduras.empty:
        return {"tabla": pd.DataFrame(), "resumen": None}

    filas_resultado = []
    for _, row in maduras.iterrows():
        fecha_objetivo = (row["fecha"] + pd.Timedelta(days=horizonte_dias)).strftime("%Y-%m-%d")
        precio_futuro = obtener_precio_en_fecha(row["ticker"], fecha_objetivo)
        if precio_futuro is None:
            continue
        retorno = (precio_futuro - row["precio"]) / row["precio"]
        if row["señal"] == "verde":
            resultado_txt = "✅ Acertó" if retorno > 0 else "❌ Falló"
        elif row["señal"] == "rojo":
            resultado_txt = "✅ Acertó (evitó pérdida)" if retorno < 0 else "❌ Falló (se perdió una subida)"
        else:
            resultado_txt = "➖ Neutral (amarillo)"

        filas_resultado.append({
            "Fecha Señal": row["fecha"].strftime("%Y-%m-%d"),
            "Ticker": row["ticker"],
            "Señal": row["señal"].capitalize(),
            "Precio Entonces": f"${row['precio']:.2f}",
            "Precio Después": f"${precio_futuro:.2f}",
            "Retorno": f"{retorno*100:+.1f}%",
            "Resultado": resultado_txt,
        })

    df_resultado = pd.DataFrame(filas_resultado)
    if df_resultado.empty:
        return {"tabla": df_resultado, "resumen": None}

    verdes = df_resultado[df_resultado["Señal"] == "Verde"]
    rojos = df_resultado[df_resultado["Señal"] == "Rojo"]
    resumen = {
        "total_evaluadas": len(df_resultado),
        "verdes_evaluadas": len(verdes),
        "verdes_acierto_pct": (verdes["Resultado"] == "✅ Acertó").mean() * 100 if len(verdes) else None,
        "rojos_evaluadas": len(rojos),
        "rojos_acierto_pct": (rojos["Resultado"].str.startswith("✅")).mean() * 100 if len(rojos) else None,
    }
    return {"tabla": df_resultado, "resumen": resumen}


# =============================================================================
# RECORDATORIO DE APORTE PERIÓDICO (DCA — Dollar-Cost Averaging)
# =============================================================================
def cargar_dca() -> dict:
    if os.path.exists(DCA_FILE):
        try:
            with open(DCA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "proximo_aporte": datetime.now().strftime("%Y-%m-%d"),
        "frecuencia_dias": 30,
        "monto_sugerido": 100.0,
    }


def guardar_dca(data: dict):
    with open(DCA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def obtener_precio_instantaneo(ticker_symbol: str) -> float:
    try:
        t = yf.Ticker(ticker_symbol)
        precio = t.fast_info.get("lastPrice", None)
        if precio is None or np.isnan(precio):
            hist = t.history(period="1d")
            precio = hist["Close"].iloc[-1] if not hist.empty else 0.0
        return float(precio)
    except Exception:
        return 0.0


# =============================================================================
# FUNCIONES DE DATOS: Descarga y Métricas (Yahoo Finance)
# =============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def descargar_datos(ticker: str, periodo: str = "2y"):
    activo = yf.Ticker(ticker)
    hist = activo.history(period=periodo)
    if hist.empty:
        return None, None, None
    info = activo.info
    try:
        noticias = activo.news
    except Exception:
        noticias = []
    return hist, info, noticias


def obtener_historial_inspector(ticker: str, periodo: str = "6mo"):
    try:
        activo = yf.Ticker(ticker)
        hist = activo.history(period=periodo)
        if hist.empty:
            return None
        hist = hist.reset_index()
        if "Date" in hist.columns:
            hist["Date"] = pd.to_datetime(hist["Date"]).dt.tz_localize(None)
        return hist
    except Exception:
        return None


def calcular_ema(serie: pd.Series, periodo: int) -> pd.Series:
    return serie.ewm(span=periodo, adjust=False).mean()


def calcular_rsi(serie: pd.Series, periodo: int = 14) -> pd.Series:
    delta = serie.diff()
    ganancia = delta.clip(lower=0)
    perdida = -delta.clip(upper=0)
    media_ganancia = ganancia.rolling(window=periodo).mean()
    media_perdida = perdida.rolling(window=periodo).mean()
    rs = media_ganancia / media_perdida.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def agregar_indicadores_tecnicos(hist: pd.DataFrame) -> pd.DataFrame:
    df = hist.copy()
    df["EMA50"] = calcular_ema(df["Close"], 50)
    df["EMA200"] = calcular_ema(df["Close"], 200)
    df["RSI14"] = calcular_rsi(df["Close"], 14)
    return df


def extraer_fundamentales(info: dict) -> dict:
    def g(clave, default=None):
        return info.get(clave, default)

    market_cap = g("marketCap")
    total_debt = g("totalDebt")
    ebitda = g("ebitda")
    fcf = g("freeCashflow")
    peg = g("pegRatio")
    op_margin = g("operatingMargins")
    rev_growth = g("revenueGrowth")
    roe = g("returnOnEquity")

    debt_ebitda = (
        (total_debt / ebitda) if (total_debt and ebitda and ebitda != 0) else None
    )
    fcf_yield = (
        (fcf / market_cap) if (fcf and market_cap and market_cap != 0) else None
    )

    return {
        "ROIC_aprox_ROE": roe,
        "PEG": peg,
        "Deuda_EBITDA": debt_ebitda,
        "FCF_Yield": fcf_yield,
        "Margen_Operativo": op_margin,
        "Crecimiento_Ingresos_YoY": rev_growth,
        "FCF_negativo": (fcf is not None and fcf < 0),
    }


# =============================================================================
# SISTEMA DE CALIFICACIÓN Y SEMÁFORO
# =============================================================================
RATING_COLORS = {
    "Excelente": "#0B6E4F", "Muy bueno": "#1DB954", "Bueno": "#8BC34A",
    "Precaución": "#F5B700", "Malo": "#E63946", "N/D": "#9AA0A6",
}
RATING_ICONS = {
    "Excelente": "⭐", "Muy bueno": "✅", "Bueno": "🙂",
    "Precaución": "⚠️", "Malo": "🚫", "N/D": "❔",
}


def badge_html(etiqueta: str) -> str:
    color = RATING_COLORS.get(etiqueta, "#9AA0A6")
    icono = RATING_ICONS.get(etiqueta, "")
    return (
        f"<span style='background-color:{color};color:white;padding:3px 10px;"
        f"border-radius:12px;font-size:13px;font-weight:600;white-space:nowrap;'>"
        f"{icono} {etiqueta}</span>"
    )


def mostrar_metrica(contenedor, titulo: str, valor_texto: str, calificacion: str, ayuda: str = ""):
    contenedor.markdown(f"<div style='font-size:13px;color:#666;'>{titulo}</div>", unsafe_allow_html=True)
    contenedor.markdown(f"<div style='font-size:24px;font-weight:700;line-height:1.3;'>{valor_texto}</div>", unsafe_allow_html=True)
    contenedor.markdown(badge_html(calificacion), unsafe_allow_html=True)
    if ayuda:
        contenedor.caption(ayuda)
    contenedor.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


def calif_roic(v):
    if v is None: return "N/D"
    if v > 0.20: return "Excelente"
    if v > 0.15: return "Muy bueno"
    if v > 0.10: return "Bueno"
    if v > 0.05: return "Precaución"
    return "Malo"


def calif_peg(v):
    if v is None: return "N/D"
    if v <= 0: return "Precaución"
    if v <= 1.0: return "Excelente"
    if v <= 1.5: return "Muy bueno"
    if v <= 2.0: return "Bueno"
    if v <= 3.0: return "Precaución"
    return "Malo"


def calif_deuda_ebitda(v):
    if v is None: return "N/D"
    if v < 1.0: return "Excelente"
    if v < 2.5: return "Muy bueno"
    if v < 4.0: return "Bueno"
    if v < 4.5: return "Precaución"
    return "Malo"


def calif_fcf_yield(v):
    if v is None: return "N/D"
    if v < 0: return "Malo"
    if v > 0.08: return "Excelente"
    if v > 0.04: return "Muy bueno"
    if v > 0.02: return "Bueno"
    return "Precaución"


def calif_rsi(v):
    if v is None: return "N/D"
    if 45 <= v <= 65: return "Excelente"
    if (40 <= v < 45) or (65 < v <= 70): return "Bueno"
    if (30 <= v < 40) or (70 < v <= 80): return "Precaución"
    return "Malo"


def calif_tendencia(precio, ema50, ema200):
    if None in (precio, ema50, ema200): return "N/D"
    if precio > ema50 > ema200: return "Excelente"
    if precio > ema200: return "Bueno"
    if precio > ema200 * 0.95: return "Precaución"
    return "Malo"


def calif_backtest_vs_buyhold(ret_estrategia, ret_buyhold):
    if ret_estrategia is None: return "N/D"
    diff = ret_estrategia - ret_buyhold
    if diff >= 0: return "Excelente"
    if diff >= -0.10: return "Muy bueno"
    if diff >= -0.30: return "Bueno"
    if diff >= -0.60: return "Precaución"
    return "Malo"


def calif_drawdown(dd):
    if dd is None: return "N/D"
    dd_abs = abs(dd)
    if dd_abs < 0.10: return "Excelente"
    if dd_abs < 0.20: return "Muy bueno"
    if dd_abs < 0.35: return "Bueno"
    if dd_abs < 0.50: return "Precaución"
    return "Malo"


def evaluar_semaforo(fund: dict, df_tec: pd.DataFrame) -> dict:
    razones_rojo, razones_amarillo, razones_verde = [], [], []

    ultimo = df_tec.iloc[-1]
    precio = ultimo["Close"]
    ema50 = ultimo["EMA50"]
    ema200 = ultimo["EMA200"]
    rsi = ultimo["RSI14"]

    if fund["FCF_negativo"]:
        razones_rojo.append("Flujo de caja libre negativo")
    if fund["Deuda_EBITDA"] is not None and fund["Deuda_EBITDA"] > 4.5:
        razones_rojo.append(f"Deuda/EBITDA excesiva ({fund['Deuda_EBITDA']:.2f})")
    if precio < ema200:
        razones_rojo.append("Precio por debajo de la EMA 200 (tendencia bajista)")
    if ema50 < ema200:
        cruce_reciente = (df_tec["EMA50"].iloc[-30:] > df_tec["EMA200"].iloc[-30:]).any()
        if cruce_reciente:
            razones_rojo.append("Cruce de la muerte reciente")

    if razones_rojo:
        return {"color": "rojo", "razones": razones_rojo, "score": 15}

    if fund["Margen_Operativo"] is not None and fund["Margen_Operativo"] > 0.15:
        razones_verde.append("Margen operativo > 15%")
    if fund["ROIC_aprox_ROE"] is not None and fund["ROIC_aprox_ROE"] > 0.15:
        razones_verde.append("ROIC/ROE > 15%")
    if fund["Deuda_EBITDA"] is not None and fund["Deuda_EBITDA"] < 2.5:
        razones_verde.append("Deuda/EBITDA saludable (< 2.5)")
    if fund["Crecimiento_Ingresos_YoY"] is not None and fund["Crecimiento_Ingresos_YoY"] > 0.08:
        razones_verde.append("Crecimiento de ingresos YoY > 8%")

    tecnico_favorable = (precio > ema200) and (precio >= ema50 * 0.98) and (45 <= rsi <= 65)
    if tecnico_favorable:
        razones_verde.append("Precio sobre EMA200 y EMA50, con RSI en zona saludable")

    if len(razones_verde) >= 3 and tecnico_favorable:
        return {"color": "verde", "razones": razones_verde, "score": 85}

    if fund["ROIC_aprox_ROE"] is not None and fund["ROIC_aprox_ROE"] > 0.12:
        if fund["PEG"] is not None and fund["PEG"] > 2.0:
            razones_amarillo.append(f"Rentable pero sobrevalorada (PEG={fund['PEG']:.2f})")
    if fund["Deuda_EBITDA"] is not None and 2.5 < fund["Deuda_EBITDA"] < 4.0:
        razones_amarillo.append(f"Deuda moderada ({fund['Deuda_EBITDA']:.2f})")
    if ema50 <= precio <= ema200 or ema200 <= precio <= ema50:
        razones_amarillo.append("Precio en fase lateral")
    if rsi > 70:
        razones_amarillo.append(f"RSI en sobrecompra ({rsi:.1f})")

    if razones_amarillo or (0 < len(razones_verde) < 3):
        return {"color": "amarillo", "razones": razones_amarillo or razones_verde, "score": 55}

    return {"color": "amarillo", "razones": ["Datos insuficientes"], "score": 50}


COLORES = {"verde": "#1DB954", "amarillo": "#F5B700", "rojo": "#E63946"}
ETIQUETAS = {
    "verde": "🟢 OPORTUNIDAD DE ALTA PROBABILIDAD",
    "amarillo": "🟡 PRECAUCIÓN / LISTA DE SEGUIMIENTO",
    "rojo": "🔴 NO COMPRAR / DESCARTAR",
}


def backtest_estrategia(df_tec: pd.DataFrame) -> dict:
    df = df_tec.dropna(subset=["EMA200", "RSI14"]).copy()
    if len(df) < 30:
        return None

    df["retorno_diario"] = df["Close"].pct_change().fillna(0)
    df["en_mercado"] = ((df["Close"] > df["EMA200"]) & (df["RSI14"].between(40, 70))).astype(int)
    df["retorno_estrategia"] = df["retorno_diario"] * df["en_mercado"].shift(1).fillna(0)

    df["equity_estrategia"] = (1 + df["retorno_estrategia"]).cumprod()
    df["equity_buyhold"] = (1 + df["retorno_diario"]).cumprod()

    retorno_total_estrategia = df["equity_estrategia"].iloc[-1] - 1
    retorno_total_buyhold = df["equity_buyhold"].iloc[-1] - 1

    cummax = df["equity_estrategia"].cummax()
    drawdown = (df["equity_estrategia"] - cummax) / cummax
    max_drawdown = drawdown.min()

    dias_en_mercado = df[df["en_mercado"].shift(1).fillna(0) == 1]
    win_rate = (dias_en_mercado["retorno_diario"] > 0).mean() if len(dias_en_mercado) > 0 else np.nan

    return {
        "df": df,
        "retorno_estrategia": retorno_total_estrategia,
        "retorno_buyhold": retorno_total_buyhold,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "dias_en_mercado_pct": df["en_mercado"].mean(),
    }


def calcular_tamano_posicion(capital_total: float, riesgo_pct: float, precio_entrada: float, precio_stop: float):
    if precio_entrada is None or precio_stop is None or precio_entrada == precio_stop:
        return None
    riesgo_dinero = capital_total * (riesgo_pct / 100)
    diferencia = abs(precio_entrada - precio_stop)
    n_acciones = riesgo_dinero / diferencia
    monto_invertido = n_acciones * precio_entrada
    return {
        "riesgo_dinero": riesgo_dinero,
        "n_acciones": n_acciones,
        "monto_invertido": monto_invertido,
        "pct_del_capital": (monto_invertido / capital_total) * 100 if capital_total else None,
    }


# =============================================================================
# SEC EDGAR — cross-check gratuito y público de fundamentales reales
# =============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def obtener_mapa_tickers_sec():
    """Descarga el mapa oficial ticker -> CIK que publica la SEC (gratuito, público)."""
    try:
        headers = {"User-Agent": SEC_USER_AGENT}
        r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=10)
        data = r.json()
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    except Exception:
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def obtener_datos_sec(cik: str):
    """Trae los 'company facts' XBRL de un CIK específico. Puede fallar (empresa
    sin ciertos tags); en ese caso se marcan los campos como N/D, nunca se inventan."""
    if not cik:
        return None
    try:
        headers = {"User-Agent": SEC_USER_AGENT}
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _ultimo_valor_anual(facts: dict, tag: str):
    """Extrae el valor anual (10-K) más reciente de un tag us-gaap específico."""
    try:
        unidades = facts["facts"]["us-gaap"][tag]["units"]
        clave_unidad = "USD" if "USD" in unidades else list(unidades.keys())[0]
        registros = [r for r in unidades[clave_unidad] if r.get("form") == "10-K"]
        if not registros:
            return None
        registros.sort(key=lambda r: r.get("end", ""))
        return registros[-1]["val"]
    except Exception:
        return None


def cruzar_con_sec(ticker: str, mapa_cik: dict):
    """Devuelve ROE y Margen Operativo calculados desde datos oficiales de la SEC,
    para comparar contra Yahoo Finance. None si no se pudo obtener con certeza."""
    cik = mapa_cik.get(ticker.upper())
    if not cik:
        return None
    facts = obtener_datos_sec(cik)
    if not facts:
        return None

    net_income = _ultimo_valor_anual(facts, "NetIncomeLoss")
    equity = _ultimo_valor_anual(facts, "StockholdersEquity")
    revenues = _ultimo_valor_anual(facts, "Revenues") or _ultimo_valor_anual(
        facts, "RevenueFromContractWithCustomerExcludingAssessedTax"
    )
    op_income = _ultimo_valor_anual(facts, "OperatingIncomeLoss")

    roe_sec = (net_income / equity) if (net_income and equity and equity != 0) else None
    margen_sec = (op_income / revenues) if (op_income and revenues and revenues != 0) else None

    if roe_sec is None and margen_sec is None:
        return None
    return {"roe_sec": roe_sec, "margen_sec": margen_sec}


def comparar_yahoo_sec(valor_yahoo, valor_sec, tolerancia=0.20):
    """Compara un valor de Yahoo contra el de SEC. Devuelve una etiqueta de coincidencia."""
    if valor_yahoo is None or valor_sec is None:
        return "N/D"
    if valor_sec == 0:
        return "N/D"
    diferencia_relativa = abs(valor_yahoo - valor_sec) / abs(valor_sec)
    if diferencia_relativa <= tolerancia:
        return "✅ Verificado SEC"
    return "⚠️ Difiere de SEC"


# =============================================================================
# ENCABEZADO Y CONTROL DE NAVEGACIÓN
# =============================================================================
col_h1, col_h2 = st.columns([0.8, 0.2])

with col_h1:
    st.title("🚦 Arigael — Semáforo de Inversión y Simulador de Mercado")
    st.caption("Herramienta educativa de apoyo a la decisión y simulación de trading. **No es asesoría financiera.**")

with col_h2:
    st.markdown("<div class='header-author'>Autor: Mgs. César Carrión Aguirre</div>", unsafe_allow_html=True)
    img_b64 = obtener_base64_imagen("arigael_2.jpeg")
    if img_b64:
        st.markdown(f'<img src="{img_b64}" style="width: 100%; max-width: 180px; border-radius: 8px;">', unsafe_allow_html=True)

opcion_pestana = st.radio(
    "Selecciona un módulo:",
    [
        "📊 Análisis & Semáforo",
        "🎮 Simulador de Operaciones (Comercio de Papel)",
        "🏆 Top 40 Value Investing (Buffett & Munger)",
    ],
    horizontal=True,
    label_visibility="collapsed",
)

# =============================================================================
# BARRA LATERAL DINÁMICA (Panel de Control por pestaña)
# =============================================================================
with st.sidebar:
    st.markdown("### 🎛️ Panel de Control")

    if "controles_activos" not in st.session_state:
        st.session_state["controles_activos"] = True

    btn_texto = "🔓 Controles Habilitados" if st.session_state["controles_activos"] else "🔒 Controles Bloqueados"
    if st.button(btn_texto, use_container_width=True, type="secondary" if st.session_state["controles_activos"] else "primary"):
        st.session_state["controles_activos"] = not st.session_state["controles_activos"]
        st.rerun()

    controles_deshabilitados = not st.session_state["controles_activos"]
    st.divider()

    if opcion_pestana == "📊 Análisis & Semáforo":
        st.header("🔎 Buscador de Activo")
        ticker_input = (
            st.text_input("Símbolo (acción, ETF...)", value="AAPL", disabled=controles_deshabilitados)
            .strip().upper()
        )
        periodo = st.selectbox("Período histórico", ["1y", "2y", "5y", "10y"], index=1, disabled=controles_deshabilitados)

        st.divider()
        st.header("🛡️ Gestión de Riesgo")
        capital_total = st.number_input("Capital total disponible ($)", min_value=0.0, value=10000.0, step=100.0, disabled=controles_deshabilitados)
        riesgo_pct = st.slider("Riesgo máximo por operación (%)", 0.5, 10.0, 2.0, 0.5, disabled=controles_deshabilitados)
        stop_loss_pct = st.slider("Stop-loss (% caída aceptable)", 3.0, 30.0, 15.0, 1.0, disabled=controles_deshabilitados)

        st.divider()
        analizar = st.button("🔄 Forzar Datos Frescos", type="primary", use_container_width=True, disabled=controles_deshabilitados)

    elif opcion_pestana == "🎮 Simulador de Operaciones (Comercio de Papel)":
        st.header("⚙️ Herramientas del Simulador")
        st.markdown("**🎯 Alertas de Take-Profit / Stop-Loss Global**")
        tp_global = st.number_input("Objetivo Ganancia Global (%)", value=10.0, step=1.0, disabled=controles_deshabilitados)
        sl_global = st.number_input("Límite Pérdida Global (%)", value=-5.0, step=1.0, disabled=controles_deshabilitados)

        st.divider()
        st.markdown("**⚖️ Gestión y Balance de Portafolio**")
        max_peso_activo = st.slider("Máxima exposición por activo (%)", 10, 100, 30, 5, disabled=controles_deshabilitados)

        st.divider()
        st.markdown("**🔄 Gestión de Capital Virtual**")
        if st.button("⚠️ Resetear Portafolio ($100k)", use_container_width=True, type="primary", disabled=controles_deshabilitados):
            guardar_simulador({"efectivo": 100000.0, "posiciones": {}})
            st.success("Simulador restablecido a $100,000 USD.")
            st.rerun()

        st.divider()
        st.markdown("**💵 Recordatorio de Aporte Periódico (DCA)**")
        dca_data_sidebar = cargar_dca()
        nuevo_monto_dca = st.number_input(
            "Monto sugerido por aporte ($)", min_value=0.0,
            value=float(dca_data_sidebar["monto_sugerido"]), step=10.0,
            disabled=controles_deshabilitados,
        )
        opciones_frecuencia = [7, 15, 30, 60, 90]
        idx_frecuencia = opciones_frecuencia.index(dca_data_sidebar["frecuencia_dias"]) if dca_data_sidebar["frecuencia_dias"] in opciones_frecuencia else 2
        nueva_frecuencia_dca = st.selectbox(
            "Frecuencia de aporte", opciones_frecuencia, index=idx_frecuencia,
            format_func=lambda d: f"Cada {d} días", disabled=controles_deshabilitados,
        )
        if nuevo_monto_dca != dca_data_sidebar["monto_sugerido"] or nueva_frecuencia_dca != dca_data_sidebar["frecuencia_dias"]:
            dca_data_sidebar["monto_sugerido"] = nuevo_monto_dca
            dca_data_sidebar["frecuencia_dias"] = nueva_frecuencia_dca
            guardar_dca(dca_data_sidebar)

        if st.button("✅ Marcar aporte de hoy como realizado", use_container_width=True, disabled=controles_deshabilitados):
            dca_data_sidebar["proximo_aporte"] = (datetime.now() + pd.Timedelta(days=dca_data_sidebar["frecuencia_dias"])).strftime("%Y-%m-%d")
            guardar_dca(dca_data_sidebar)
            st.success("¡Aporte registrado! Recordatorio actualizado.")
            st.rerun()

        ticker_input, periodo, capital_total, riesgo_pct, stop_loss_pct, analizar = "AAPL", "2y", 10000.0, 2.0, 15.0, False

    else:
        st.header("🎯 Criterios Munger-Buffett")
        st.markdown("""
            **Métrica Sensible Clave (Foso Económico):**
            * **ROIC Elevado (>15%):** Eficiencia en la asignación de capital.
            * **Margen Operativo Sostenible:** Poder de fijación de precios (Pricing Power).
            * **Deuda Bajo Control:** Solvencia y resiliencia ante ciclos económicos.
            """)
        st.info("📋 Fuentes de datos: **Yahoo Finance** (métricas de mercado) cruzado con **SEC EDGAR** (estados financieros oficiales 10-K, gratuitos y públicos) quel se puede.")
        ticker_input, periodo, capital_total, riesgo_pct, stop_loss_pct, analizar = "AAPL", "2y", 10000.0, 2.0, 15.0, False

    st.divider()
    st.subheader("⏱️ Configuración en Vivo")
    modo_envivo = st.checkbox("Actualización automática en vivo", value=False, disabled=controles_deshabilitados)
    intervalo = st.slider("Frecuencia (segundos)", min_value=5, max_value=60, value=15, disabled=controles_deshabilitados)


# =============================================================================
# DESCARGA DE DATOS GENERAL (para Módulo 1)
# =============================================================================
if analizar:
    descargar_datos.clear()

hist, info, noticias = descargar_datos(ticker_input, periodo)

if hist is None:
    st.error(f"No se encontraron datos para '{ticker_input}'. Verifica el símbolo.")
    st.stop()

df_tec = agregar_indicadores_tecnicos(hist)
fund = extraer_fundamentales(info or {})
resultado_semaforo = evaluar_semaforo(fund, df_tec)
backtest = backtest_estrategia(df_tec)

precio_actual = df_tec["Close"].iloc[-1]
precio_stop_sugerido = precio_actual * (1 - stop_loss_pct / 100)
nombre_empresa = (info or {}).get("longName", ticker_input)


# =============================================================================
# MÓDULO 1: ANÁLISIS Y SEMÁFORO
# =============================================================================
if opcion_pestana == "📊 Análisis & Semáforo":
    st.subheader(f"{nombre_empresa} ({ticker_input}) — ${precio_actual:,.2f}")

    col_verde, col_rojo = st.columns(2)

    with col_verde:
        st.markdown("<div style='border:3px solid #1DB954;border-radius:10px;padding:15px;'>", unsafe_allow_html=True)
        st.markdown("### 🟢 Diagnóstico (Educativo)")

        st.markdown("**📊 Análisis Técnico**")
        precio_hoy = df_tec["Close"].iloc[-1]
        ema50_hoy = df_tec["EMA50"].iloc[-1]
        ema200_hoy = df_tec["EMA200"].iloc[-1]
        rsi_hoy = df_tec["RSI14"].iloc[-1]

        c1, c2, c3 = st.columns(3)
        mostrar_metrica(c1, "Tendencia", f"${precio_hoy:,.2f}", calif_tendencia(precio_hoy, ema50_hoy, ema200_hoy))
        c2.markdown("<div style='font-size:13px;color:#666;'>EMA 50 / 200</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='font-size:15px;'>EMA50: <b>${ema50_hoy:,.2f}</b><br>EMA200: <b>${ema200_hoy:,.2f}</b></div>", unsafe_allow_html=True)
        mostrar_metrica(c3, "RSI (14)", f"{rsi_hoy:.1f}", calif_rsi(rsi_hoy))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_tec.index, y=df_tec["Close"], name="Precio", line=dict(color="#333")))
        fig.add_trace(go.Scatter(x=df_tec.index, y=df_tec["EMA50"], name="EMA 50", line=dict(color="#F5B700")))
        fig.add_trace(go.Scatter(x=df_tec.index, y=df_tec["EMA200"], name="EMA 200", line=dict(color="#E63946")))
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**🏛️ Análisis Fundamental**")
        roic_txt = f"{fund['ROIC_aprox_ROE']*100:.1f}%" if fund["ROIC_aprox_ROE"] is not None else "N/D"
        peg_txt = f"{fund['PEG']:.2f}" if fund["PEG"] is not None else "N/D"
        deuda_txt = f"{fund['Deuda_EBITDA']:.2f}x" if fund["Deuda_EBITDA"] is not None else "N/D"
        fcf_txt = f"{fund['FCF_Yield']*100:.1f}%" if fund["FCF_Yield"] is not None else "N/D"

        f1, f2 = st.columns(2)
        mostrar_metrica(f1, "ROIC (ROE)", roic_txt, calif_roic(fund["ROIC_aprox_ROE"]))
        mostrar_metrica(f2, "Deuda / EBITDA", deuda_txt, calif_deuda_ebitda(fund["Deuda_EBITDA"]))
        mostrar_metrica(f1, "PEG Ratio", peg_txt, calif_peg(fund["PEG"]))
        mostrar_metrica(f2, "FCF Yield", fcf_txt, calif_fcf_yield(fund["FCF_Yield"]))

        # --- INDICADOR PRINCIPAL, AGRANDADO (pedido explícito) ---
        st.markdown("---")
        st.markdown(
            f"""
            <div style="background-color:{COLORES[resultado_semaforo['color']]};color:white;
                        padding:22px;border-radius:14px;text-align:center;
                        box-shadow:0 4px 14px rgba(0,0,0,0.35);">
                <div style="font-size:26px;font-weight:900;letter-spacing:0.5px;line-height:1.3;">
                    {ETIQUETAS[resultado_semaforo['color']]}
                </div>
                <div style="font-size:15px;font-weight:600;margin-top:6px;opacity:0.9;">
                    Score interno: {resultado_semaforo['score']}/100
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for r in resultado_semaforo["razones"]:
            st.write(f"• {r}")

        # Registro automático para el historial de precisión (máx. 1 por ticker/día)
        registrar_señal_bitacora(ticker_input, resultado_semaforo["color"], precio_actual)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_rojo:
        st.markdown("<div style='border:3px solid #E63946;border-radius:10px;padding:15px;'>", unsafe_allow_html=True)
        st.markdown("### 🔴 Backtesting y Gestión de Riesgo")

        if backtest is not None:
            calif_estrat = calif_backtest_vs_buyhold(backtest["retorno_estrategia"], backtest["retorno_buyhold"])
            b1, b2 = st.columns(2)
            mostrar_metrica(b1, "Retorno Estrategia", f"{backtest['retorno_estrategia']*100:,.1f}%", calif_estrat)
            mostrar_metrica(b2, "Retorno Buy & Hold", f"{backtest['retorno_buyhold']*100:,.1f}%", "N/D")
            b3, b4 = st.columns(2)
            mostrar_metrica(b3, "Máx. Caída", f"{backtest['max_drawdown']*100:,.1f}%", calif_drawdown(backtest["max_drawdown"]))
            b4.metric("% Días Mercado", f"{backtest['dias_en_mercado_pct']*100:,.0f}%")

            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=backtest["df"].index, y=backtest["df"]["equity_estrategia"], name="Estrategia", line=dict(color="#1DB954")))
            fig_bt.add_trace(go.Scatter(x=backtest["df"].index, y=backtest["df"]["equity_buyhold"], name="Buy & Hold", line=dict(color="#888", dash="dot")))
            fig_bt.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
            st.plotly_chart(fig_bt, use_container_width=True)

        st.markdown("**💰 Calculadora de Tamaño de Posición**")
        clave_estado = f"{ticker_input}_{stop_loss_pct}"
        if st.session_state.get("_clave_stop_loss") != clave_estado:
            st.session_state["precio_stop_manual"] = float(round(precio_stop_sugerido, 2))
            st.session_state["_clave_stop_loss"] = clave_estado

        precio_stop_manual = st.number_input("Precio de Stop-Loss ($)", min_value=0.0, step=0.5, key="precio_stop_manual", disabled=controles_deshabilitados)
        posicion = calcular_tamano_posicion(capital_total, riesgo_pct, precio_actual, precio_stop_manual)
        if posicion:
            p1, p2 = st.columns(2)
            p1.metric("Dinero en Riesgo", f"${posicion['riesgo_dinero']:,.2f}")
            p2.metric("Acciones Sugeridas", f"{posicion['n_acciones']:.2f}")
            p3, p4 = st.columns(2)
            p3.metric("Monto a Invertir", f"${posicion['monto_invertido']:,.2f}")
            p4.metric("% del Capital", f"{posicion['pct_del_capital']:,.1f}%")

        st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # HISTORIAL DE PRECISIÓN DEL SEMÁFORO (evidencia real, no promesa)
    # =========================================================================
    st.divider()
    with st.expander("📈 Historial de Precisión del Semáforo — evidencia real, no una promesa"):
        st.caption(
            "Cada vez que analizas un ticker aquí, se guarda automáticamente la señal (máx. 1 vez "
            "por ticker por día). Cuando pase suficiente tiempo, puedes ver si esas señales realmente "
            "acertaron o no — con datos reales, no con marketing."
        )
        horizonte_dias = st.number_input(
            "Evaluar señales que ya tengan al menos esta cantidad de días",
            min_value=7, max_value=365, value=90, step=1,
            help="Tú eliges qué significa 'suficiente tiempo' para juzgar una señal.",
        )
        if st.button("🔄 Calcular precisión histórica"):
            with st.spinner("Comparando señales pasadas contra lo que realmente pasó..."):
                st.session_state["_resultado_historial"] = evaluar_precision_historial(int(horizonte_dias))

        resultado_historial = st.session_state.get("_resultado_historial")
        if resultado_historial is None:
            st.info("Presiona el botón para calcular. Necesitas señales registradas con suficiente antigüedad.")
        elif resultado_historial["resumen"] is None:
            st.info(
                "Aún no hay señales con al menos esa cantidad de días registradas. "
                "Sigue usando el Módulo 1 con distintos tickers y vuelve más adelante."
            )
        else:
            r = resultado_historial["resumen"]
            h1, h2, h3 = st.columns(3)
            h1.metric("Señales evaluadas", r["total_evaluadas"])
            h2.metric(
                "Verdes que acertaron",
                f"{r['verdes_acierto_pct']:.0f}%" if r["verdes_acierto_pct"] is not None else "N/D",
                help=f"De {r['verdes_evaluadas']} señales verdes maduras",
            )
            h3.metric(
                "Rojas que acertaron",
                f"{r['rojos_acierto_pct']:.0f}%" if r["rojos_acierto_pct"] is not None else "N/D",
                help=f"De {r['rojos_evaluadas']} señales rojas maduras",
            )
            st.dataframe(resultado_historial["tabla"], use_container_width=True, hide_index=True)
            st.caption(
                "⚠️ Con pocas señales evaluadas, estos porcentajes no son estadísticamente "
                "confiables — son un indicio, no una prueba. Entre más señales acumules con el "
                "tiempo, más significativo se vuelve este historial."
            )


# =============================================================================
# MÓDULO 2: SIMULADOR DE TRADING EN VIVO (PAPER TRADING)
# =============================================================================
elif opcion_pestana == "🎮 Simulador de Operaciones (Comercio de Papel)":
    sim_data = cargar_simulador()
    efectivo = sim_data["efectivo"]
    posiciones = sim_data["posiciones"]

    valor_portafolio_acciones = 0.0
    filas_tabla = []
    datos_treemap = []

    for sim_ticker, datos in posiciones.items():
        cant = datos["cantidad"]
        p_promedio = datos["precio_promedio"]
        p_actual = obtener_precio_instantaneo(sim_ticker)
        if p_actual == 0.0:
            p_actual = p_promedio

        val_pos = cant * p_actual
        pnl = (p_actual - p_promedio) * cant
        pnl_pct = ((p_actual - p_promedio) / p_promedio) * 100 if p_promedio > 0 else 0.0

        valor_portafolio_acciones += val_pos
        filas_tabla.append({
            "Ticker": sim_ticker, "Cantidad": cant,
            "Precio Compra": f"${p_promedio:,.2f}", "Precio Actual": f"${p_actual:,.2f}",
            "Valor Mercado": f"${val_pos:,.2f}", "Ganancia/Pérdida ($)": f"${pnl:+,.2f}",
            "Rendimiento (%)": f"{pnl_pct:+.3f}%",
        })
        datos_treemap.append({"Ticker": sim_ticker, "Valor": val_pos, "pnl_pct": pnl_pct})

    patrimonio_total = efectivo + valor_portafolio_acciones
    pnl_total = patrimonio_total - 100000.0
    pnl_total_pct = (pnl_total / 100000.0) * 100

    # =========================================================================
    # RECORDATORIO NÚCLEO/SATÉLITE + ALERTA DE CONCENTRACIÓN + APORTE DCA
    # =========================================================================
    st.info(
        "💡 **Recordatorio de estrategia:** lo que respalda tu capital a largo plazo es la "
        "diversificación, no encontrar la acción perfecta. Idealmente, la mayoría de tu capital "
        "real debería estar en algo diversificado (ej. un ETF amplio como el S&P 500) como "
        "**núcleo estable**, y usar acciones individuales como esta solo como una porción "
        "pequeña y acotada ('satélite') para aprender y arriesgar con criterio."
    )

    if patrimonio_total > 0 and datos_treemap:
        posiciones_concentradas = [
            (d["Ticker"], d["Valor"] / patrimonio_total * 100)
            for d in datos_treemap
            if (d["Valor"] / patrimonio_total * 100) > 25
        ]
        if posiciones_concentradas:
            detalle = ", ".join(f"{t} ({p:.0f}%)" for t, p in posiciones_concentradas)
            st.warning(
                f"⚠️ **Concentración alta:** {detalle} representa(n) más del 25% de tu "
                f"portafolio. Una sola mala noticia en esa empresa golpearía una porción grande "
                f"de tu capital simulado. Considera diversificar en más posiciones."
            )

    dca_data = cargar_dca()
    fecha_proxima = pd.to_datetime(dca_data["proximo_aporte"])
    dias_restantes = (fecha_proxima - pd.Timestamp(datetime.now().date())).days
    if dias_restantes <= 0:
        st.error(f"💵 **¡Toca tu aporte periódico!** Monto sugerido: ${dca_data['monto_sugerido']:,.2f} (configúralo en la barra lateral)")
    else:
        st.caption(f"💵 Próximo aporte sugerido en {dias_restantes} días (${dca_data['monto_sugerido']:,.2f}) — configúralo en la barra lateral.")

    st.markdown("---")

    col_encabezado_izq, col_encabezado_der = st.columns([2.0, 2.0], gap="large")

    with col_encabezado_izq:
        st.subheader("🎮 Simulador de Operaciones en Tiempo Real")
        st.caption("Opera con $100,000 USD virtuales. Las transacciones se guardan en tu equipo.")

        m1, m2, m3 = st.columns(3)
        m1.metric("Patrimonio Total", f"${patrimonio_total:,.2f}")
        m2.metric("Efectivo Disponible", f"${efectivo:,.2f}")
        m3.metric("Invertido Acciones", f"${valor_portafolio_acciones:,.2f}")

        st.markdown("---")
        pnl_color = "#1DB954" if pnl_total >= 0 else "#E63946"
        pnl_comentario = "Vas ganando 🚀" if pnl_total >= 0 else "Vas perdiendo 📉"

        st.markdown(
            f"""
            <div style="background-color:#1e222d; padding:15px; border-radius:12px; border:2px solid {pnl_color}; text-align:center;">
                <div style="font-size:16px; color:#aaa; font-weight:600;">Ganancia / Pérdida Total de la Cuenta</div>
                <div style="font-size:26px; font-weight:bold; color:white;">${pnl_total:+,.2f}</div>
                <div style="font-size:55px; font-weight:900; color:{pnl_color}; line-height:1.1; margin:8px 0;">
                    {pnl_total_pct:+.3f}%
                </div>
                <div style="font-size:20px; font-weight:800; color:{pnl_color}; text-transform:uppercase; letter-spacing:1px;">
                    {pnl_comentario}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_encabezado_der:
        # --- MAPA DE CALOR AGRANDADO (pedido explícito) ---
        st.markdown("<div style='font-size:18px;font-weight:800;margin-bottom:6px;'>🔥 Mapa de Calor del Rendimiento de tu Portafolio</div>", unsafe_allow_html=True)

        if datos_treemap:
            colores_treemap = ["#1DB954" if d["pnl_pct"] >= 0 else "#E63946" for d in datos_treemap]
            # El TAMAÑO de cada caja representa cuánto dinero tienes invertido ahí
            # (peso real en tu portafolio), no el % de ganancia/pérdida — así una
            # posición recién comprada con 0% de cambio sigue siendo visible.
            valores_tamano = [max(d["Valor"], 0.01) for d in datos_treemap]

            fig_mapa = go.Figure(
                go.Treemap(
                    labels=[d["Ticker"] for d in datos_treemap],
                    parents=[""] * len(datos_treemap),
                    values=valores_tamano,
                    customdata=[d["pnl_pct"] for d in datos_treemap],
                    texttemplate="<b>%{label}</b><br>%{customdata:+.3f}%",
                    textfont=dict(size=24, color="white", family="Arial Black"),
                    marker=dict(colors=colores_treemap, line=dict(width=2, color="#0e1117")),
                    hovertemplate="<b>%{label}</b><br>Rendimiento: %{customdata:+.3f}%<extra></extra>",
                )
            )
            fig_mapa.update_layout(margin=dict(t=2, l=2, r=2, b=2), height=480)
            st.plotly_chart(fig_mapa, use_container_width=True)
        else:
            st.info("Compra activos para activar el mapa de calor.")

    st.divider()
    col_trade, col_pos = st.columns([1, 1.5])

    with col_trade:
        st.subheader("🛒 Ejecutar Operación")
        sim_ticker_op = st.text_input("Ticker a operar:", value="AAPL", key="sim_ticker_input", disabled=controles_deshabilitados).upper()
        cant_op = st.number_input("Cantidad de acciones:", min_value=1, value=10, step=1)

        p_envivo = obtener_precio_instantaneo(sim_ticker_op)
        costo_total_op = p_envivo * cant_op
        st.info(f"Precio en vivo de **{sim_ticker_op}**: **${p_envivo:,.2f}**\n\nMonto total: **${costo_total_op:,.2f}**")

        b_compra, b_venta = st.columns(2)
        if b_compra.button("🟢 COMPRAR", use_container_width=True, type="primary", disabled=controles_deshabilitados):
            if p_envivo <= 0:
                st.error("No se pudo obtener el precio en vivo del activo.")
            elif efectivo >= costo_total_op:
                sim_data["efectivo"] -= costo_total_op
                if sim_ticker_op in sim_data["posiciones"]:
                    cant_prev = sim_data["posiciones"][sim_ticker_op]["cantidad"]
                    p_prev = sim_data["posiciones"][sim_ticker_op]["precio_promedio"]
                    nuevo_p = ((cant_prev * p_prev) + costo_total_op) / (cant_prev + cant_op)
                    sim_data["posiciones"][sim_ticker_op]["cantidad"] += cant_op
                    sim_data["posiciones"][sim_ticker_op]["precio_promedio"] = nuevo_p
                else:
                    sim_data["posiciones"][sim_ticker_op] = {"cantidad": cant_op, "precio_promedio": p_envivo}
                guardar_simulador(sim_data)
                st.success(f"¡Compradas {cant_op} acciones de {sim_ticker_op}!")
                st.rerun()
            else:
                st.error("Fondos en efectivo insuficientes.")

        if b_venta.button("🔴 VENDER", use_container_width=True, disabled=controles_deshabilitados):
            if sim_ticker_op in sim_data["posiciones"] and sim_data["posiciones"][sim_ticker_op]["cantidad"] >= cant_op:
                sim_data["efectivo"] += costo_total_op
                sim_data["posiciones"][sim_ticker_op]["cantidad"] -= cant_op
                if sim_data["posiciones"][sim_ticker_op]["cantidad"] == 0:
                    del sim_data["posiciones"][sim_ticker_op]
                guardar_simulador(sim_data)
                st.success(f"¡Vendidas {cant_op} acciones de {sim_ticker_op}!")
                st.rerun()
            else:
                st.error("No posees suficientes acciones para vender.")

    with col_pos:
        st.subheader("💼 Portafolio Virtual Activo")
        if filas_tabla:
            st.dataframe(pd.DataFrame(filas_tabla), use_container_width=True, hide_index=True)
        else:
            st.info("Aún no tienes posiciones abiertas. Realiza una compra para comenzar.")

    st.divider()
    st.subheader("📈 Inspector Gráfico de Posiciones Activas")

    if posiciones:
        ticker_sel = st.selectbox("Selecciona un activo de tu portafolio:", options=list(posiciones.keys()), key="inspector_select_ticker", disabled=controles_deshabilitados)
        if ticker_sel:
            datos_pos = posiciones[ticker_sel]
            cant_pos = datos_pos["cantidad"]
            p_compra = datos_pos["precio_promedio"]
            hist_sim = obtener_historial_inspector(ticker_sel, periodo="6mo")

            if hist_sim is not None and not hist_sim.empty:
                p_actual_sim = hist_sim["Close"].iloc[-1]
                pnl_sim = (p_actual_sim - p_compra) * cant_pos
                pnl_pct_sim = ((p_actual_sim - p_compra) / p_compra) * 100 if p_compra > 0 else 0

                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                col_i1.metric("Acciones Poseídas", f"{cant_pos}")
                col_i2.metric("Precio Promedio", f"${p_compra:,.2f}")
                col_i3.metric("Precio Actual", f"${p_actual_sim:,.2f}")
                col_i4.metric("PnL de Posición", f"${pnl_sim:+,.2f}", f"{pnl_pct_sim:+.3f}%")

                eje_x = hist_sim["Date"] if "Date" in hist_sim.columns else hist_sim.index
                fig_pos = go.Figure()
                fig_pos.add_trace(go.Scatter(x=eje_x, y=hist_sim["Close"], mode="lines", name=f"Precio {ticker_sel}", line=dict(color="#2962FF", width=2.5)))
                color_linea_compra = "#1DB954" if p_actual_sim >= p_compra else "#E63946"
                fig_pos.add_hline(y=p_compra, line_dash="dash", line_color=color_linea_compra, line_width=2,
                                   annotation_text=f" Tu Precio de Compra (${p_compra:,.2f})", annotation_position="bottom right")
                fig_pos.update_layout(title=f"Evolución de {ticker_sel} vs. Tu Precio de Entrada", height=380,
                                       margin=dict(l=10, r=10, t=35, b=10), hovermode="x unified")
                st.plotly_chart(fig_pos, use_container_width=True)


# =============================================================================
# MÓDULO 3: TOP 40 VALUE INVESTING (BUFFETT & MUNGER) — Yahoo + SEC EDGAR
# =============================================================================
else:
    st.subheader("🏆 Top 40 Acciones Value por Sectores (Metodología Munger-Buffett)")
    st.caption(
        "Filtro fundamental basado en **ROIC Alto**, **Foso Económico (Moat)**, "
        "**Márgenes Operativos Saludables** y **Bajo Nivel de Deuda**. "
        "Datos de **Yahoo Finance**, cruzados contra estados financieros oficiales de **SEC EDGAR** cuando están disponibles."
    )
    st.info(
        "💡 Este Top 40 sirve para **investigar candidatas**, no para concentrar todo tu capital "
        "aquí. Considera usarlo solo para la porción 'satélite' pequeña de tu portafolio, "
        "manteniendo la mayoría en algo diversificado como núcleo estable."
    )

    # Universo de 40 empresas de calidad (Munger Quality Compounders) por sectores.
    # Nota: se corrigió "TSMC" -> "TSM" (símbolo real en Yahoo Finance).
    top_40_empresas = [
        {"Ticker": "AAPL", "Sector": "Tecnología", "Moat": "Ecosistema / Marca"},
        {"Ticker": "MSFT", "Sector": "Tecnología", "Moat": "Efecto Red / Switching Costs"},
        {"Ticker": "NVDA", "Sector": "Tecnología", "Moat": "Liderazgo Tecnológico / Software"},
        {"Ticker": "GOOGL", "Sector": "Servicios de Comunicación", "Moat": "Efecto Red / Datos"},
        {"Ticker": "META", "Sector": "Servicios de Comunicación", "Moat": "Efecto Red Social"},
        {"Ticker": "AMZN", "Sector": "Consumo Cíclico", "Moat": "Escala / Logística"},
        {"Ticker": "TSM", "Sector": "Tecnología", "Moat": "Ventaja de Costo y Escala Fab"},
        {"Ticker": "BRK-B", "Sector": "Financiero", "Moat": "Capital Reconstruible / Diversificación"},
        {"Ticker": "JNJ", "Sector": "Salud", "Moat": "Patentes y Marcas Globales"},
        {"Ticker": "LLY", "Sector": "Salud", "Moat": "Propiedad Intelectual / Farmacéutica"},
        {"Ticker": "PG", "Sector": "Consumo Defensivo", "Moat": "Liderazgo en Marca y Distribución"},
        {"Ticker": "KO", "Sector": "Consumo Defensivo", "Moat": "Red de Distribución Global"},
        {"Ticker": "PEP", "Sector": "Consumo Defensivo", "Moat": "Economías de Escala"},
        {"Ticker": "COST", "Sector": "Consumo Defensivo", "Moat": "Suscripción y Ventaja de Costo"},
        {"Ticker": "V", "Sector": "Servicios Financieros", "Moat": "Efecto Red / Duopolio"},
        {"Ticker": "MA", "Sector": "Servicios Financieros", "Moat": "Efecto Red / Duopolio"},
        {"Ticker": "HD", "Sector": "Consumo Cíclico", "Moat": "Escala y Ubicación Geográfica"},
        {"Ticker": "UNH", "Sector": "Salud", "Moat": "Integración Vertical / Escala"},
        {"Ticker": "ABT", "Sector": "Salud", "Moat": "Diversificación Dispositivos Médicos"},
        {"Ticker": "XOM", "Sector": "Energía", "Moat": "Ventaja de Costo de Extracción"},
        {"Ticker": "AXP", "Sector": "Servicios Financieros", "Moat": "Marca / Red de Cliente Premium"},
        {"Ticker": "TJX", "Sector": "Consumo Cíclico", "Moat": "Escala en Retail de Descuento"},
        {"Ticker": "MCD", "Sector": "Consumo Cíclico", "Moat": "Franquicia / Bienes Raíces"},
        {"Ticker": "SBUX", "Sector": "Consumo Cíclico", "Moat": "Marca / Fidelización"},
        {"Ticker": "ADBE", "Sector": "Tecnología", "Moat": "Suscripción / Switching Costs"},
        {"Ticker": "ORCL", "Sector": "Tecnología", "Moat": "Switching Costs Empresariales"},
        {"Ticker": "CRM", "Sector": "Tecnología", "Moat": "Ecosistema Empresarial"},
        {"Ticker": "TXN", "Sector": "Tecnología", "Moat": "Escala en Semiconductores Analógicos"},
        {"Ticker": "ADP", "Sector": "Servicios Financieros", "Moat": "Switching Costs / Nómina"},
        {"Ticker": "SPGI", "Sector": "Servicios Financieros", "Moat": "Duopolio de Calificación Crediticia"},
        {"Ticker": "MCO", "Sector": "Servicios Financieros", "Moat": "Duopolio de Calificación Crediticia"},
        {"Ticker": "BLK", "Sector": "Servicios Financieros", "Moat": "Escala en Gestión de Activos"},
        {"Ticker": "CB", "Sector": "Servicios Financieros", "Moat": "Disciplina de Suscripción (Seguros)"},
        {"Ticker": "PGR", "Sector": "Servicios Financieros", "Moat": "Ventaja de Datos (Seguros)"},
        {"Ticker": "SYK", "Sector": "Salud", "Moat": "Tecnología Médica Especializada"},
        {"Ticker": "ISRG", "Sector": "Salud", "Moat": "Cirugía Robótica / Patentes"},
        {"Ticker": "REGN", "Sector": "Salud", "Moat": "Propiedad Intelectual Biotecnológica"},
        {"Ticker": "DHR", "Sector": "Salud", "Moat": "Compounder Diversificado de Calidad"},
        {"Ticker": "LOW", "Sector": "Consumo Cíclico", "Moat": "Escala en Retail de Mejoras al Hogar"},
        {"Ticker": "CMG", "Sector": "Consumo Cíclico", "Moat": "Marca / Modelo Operativo Eficiente"},
    ]

    with st.spinner("Construyendo mapa oficial de tickers de la SEC..."):
        mapa_cik_sec = obtener_mapa_tickers_sec()

    def analizar_empresa_top40(emp):
        t = emp["Ticker"]
        try:
            ticker_obj = yf.Ticker(t)
            inf = ticker_obj.info or {}

            roe = inf.get("returnOnEquity", 0.0) or 0.0
            margen_op = inf.get("operatingMargins", 0.0) or 0.0
            total_debt = inf.get("totalDebt", 0.0) or 0.0
            ebitda = inf.get("ebitda", 1.0) or 1.0
            debt_ebitda = total_debt / ebitda if ebitda != 0 else 0.0
            fcf = inf.get("freeCashflow", 0.0) or 0.0
            mcap = inf.get("marketCap", 1.0) or 1.0
            fcf_yield = fcf / mcap if mcap != 0 else 0.0
            peg = inf.get("pegRatio", 0.0) or 0.0

            # Metodología sin cambios: Score Munger = ROIC/ROE + Margen + FCF Yield - Deuda
            score_munger = (roe * 40) + (margen_op * 30) + (fcf_yield * 20) - (min(debt_ebitda, 5) * 2)

            # Cross-check gratuito y público contra SEC EDGAR (informativo, no altera el score)
            sec_data = cruzar_con_sec(t, mapa_cik_sec)
            verificacion_sec = "N/D"
            if sec_data:
                verificacion_sec = comparar_yahoo_sec(roe, sec_data.get("roe_sec"))

            return {
                "Ticker": t, "error": False,
                "Empresa": inf.get("shortName", t),
                "Sector": emp["Sector"],
                "Foso Económico (Moat)": emp["Moat"],
                "ROIC/ROE": f"{roe * 100:.1f}%",
                "Margen Op.": f"{margen_op * 100:.1f}%",
                "Deuda/EBITDA": f"{debt_ebitda:.2f}x",
                "FCF Yield": f"{fcf_yield * 100:.1f}%",
                "PEG": f"{peg:.2f}" if peg else "N/D",
                "Verificación SEC": verificacion_sec,
                "Score Munger": round(score_munger, 2),
            }
        except Exception:
            return {"Ticker": t, "error": True}

    @st.cache_data(ttl=1800, show_spinner="Analizando 40 empresas: Yahoo Finance + cruce SEC EDGAR...")
    def construir_ranking_top40(_mapa_cik):
        with ThreadPoolExecutor(max_workers=6) as executor:
            resultados = list(executor.map(analizar_empresa_top40, top_40_empresas))

        errores = [r["Ticker"] for r in resultados if r.get("error")]
        validos = [r for r in resultados if not r.get("error")]

        df_rank = pd.DataFrame(validos)
        if not df_rank.empty:
            df_rank = df_rank.sort_values(by="Score Munger", ascending=False).reset_index(drop=True)
            df_rank.insert(0, "Rank", df_rank.index + 1)
            df_rank = df_rank.drop(columns=["error"])
        return df_rank, errores

    df_top40, errores_top40 = construir_ranking_top40(mapa_cik_sec)

    st.markdown("### 📊 Clasificación Compuesta (Munger Quality Score)")

    # --- SCORE MUNGER MÁS VISIBLE: columna resaltada con formato condicional ---
    if not df_top40.empty:
        st.dataframe(
            df_top40,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score Munger": st.column_config.ProgressColumn(
                    "Score Munger",
                    help="Puntaje compuesto: ROIC/ROE + Margen Operativo + FCF Yield − Deuda/EBITDA",
                    format="%.2f",
                    min_value=float(df_top40["Score Munger"].min()),
                    max_value=float(df_top40["Score Munger"].max()),
                ),
                "Rank": st.column_config.NumberColumn("Rank", format="%d"),
            },
            height=600,
        )

    if errores_top40:
        with st.expander(f"⚠️ {len(errores_top40)} tickers con ERROR DATOS (no incluidos en el ranking)"):
            st.write(", ".join(errores_top40))

    col_sec1, col_sec2 = st.columns([1, 1.4])
    with col_sec1:
        st.markdown("#### 🏛️ Los 4 Pilares del Value Investing Perfeccionado")
        st.write("""
        1. **Negocio Inteligible:** Comprensión clara de las ventajas competitivas.
        2. **Ventaja Competitiva Duradera (Moat):** Capacidad de proteger los beneficios de la competencia.
        3. **Management Capaz e Íntegro:** Asignación óptima del capital sobrante (mantenimiento vs. expansión).
        4. **Precio Razonable (Margin of Safety):** Comprar un gran negocio a un precio justo, en lugar de un negocio mediocre a precio de remate.
        """)
        st.caption(
            "⚠️ Este score es una heurística propia, no una recomendación de compra ni una "
            "validación estadística de resultados futuros. La columna 'Verificación SEC' "
            "indica si el ROE de Yahoo coincide razonablemente (±20%) con los estados "
            "financieros oficiales presentados ante el regulador — no valida el score en sí."
        )

    with col_sec2:
        # --- GRÁFICA DE BARRAS DE LAS 40, ILUSTRATIVA (pedido explícito) ---
        if not df_top40.empty:
            df_grafica = df_top40.sort_values(by="Score Munger", ascending=True)
            colores_barras = [
                "#0B6E4F" if v >= 70 else "#1DB954" if v >= 40 else "#F5B700" if v >= 15 else "#E63946"
                for v in df_grafica["Score Munger"]
            ]
            fig_top = go.Figure(
                go.Bar(
                    y=df_grafica["Ticker"],
                    x=df_grafica["Score Munger"],
                    orientation="h",
                    marker_color=colores_barras,
                    text=df_grafica["Score Munger"],
                    texttemplate="%{text:.1f}",
                    textposition="outside",
                )
            )
            fig_top.update_layout(
                title="Score Munger — Las 40 Empresas Analizadas",
                height=1000,
                margin=dict(l=10, r=40, t=40, b=10),
                xaxis_title="Score Munger",
                yaxis=dict(tickfont=dict(size=11)),
            )
            st.plotly_chart(fig_top, use_container_width=True)


# =============================================================================
# LÓGICA DE REFRESCO AUTOMÁTICO EN VIVO
# =============================================================================
if modo_envivo:
    time.sleep(intervalo)
    st.rerun()
