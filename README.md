# QR Etiquetado Control Especial (Colombia)

Genera etiquetas con **franja verde/amarilla**, datos obligatorios y **QR** con contenido JSON, en cumplimiento de la **Resolución 1478 de 2006** y la **Circular 01 de 2016 del FNE**.

## Cómo ejecutar
```bash
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app_qr_control_especial.py

# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app_qr_control_especial.py
```

## Campos
- Nombre genérico y concentración
- Presentación y forma farmacéutica
- Lote, fecha de fabricación, fecha de vencimiento
- Registro sanitario
- Fabricante e importador
- ID/Entidad y fecha de reempaque (opcionales)
- Conservación y advertencias
- Tipo de control: **Psicotrópico (franja verde)** o **Estupefaciente (franja amarilla)**

## CSV por lotes
Descarga la plantilla desde la barra lateral y cárgala con múltiples filas para generar un ZIP de etiquetas.

> El QR contiene un JSON con toda la información (normativa, producto, lote, entidad, conservación y advertencias) para trazabilidad.
