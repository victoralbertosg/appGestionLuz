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
    css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }}
        
        .main-header {{
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.18);
            color: #1a472a;
            font-size: 38px;
            font-weight: 800;
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .stButton>button {{
            background: linear-gradient(45deg, #2e7d32, #43a047);
            color: white;
            border: none;
            padding: 0.8rem 1rem;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(46, 125, 50, 0.3);
        }}
        
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(46, 125, 50, 0.4);
            color: white;
        }}

        .card {{
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
        }}
        
        div[data-testid="stMetricValue"] {{
            font-size: 24px;
            color: #2e7d32;
        }}
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)

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
    
    # INTENTO 1: Leer desde archivo local (PC)
    import os
    if os.path.exists('credentials.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    else:
        # INTENTO 2: Leer desde Secrets (Nube)
        try:
            if "gcp_service_account" in st.secrets:
                creds_dict = dict(st.secrets["gcp_service_account"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            else:
                raise Exception("No 'gcp_service_account' in st.secrets")
        except:
            raise Exception("No se encontraron credenciales válidas (falta credentials.json o configurar st.secrets)")
        
    client = gspread.authorize(creds)
    return client.open("SysLuz")

# --- 3. LÓGICA DE LA APLICACIÓN ---
apply_custom_css()
st.markdown(f'<div class="main-header">⚡ {config["edificio"]["nombre"]}</div>', unsafe_allow_html=True)
st.write(f"📍 **Dirección:** {config['edificio']['direccion']}")

if 'calculated' not in st.session_state:
    st.session_state.calculated = False

try:
    doc = get_gsheet_connection()
    hoja_lecturas = doc.worksheet("Historico_Lecturas")
    hoja_pagos = doc.worksheet("Historico_Pagos")

    # Obtener lecturas del mes anterior
    data_lecturas = hoja_lecturas.get_all_values()
    ultima_fila = data_lecturas[-1]
    mes_anterior_nombre = ultima_fila[0]
    num_deptos = len(config['departamentos'])
    lecturas_pasadas = [float(x) for x in ultima_fila[1:num_deptos+1]]

    
    # Calcular consumos del mes pasado para referencia
    consumos_pasados = [0.0] * len(config['departamentos'])
    if len(data_lecturas) >= 2:
        penultima_fila = data_lecturas[-2]
        lecturas_anteriores_a_la_pasada = [float(x) for x in penultima_fila[1:num_deptos+1]]

        # Diferencias brutas del mes pasado
        diffs_pasadas = [max(0.0, lp - la) for lp, la in zip(lecturas_pasadas, lecturas_anteriores_a_la_pasada)]
        
        # Aplicar lógica de serie al mes pasado para mostrar el dato real
        cp_temp = []
        for i in range(len(diffs_pasadas)):
            d = diffs_pasadas[i]
            if i == 0: cp = d
            elif i == 1: cp = max(0.0, d - cp_temp[0])
            elif i == 2: cp = max(0.0, d - (cp_temp[0] + cp_temp[1]))
            elif i == 3: cp = d
            else: cp = d

            cp_temp.append(cp)
        consumos_pasados = cp_temp

    # --- INTERFAZ DE ENTRADA ---
    st.subheader("📋 Datos del Mes Actual")
    c1, c2 = st.columns(2)
    with c1:
        mes_actual = st.text_input("Mes de Cobro", value=datetime.now().strftime("%Y-%m"))
    with c2:
        monto_total = st.number_input(f"Monto del Recibo General ({config['edificio']['simbolo']})", min_value=0.0)

    st.write("---")
    st.subheader("📏 Registro de Medidores")
    st.info(f"💡 **Instrucciones:** Ingrese la **lectura actual**. Referencia anterior: {mes_anterior_nombre}")

    # Entrada de medidas en formato horizontal
    cols = st.columns(len(config['departamentos']))
    medidas_nuevas = []
    consumos_calculados = []
    
    for i, depto in enumerate(config['departamentos']):
        with cols[i]:
            val = st.number_input(
                f"{depto['nombre']}", 
                min_value=0.0, 
                value=0.0,
                help=f"Lectura anterior: {lecturas_pasadas[i]} kW",
                key=f"d_{i}"
            )
            medidas_nuevas.append(val)
            
            # Cálculo de consumo según lógica de instalación en serie
            # diff es el consumo acumulado detectado por este medidor en el mes
            diff = max(0.0, val - lecturas_pasadas[i])
            
            if i == 0: # Dpto 101: Continua igual (Consumo Directo)
                consumo_v = diff
            elif i == 1: # Dpto 102: Diferencia - Consumo 101
                consumo_v = max(0.0, diff - consumos_calculados[0])
            elif i == 2: # Dpto 103: Diferencia - (Consumo 101 + 102)
                consumo_v = max(0.0, diff - (consumos_calculados[0] + consumos_calculados[1]))
            elif i == 3: # Dpto 104: Continua igual
                consumo_v = diff
            else:

                consumo_v = diff
            
            consumos_calculados.append(consumo_v)

            # Mostrar consumo en tiempo real e información de referencia
            html_label = f"<div style='font-size: 0.8rem;'>"
            
            # Referencia de Lectura Anterior (siempre visible)
            html_label += f"<span style='color: #616161;'>Lectura Ant: <b>{lecturas_pasadas[i]:.1f}</b></span>"
            
            # Consumo Actual Calculado (si se ha ingresado algo)
            if val > 0:
                if consumo_v > 0:
                    html_label += f" | <span style='color: #2e7d32; font-weight: bold;'>▲ Consumo: {consumo_v:.1f} kW</span>"
                elif val < lecturas_pasadas[i]:
                    html_label += f" | <span style='color: #d32f2f; font-weight: bold;'>⚠️ Error Lectura</span>"
                else:
                    html_label += f" | <span style='color: #757575;'>Sin consumo neto</span>"
            
            html_label += "</div>"
            st.markdown(html_label, unsafe_allow_html=True)

    # --- BOTONES DE ACCIÓN ---
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        if st.button("🧮 CALCULAR DISTRIBUCIÓN"):
            # Validar que al menos una lectura haya cambiado y sea mayor a la anterior
            if any(m > p for m, p in zip(medidas_nuevas, lecturas_pasadas)) and monto_total > 0:
                st.session_state.calculated = True
            elif monto_total <= 0:
                st.warning("⚠️ El monto del recibo debe ser mayor a 0.")
            else:
                st.warning(f"⚠️ Las lecturas actuales deben ser mayores a las de {mes_anterior_nombre} para calcular un consumo.")

    with col_btn2:
        if st.button("🧹 NUEVO CÁLCULO"):
            st.session_state.calculated = False
            st.rerun()

    # --- RESULTADOS ---
    if st.session_state.calculated:
        # Usar los consumos ya calculados con la lógica de serie
        consumos = consumos_calculados
        consumo_total_edificio = sum(consumos)
        
        if consumo_total_edificio <= 0:
            st.error(f"❌ **No hay consumo detectable:** Las lecturas actuales son iguales o menores a las de {mes_anterior_nombre}. No se puede distribuir el monto de {config['edificio']['simbolo']} {monto_total} si no hay consumo de energía.")
            st.session_state.calculated = False
        else:
            pagos_calculados = []
            for c in consumos:
                pago = (c / consumo_total_edificio) * monto_total
                pagos_calculados.append(pago)

            # Crear tabla de vista previa
            df_preview = pd.DataFrame({
                "Departamento": [d['nombre'] for d in config['departamentos']],
                "Mes Cobro": [mes_actual] * len(config['departamentos']),
                "Lect. Anterior": lecturas_pasadas,
                "Lect. Actual": medidas_nuevas,
                "Consumo (kW)": consumos,
                "Monto a Pagar": [f"{config['edificio']['simbolo']} {p:.2f}" for p in pagos_calculados]
            })

            st.write(f"---")
            st.subheader(f"🔍 Resumen de Cobranza - Período: {mes_actual}")
            
            # --- MÉTRICAS DE RESUMEN ---
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Consumo Total Edificio", f"{consumo_total_edificio:.1f} kW")
            with m2:
                st.metric("Monto a Distribuir", f"{config['edificio']['simbolo']} {monto_total:.2f}")
            with m3:
                st.metric("Promedio por Dpto", f"{config['edificio']['simbolo']} {(monto_total/len(config['departamentos'])):.2f}")
            
            st.table(df_preview)

            # --- BOTÓN DE REGISTRO ---
            with col_btn3:
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
                    
                    st.success(f"✅ ¡Éxito! Los datos de {mes_actual} se han guardado correctamente.")
                    st.session_state.calculated = False
                    st.balloons()
    elif any(m > 0 for m in medidas_nuevas):
        st.warning("Asegúrate de que las lecturas actuales sean mayores a las anteriores y que el monto sea mayor a 0.")

except Exception as e:
    st.error(f"⚠️ Error: {e}")