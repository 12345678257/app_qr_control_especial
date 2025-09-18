# QR Generator (Streamlit) — v3.3

Genera **códigos QR** con la información del medicamento. Incluye:
- Modos: *Mini página (tabla)*, *Texto legible*, *JSON*, *URL*.
- Fallback automático para evitar QRs demasiado densos.
- Modo por lotes desde CSV (descarga ZIP con PNGs).

## Ejecutar
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app_qr_medicamentos_v3_3.py
```
