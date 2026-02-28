import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime

# --- 1. CARGA DE CONFIGURACIÓN Y ESTILOS ---
def load_config():
    with open('settings.json', 'r', encoding='utf-8') as f:
        return json.load(f)

config = load_config()

def apply_custom_css():
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #f4f7f6; }}
        .main-header {{ color: #1e5631; font-size: 32px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
        .stButton>button {{
            background-color: #2e7d32; color: white; width: 100%; border-radius: 8px; height: 3em; font-weight: bold;
        }}
        .stTable {{ background-color: white; border-radius: 10px; }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
#def get_gsheet_connection():
    # Define los permisos necesarios
 #   scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Carga las credenciales del archivo JSON descargado de Google Cloud
  #  creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
   # client = gspread.authorize(creds)
    # Abre el documento (Asegúrate de que el nombre coincida)
    #return client.open("SysLuz")

def get_gsheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # INTENTO 1: Leer desde Secrets (Nube)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    # INTENTO 2: Leer desde archivo local (PC)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    return client.open("Control_Electricidad_Edificio")

# --- 3. LÓGICA DE LA APLICACIÓN ---
apply_custom_css()
st.markdown(f'<div class="main-header">⚡ {config["edificio"]["nombre"]}</div>', unsafe_allow_html=True)
st.caption(f"📍 {config['edificio']['direccion']}")

try:
    doc = get_gsheet_connection()
    hoja_lecturas = doc.worksheet("Historico_Lecturas")
    hoja_pagos = doc.worksheet("Historico_Pagos")

    # Obtener lecturas del mes anterior
    data_lecturas = hoja_lecturas.get_all_values()
    ultima_fila = data_lecturas[-1]
    mes_anterior = ultima_fila[0]
    lecturas_pasadas = [float(x) for x in ultima_fila[1:]]

    # --- INTERFAZ DE ENTRADA ---
    st.subheader("📋 Datos del Mes Actual")
    c1, c2 = st.columns(2)
    with c1:
        mes_actual = st.text_input("Mes de Cobro", value=datetime.now().strftime("%Y-%m"))
    with c2:
        monto_total = st.number_input(f"Monto del Recibo General ({config['edificio']['simbolo']})", min_value=0.0)

    st.write("---")
    st.subheader("📏 Registro de Medidores")
    st.info(f"Referencia: Medidas registradas en {mes_anterior}")

    # Entrada de medidas en formato horizontal
    cols = st.columns(len(config['departamentos']))
    medidas_nuevas = []
    
    for i, depto in enumerate(config['departamentos']):
        with cols[i]:
            val = st.number_input(f"{depto['nombre']}", min_value=0.0, key=f"d_{i}")
            medidas_nuevas.append(val)

    # --- CÁLCULOS ---
    consumos = [medidas_nuevas[i] - lecturas_pasadas[i] for i in range(len(medidas_nuevas))]
    consumo_total_edificio = sum(consumos)

    if consumo_total_edificio > 0 and monto_total > 0:
        # Calcular proporciones y pagos
        pagos_calculados = []
        for c in consumos:
            pago = (c / consumo_total_edificio) * monto_total
            pagos_calculados.append(pago)

        # Crear tabla de vista previa
        df_preview = pd.DataFrame({
            "Departamento": [d['nombre'] for d in config['departamentos']],
            "Lect. Anterior": lecturas_pasadas,
            "Lect. Actual": medidas_nuevas,
            "Consumo (kW)": consumos,
            "Pago Sugerido": [f"{config['edificio']['simbolo']} {p:.2f}" for p in pagos_calculados]
        })

        st.write("### 🔍 Vista Previa de Cobranza")
        st.table(df_preview)

        # --- BOTÓN DE REGISTRO ---
        if st.button("💾 REGISTRAR EN GOOGLE SHEETS"):
            # 1. Registrar en Historico_Lecturas
            hoja_lecturas.append_row([mes_actual] + medidas_nuevas)
            
            # 2. Registrar en Historico_Pagos
            for i, depto in enumerate(config['departamentos']):
                hoja_pagos.append_row([
                    mes_actual,
                    depto['nombre'],
                    consumos[i],
                    round(pagos_calculados[i], 2),
                    "Pendiente",
                    str(datetime.now())
                ])
            
            st.success("✅ Datos sincronizados correctamente. Los históricos han sido actualizados.")
    elif any(m > 0 for m in medidas_nuevas):
        st.warning("Asegúrate de que las lecturas actuales sean mayores a las anteriores y que el monto sea mayor a 0.")

except Exception as e:
    st.error(f"⚠️ Error de Conexión: Verifique que 'credentials.json' sea válido y que el archivo de Google Sheets tenga los permisos compartidos con el email del Service Account.")