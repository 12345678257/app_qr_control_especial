@echo off
cd /d "%~dp0qr_generator"
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app_qr_medicamentos_v3_3.py
