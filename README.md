# Suite QR Medicamentos

Este repo contiene:
- `qr_generator/` → **App Streamlit** para generar QR (individual y por lotes).
- `qr_capturador_excel/` → **App de escritorio** (Tkinter) para escanear y tabular a Excel.

## Ejecutar — Generador (Streamlit)
```bash
cd qr_generator
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app_qr_medicamentos_v3_3.py
```

## Ejecutar — Capturador a Excel
```bash
cd qr_capturador_excel
pip install -r requirements.txt
python capturador_qr_excel_v2.py
```

## Subir a GitHub (pasos rápidos)

1. Crea un repo vacío en GitHub (sin README).
2. En esta carpeta (raíz del proyecto):
```bash
git init
git add .
git commit -m "Init: generador QR + capturador Excel"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

> Si prefieres SSH:
```bash
git remote remove origin 2>NUL
git remote add origin git@github.com:TU_USUARIO/TU_REPO.git
git push -u origin main
```

## Licencia
MIT
