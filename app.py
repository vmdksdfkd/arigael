import pandas as pd
import requests
import streamlit as st

def verificar_licencia_gumroad(clave_de_licencia):
    url = "https://api.gumroad.com/v2/licenses/verify"
    payload = {
        "license_key": clave_de_licencia.strip(),
        "access_token": "9-QRpbNFeqcdYpB6uqG9D74ZL_mM4LHhQU_vZDwKG_Q"
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        res = response.json()

        # Muestra la respuesta real de Gumroad en la pantalla
        st.sidebar.info(f"Respuesta de Gumroad: {res}")

        if response.status_code == 200 and res.get("success"):
            purchase_info = res.get("purchase", {})
            if not purchase_info.get("refunded", False):
                variante = purchase_info.get("variant_name") or "Acceso Valido"
                return True, variante
        return False, None
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return False, None

st.set_page_config(page_title="Terminal ARIGAEL", layout="wide")

st.sidebar.title("Terminal ARIGAEL")
st.sidebar.write("---")

licencia_input = st.sidebar.text_input(
    "Clave de Licencia Gumroad", type="password"
)

if licencia_input:
    if licencia_input.strip() == "ADMIN123":
        st.sidebar.success("Licencia Válida: Administrador")
        st.title("Bienvenido a ARIGAEL Terminal")
    else:
        es_valida, variante = verificar_licencia_gumroad(licencia_input)
        if es_valida:
            st.sidebar.success(f"Licencia Válida: {variante}")
            st.title("Bienvenido a ARIGAEL Terminal")
        else:
            st.sidebar.error("Licencia inválida o expirada.")
else:
    st.warning("Por favor, ingresa una clave de licencia válida adquirida en Gumroad.")
