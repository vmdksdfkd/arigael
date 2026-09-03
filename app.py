# -*- coding: utf-8 -*-
import requests  # Asegúrate de tener import requests al inicio de tu archivo
import streamlit as st  # <--- Agregado aquí para evitar 'st no está definido'
import time
import base64
import json
import os
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# --- FUNCIÓN DE VALIDACIÓN DE GUMROAD ---
def validar_licencia_gumroad(license_key: str) -> bool:
    """Verifica si la clave ingresada por el usuario es válida en Gumroad."""
    url = "https://api.gumroad.com/v2/licenses/verify"
    payload = {
        "product_permalink": "jgulbh",  # ID/Permalink extraído de tu URL de Gumroad
        "license_key": license_key.strip(),
        "increment_uses_count": "false"
    }
    try:
        response = requests.post(url, data=payload, timeout=5)
        res_data = response.json()
        # Devuelve True si la compra existe y no ha sido reembolsada
        return res_data.get("success", False) and not res_data.get(
            "purchase", {}
        ).get("refunded", False)
    except Exception:
        return False
# =============================================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA Y ESTILOS
# =============================================================================
st.set_page_config(
    page_title="Semáforo de Inversión y Simulador",
    page_icon="🚦",
    layout="wide",
)

# =============================================================================
# BARRA LATERAL (CONTROL DE LICENCIA EN VIVO)
# =============================================================================
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
            # Tu clave maestra personal (para que tú entres siempre gratis)
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
    st.title("🔒 Semáforo de Inversión y Simulador — Versión Semipro")
    st.warning(
        "⚠️ Necesitas una licencia válida para usar esta herramienta. "
        "Ingresa tu clave en la barra lateral izquierda para continuar."
    )
    st.info(
        "¿No tienes clave? Consíguela en tu página de producto de Gumroad."
    )
    st.stop()
"""
========
 SEMÁFORO DE INVERSIÓN Y SIMULADOR EN VIVO (PAPER TRADING) - VERSIÓN SEMIPRO
=============================================================================
"""



# =============================================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA Y ESTILOS
# =============================================================================


# Estilo CSS para pestañas gigantes, radio buttons y panel lateral
st.markdown("""
    <style>
    div[data-testid="stRadio"] > div {
        gap: 15px;
    }
    div[data-testid="stRadio"] label {
        font-size: 18px !important;
        font-weight: 800 !important;
        padding: 10px 20px !important;
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
# FUNCIONES DE DATOS: Descarga y Métricas
# =============================================================================
@st.cache_data(ttl=60, show_spinner=False)
def descargar_datos(ticker: str, periodo: str = "2y"):
    activo = yf.Ticker(ticker)
    hist = activo.history(period=periodo)
    if hist.empty:
        return None, None, None
    try:
        info = activo.info
    except Exception:
        info = {}
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
    if not info:
        info = {}

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
    
    # Manejo seguro y completo para evitar errores de sintaxis y cierres abruptos
    if fcf is not None and market_cap is not None and market_cap != 0:
        fcf_yield = fcf / market_cap
    else:
        fcf_yield = None

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
    "Excelente": "#0B6E4F",
    "Muy bueno": "#1DB954",
    "Bueno": "#8BC34A",
    "Precaución": "#F5B700",
    "Malo": "#E63946",
    "N/D": "#9AA0A6",
}
RATING_ICONS = {
    "Excelente": "⭐",
    "Muy bueno": "✅",
    "Bueno": "🙂",
    "Precaución": "⚠️",
    "Malo": "🚫",
    "N/D": "❔",
}


def badge_html(etiqueta: str) -> str:
    color = RATING_COLORS.get(etiqueta, "#9AA0A6")
    icono = RATING_ICONS.get(etiqueta, "")
    return (
        f"<span style='background-color:{color};color:white;padding:2px 8px;"
        f"border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap;'>"
        f"{icono} {etiqueta}</span>"
    )


def mostrar_metrica(contenedor, titulo: str, valor_texto: str, calificacion: str, ayuda: str = ""):
    contenedor.markdown(f"<div style='font-size:12px;color:#888;'>{titulo}</div>", unsafe_allow_html=True)
    contenedor.markdown(f"<div style='font-size:22px;font-weight:700;'>{valor_texto}</div>", unsafe_allow_html=True)
    contenedor.markdown(badge_html(calificacion), unsafe_allow_html=True)
    if ayuda:
        contenedor.caption(ayuda)


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

    if razones_rojo:
        return {"color": "rojo", "razones": razones_rojo, "score": 15}

    if fund["ROIC_aprox_ROE"] is not None and fund["ROIC_aprox_ROE"] > 0.12:
        if fund["PEG"] is not None and fund["PEG"] > 2.0:
            razones_amarillo.append(f"Rentable pero sobrevalorada (PEG={fund['PEG']:.2f})")
    if rsi > 70:
        razones_amarillo.append(f"RSI en sobrecompra ({rsi:.1f})")

    if razones_amarillo:
        return {"color": "amarillo", "razones": razones_amarillo, "score": 55}

    razones_verde.append("Tendencia y fundamentales alineados positivamente")
    return {"color": "verde", "razones": razones_verde, "score": 85}


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

    return {
        "df": df,
        "retorno_estrategia": retorno_total_estrategia,
        "retorno_buyhold": retorno_total_buyhold,
        "max_drawdown": max_drawdown,
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
# ENCABEZADO PRINCIPAL
# =============================================================================
col_h1, col_h2 = st.columns([0.8, 0.2])

with col_h1:
    st.title("🚦 Semáforo de Inversión y Simulador — Versión Semipro")
    st.caption("Herramienta educativa de apoyo a la decisión y simulación de trading. No es asesoría financiera.")

with col_h2:
    st.markdown("<div class='header-author'>Autor: Mgs. César Carrión Aguirre</div>", unsafe_allow_html=True)
    img_b64 = obtener_base64_imagen("arigael_2.jpeg")
    if img_b64:
        st.markdown(f'<img src="{img_b64}" style="width: 100%; max-width: 180px; border-radius: 8px;">', unsafe_allow_html=True)

# Selección de pestaña
opcion_pestana = st.radio(
    "Selecciona un módulo:",
    [
        "📊 Análisis & Semáforo",
        "🎮 Simulador de Operaciones (Comercio de Papel)",
        "🏆 Top 20 de inversión en valor (Buffett & Munger)",
    ],
    horizontal=True,
    label_visibility="collapsed",
)


# =============================================================================
# BARRA LATERAL (INCLUYE CONTROL DE LICENCIA Y CONTROLES)
# =============================================================================
with st.sidebar:
    st.markdown("### 🎛 Panel de Control")

    if "controles_activos" not in st.session_state:
        st.session_state["controles_activos"] = True

    btn_texto = "🔓 Controles Habilitados" if st.session_state["controles_activos"] else "🔒 Controles Bloqueados"
    if st.button(btn_texto, use_container_width=True):
        st.session_state["controles_activos"] = not st.session_state["controles_activos"]
        st.rerun()

    controles_deshabilitados = not st.session_state["controles_activos"]
    st.divider()

    if opcion_pestana == "📊 Análisis & Semáforo":
        st.header("🔎 Buscador de Activo")
        ticker_input = (
            st.text_input(
                "Símbolo (acción, ETF...)",
                value="AAPL",
                disabled=controles_deshabilitados,
            )
            .strip()
            .upper()
        )

        periodo = st.selectbox(
            "Período histórico",
            ["1y", "2y", "5y", "10y"],
            index=1,
            disabled=controles_deshabilitados,
        )

        st.divider()
        st.header("🛡️ Gestión de Riesgo")
        capital_total = st.number_input(
            "Total de capital ($)",
            min_value=0.0,
            value=10000.0,
            step=100.0,
            disabled=controles_deshabilitados,
        )
        riesgo_pct = st.slider(
            "Riesgo máximo por op (%)",
            0.5,
            10.0,
            2.0,
            0.5,
            disabled=controles_deshabilitados,
        )
        stop_loss_pct = st.slider(
            "Stop-loss (% caída)",
            3.0,
            30.0,
            15.0,
            1.0,
            disabled=controles_deshabilitados,
        )

        st.divider()
        analizar = st.button(
            "🔄 Actualizar Datos",
            type="primary",
            use_container_width=True,
            disabled=controles_deshabilitados,
        )

    else:
        ticker_input = "AAPL"
        periodo = "2y"
        capital_total = 10000.0
        riesgo_pct = 2.0
        stop_loss_pct = 15.0
        analizar = False


# =============================================================================
# DESCARGA DE DATOS GENERAL
# =============================================================================
if analizar:
    descargar_datos.clear()

hist, info, noticias = descargar_datos(ticker_input, periodo)

if hist is None:
    st.error(f"No se encontraron datos para '{ticker_input}'.")
    st.stop()

df_tec = agregar_indicadores_tecnicos(hist)
fund = extraer_fundamentales(info or {})
resultado_semaforo = evaluar_semaforo(fund, df_tec)
backtest = backtest_estrategia(df_tec)

precio_actual = df_tec["Close"].iloc[-1]
precio_stop_sugerido = precio_actual * (1 - stop_loss_pct / 100)
nombre_empresa = (info or {}).get("longName", ticker_input)


# =============================================================================
# MÓDULO 1: ANÁLISIS Y SEMÁFORO (Estructura de 2 Columnas Restaurada)
# =============================================================================
if opcion_pestana == "📊 Análisis & Semáforo":
    st.subheader(f"{ticker_input} — {precio_actual:,.2f} $")

    # División exacta en 2 columnas paralelas
    col_verde, col_rojo = st.columns(2)

    with col_verde:
        st.markdown(
            "<div style='border:1px solid #1DB954;border-radius:8px;padding:12px;'>",
            unsafe_allow_html=True,
        )
        st.markdown("### 🟢 Diagnóstico (Educativo)")

        st.markdown("**📊 Análisis Técnico**")
        precio_hoy = df_tec["Close"].iloc[-1]
        ema50_hoy = df_tec["EMA50"].iloc[-1]
        ema200_hoy = df_tec["EMA200"].iloc[-1]
        rsi_hoy = df_tec["RSI14"].iloc[-1]

        c1, c2, c3 = st.columns(3)
        mostrar_metrica(c1, "Tendencia", f"{precio_hoy:,.2f} $", calif_tendencia(precio_hoy, ema50_hoy, ema200_hoy))
        c2.markdown("<div style='font-size:12px;color:#888;'>EMA 50 / 200</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='font-size:13px;'>EMA50: <b>{ema50_hoy:,.2f} $</b><br>EMA200: <b>{ema200_hoy:,.2f} $</b></div>", unsafe_allow_html=True)
        mostrar_metrica(c3, "RSI (14)", f"{rsi_hoy:.1f}", calif_rsi(rsi_hoy))

        # Gráfico técnico ajustado
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_tec.index, y=df_tec["Close"], name="Precio", line=dict(color="#2962FF", width=1.5)))
        fig.add_trace(go.Scatter(x=df_tec.index, y=df_tec["EMA50"], name="EMA 50", line=dict(color="#F5B700", width=1.2)))
        fig.add_trace(go.Scatter(x=df_tec.index, y=df_tec["EMA200"], name="EMA 200", line=dict(color="#E63946", width=1.2)))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**🏛️ Análisis Fundamental**")
        roic_txt = f"{fund['ROIC_aprox_ROE']*100:.1f}%" if fund["ROIC_aprox_ROE"] is not None else "N/D"
        peg_txt = f"{fund['PEG']:.2f}" if fund["PEG"] is not None else "N/D"
        deuda_txt = f"{fund['Deuda_EBITDA']:.2f}x" if fund["Deuda_EBITDA"] is not None else "N/D"
        fcf_txt = f"{fund['FCF_Yield']*100:.1f}%" if fund["FCF_Yield"] is not None else "N/D"

        f1, f2 = st.columns(2)
        mostrar_metrica(f1, "ROIC (ROE)", roic_txt, calif_roic(fund["ROIC_aprox_ROE"]))
        mostrar_metrica(f2, "Deuda / EBITDA", deuda_txt, calif_deuda_ebitda(fund["Deuda_EBITDA"]))
        mostrar_metrica(f1, "Relación PEG", peg_txt, calif_peg(fund["PEG"]))
        mostrar_metrica(f2, "Rendimiento del FCF", fcf_txt, calif_fcf_yield(fund["FCF_Yield"]))

        st.markdown("---")
        st.markdown(
            f"<div style='background-color:{COLORES[resultado_semaforo['color']]};color:black;padding:8px;border-radius:6px;text-align:center;font-weight:bold;'>"
            f"{ETIQUETAS[resultado_semaforo['color']]}</div>",
            unsafe_allow_html=True,
        )
        for r in resultado_semaforo["razones"]:
            st.write(f"• {r}")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_rojo:
        st.markdown(
            "<div style='border:1px solid #E63946;border-radius:8px;padding:12px;'>",
            unsafe_allow_html=True,
        )
        st.markdown("### 🔴 Backtesting y Gestión de Riesgo")

        if backtest is not None:
            calif_estrat = calif_backtest_vs_buyhold(backtest["retorno_estrategia"], backtest["retorno_buyhold"])
            b1, b2 = st.columns(2)
            mostrar_metrica(b1, "Retorno Estrategia", f"{backtest['retorno_estrategia']*100:,.1f}%", calif_estrat)
            mostrar_metrica(b2, "Retorno Buy & Hold", f"{backtest['retorno_buyhold']*100:,.1f}%", "N/D")
            
            b3, b4 = st.columns(2)
            mostrar_metrica(b3, "Máx. Caída", f"{backtest['max_drawdown']*100:,.1f}%", calif_drawdown(backtest["max_drawdown"]))
            b4.metric("% Días Mercado", f"{backtest['dias_en_mercado_pct']*100:,.0f}%")

            # Gráfico del Backtest
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(x=backtest["df"].index, y=backtest["df"]["equity_estrategia"], name="Estrategia", line=dict(color="#1DB954")))
            fig_bt.add_trace(go.Scatter(x=backtest["df"].index, y=backtest["df"]["equity_buyhold"], name="Comprar y mantener", line=dict(color="#888", dash="dot")))
            fig_bt.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h"))
            st.plotly_chart(fig_bt, use_container_width=True)

        st.markdown("**💰 Calculadora de Tamaño de Posición**")
        precio_stop_manual = st.number_input(
            "Precio de Stop-Loss ($)",
            min_value=0.0,
            value=float(round(precio_stop_sugerido, 2)),
            step=0.5,
            disabled=controles_deshabilitados,
        )
        
        posicion = calcular_tamano_posicion(capital_total, riesgo_pct, precio_actual, precio_stop_manual)
        if posicion:
            p1, p2 = st.columns(2)
            p1.metric("Dinero en Riesgo", f"{posicion['riesgo_dinero']:,.2f} $")
            p2.metric("Acciones Sugeridas", f"{posicion['n_acciones']:.2f}")
            
            p3, p4 = st.columns(2)
            p3.metric("Monto a Invertir", f"{posicion['monto_invertido']:,.2f} $")
            p4.metric("% del Capital", f"{posicion['pct_del_capital']:,.1f}%")

        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# MÓDULO 2: SIMULADOR DE TRADING EN VIVO (PAPER TRADING)
# =============================================================================
elif opcion_pestana == "🎮 Simulador de Operaciones (Comercio de Papel)":
    sim_data = cargar_simulador()
    efectivo = sim_data["efectivo"]
    posiciones = sim_data["posiciones"]

    valor_portafolio_acciones = 0.0
    filas_tabla = []

    for sim_ticker, datos in posiciones.items():
        cant = datos["cantidad"]
        p_promedio = datos["precio_promedio"]
        p_actual = obtener_precio_instantaneo(sim_ticker) or p_promedio

        val_pos = cant * p_actual
        pnl = (p_actual - p_promedio) * cant
        pnl_pct = ((p_actual - p_promedio) / p_promedio) * 100 if p_promedio > 0 else 0.0

        valor_portafolio_acciones += val_pos
        filas_tabla.append(
            {
                "Ticker": sim_ticker,
                "Cantidad": cant,
                "Precio Compra": f"${p_promedio:,.2f}",
                "Precio Actual": f"${p_actual:,.2f}",
                "Valor Mercado": f"${val_pos:,.2f}",
                "Ganancia/Pérdida ($)": f"${pnl:+,.2f}",
                "Rendimiento (%)": f"{pnl_pct:+.2f}%",
            }
        )

    st.subheader("🎮 Simulador de Operaciones en Tiempo Real")
    m1, m2, m3 = st.columns(3)
    m1.metric("Patrimonio Total", f"${(efectivo + valor_portafolio_acciones):,.2f}")
    m2.metric("Efectivo Disponible", f"${efectivo:,.2f}")
    m3.metric("Invertido en Acciones", f"${valor_portafolio_acciones:,.2f}")

    st.divider()
    col_trade, col_pos = st.columns([1, 1.5])

    with col_trade:
        st.subheader("🛒 Operar Activo")
        sim_ticker_op = st.text_input("Ticker:", value="AAPL").upper()
        cant_op = st.number_input("Cantidad:", min_value=1, value=10, step=1)
        p_envivo = obtener_precio_instantaneo(sim_ticker_op)
        costo_total = p_envivo * cant_op

        st.write(f"Precio en vivo: **${p_envivo:,.2f}** | Total: **${costo_total:,.2f}**")

        b_compra, b_venta = st.columns(2)
        if b_compra.button("🟢 COMPRAR", use_container_width=True):
            if efectivo >= costo_total:
                sim_data["efectivo"] -= costo_total
                if sim_ticker_op in sim_data["posiciones"]:
                    cant_p = sim_data["posiciones"][sim_ticker_op]["cantidad"]
                    p_p = sim_data["posiciones"][sim_ticker_op]["precio_promedio"]
                    sim_data["posiciones"][sim_ticker_op]["cantidad"] += cant_op
                    sim_data["posiciones"][sim_ticker_op]["precio_promedio"] = ((cant_p * p_p) + costo_total) / (cant_p + cant_op)
                else:
                    sim_data["posiciones"][sim_ticker_op] = {"cantidad": cant_op, "precio_promedio": p_envivo}
                guardar_simulador(sim_data)
                st.success("Compra realizada.")
                st.rerun()

        if b_venta.button("🔴 VENDER", use_container_width=True):
            if sim_ticker_op in sim_data["posiciones"] and sim_data["posiciones"][sim_ticker_op]["cantidad"] >= cant_op:
                sim_data["efectivo"] += costo_total
                sim_data["posiciones"][sim_ticker_op]["cantidad"] -= cant_op
                if sim_data["posiciones"][sim_ticker_op]["cantidad"] == 0:
                    del sim_data["posiciones"][sim_ticker_op]
                guardar_simulador(sim_data)
                st.success("Venta realizada.")
                st.rerun()

    with col_pos:
        st.subheader("💼 Portafolio Activo")
        if filas_tabla:
            st.dataframe(pd.DataFrame(filas_tabla), use_container_width=True, hide_index=True)
        else:
            st.info("No tienes posiciones abiertas.")


# =============================================================================
# MÓDULO 3: TOP 20 VALUE INVESTING (BUFFETT & MUNGER)
# =============================================================================
else:
    st.subheader("🏆 Top 20 Acciones Value por Sectores (Metodología Munger-Buffett)")
    
    top_20_empresas = [
        {"Ticker": "AAPL", "Sector": "Tecnología", "Moat": "Ecosistema / Marca"},
        {"Ticker": "MSFT", "Sector": "Tecnología", "Moat": "Efecto Red / Switching Costs"},
        {"Ticker": "NVDA", "Sector": "Tecnología", "Moat": "Liderazgo Tecnológico"},
        {"Ticker": "GOOGL", "Sector": "Servicios de Comunicación", "Moat": "Efecto Red / Datos"},
        {"Ticker": "META", "Sector": "Servicios de Comunicación", "Moat": "Efecto Red Social"},
        {"Ticker": "AMZN", "Sector": "Consumo Cíclico", "Moat": "Escala / Logística"},
        {"Ticker": "BRK-B", "Sector": "Financiero", "Moat": "Diversificación / Capital"},
        {"Ticker": "JNJ", "Sector": "Salud", "Moat": "Patentes Globales"},
        {"Ticker": "KO", "Sector": "Consumo Defensivo", "Moat": "Distribución Global"},
        {"Ticker": "PEP", "Sector": "Consumo Defensivo", "Moat": "Economías de Escala"},
    ]

    st.dataframe(pd.DataFrame(top_20_empresas), use_container_width=True)
