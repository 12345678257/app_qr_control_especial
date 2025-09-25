# -*- coding: utf-8 -*-
import io, json, csv, datetime
import urllib.parse as urlp
import streamlit as st
import qrcode
from PIL import Image, ImageDraw

st.set_page_config(page_title="QR Medicamentos", page_icon="🔲", layout="centered")
st.title("🔲 Generador de QR (Medicamentos) — By Luis Cordoba Garcia")

# ========= Utilidades de QR =========

def make_qr(data, ecc="Q", color="black", size=512, border=4):
    import qrcode.constants as C
    ecc_map = {"L": C.ERROR_CORRECT_L, "M": C.ERROR_CORRECT_M,
               "Q": C.ERROR_CORRECT_Q, "H": C.ERROR_CORRECT_H}
    qr = qrcode.QRCode(
        version=None,
        box_size=max(1, size // 50),
        border=border,
        error_correction=ecc_map.get(ecc, C.ERROR_CORRECT_Q),
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=color, back_color="white").convert("RGB")
    return img.resize((size, size), Image.Resampling.NEAREST)

def center_logo(qr_img: Image.Image, logo_img: Image.Image,
                scale: float = 0.20, pad_ratio: float = 0.12, round_ratio: float = 0.25) -> Image.Image:
    """Coloca un logo centrado con marco blanco redondeado."""
    qr_w, qr_h = qr_img.size
    logo = logo_img.convert("RGBA").copy()
    max_side = int(min(qr_w, qr_h) * max(0.08, min(scale, 0.30)))
    logo.thumbnail((max_side, max_side), Image.LANCZOS)
    pad = int(max(2, max_side * pad_ratio))
    bg_w, bg_h = logo.width + 2 * pad, logo.height + 2 * pad

    bg = Image.new("RGBA", (bg_w, bg_h), (255, 255, 255, 255))
    mask = Image.new("L", (bg_w, bg_h), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, bg_w, bg_h), radius=int(min(bg_w, bg_h) * round_ratio), fill=255)
    bg.putalpha(mask)

    out = qr_img.convert("RGBA")
    cx, cy = (qr_w - bg_w) // 2, (qr_h - bg_h) // 2
    out.alpha_composite(bg, (cx, cy))
    out.alpha_composite(logo, (cx + pad, cy + pad))
    return out.convert("RGB")

def control_color(control):
    # color solo decorativo; tu nuevo cabezote no incluye 'control'
    return "#00a859"

def build_payload(row: dict, modo: str) -> str:
    """Texto legible o JSON estructurado dentro del QR."""
    if modo == "JSON estructurado":
        return json.dumps({
            "producto": {
                "codigo": row.get("Codigo del medicamento",""),
                "nombre_generico": row.get("nombre_generico",""),
                "concentracion": row.get("concentracion",""),
                "forma_farmaceutica": row.get("forma_farmaceutica",""),
                "presentacion": row.get("presentacion",""),
                "registro_sanitario": row.get("registro_sanitario","")
            },
            "lote": {
                "codigo": row.get("lote",""),
                "fecha_vencimiento": row.get("fecha_vencimiento","")
            },
            "fabricante": row.get("fabricante",""),
            "entidad": {"id": row.get("id_hospital","")},
            "conservacion": row.get("conservacion",""),
            "advertencias": row.get("advertencias",""),
            "normativa": row.get("normativa","Res 1478/2006 - Circ 01/2016 FNE")
        }, ensure_ascii=False, separators=(",",":"))
    else:
        return (
            f"CODIGO: {row.get('Codigo del medicamento','')}\n"
            f"MEDICAMENTO: {row.get('nombre_generico','')} {row.get('concentracion','')}\n"
            f"FORMA FARMACÉUTICA: {row.get('forma_farmaceutica','')}\n"
            f"PRESENTACIÓN: {row.get('presentacion','')}\n"
            f"REGISTRO SANITARIO: {row.get('registro_sanitario','')}\n"
            f"LOTE: {row.get('lote','')}\n"
            f"FECHA VENCIMIENTO: {row.get('fecha_vencimiento','')}\n"
            f"FABRICANTE: {row.get('fabricante','')}\n"
            f"ENTIDAD/HOSPITAL: {row.get('id_hospital','')}\n"
            f"CONSERVACIÓN: {row.get('conservacion','')}\n"
            f"ADVERTENCIAS: {row.get('advertencias','')}\n"
            f"NORMATIVA: {row.get('normativa','Res 1478/2006 - Circ 01/2016 FNE')}"
        )

def public_qr_url(payload: str, size: int = 384, ecc: str = "Q") -> str:
    """Link público al PNG del QR (se genera on-the-fly)."""
    return (
        "https://quickchart.io/qr"
        f"?text={urlp.quote(payload, safe='')}"
        f"&ecLevel={ecc}"
        f"&size={size}"
    )

# ========= UI — Individual =========
with st.expander("🧩 Generar QR individual", expanded=True):
    modo = st.radio("Contenido", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

    colT1, colT2, colT3 = st.columns([1,1,1])
    with colT1: qr_size = st.slider("Tamaño del QR (px)", 192, 1024, 384, 32)
    with colT2: border = st.slider("Borde (quiet zone)", 2, 10, 4, 1)
    with colT3: logo_scale = st.slider("Logo (% del lado)", 8, 30, 20, 1)
    logo_file = st.file_uploader("Logo en el centro (opcional)", type=["png","jpg","jpeg","webp"])

    # Campos del NUEVO cabezote
    col1, col2 = st.columns(2)
    with col1:
        codigo = st.text_input("Codigo del medicamento", "ABC-001")
        nombre = st.text_input("Nombre genérico*", "CLONAZEPAM")
        conc   = st.text_input("Concentración*", "2 mg")
        forma  = st.text_input("Forma farmacéutica*", "Tableta")
        present= st.text_input("Presentación*", "Blíster x10")
        reg    = st.text_input("Registro sanitario*", "INVIMA 2019M-000000-R1")
    with col2:
        lote   = st.text_input("Lote*", "ABC123")
        ven    = st.text_input("Fecha vencimiento (MM/AAAA)*", "12/2025")
        fabricante = st.text_input("Fabricante*", "Laboratorio XYZ S.A.")
        entidad    = st.text_input("Entidad/Hospital", "Hospital ABC")
        cons = st.text_area("Conservación","Conservar a temperatura ambiente (<25°C), protegido de la luz y humedad.", height=80)
        adv  = st.text_area("Advertencias","Venta bajo fórmula médica. Manténgase fuera del alcance de los niños.", height=80)
    normativa = st.text_input("Normativa", "Res 1478/2006 - Circ 01/2016 FNE")

    if st.button("🔲 Generar QR individual", type="primary"):
        row = {
            "Codigo del medicamento": codigo,
            "nombre_generico": nombre,
            "concentracion": conc,
            "forma_farmaceutica": forma,
            "presentacion": present,
            "registro_sanitario": reg,
            "lote": lote,
            "fecha_vencimiento": ven,
            "fabricante": fabricante,
            "id_hospital": entidad,
            "conservacion": cons,
            "advertencias": adv,
            "normativa": normativa
        }

        payload = build_payload(row, modo)
        ecc_level = "H" if logo_file else "Q"

        img = make_qr(payload, ecc=ecc_level, color=control_color(None),
                      size=qr_size, border=border)
        if logo_file:
            img = center_logo(img, Image.open(logo_file), scale=logo_scale/100.0)

        st.image(img, caption=f"QR generado (ECC: {ecc_level})", use_container_width=True)

        # Link público al PNG del QR
        url_publica = public_qr_url(payload, size=qr_size, ecc=ecc_level)
        st.text_input("URL pública del QR", value=url_publica, help="Puedes copiarla y abrirla en cualquier lugar.")

        # Descargar PNG
        bio = io.BytesIO(); img.save(bio, "PNG")
        st.download_button("⬇️ Descargar PNG", data=bio.getvalue(),
                           file_name=f"qr_{nombre}_{lote}.png", mime="image/png")

# ========= UI — Lote (CSV) =========
st.divider(); st.subheader("📦 Generación masiva desde CSV")

HEAD_IN = [
    "Codigo del medicamento","nombre_generico","concentracion","forma_farmaceutica","presentacion",
    "registro_sanitario","lote","fecha_vencimiento","fabricante","id_hospital","conservacion",
    "advertencias","normativa"
]

HEAD_OUT = [
    "timestamp","Codigo del medicamento","nombre_generico","concentracion","forma_farmaceutica",
    "presentacion","registro_sanitario","lote","fecha_vencimiento","fabricante","id_hospital",
    "conservacion","advertencias","normativa","url_qr","raw"
]

tpl = ",".join(HEAD_OUT) + "\n" + \
      f"{datetime.datetime.now():%d/%m/%Y %H:%M},ABC-001,CLONAZEPAM,2 mg,Tableta,Blíster x10,INVIMA 2019M-000000-R1,ABC123,12/2025,Laboratorio XYZ S.A.,Hospital ABC,Conservar <25°C,Venta bajo fórmula médica,Res 1478/2006 - Circ 01/2016 FNE,,\n"

st.download_button("📄 Plantilla CSV (nuevo cabezote)", data=tpl.encode("utf-8"),
                   file_name="plantilla_medicamentos_qr_nuevo.csv", mime="text/csv")

uploaded = st.file_uploader("Sube el CSV (nuevo cabezote o solo los campos de entrada)", type=["csv"])
modo_batch = st.radio("Contenido del QR (lote)", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

# Reusar el logo también en lote (si fue subido arriba)
logo_img_batch = None
if 'logo_file' in locals() and logo_file is not None:
    try:
        logo_img_batch = Image.open(logo_file).convert("RGBA")
    except Exception:
        logo_img_batch = None

if uploaded is not None:
    # Leer CSV (acepta tanto HEAD_OUT como HEAD_IN)
    try:
        text = uploaded.getvalue().decode("utf-8-sig")
    except Exception:
        text = uploaded.getvalue().decode("latin-1")
    reader = csv.DictReader(text.splitlines())
    fieldnames = [f.strip() for f in (reader.fieldnames or [])]

    # ¿Es un archivo con HEAD_OUT? -> lo tratamos como HEAD_IN quitando las columnas extra
    if set(HEAD_OUT).issubset(set(fieldnames)) or ("url_qr" in fieldnames and "raw" in fieldnames):
        # normalizamos a HEAD_IN
        rows_in = []
        for r in reader:
            rows_in.append({k: r.get(k, "") for k in HEAD_IN})
    else:
        # validar que al menos tenga los de entrada
        missing = [c for c in HEAD_IN if c not in fieldnames]
        if missing:
            st.error("❌ Faltan columnas: " + ", ".join(missing))
            st.stop()
        rows_in = list(reader)

    st.success(f"✅ {len(rows_in)} filas")
    st.dataframe(rows_in[:10])

    # Preparar salida, PNGs y CSV con url_qr
    if st.button("🔲 Generar ZIP + CSV con URLs", type="primary"):
        import zipfile
        zip_buf = io.BytesIO()
        out_csv_buf = io.StringIO(newline="")
        w = csv.writer(out_csv_buf, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        w.writerow(HEAD_OUT)

        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, r in enumerate(rows_in):
                # normalizar row
                row = {k: (r.get(k, "") or "") for k in HEAD_IN}
                # payload
                payload = build_payload(row, modo_batch)
                # link público
                ecc_for_batch = "H" if logo_img_batch else "Q"
                url_publica = public_qr_url(payload, size=384, ecc=ecc_for_batch)

                # PNG (con o sin logo)
                img = make_qr(payload, ecc=ecc_for_batch, color=control_color(None),
                              size=384, border=4)
                if logo_img_batch:
                    img = center_logo(img, logo_img_batch, scale=0.20)
                png = io.BytesIO(); img.save(png, "PNG")

                # nombre de archivo
                base = f"{i+1:03d}_{row.get('nombre_generico','med').strip().replace(' ','_')}_{row.get('lote','').strip()}"
                z.writestr(base + ".png", png.getvalue())

                # fila salida (con timestamp, url_qr y raw)
                timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                out_row = [
                    timestamp,
                    row.get("Codigo del medicamento",""),
                    row.get("nombre_generico",""),
                    row.get("concentracion",""),
                    row.get("forma_farmaceutica",""),
                    row.get("presentacion",""),
                    row.get("registro_sanitario",""),
                    row.get("lote",""),
                    row.get("fecha_vencimiento",""),
                    row.get("fabricante",""),
                    row.get("id_hospital",""),
                    row.get("conservacion",""),
                    row.get("advertencias",""),
                    row.get("normativa","Res 1478/2006 - Circ 01/2016 FNE"),
                    url_publica,
                    payload
                ]
                w.writerow(out_row)

        st.download_button("⬇️ Descargar ZIP de PNGs", data=zip_buf.getvalue(),
                           file_name="qrs_lote.zip", mime="application/zip")
        st.download_button("⬇️ Descargar CSV con URLs", data=out_csv_buf.getvalue().encode("utf-8"),
                           file_name="salida_con_urls.csv", mime="text/csv")
