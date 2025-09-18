@echo off
cd /d "%~dp0qr_capturador_excel"
py -3 -m pip install -r requirements.txt
py -3 capturador_qr_excel_v2.py
