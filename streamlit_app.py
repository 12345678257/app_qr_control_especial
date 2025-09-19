# -*- coding: utf-8 -*-
import io, json, csv
import streamlit as st
import qrcode
from PIL import Image, ImageDraw  # <— añadimos ImageDraw

st.set_page_config(page_title="QR Medicamentos", page_icon="🔲", layout="centered")
st.title("🔲 Generador de QR (Medicamentos) — By Luis Cordoba Garcia")

def make_qr(data, ecc="Q", color="black", size=512, border=4):
    import qrcode.constants as C
    ecc_map={"L":C.ERROR_CORRECT_L,"M":C.ERROR_CORRECT_M,"Q":C.ERROR_CORRECT_Q,"H":C.ERROR_CORRECT_H}
    qr=qrcode.QRCode(version=None, box_size=max(1,size//50), border=border,
                     error_correction=ecc_map.get(ecc,C.ERROR_CORRECT_Q))
    qr.add_data(data); qr.make(fit=True)
    img=qr.make_image(fill_color=color, back_color="white").convert("RGB")
    return img.resize((size,size), Image.Resampling.NEAREST)

# ------ NUEVO: colocar un logo centrado con fondo blanco redondeado ------
def center_logo(qr_img: Image.Image, logo_img: Image.Image,
                scale: float = 0.20, pad_ratio: float = 0.12, round_ratio: float = 0.25) -> Image.Image:
    """
    scale: fracción del lado del QR ocupada por el logo (0.20 = 20%)
    pad_ratio: grosor del marco blanco alrededor del logo (relativo al lado del logo)
    round_ratio: radio de las esquinas del marco blanco (relativo al menor lado)
    """
    qr_w, qr_h = qr_img.size
    logo = logo_img.convert("RGBA").copy()
    # tamaño máximo del logo
    max_side = int(min(qr_w, qr_h) * max(0.08, min(scale, 0.30)))  # 8%–30% seguro
    logo.thumbnail((max_side, max_side), Image.LANCZOS)

    # marco blanco redondeado para contraste
    pad = int(max(2, max_side * pad_ratio))
    bg_w, bg_h = logo.width + 2*pad, logo.height + 2*pad
    bg = Image.new("RGBA", (bg_w, bg_h), (255, 255, 255, 255))
    mask = Image.new("L", (bg_w, bg_h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, bg_w, bg_h), radius=int(min(bg_w, bg_h)*round_ratio), fill=255)
    bg.putalpha(mask)

    out = qr_img.convert("RGBA")
    cx = (qr_w - bg_w) // 2
    cy = (qr_h - bg_h) // 2
    out.alpha_composite(bg, (cx, cy))
    out.alpha_composite(logo, (cx + pad, cy + pad))
    return out.convert("RGB")
# -------------------------------------------------------------------------

FIELDS=["nombre_generico","concentracion","forma_farmaceutica","presentacion","control",
        "registro_sanitario","lote","fecha_fabricacion","fecha_vencimiento","fabricante",
        "importador","id_hospital","fecha_reempaque","conservacion","advertencias"]

def build_payload(row, modo):
    if modo=="JSON estructurado":
        return json.dumps({
            "producto":{
                "nombre_generico":row.get("nombre_generico",""),
                "concentracion":row.get("concentracion",""),
                "forma_farmaceutica":row.get("forma_farmaceutica",""),
                "presentacion":row.get("presentacion",""),
                "registro_sanitario":row.get("registro_sanitario",""),
                "control":row.get("control",""),
            },
            "lote":{"codigo":row.get("lote",""),
                    "fecha_fabricacion":row.get("fecha_fabricacion",""),
                    "fecha_vencimiento":row.get("fecha_vencimiento","")},
            "fabricante":row.get("fabricante",""),
            "importador":row.get("importador",""),
            "entidad":{"id":row.get("id_hospital",""),
                       "reempaque":row.get("fecha_reempaque","")},
            "conservacion":row.get("conservacion",""),
            "advertencias":row.get("advertencias",""),
            "normativa":["Res 1478/2006","Circ 01/2016 FNE"]
        }, ensure_ascii=False, separators=(",",":"))
    else:
        return (
            f"MEDICAMENTO: {row.get('nombre_generico','')} {row.get('concentracion','')}\n"
            f"FORMA FARMACÉUTICA: {row.get('forma_farmaceutica','')}\n"
            f"PRESENTACIÓN: {row.get('presentacion','')}\n"
            f"TIPO DE CONTROL: {row.get('control','')}\n"
            f"REGISTRO SANITARIO: {row.get('registro_sanitario','')}\n"
            f"LOTE: {row.get('lote','')}\n"
            f"FECHA FABRICACIÓN: {row.get('fecha_fabricacion','')}\n"
            f"FECHA VENCIMIENTO: {row.get('fecha_vencimiento','')}\n"
            f"FABRICANTE: {row.get('fabricante','')}\n"
            f"IMPORTADOR: {row.get('importador','')}\n"
            f"ENTIDAD: {row.get('id_hospital','')}\n"
            f"FECHA REEMPAQUE: {row.get('fecha_reempaque','')}\n"
            f"CONSERVACIÓN: {row.get('conservacion','')}\n"
            f"ADVERTENCIAS: {row.get('advertencias','')}\n"
            "NORMATIVA: Res 1478/2006 - Circ 01/2016 FNE"
        )

def control_color(control): 
    return "#ffcc00" if "estu" in (control or "").lower() else "#00a859"

with st.expander("🧩 Generar QR individual", expanded=True):
    modo = st.radio("Contenido", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

    # NUEVO: controles de tamaño y logo
    colT1, colT2, colT3 = st.columns([1,1,1])
    with colT1:
        qr_size = st.slider("Tamaño del QR (px)", 192, 1024, 384, 32)
    with colT2:
        border = st.slider("Borde (quiet zone)", 2, 10, 4, 1)
    with colT3:
        logo_scale = st.slider("Logo (% del lado)", 8, 30, 20, 1)
    logo_file = st.file_uploader("Logo en el centro (opcional)", type=["png","jpg","jpeg","webp"])

    col1,col2 = st.columns(2)
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
    cons=st.text_area("Conservación","Conservar a temperatura ambiente (<25°C), protegido de la luz y humedad.")
    adv=st.text_area("Advertencias","Venta bajo fórmula médica. Manténgase fuera del alcance de los niños.")

    if st.button("🔲 Generar QR individual", type="primary"):
        row={k:"" for k in FIELDS}
        row.update({"nombre_generico":nombre,"concentracion":conc,"forma_farmaceutica":forma,
                    "presentacion":present,"control":control,"registro_sanitario":reg,"lote":lote,
                    "fecha_fabricacion":fab,"fecha_vencimiento":ven,"fabricante":fabricante,
                    "importador":importador,"id_hospital":entidad,"fecha_reempaque":reem,
                    "conservacion":cons,"advertencias":adv})
        payload=build_payload(row, modo)
        # Con logo → usar ECC H (más robusto)
        ecc_level = "H" if logo_file else "Q"
        img=make_qr(payload, ecc=ecc_level, color=control_color(control),
                    size=qr_size, border=border)

        if logo_file:
            logo_img = Image.open(logo_file)
            img = center_logo(img, logo_img, scale=logo_scale/100.0)

        st.image(img, caption=f"QR generado (ECC: {ecc_level})", use_container_width=True)
        bio=io.BytesIO(); img.save(bio,"PNG")
        st.download_button("⬇️ Descargar PNG", data=bio.getvalue(),
                           file_name=f"qr_{nombre}_{lote}.png", mime="image/png")

st.divider(); st.subheader("📦 Generación masiva desde CSV")
tpl_cols=["nombre_generico","concentracion","forma_farmaceutica","presentacion","control",
         "registro_sanitario","lote","fecha_fabricacion","fecha_vencimiento","fabricante",
         "importador","id_hospital","fecha_reempaque","conservacion","advertencias"]
tpl=",".join(tpl_cols)+"\n"+"CLONAZEPAM,2 mg,Tableta,Blíster x10,Psicotrópico,INVIMA 2019M-000000-R1,ABC123,04/2024,12/2025,Laboratorio XYZ S.A.,Import Pharma SAS,Hospital ABC,04/2024,Conservar <25°C,Venta bajo fórmula médica\n"
st.download_button("📄 Plantilla CSV", data=tpl.encode("utf-8"),
                   file_name="plantilla_medicamentos_qr.csv", mime="text/csv")

uploaded = st.file_uploader("Sube el CSV de la plantilla", type=["csv"])
modo_batch = st.radio("Contenido (lote)", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

# Reusar el logo también en lote (si fue subido arriba)
logo_img_batch = None
if logo_file is not None:
    try:
        logo_img_batch = Image.open(logo_file).convert("RGBA")
    except Exception:
        logo_img_batch = None

if uploaded is not None:
    ...
    if st.button("🔲 Generar ZIP con QRs", type="primary"):
        import zipfile, io as _io
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, r in enumerate(rows):
                row = {k: (r.get(k, '') or '') for k in tpl_cols}
                payload = build_payload(row, modo_batch)

                # ECC alto si hay logo
                ecc_for_batch = "H" if logo_img_batch else "Q"
                img = make_qr(payload,
                              ecc=ecc_for_batch,
                              color=control_color(row.get('control','')),
                              size=qr_size,               # usa el mismo tamaño del slider
                              border=border)              # usa el mismo quiet zone

                if logo_img_batch:
                    img = center_logo(img, logo_img_batch, scale=logo_scale/100.0)

                bio = _io.BytesIO(); img.save(bio, "PNG")
                name = f"{i+1:03d}_{row.get('nombre_generico','med').strip().replace(' ','_')}_{row.get('lote','').strip()}.png"
                z.writestr(name, bio.getvalue())

        st.download_button("⬇️ Descargar ZIP", data=buf.getvalue(),
                           file_name="qrs_lote.zip", mime="application/zip")
