# -*- coding: utf-8 -*-
import io, json, csv, datetime, urllib.parse as urlp
import streamlit as st
import qrcode
from PIL import Image, ImageDraw

# Opcional para leer XLSX/crear XLSX
try:
    import pandas as pd
except Exception:
    pd = None

st.set_page_config(page_title="QR Medicamentos", page_icon="🔲", layout="centered")
st.title("🔲 Generador de QR (Medicamentos)")

# ========== Constantes (campos base para construir el payload) ==========
HEAD_IN = [
    "Codigo del medicamento","nombre_generico","concentracion","forma_farmaceutica","presentacion",
    "registro_sanitario","lote","fecha_vencimiento","fabricante","id_hospital","conservacion",
    "advertencias","normativa"
]
# Nota: el orden final del archivo de salida ahora se toma de la plantilla del usuario.

# ========== Utilidades de QR ==========
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

def control_color(_):
    return "#00a859"

def build_payload(row: dict, modo: str) -> str:
    """Texto legible o JSON estructurado dentro del QR (nuevo cabezote)."""
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
    """Link público al PNG del QR (QuickChart)."""
    return (
        "https://quickchart.io/qr"
        f"?text={urlp.quote(payload, safe='')}"
        f"&ecLevel={ecc}"
        f"&size={size}"
    )

# ========== Lectura de plantilla (CSV/XLSX) conservando CABEZOTE del usuario ==========
def read_table(uploaded_file):
    """
    Devuelve (records_original:list[dict], delimiter:str|None, input_headers:list[str])
    - CSV: autodetecta delimitador (',' o ';')
    - XLSX: usa pandas, sin delimitador
    No reordena ni cambia los nombres de columnas; preserva el cabezote del usuario.
    """
    # XLSX
    if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        if pd is None:
            st.error("❌ Falta pandas para leer Excel. Instala: `pip install pandas openpyxl`")
            st.stop()
        try:
            df = pd.read_excel(uploaded_file, dtype=str).fillna("")
        except Exception as e:
            st.error(f"❌ No se pudo leer el Excel: {e}")
            st.stop()
        fieldnames = [str(c).strip() for c in df.columns]
        return df.to_dict(orient="records"), None, fieldnames

    # CSV
    raw = uploaded_file.getvalue()
    try:
        text = raw.decode("utf-8-sig")
    except Exception:
        text = raw.decode("latin-1")
    first_line = text.splitlines()[0] if text else ""
    delim = ";" if first_line.count(";") >= first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    fieldnames = [f.strip() for f in (reader.fieldnames or [])]
    return list(reader), delim, fieldnames

# ========== Individual ==========
with st.expander("🧩 Generar QR individual", expanded=True):
    modo = st.radio("Contenido del QR", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

    col_cfg = st.columns(3)
    with col_cfg[0]:
        qr_size = st.slider("Tamaño del QR (px)", 192, 1024, 384, 32)
    with col_cfg[1]:
        border = st.slider("Borde (quiet zone)", 2, 10, 4, 1)
    with col_cfg[2]:
        logo_scale = st.slider("Logo (% del lado)", 8, 30, 20, 1)
    logo_file = st.file_uploader("Logo en el centro (opcional)", type=["png","jpg","jpeg","webp"])

    # NUEVO cabezote (solo campos de entrada)
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

        # URL pública al PNG del QR
        url_publica = public_qr_url(payload, size=qr_size, ecc=ecc_level)
        st.text_input("URL pública del QR", value=url_publica, help="Cópiala y ábrela en cualquier lugar.")

        # Descargar PNG
        bio = io.BytesIO(); img.save(bio, "PNG")
        st.download_button("⬇️ Descargar PNG", data=bio.getvalue(),
                           file_name=f"qr_{nombre}_{lote}.png", mime="image/png")

# ========== Plantilla de ejemplo (opcional) ==========
st.divider(); st.subheader("📄 Plantilla de ejemplo (nuevo cabezote)")
if pd is not None:
    tpl_df = pd.DataFrame([{
        "timestamp": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Codigo del medicamento": "ABC-001",
        "nombre_generico": "CLONAZEPAM",
        "concentracion": "2 mg",
        "forma_farmaceutica": "Tableta",
        "presentacion": "Blíster x10",
        "registro_sanitario": "INVIMA 2019M-000000-R1",
        "lote": "ABC123",
        "fecha_vencimiento": "12/2025",
        "fabricante": "Laboratorio XYZ S.A.",
        "id_hospital": "Hospital ABC",
        "conservacion": "Conservar <25°C",
        "advertencias": "Venta bajo fórmula médica",
        "normativa": "Res 1478/2006 - Circ 01/2016 FNE",
        "url_qr": "",
        "raw": ""
    }])
    col_tpl = st.columns(2)
    # CSV
    csv_buf = io.StringIO(newline="")
    tpl_df.to_csv(csv_buf, index=False)
    col_tpl[0].download_button("⬇️ Descargar plantilla CSV", data=csv_buf.getvalue().encode("utf-8"),
                               file_name="plantilla_medicamentos_qr_nuevo.csv", mime="text/csv")
    # XLSX
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="xlsxwriter") as writer:
        tpl_df.to_excel(writer, index=False, sheet_name="plantilla")
    col_tpl[1].download_button("⬇️ Descargar plantilla XLSX", data=xlsx_buf.getvalue(),
                               file_name="plantilla_medicamentos_qr_nuevo.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ========== Lote (CSV/XLSX) — salida horizontal con el mismo orden de tu plantilla ==========
st.divider(); st.subheader("📦 Generación masiva (CSV o XLSX)")
uploaded = st.file_uploader("Sube la plantilla CSV/XLSX (usamos exactamente tu orden de columnas)", type=["csv","xlsx","xls"])
modo_batch = st.radio("Contenido del QR (lote)", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

# Reutilizar logo del individual
logo_img_batch = None
if 'logo_file' in locals() and logo_file is not None:
    try:
        logo_img_batch = Image.open(logo_file).convert("RGBA")
    except Exception:
        logo_img_batch = None

if uploaded is not None:
    records, delim_in, input_headers = read_table(uploaded)
    st.success(f"✅ {len(records)} filas detectadas")
    st.dataframe(records[:10])

    # Determinar encabezado de salida: el MISMO orden de la plantilla
    out_headers = list(input_headers)  # copia
    # Si no está timestamp, lo insertamos al inicio
    if "timestamp" not in out_headers:
        out_headers.insert(0, "timestamp")
    # Asegurar url_qr y raw al final (en ese orden)
    for extra in ["url_qr", "raw"]:
        if extra in out_headers:
            out_headers.remove(extra)
        out_headers.append(extra)

    # Selector delimitador para CSV de salida
    delim_out = st.selectbox("Delimitador para CSV de salida",
                             ["Automático (igual a entrada)", "Coma (,)", "Punto y coma (;)"],
                             index=0)
    if delim_out == "Automático (igual a entrada)":
        delim_used = (delim_in if delim_in in (",",";") else ",")
    elif delim_out == "Coma (,)":
        delim_used = ","
    else:
        delim_used = ";"

    if st.button("🔲 Generar ZIP de PNGs + CSV/XLSX con URLs (orden = tu plantilla)", type="primary"):
        import zipfile
        zip_buf = io.BytesIO()
        out_rows = []

        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, r in enumerate(records):
                # Para construir el payload necesitamos estos campos base:
                base_row = {k: (r.get(k, "") or "") for k in HEAD_IN}
                payload = build_payload(base_row, modo_batch)
                ecc_for_batch = "H" if logo_img_batch else "Q"
                url_publica = public_qr_url(payload, size=384, ecc=ecc_for_batch)

                # PNG (con o sin logo)
                img = make_qr(payload, ecc=ecc_for_batch, color=control_color(None),
                              size=384, border=4)
                if logo_img_batch:
                    img = center_logo(img, logo_img_batch, scale=0.20)
                png = io.BytesIO(); img.save(png, "PNG")

                base_name = f"{i+1:03d}_{base_row.get('nombre_generico','med').strip().replace(' ','_')}_{base_row.get('lote','').strip()}"
                z.writestr(base_name + ".png", png.getvalue())

                # Fila de salida: partimos de las columnas del usuario en su mismo orden
                out = {k: (r.get(k, "") or "") for k in input_headers}
                out["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                out["url_qr"] = url_publica
                out["raw"] = payload
                out_rows.append(out)

        # CSV salida con el MISMO orden de la plantilla
        csv_out_buf = io.StringIO(newline="")
        w = csv.DictWriter(csv_out_buf, fieldnames=out_headers, delimiter=delim_used, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for row in out_rows:
            # Asegurar todas las llaves presentes (vacías si faltan)
            w.writerow({k: row.get(k, "") for k in out_headers})

        # XLSX salida con el MISMO orden
        xlsx_bytes = b""
        if pd is not None:
            df_out = pd.DataFrame([{k: r.get(k, "") for k in out_headers} for r in out_rows])
            xlsx_out = io.BytesIO()
            with pd.ExcelWriter(xlsx_out, engine="xlsxwriter") as writer:
                df_out.to_excel(writer, index=False, sheet_name="salida")
            xlsx_bytes = xlsx_out.getvalue()

        st.download_button("⬇️ Descargar ZIP de PNGs", data=zip_buf.getvalue(),
                           file_name="qrs_lote.zip", mime="application/zip")
        st.download_button("⬇️ Descargar CSV con URLs (orden = tu plantilla)",
                           data=csv_out_buf.getvalue().encode("utf-8"),
                           file_name="salida_con_urls.csv", mime="text/csv")
        if xlsx_bytes:
            st.download_button("⬇️ Descargar XLSX con URLs (orden = tu plantilla)",
                               data=xlsx_bytes,
                               file_name="salida_con_urls.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("ℹ️ Para XLSX instala `pandas` y `xlsxwriter` en requirements.")
