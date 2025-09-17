# -*- coding: utf-8 -*-
"""
App de Etiquetado con QR para Medicamentos de Control Especial
Cumple con la Resolución 1478 de 2006 y la Circular 01 de 2016 del FNE (Colombia).
Autor: ChatGPT
"""

import io
import json
import base64
import textwrap
from datetime import datetime
from typing import Dict, Any

import streamlit as st

# Dependencias gráficas
from PIL import Image, ImageDraw, ImageFont
import qrcode

try:
    import pandas as pd
except Exception:
    pd = None

# --------------------------- Utilidades ---------------------------

def mm_to_px(mm: float, dpi: int = 300) -> int:
    # 1 pulgada = 25.4 mm
    return int((mm / 25.4) * dpi)

def _load_font(size: int):
    # Intentar usar DejaVu (viene en la mayoría de entornos); si no, usar la básica
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except Exception:
        return ImageFont.load_default()

def make_qr(payload: Dict[str, Any], box_size: int = 10, border: int = 2) -> Image.Image:
    qr = qrcode.QRCode(version=None, box_size=box_size, border=border, error_correction=qrcode.constants.ERROR_CORRECT_Q)
    qr.add_data(json.dumps(payload, ensure_ascii=False))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.convert("RGB")

def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width_px: int) -> str:
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width_px:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return "\n".join(lines)

# --------------------------- Render de Etiqueta ---------------------------

def render_label(data: Dict[str, Any], template: str = "sachet", dpi: int = 300) -> Image.Image:
    """
    Templates:
      - 'sachet'  : 80x100 mm, franja superior
      - 'blister' : 60x90  mm, esquina redondeada (simple)
    """
    if template == "sachet":
        w_mm, h_mm = 80, 100
    else:
        w_mm, h_mm = 60, 90

    W, H = mm_to_px(w_mm, dpi), mm_to_px(h_mm, dpi)
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # Colores para franja
    control = (data.get("control") or "").strip().lower()
    if "estupe" in control:
        band_color = (255, 204, 0)   # Amarilla
        band_text = "MEDICAMENTO DE CONTROL ESPECIAL · ESTUPEFACIENTE"
    else:
        band_color = (0, 168, 89)    # Verde psicotrópicos
        band_text = "MEDICAMENTO DE CONTROL ESPECIAL · PSICOTRÓPICO"

    # Franja superior
    band_h = int(H * 0.13)
    draw.rectangle([0, 0, W, band_h], fill=band_color)

    # Título en franja
    font_band = _load_font(size=int(band_h*0.38))
    tw = draw.textlength(band_text, font=font_band)
    draw.text(((W - tw) / 2, int(band_h*0.30)), band_text, fill="white", font=font_band)

    # Encabezado de medicamento
    margin = mm_to_px(6, dpi)
    y = band_h + mm_to_px(4, dpi)

    font_h1 = _load_font(size=int(H * 0.08))
    font_h2 = _load_font(size=int(H * 0.055))
    font_body = _load_font(size=int(H * 0.042))
    font_small = _load_font(size=int(H * 0.035))

    nombre = (data.get("nombre_generico") or "").upper().strip()
    concent = (data.get("concentracion") or "").strip()
    forma = (data.get("forma_farmaceutica") or "").strip()
    present = (data.get("presentacion") or "").strip()

    # Nombre genérico
    draw.text((margin, y), nombre, fill="black", font=font_h1)
    y += font_h1.size + mm_to_px(1.5, dpi)
    # Concentración
    draw.text((margin, y), concent, fill="black", font=font_h2)
    y += font_h2.size + mm_to_px(1.5, dpi)
    # Presentación / forma
    pf_line = f"{forma} · {present}".strip(" ·")
    draw.text((margin, y), pf_line, fill="black", font=font_body)
    y += font_body.size + mm_to_px(3, dpi)

    # Columna de datos y QR
    qr_side = int(H * 0.28)
    payload = build_qr_payload(data)
    qr_img = make_qr(payload, box_size=8, border=2).resize((qr_side, qr_side))

    # Datos obligatorios
    datos = [
        f"Lote: {data.get('lote','')}",
        f"Fab.: {data.get('fecha_fabricacion','')}",
        f"Vence: {data.get('fecha_vencimiento','')}",
        f"Reg. Sanitario: {data.get('registro_sanitario','')}",
        f"Fabricante: {data.get('fabricante','')}",
        f"Importador: {data.get('importador','')}",
    ]
    # Opcionales
    if data.get("id_hospital"):
        datos.append(f"ID/Entidad: {data.get('id_hospital')}")
    if data.get("fecha_reempaque"):
        datos.append(f"Reempaque: {data.get('fecha_reempaque')}")

    max_text_width = W - (margin*2 + qr_side + mm_to_px(4, dpi))
    for line in datos:
        wrapped = wrap_text(draw, line, font_body, max_text_width)
        draw.multiline_text((margin, y), wrapped, fill="black", font=font_body, spacing=2)
        y += (font_body.size + mm_to_px(1.2, dpi)) * (wrapped.count("\\n") + 1)

    # Colocar QR a la derecha
    qr_x = W - margin - qr_side
    qr_y = band_h + int((H*0.35 - band_h - qr_side) / 2)
    img.paste(qr_img, (qr_x, max(band_h + mm_to_px(2, dpi), qr_y)))

    # Instrucciones y advertencias
    y = int(H * 0.60)
    cons = data.get("conservacion", "")
    adv = data.get("advertencias", "")

    if cons:
        cons_title = "Conservación:"
        draw.text((margin, y), cons_title, fill="black", font=font_body); y += font_body.size + 4
        draw.multiline_text((margin, y), wrap_text(draw, cons, font_small, W - margin*2), fill="black", font=font_small, spacing=2)
        y += mm_to_px(5, dpi)

    if adv:
        draw.text((margin, y), "Advertencias:", fill="black", font=font_body); y += font_body.size + 4
        draw.multiline_text((margin, y), wrap_text(draw, adv, font_small, W - margin*2), fill="black", font=font_small, spacing=2)

    # Pie de normativa
    foot = "Cumple Res. 1478/2006 y Circ. 01/2016 FNE"
    ftw = draw.textlength(foot, font=font_small)
    draw.text(((W - ftw) / 2, H - mm_to_px(7, dpi)), foot, fill="black", font=font_small)

    return img

def build_qr_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    # Estructura JSON con campos normativos y meta para trazabilidad
    payload = {
        "v": 1,
        "normativa": ["Res 1478/2006", "Circ 01/2016 FNE"],
        "producto": {
            "nombre_generico": data.get("nombre_generico"),
            "concentracion": data.get("concentracion"),
            "forma_farmaceutica": data.get("forma_farmaceutica"),
            "presentacion": data.get("presentacion"),
            "registro_sanitario": data.get("registro_sanitario"),
            "control": data.get("control"),
        },
        "lote": {
            "codigo": data.get("lote"),
            "fecha_fabricacion": data.get("fecha_fabricacion"),
            "fecha_vencimiento": data.get("fecha_vencimiento"),
        },
        "fabricante": data.get("fabricante"),
        "importador": data.get("importador"),
        "entidad": {
            "id": data.get("id_hospital"),
            "reempaque": data.get("fecha_reempaque"),
        },
        "conservacion": data.get("conservacion"),
        "advertencias": data.get("advertencias"),
    }
    return payload

def image_download_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()

# --------------------------- UI ---------------------------

st.set_page_config(page_title="QR Etiquetado Control Especial", page_icon="🧪", layout="centered")

st.title("🧪 Generador de etiquetas con QR")
st.caption("Cumplimiento: **Resolución 1478 de 2006** y **Circular 01 de 2016 del FNE** (Colombia).")

with st.sidebar:
    st.header("⚙️ Configuración")
    template = st.selectbox("Plantilla", ["sachet", "blister"], help="Ejemplos como los de la imagen: sobre tipo sachet o blíster.")
    control = st.selectbox("Tipo de control", ["Psicotrópico (franja verde)", "Estupefaciente (franja amarilla)"])
    dpi = st.slider("Calidad (DPI)", 200, 600, 300, step=50)
    st.markdown("---")
    st.markdown("### Modo por lotes (CSV)")
    st.markdown("Descarga la plantilla de columnas y cárgala con tus registros.")

    cols = ["nombre_generico","concentracion","forma_farmaceutica","presentacion",
            "lote","fecha_fabricacion","fecha_vencimiento","registro_sanitario",
            "fabricante","importador","id_hospital","fecha_reempaque",
            "conservacion","advertencias","control"]
    csv_template = ",".join(cols) + "\\n"
    st.download_button("📄 Descargar plantilla CSV", data=csv_template.encode("utf-8"), file_name="plantilla_etiquetas.csv", mime="text/csv")

    uploaded_csv = st.file_uploader("Subir CSV para generar ZIP", type=["csv"])

# Formulario principal
with st.form("datos"):
    st.subheader("Datos del medicamento")
    c1, c2 = st.columns(2)
    with c1:
        nombre_generico = st.text_input("Nombre genérico", "CLONAZEPAM")
        concentracion = st.text_input("Concentración", "2 mg")
        forma = st.text_input("Forma farmacéutica", "Tableta")
        presentacion = st.text_input("Presentación", "Blíster x10")
        lote = st.text_input("Lote", "ABC123")
        regsan = st.text_input("Registro sanitario", "INVIMA 2019M-000000-R1")
        fabricante = st.text_input("Fabricante", "Laboratorio XYZ S.A.")
        importador = st.text_input("Importador", "Import Pharma SAS")
    with c2:
        fecha_fab = st.text_input("Fecha de fabricación (MM/AAAA)", "04/2024")
        fecha_ven = st.text_input("Fecha de vencimiento (MM/AAAA)", "12/2025")
        entidad = st.text_input("ID/Entidad (opcional)", "Hospital ABC")
        reempaque = st.text_input("Fecha de reempaque (MM/AAAA, opcional)", "04/2024")
        conservacion = st.text_area("Conservación", "Conservar a temperatura <25°C, protegido de la luz y humedad.")
        advertencias = st.text_area("Advertencias", "Venta bajo fórmula médica. Manténgase fuera del alcance de los niños. Uso exclusivo bajo control.")
    submitted = st.form_submit_button("Generar etiqueta")

if submitted:
    data = {
        "nombre_generico": nombre_generico,
        "concentracion": concentracion,
        "forma_farmaceutica": forma,
        "presentacion": presentacion,
        "lote": lote,
        "fecha_fabricacion": fecha_fab,
        "fecha_vencimiento": fecha_ven,
        "registro_sanitario": regsan,
        "fabricante": fabricante,
        "importador": importador,
        "id_hospital": entidad,
        "fecha_reempaque": reempaque,
        "conservacion": conservacion,
        "advertencias": advertencias,
        "control": "Estupefaciente" if control.startswith("Estupe") else "Psicotrópico",
    }

    img = render_label(data, template=template, dpi=dpi)

    st.image(img, caption="Vista previa", use_column_width=True)
    st.download_button("⬇️ Descargar PNG", data=image_download_bytes(img, "PNG"), file_name=f"etiqueta_{nombre_generico.strip().upper().replace(' ','_')}.png", mime="image/png")

# Lotes desde CSV
if uploaded_csv is not None:
    if pd is None:
        st.error("Para modo por lotes se requiere la librería pandas. Instálala con: pip install pandas")
    else:
        try:
            import pandas as _p
            df = _p.read_csv(uploaded_csv, dtype=str).fillna("")
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, row in df.iterrows():
                    rec = row.to_dict()
                    # asegurar 'control' si no viene en CSV; usar el del sidebar
                    rec.setdefault("control", "Estupefaciente" if control.startswith("Estupe") else "Psicotrópico")
                    img = render_label(rec, template=template)
                    fname = f"etiqueta_{i+1}_{(rec.get('nombre_generico') or 'producto').upper().replace(' ','_')}.png"
                    bio = io.BytesIO()
                    img.save(bio, format="PNG")
                    zf.writestr(fname, bio.getvalue())
            st.download_button("⬇️ Descargar ZIP de etiquetas", data=zip_buffer.getvalue(), file_name="etiquetas_qr.zip", mime="application/zip")
            st.success(f"Se generaron {len(df)} etiquetas.")
        except Exception as e:
            st.exception(e)
