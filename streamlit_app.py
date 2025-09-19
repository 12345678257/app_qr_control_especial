# -*- coding: utf-8 -*-
import io, json
import streamlit as st
import qrcode
from PIL import Image

def make_qr(data, ecc="Q", color="black", size=512, border=4):
    import qrcode.constants as C
    ecc_map={"L":C.ERROR_CORRECT_L,"M":C.ERROR_CORRECT_M,"Q":C.ERROR_CORRECT_Q,"H":C.ERROR_CORRECT_H}
    qr=qrcode.QRCode(version=None, box_size=max(1,size//50), border=border, error_correction=ecc_map.get(ecc,C.ERROR_CORRECT_Q))
    qr.add_data(data); qr.make(fit=True)
    img=qr.make_image(fill_color=color, back_color="white").convert("RGB")
    return img.resize((size,size), Image.Resampling.NEAREST)

st.set_page_config(page_title="QR Medicamentos", page_icon="🔲", layout="centered")
st.title("🔲 Generador de QR (Medicamentos) — FIX6 listo para Streamlit Cloud")

modo=st.radio("Modo de contenido",["Texto legible","JSON estructurado"],index=0)

col1,col2=st.columns(2)
with col1:
    nombre=st.text_input("Nombre genérico*", "CLONAZEPAM")
    conc=st.text_input("Concentración*", "2 mg")
    forma=st.text_input("Forma farmacéutica*", "Tableta")
    present=st.text_input("Presentación*", "Blíster x10")
    control=st.selectbox("Tipo de control*", ["Psicotrópico","Estupefaciente"], index=0)
    reg=st.text_input("Registro sanitario*", "INVIMA 2019M-000000-R1")
with col2:
    lote=st.text_input("Lote*", "ABC123")
    fab=st.text_input("Fecha fabricación (MM/AAAA)*", "04/2024")
    ven=st.text_input("Fecha vencimiento (MM/AAAA)*", "12/2025")
    fabricante=st.text_input("Fabricante*", "Laboratorio XYZ S.A.")
    importador=st.text_input("Importador", "Import Pharma SAS")
    entidad=st.text_input("Entidad/Hospital", "Hospital ABC")
    reem=st.text_input("Fecha reempaque (MM/AAAA)", "04/2024")

cons=st.text_area("Conservación", "Conservar a temperatura ambiente (<25°C), protegido de la luz y humedad.")
adv=st.text_area("Advertencias", "Venta bajo fórmula médica. Manténgase fuera del alcance de los niños.")

if st.button("Generar QR", type="primary"):
    if modo=="JSON estructurado":
        payload=json.dumps({
            "producto":{
                "nombre_generico":nombre,"concentracion":conc,"forma_farmaceutica":forma,"presentacion":present,
                "registro_sanitario":reg,"control":control
            },
            "lote":{"codigo":lote,"fecha_fabricacion":fab,"fecha_vencimiento":ven},
            "fabricante":fabricante,"importador":importador,
            "entidad":{"id":entidad,"reempaque":reem},
            "conservacion":cons,"advertencias":adv,
            "normativa":["Res 1478/2006","Circ 01/2016 FNE"]
        }, ensure_ascii=False, separators=(",",":"))
    else:
        payload=(
            f"MEDICAMENTO: {nombre} {conc}\n"
            f"FORMA FARMACÉUTICA: {forma}\n"
            f"PRESENTACIÓN: {present}\n"
            f"TIPO DE CONTROL: {control}\n"
            f"REGISTRO SANITARIO: {reg}\n"
            f"LOTE: {lote}\n"
            f"FECHA FABRICACIÓN: {fab}\n"
            f"FECHA VENCIMIENTO: {ven}\n"
            f"FABRICANTE: {fabricante}\n"
            f"IMPORTADOR: {importador}\n"
            f"ENTIDAD: {entidad}\n"
            f"FECHA REEMPAQUE: {reem}\n"
            f"CONSERVACIÓN: {cons}\n"
            f"ADVERTENCIAS: {adv}\n"
            "NORMATIVA: Res 1478/2006 - Circ 01/2016 FNE"
        )
    color = "#00a859" if control.lower().startswith("psico") else "#ffcc00"
    img = make_qr(payload, ecc="Q", color=color, size=512, border=4)
    st.image(img, caption="QR generado", use_column_width=True)
    bio=io.BytesIO(); img.save(bio,"PNG")
    st.download_button("⬇️ Descargar PNG", data=bio.getvalue(), file_name=f"qr_{nombre}_{lote}.png", mime="image/png")
