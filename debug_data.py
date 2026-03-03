import gspread
from oauth2client.service_account import ServiceAccountCredentials

def check_data():
    print("--- Verificando datos en 'Historico_Lecturas' ---")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        doc = client.open('SysLuz')
        hoja = doc.worksheet('Historico_Lecturas')
        
        data = hoja.get_all_values()
        
        if not data:
            print("🚫 La hoja 'Historico_Lecturas' está vacía.")
        else:
            print(f"✅ Se han encontrado {len(data)} filas de datos.")
            print(f"Última fila (muestra): {data[-1]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_data()
