# ⚡ AppGestionLuz - Sistema de Control de Electricidad

## 📝 Descripción General
AppGestionLuz es una aplicación web interactiva diseñada para la gestión y distribución de costos de electricidad en edificios residenciales. La aplicación destaca por manejar una **lógica de instalación en serie**, donde el consumo de ciertos departamentos depende de las lecturas acumuladas de otros.

## 🛠️ Stack Tecnológico
- **Frontend**: [Streamlit](https://streamlit.io/) (Framework de Python para UIs rápidas).
- **Base de Datos**: [Google Sheets API](https://developers.google.com/sheets/api) (Usado como backend ligero y accesible).
- **Lenguaje**: Python 3.x.
- **Librerías Clave**:
  - `gspread`: Manipulación de hojas de cálculo de Google.
  - `pandas`: Manejo y procesamiento de tablas de datos.
  - `fpdf2`: Generación de reportes profesionales en PDF.
  - `matplotlib`: Creación de gráficos estadísticos de consumo.

---

## 📐 Arquitectura de Datos
La aplicación se conecta a un archivo de Google Sheets llamado **"SysLuz"**, el cual debe contener dos hojas principales:
1. **`Historico_Lecturas`**: Almacena las lecturas de los medidores mes a mes.
   - Columna A: Mes (YYYY-MM).
   - Columnas B en adelante: Lecturas de cada departamento.
2. **`Historico_Pagos`**: Registra los pagos calculados.
   - Almacena: Mes, Departamento, Consumo (kW), Monto, Estado y Fecha de Registro.

---

## 🧠 Lógica de Negocio (Instalación en Serie)
La característica más crítica de esta aplicación es su cálculo de consumo basado en la posición física de los medidores:

| Departamento | Método de Cálculo de Consumo (kW) |
| :--- | :--- |
| **Dpto 101** | `Lectura Actual - Lectura Anterior` (Consumo Directo) |
| **Dpto 102** | `(Dif. Medidor 102) - (Consumo 101)` |
| **Dpto 103** | `(Dif. Medidor 103) - (Consumo 101 + Consumo 102)` |
| **Dpto 104** | `Lectura Actual - Lectura Anterior` (Consumo Directo) |
| **Dpto 105** | `(Dif. Medidor 105) - (Consumo 101 + 102 + 103 + 104)` |

*Nota: Todas las diferencias individuales se calculan primero como `Lectura Actual - Lectura Anterior` del medidor específico.*

---

## 🚀 Funcionalidades Principales

### 1. Registro de Lecturas
- Interfaz intuitiva con validación en tiempo real.
- Muestra la **Lectura Anterior** debajo de cada campo para evitar errores de ingreso.
- Cálculo de consumo instantáneo mientras se escribe.

### 2. Cálculos y Distribución
- Distribuye el monto total del recibo general de forma proporcional al consumo de cada departamento.
- Genera métricas clave: Consumo total del edificio, monto total y promedio por departamento.

### 3. Visualización de Datos
- Tabla resumen detallada con lecturas y montos.
- Gráfico de barras comparativo para identificar picos de consumo.

### 4. Reportes y Exportación
- **PDF**: Genera un reporte formal con sello de tiempo, tabla de cobranza y gráfico de consumo.
- **Registro Automático**: Sincroniza los datos con Google Sheets con un solo clic.

---

## ⚙️ Configuración y Despliegue

### Requisitos Previos
1. Archivo `credentials.json` de una cuenta de servicio de Google Cloud.
2. Compartir el Google Sheet con el correo electrónico de la cuenta de servicio.

### Archivo `settings.json`
Permite personalizar la aplicación sin tocar el código:
```json
{
  "edificio": {
    "nombre": "Nombre del Edificio",
    "direccion": "Dirección Real",
    "moneda": "Soles/Dólares",
    "simbolo": "S/ o $"
  },
  "departamentos": [
    {"id": 1, "nombre": "Dpto 101"},
    ...
  ]
}
```

---
*Desarrollado para la gestión eficiente de energía.*
