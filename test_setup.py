import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os

def test_setup():
    print("--- Verificando Configuración ---")
    
    # 1. Verificar settings.json
    try:
        with open('settings.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            print("✅ settings.json: OK")
    except Exception as e:
        print(f"❌ settings.json: ERROR - {e}")

    # 2. Verificar credentials.json
    if os.path.exists('credentials.json'):
        print("✅ credentials.json: EXISTE")
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            print("✅ credentials.json: FORMATO VÁLIDO")
        except Exception as e:
            print(f"❌ credentials.json: ERROR DE FORMATO - {e}")
    else:
        print("❌ credentials.json: NO ENCONTRADO")

    # 3. Verificar dependencias críticas
    try:
        import streamlit as st
        print("✅ Streamlit: INSTALADO")
    except ImportError:
        print("❌ Streamlit: NO INSTALADO")

    print("\nTodo parece estar listo para ejecutar 'streamlit run app.py'")

if __name__ == "__main__":
    test_setup()
