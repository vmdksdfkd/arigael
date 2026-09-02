Python 3.11.3 (tags/v3.11.3:f3909b8, Apr  4 2023, 23:49:59) [MSC v.1934 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
import pandas as pd
import requests
import streamlit as st

# ID de tu producto publicado en Gumroad
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
...                 )
...                 return True, variante
...     except Exception:
...         pass
...     return False, None
... 
... 
... # --- CONFIGURACIÓN DE LA PÁGINA STREAMLIT ---
... st.set_page_config(page_title="ARIGAEL Terminal", layout="wide")
... 
... st.sidebar.title("ARIGAEL Terminal")
... st.sidebar.write("---")
... 
... # Control de Licencia en la barra lateral
... licencia_input = st.sidebar.text_input(
...     "Clave de Licencia Gumroad", type="password"
... )
... 
... if licencia_input:
...     es_valida, plan = verificar_licencia_gumroad(licencia_input)
...     if es_valida:
...         st.sidebar.success(f"Licencia Activa: {plan}")
...         st.title("Bienvenido a ARIGAEL Terminal")
...         st.write(
...             f"Acceso concedido para el plan **{plan}**. Aquí se desplegarán las herramientas de análisis financiero."
...         )
...         # Aquí irá el resto de tu plataforma interactiva
...     else:
...         st.sidebar.error("Licencia inválida o expirada.")
...         st.warning(
...             "Por favor, ingresa una clave de licencia válida adquirida en Gumroad para desbloquear la plataforma."
...         )
... else:
...     st.title("ARIGAEL Terminal")
...     st.info(
...         "Por favor, ingresa tu Clave de Licencia en la barra lateral izquierda para acceder."
