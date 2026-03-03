import gspread
from oauth2client.service_account import ServiceAccountCredentials

def list_spreadsheets():
    print("--- Listando hojas de cálculo compartidas ---")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Listamos todos los archivos a los que tiene acceso
        spreadsheets = client.openall()
        
        if not spreadsheets:
            print("🚫 No se encontró ninguna hoja de cálculo compartida con este Service Account.")
            print("Asegúrate de haber compartido el archivo con: gestor-luz@sysgestionluz.iam.gserviceaccount.com")
        else:
            print(f"✅ Se han encontrado {len(spreadsheets)} archivos:")
            for s in spreadsheets:
                print(f" - Título: '{s.title}' | ID: {s.id}")
                
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")

if __name__ == "__main__":
    list_spreadsheets()
