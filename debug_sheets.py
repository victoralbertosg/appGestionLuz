import gspread
from oauth2client.service_account import ServiceAccountCredentials

def list_worksheets():
    print("--- Verificando pestañas en 'SysLuz' ---")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        doc = client.open('SysLuz')
        
        worksheets = doc.worksheets()
        print(f"✅ Archivo '{doc.title}' abierto correctamente.")
        print(f"Se han encontrado {len(worksheets)} pestañas:")
        for w in worksheets:
            print(f" - '{w.title}'")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_worksheets()
