import pandas as pd
import requests
import streamlit as st

GUMROAD_PRODUCT_ID = "jgulbh"


def verificar_licencia_gumroad(license_key):
    url = "https://api.gumroad.com/v2/licenses/verify"
    payload = {"product_id": GUMROAD_PRODUCT_ID, "license_key": license_key}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            res = response.json()
            if res.get("success"):
                variante = res.get("purchase", {}).get(
                    "variant_name", "Semipro"
                )
                return True, variante
    except Exception:
        pass
    return False, None


st.set_page_config(page_title="ARIGAEL Terminal", layout="wide")

st.sidebar.title("ARIGAEL Terminal")
st.sidebar.write("---")

licencia_input = st.sidebar.text_input(
    "Clave de Licencia Gumroad", type="password"
)

if licencia_input:
    es_valida, plan = verificar_licencia_gumroad(licencia_input)
    if es_valida:
        st.sidebar.success(f"Licencia Activa: {plan}")
        st.title("Bienvenido a ARIGAEL Terminal")
        st.write(
            f"Acceso concedido para el plan **{plan}**. Plataforma lista para análisis."
        )
    else:
        st.sidebar.error("Licencia inválida o expirada.")
        st.warning(
            "Por favor, ingresa una clave de licencia válida adquirida en Gumroad."
        )
else:
    st.title("ARIGAEL Terminal")
    st.info(
        "Por favor, ingresa tu Clave de Licencia en la barra lateral izquierda para acceder."
    )
