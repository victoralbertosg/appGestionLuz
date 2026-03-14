import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import urllib.parse

# --- 0. FUNCIONES DE UTILIDAD ---
def clean_float(value):
    """Limpia y convierte un valor a float, manejando comas como decimales."""
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        # Reemplazar coma por punto y eliminar espacios
        cleaned = str(value).replace(',', '.').strip()
        return float(cleaned)
    except ValueError:
        return 0.0

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

def reset_form():
    # 1. Resetear bandera de cálculo
    st.session_state.calculated = False
    
    # 2. Resetear el monto del recibo
    st.session_state.monto_recibo = 0.0
    
    # 3. Resetear todas las lecturas de departamentos
    if 'departamentos' in config:
        for i in range(len(config['departamentos'])):
            key = f"d_{i}"
            if key in st.session_state:
                st.session_state[key] = 0.0

try:
    doc = get_gsheet_connection()
    hoja_lecturas = doc.worksheet("Historico_Lecturas")
    hoja_pagos = doc.worksheet("Historico_Pagos")

    # 1. Obtener todos los datos históricos
    data_lecturas = hoja_lecturas.get_all_values()
    data_pagos = hoja_pagos.get_all_values() if hoja_pagos else []
    
    # Crear un set de meses ya calculados para búsqueda rápida
    meses_calculados = set([row[0] for row in data_pagos[1:]]) if len(data_pagos) > 1 else set()
    num_deptos = len(config['departamentos'])
    
    # --- NAVEGACIÓN POR PESTAÑAS ---
    tab_registro, tab_calculo = st.tabs(["📝 REGISTRO DE LECTURAS", "🧮 CÁLCULO Y CONSULTAS"])

    with tab_registro:
        st.subheader("📋 Registro de Nuevas Lecturas")
        st.info("💡 Ingrese el periodo (ej. 2026-04) para habilitar el formulario. El sistema cargará automáticamente la última referencia.")
        
        # Último registro para referencia (por defecto)
        ultima_fila = data_lecturas[-1]
        mes_anterior_nombre = ultima_fila[0]
        lecturas_referencia = [clean_float(x) for x in ultima_fila[1:num_deptos+1]]

        c1, c2 = st.columns(2)
        with c1:
            mes_nuevo = st.text_input("Mes de Lectura (YYYY-MM)", value="", key="mes_reg_input", placeholder="Ej: 2026-04")
        
        if mes_nuevo.strip():
            # Validación en tiempo real de mes duplicado solo si hay texto
            meses_registrados = [row[0] for row in data_lecturas]
            es_duplicado = mes_nuevo in meses_registrados
            es_calculado = mes_nuevo in meses_calculados
            
            # Eliminamos el bloqueo estricto post-guardado asignando False incondicionalmente.
            # Esto permite modificaciones ilimitadas sobre el mismo periodo sin tener que refrescar o deseleccionar.
            acaba_de_guardar = False
            
            # Solo para mostrar el mensaje temporal de éxito que desaparece al iterar
            mostrar_exito_temporal = (mes_nuevo == st.session_state.get('ultimo_guardado', ''))
            
            if es_calculado:
                st.error(f"❌ El periodo **{mes_nuevo}** ya se encuentra registrado y calculado. No puede ser modificado.")
            else:
                st.write("---")
                
                # Configurar valores según si es duplicado(pendiente) o nuevo
                if es_duplicado:
                    st.info(f"✏️ El periodo **{mes_nuevo}** está pendiente de cálculo. Puede modificar los valores registrados.")
                    idx_mod = meses_registrados.index(mes_nuevo)
                    lecturas_actuales_mod = [clean_float(x) for x in data_lecturas[idx_mod][1:num_deptos+1]]
                    
                    if idx_mod > 1: # Índice 0 es cabecera
                        mes_anterior_nombre_ref = data_lecturas[idx_mod-1][0]
                        lecturas_referencia_ref = [clean_float(x) for x in data_lecturas[idx_mod-1][1:num_deptos+1]]
                    else:
                        mes_anterior_nombre_ref = "N/A"
                        lecturas_referencia_ref = [0.0] * num_deptos
                        
                    st.markdown(f"### 📏 Modificación de Medidores | Ref: {mes_nuevo} (Anterior: {mes_anterior_nombre_ref})")
                else:
                    mes_anterior_nombre_ref = mes_anterior_nombre
                    lecturas_referencia_ref = lecturas_referencia
                    lecturas_actuales_mod = [0.0] * num_deptos
                    st.markdown(f"### 📏 Ingreso de Medidores | Ref: {mes_nuevo} (Anterior: {mes_anterior_nombre_ref})")
                
                if mostrar_exito_temporal:
                    st.success(f"✅ Lecturas de {mes_nuevo} guardadas/actualizadas correctamente en la base de datos.")
                    # Limpiamos el estado para que el mensaje no se quede pegado si edita de nuevo
                    st.session_state.ultimo_guardado = None

                # Formulario vinculado a la key del mes para recreación forzada si cambia el mes
                with st.form(key=f"form_registro_lecturas_{mes_nuevo}", clear_on_submit=False):
                    cols_reg = st.columns(num_deptos)
                    nuevas_lecturas_input = []
                    for i, depto in enumerate(config['departamentos']):
                        with cols_reg[i]:
                            val = st.number_input(
                                f"{depto['nombre']}", 
                                min_value=0.0, 
                                value=float(lecturas_actuales_mod[i]) if es_duplicado else 0.0,
                                help=f"Lectura anterior: {lecturas_referencia_ref[i]} kW",
                                key=f"form_reg_d_{i}_{mes_nuevo}"
                            )
                            nuevas_lecturas_input.append(val)
                            st.caption(f"Ant: {lecturas_referencia_ref[i]}")

                    texto_boton = "🔄 MODIFICAR LECTURAS" if es_duplicado else "💾 GUARDAR LECTURAS"
                    submit_btn = st.form_submit_button(texto_boton, use_container_width=True, disabled=acaba_de_guardar)
                    
                    if submit_btn:
                        if any(m > p for m, p in zip(nuevas_lecturas_input, lecturas_referencia_ref)):
                            st.session_state.ultimo_guardado = mes_nuevo
                            if es_duplicado:
                                idx_mod = meses_registrados.index(mes_nuevo)
                                celda_rango = f"A{idx_mod+1}"
                                hoja_lecturas.update([[mes_nuevo] + nuevas_lecturas_input], celda_rango)
                            else:
                                hoja_lecturas.append_row([mes_nuevo] + nuevas_lecturas_input)
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("⚠️ Las lecturas actuales deben ser mayores a las anteriores para registrar un consumo válido.")
        else:
            st.warning("⚠️ Escriba un 'Mes de Lectura' para comenzar.")
    with tab_calculo:
        st.subheader("🧮 Gestión de Pagos y Distribución")
        
        # Seleccionar periodo de la lista de lecturas (excluyendo cabecera)
        periodos_disponibles = [row[0] for row in data_lecturas[1:]][::-1] # Invertir para ver más recientes primero
        
        if not periodos_disponibles:
            st.warning("No hay lecturas registradas aún.")
        else:
            periodo_sel = st.selectbox("Seleccione el Periodo a Gestionar", periodos_disponibles)
            es_calculado = periodo_sel in meses_calculados
            
            # Obtener datos de ese periodo específico
            idx_periodo = next(i for i, row in enumerate(data_lecturas) if row[0] == periodo_sel)
            lecturas_actuales = [clean_float(x) for x in data_lecturas[idx_periodo][1:num_deptos+1]]
            
            # Obtener lecturas del mes anterior al seleccionado para el cálculo
            if idx_periodo > 1:
                lecturas_anteriores = [clean_float(x) for x in data_lecturas[idx_periodo-1][1:num_deptos+1]]
            else:
                lecturas_anteriores = [0.0] * num_deptos

            # Re-producir la lógica de serie
            consumos_periodo = []
            for i in range(num_deptos):
                diff = max(0.0, lecturas_actuales[i] - lecturas_anteriores[i])
                if i == 0: c = diff
                elif i == 1: c = max(0.0, diff - consumos_periodo[0])
                elif i == 2: c = max(0.0, diff - (consumos_periodo[0] + consumos_periodo[1]))
                elif i == 3: c = diff
                else: c = diff
                consumos_periodo.append(c)

            if es_calculado:
                st.success(f"✅ Este periodo ya ha sido calculado.")
                # Mapeo robusto: buscar cada departamento por nombre en los pagos registrados
                filas_pagos = [row for row in data_pagos if row[0] == periodo_sel]
                mapa_pagos = {row[1]: clean_float(row[3]) for row in filas_pagos}
                
                # Asegurar que pagos_individuales tenga el mismo orden y longitud que los departamentos en config
                pagos_individuales = [mapa_pagos.get(d['nombre'], 0.0) for d in config['departamentos']]
                monto_total_his = sum(pagos_individuales)
            else:
                st.warning(f"⏳ Periodo pendiente de cálculo.")
                monto_total_his = st.number_input(f"Ingrese Monto del Recibo General ({config['edificio']['simbolo']})", min_value=0.0, value=0.0)

            # --- VISUALIZACIÓN DE RESULTADOS ---
            # Siempre mostramos la tabla con las lecturas, independiente del monto o consumo
            consumo_total_edificio = sum(consumos_periodo)
            
            if es_calculado:
                pagos_finales = pagos_individuales
            else:
                if consumo_total_edificio > 0 and monto_total_his > 0:
                    pagos_finales = [(c / consumo_total_edificio) * monto_total_his for c in consumos_periodo]
                else:
                    pagos_finales = [0.0] * num_deptos

            df_resumen = pd.DataFrame({
                "Departamento": [d['nombre'] for d in config['departamentos']],
                "Lect. Anterior": lecturas_anteriores,
                "Lect. Actual": lecturas_actuales,
                "Consumo (kW)": consumos_periodo,
                "Monto a Pagar": [f"{config['edificio']['simbolo']} {p:.2f}" for p in pagos_finales]
            })

            st.table(df_resumen)
            
            if es_calculado or monto_total_his > 0:
                st.write("---")
                m1, m2, m3 = st.columns(3)
                with m1: st.metric("Consumo Total", f"{consumo_total_edificio:.1f} kW")
                with m2: st.metric("Monto Total", f"{config['edificio']['simbolo']} {monto_total_his:.2f}")
                with m3: st.metric("Promedio/Dpto", f"{config['edificio']['simbolo']} {(monto_total_his/num_deptos):.2f}")
                
                # Gráfico
                st.bar_chart(pd.DataFrame({"Depto": [d['nombre'] for d in config['departamentos']], "kW": consumos_periodo}).set_index("Depto"))

                # Botones Finales
                c_pdf, c_reg = st.columns(2)
                with c_pdf:
                    # --- FUNCION DE REPORTE ---
                    def generate_pdf_v2(df, mes, monto_total, config, consumos):
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("helvetica", "B", 16)
                        pdf.cell(190, 10, f"Reporte de Cobranza - {config['edificio']['nombre']}", ln=True, align="C")
                        pdf.set_font("helvetica", "", 12)
                        pdf.cell(190, 10, f"Mes: {mes} | Monto Total: {config['edificio']['simbolo']} {monto_total:.2f}", ln=True, align="C")
                        pdf.ln(10)
                        pdf.set_font("helvetica", "B", 10)
                        col_widths = [40, 35, 35, 35, 45]
                        headers = ["Departamento", "Lect. Ant", "Lect. Act", "Consumo", "Monto"]
                        for j, header in enumerate(headers): pdf.cell(col_widths[j], 10, header, border=1, align="C")
                        pdf.ln()
                        pdf.set_font("helvetica", "", 10)
                        for index, row in df.iterrows():
                            pdf.cell(col_widths[0], 10, str(row["Departamento"]), border=1)
                            pdf.cell(col_widths[1], 10, str(row["Lect. Anterior"]), border=1)
                            pdf.cell(col_widths[2], 10, str(row["Lect. Actual"]), border=1)
                            pdf.cell(col_widths[3], 10, str(row["Consumo (kW)"]), border=1)
                            pdf.cell(col_widths[4], 10, str(row["Monto a Pagar"]), border=1)
                            pdf.ln()
                        plt.figure(figsize=(8, 5))
                        plt.bar(df["Departamento"], consumos, color='#2e7d32')
                        img_buf = io.BytesIO()
                        plt.savefig(img_buf, format='png')
                        plt.close() # Buena práctica para liberar memoria
                        pdf.ln(10)
                        pdf.image(img_buf, x=10, w=180)
                        return bytes(pdf.output())

                    pdf_b = generate_pdf_v2(df_resumen, periodo_sel, monto_total_his, config, consumos_periodo)
                    st.download_button("📄 DESCARGAR PDF", data=pdf_b, file_name=f"Reporte_{periodo_sel}.pdf", mime="application/pdf")
                
                with c_reg:
                    if not es_calculado:
                        if st.button("💾 VALIDAR Y REGISTRAR CÁLCULOS", use_container_width=True):
                            for j, depto in enumerate(config['departamentos']):
                                hoja_pagos.append_row([
                                    periodo_sel,
                                    depto['nombre'],
                                    consumos_periodo[j],
                                    round(pagos_finales[j], 2),
                                    "Pendiente",
                                    str(datetime.now())
                                ])
                            st.success("✅ Cálculos registrados correctamente.")
                            st.balloons()
                            st.rerun()
                    else:
                        st.info("ℹ️ Los datos ya están registrados en la base de datos.")

except Exception as e:
    st.error(f"⚠️ Error inesperado: {e}")
    import traceback
    st.expander("Ver detalle del error").code(traceback.format_exc())