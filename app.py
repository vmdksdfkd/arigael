import pandas as pd
import requests
import streamlit as st

def verificar_licencia_gumroad(clave_de_licencia):
    url = "https://api.gumroad.com/v2/licenses/verify"
    payload = {"product_permalink": "jgulbh", "license_key": clave_de_licencia}
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            res = response.json()
            if res.get("success"):
                variant = res.get("purchase", {}).get("variant_name", "Semiprofesional")
                return True, variant
    except Exception:
        pass
    return False, None

st.set_page_config(page_title="Terminal ARIGAEL", layout="wide")

st.sidebar.title("Terminal ARIGAEL")
st.sidebar.write("---")

licencia_input = st.sidebar.text_input(
    "Clave de Licencia Gumroad", type="password"
)

if licencia_input:
    es_valida, variante = verificar_licencia_gumroad(licencia_input)
    if es_valida:
        st.sidebar.success(f"Licencia Válida: {variante}")
        st.title("Bienvenido a ARIGAEL Terminal")
        # Aquí va el resto del contenido de tu aplicación
    else:
        st.sidebar.error("Licencia inválida o expirada.")
else:
    st.warning("Por favor, ingresa una clave de licencia válida adquirida en Gumroad.")
