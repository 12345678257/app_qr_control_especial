# -*- coding: utf-8 -*-
import io, json, csv, datetime, urllib.parse as urlp
import streamlit as st
import qrcode
from PIL import Image, ImageDraw

try:
    import pandas as pd
except Exception:
    pd = None

st.set_page_config(page_title="QR Medicamentos", page_icon="🔲", layout="centered")
st.title("🔲 Generador de QR (Medicamentos) — 1.5\" físico (DPI embebido)")

HEAD_IN = [
    "Codigo del medicamento","nombre_generico","concentracion","forma_farmaceutica","presentacion",
    "registro_sanitario","lote","fecha_vencimiento","fabricante","id_hospital","conservacion",
    "advertencias","normativa"
]

def center_logo(qr_img: Image.Image, logo_img: Image.Image,
                scale: float = 0.20, pad_ratio: float = 0.12, round_ratio: float = 0.25) -> Image.Image:
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

def make_qr_physical(data: str, inches: float, dpi: int, ecc: str, color: str, border: int,
                     logo_img=None, logo_scale: float = 0.20):
    import qrcode.constants as C
    ecc_map = {"L": C.ERROR_CORRECT_L, "M": C.ERROR_CORRECT_M,
               "Q": C.ERROR_CORRECT_Q, "H": C.ERROR_CORRECT_H}

    target_px = int(round(inches * dpi))
    qr_tmp = qrcode.QRCode(version=None, box_size=1, border=border,
                           error_correction=ecc_map.get(ecc, C.ERROR_CORRECT_Q))
    qr_tmp.add_data(data); qr_tmp.make(fit=True)
    modules = qr_tmp.modules_count
    total_modules = modules + 2 * border
    box_size = max(1, target_px // total_modules)
    actual_px = total_modules * box_size

    qr = qrcode.QRCode(version=None, box_size=box_size, border=border,
                       error_correction=ecc_map.get(ecc, C.ERROR_CORRECT_Q))
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color=color, back_color="white").convert("RGB")

    if actual_px < target_px:
        pad = (target_px - actual_px) // 2
        canvas = Image.new("RGB", (target_px, target_px), "white")
        canvas.paste(img, (pad, pad)); img = canvas; actual_px = target_px

    if logo_img is not None:
        img = center_logo(img, logo_img, scale=logo_scale)

    mm_per_pixel = 25.4 / dpi
    info = {
        "dpi": dpi, "inches": inches, "target_px": target_px, "actual_px": actual_px,
        "modules": modules, "border_modules": border, "box_size_px": box_size,
        "module_size_mm": round(box_size * mm_per_pixel, 3), "ecc": ecc
    }
    return img, info

def control_color(_): return "#00a859"

def build_payload(row: dict, modo: str) -> str:
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
            "lote": {"codigo": row.get("lote",""), "fecha_vencimiento": row.get("fecha_vencimiento","")},
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

def public_qr_url(payload: str, size: int, ecc: str) -> str:
    return "https://quickchart.io/qr?text=" + urlp.quote(payload, safe="") + f"&ecLevel={ecc}&size={size}"

def read_table(uploaded_file):
    if uploaded_file.name.lower().endswith((".xlsx",".xls")):
        if pd is None:
            st.error("❌ Falta pandas para leer Excel. Instala: `pip install pandas openpyxl`"); st.stop()
        try:
            df = pd.read_excel(uploaded_file, dtype=str).fillna("")
        except Exception as e:
            st.error(f"❌ No se pudo leer el Excel: {e}"); st.stop()
        return df.to_dict(orient="records"), None, [str(c).strip() for c in df.columns]
    raw = uploaded_file.getvalue()
    try: text = raw.decode("utf-8-sig")
    except Exception: text = raw.decode("latin-1")
    first = text.splitlines()[0] if text else ""
    delim = ";" if first.count(";") >= first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return list(reader), delim, [f.strip() for f in (reader.fieldnames or [])]

# ---------------- Individual ----------------
with st.expander("🧩 Generar QR individual", expanded=True):
    modo = st.radio("Contenido del QR", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

    c1,c2,c3 = st.columns(3)
    with c1: inches = st.number_input("Tamaño físico (pulgadas)", 1.0, 3.0, 1.5, 0.1)
    with c2: dpi = st.selectbox("DPI", [203,300,600], index=1)
    with c3: border = st.slider("Borde (quiet zone)", 2, 10, 4, 1)

    l1,l2 = st.columns(2)
    with l1: logo_scale = st.slider("Logo (% del lado)", 8, 30, 20, 1)
    with l2: logo_file = st.file_uploader("Logo (PNG/JPG/WebP opcional)", type=["png","jpg","jpeg","webp"])

    col1,col2 = st.columns(2)
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
        cons = st.text_area("Conservación","Conservar a temperatura ambiente (<25°C)", height=80)
        adv  = st.text_area("Advertencias","Venta bajo fórmula médica.", height=80)
    normativa = st.text_input("Normativa", "Res 1478/2006 - Circ 01/2016 FNE")

    if st.button("🔲 Generar QR individual", type="primary"):
        row = {"Codigo del medicamento":codigo,"nombre_generico":nombre,"concentracion":conc,
               "forma_farmaceutica":forma,"presentacion":present,"registro_sanitario":reg,
               "lote":lote,"fecha_vencimiento":ven,"fabricante":fabricante,"id_hospital":entidad,
               "conservacion":cons,"advertencias":adv,"normativa":normativa}
        payload = build_payload(row, modo)
        ecc_level = "H" if logo_file else "Q"
        logo_img = Image.open(logo_file).convert("RGBA") if logo_file else None
        img, info = make_qr_physical(payload, inches, dpi, ecc_level, control_color(None), border, logo_img, logo_scale/100.0)
        st.image(img, caption=f"{int(info['actual_px'])}x{int(info['actual_px'])} px @ {dpi} dpi • ECC {ecc_level}", use_container_width=True)
        url_publica = public_qr_url(payload, size=info["actual_px"], ecc=ecc_level)
        st.text_input("URL pública del QR", value=url_publica)
        bio = io.BytesIO(); img.save(bio, "PNG", dpi=(dpi,dpi))  # <-- DPI embebido
        st.download_button("⬇️ Descargar PNG (DPI embebido)", data=bio.getvalue(), file_name=f"qr_{nombre}_{lote}.png", mime="image/png")

# ---------------- Plantillas ----------------
st.divider(); st.subheader("📄 Plantillas de ejemplo")
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
    ctpl = st.columns(2)
    csv_buf = io.StringIO(newline=""); tpl_df.to_csv(csv_buf, index=False)
    ctpl[0].download_button("⬇️ Plantilla CSV", data=csv_buf.getvalue().encode("utf-8"), file_name="plantilla_medicamentos_qr_nuevo.csv", mime="text/csv")
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="xlsxwriter") as writer: tpl_df.to_excel(writer, index=False, sheet_name="plantilla")
    ctpl[1].download_button("⬇️ Plantilla XLSX", data=xlsx_buf.getvalue(), file_name="plantilla_medicamentos_qr_nuevo.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------- Lote ----------------
st.divider(); st.subheader("📦 Generación masiva (CSV o XLSX)")
uploaded = st.file_uploader("Sube la plantilla", type=["csv","xlsx","xls"])
modo_batch = st.radio("Contenido del QR (lote)", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

st.markdown("### Parámetros de impresión del lote")
cp = st.columns(3)
with cp[0]: inches_batch = st.number_input("Tamaño físico (pulgadas) (lote)", 1.0, 3.0, 1.5, 0.1)
with cp[1]: dpi_batch = st.selectbox("DPI (lote)", [203,300,600], index=1)
with cp[2]: border_batch = st.slider("Borde (quiet zone) (lote)", 2, 10, 4, 1)

logo_img_batch = None
if 'logo_file' in locals() and logo_file is not None:
    try: logo_img_batch = Image.open(logo_file).convert("RGBA")
    except Exception: logo_img_batch = None

def read_table(uploaded_file):
    if uploaded_file.name.lower().endswith((".xlsx",".xls")):
        if pd is None:
            st.error("❌ Falta pandas para leer Excel. Instala: `pip install pandas openpyxl`"); st.stop()
        try: df = pd.read_excel(uploaded_file, dtype=str).fillna("")
        except Exception as e: st.error(f"❌ No se pudo leer el Excel: {e}"); st.stop()
        return df.to_dict(orient="records"), None, [str(c).strip() for c in df.columns]
    raw = uploaded_file.getvalue()
    try: text = raw.decode("utf-8-sig")
    except Exception: text = raw.decode("latin-1")
    first = text.splitlines()[0] if text else ""
    delim = ";" if first.count(";") >= first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    return list(reader), delim, [f.strip() for f in (reader.fieldnames or [])]

if uploaded is not None:
    records, delim_in, input_headers = read_table(uploaded); st.success(f"✅ {len(records)} filas"); st.dataframe(records[:10])
    out_headers = list(input_headers); 
    if "timestamp" not in out_headers: out_headers.insert(0, "timestamp")
    for extra in ["url_qr","raw"]:
        if extra in out_headers: out_headers.remove(extra)
        out_headers.append(extra)
    delim_out = st.selectbox("Delimitador CSV salida", ["Auto (=entrada)","Coma (,)","Punto y coma (;)"], index=0)
    delim_used = (delim_in if delim_out=="Auto (=entrada)" and delim_in in (",",";") else ("," if delim_out=="Coma (,)" else ";"))

    if st.button("🔲 Generar ZIP de PNGs + CSV/XLSX con URLs", type="primary"):
        import zipfile
        zip_buf = io.BytesIO(); out_rows=[]
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i,r in enumerate(records):
                base_row = {k:(r.get(k,"") or "") for k in HEAD_IN}
                payload = build_payload(base_row, modo_batch)
                ecc_batch = "H" if logo_img_batch else "Q"
                img, info_qr = make_qr_physical(payload, inches_batch, dpi_batch, ecc_batch, control_color(None), border_batch, logo_img_batch, 0.20)
                # PNG con DPI embebido
                bio = io.BytesIO(); img.save(bio, "PNG", dpi=(dpi_batch,dpi_batch))
                name = f"{i+1:03d}_{base_row.get('nombre_generico','med').strip().replace(' ','_')}_{base_row.get('lote','').strip()}.png"
                z.writestr(name, bio.getvalue())
                # URL pública usando los mismos pixeles
                url_publica = public_qr_url(payload, size=info_qr["actual_px"], ecc=ecc_batch)
                # Fila salida
                out = {k:(r.get(k,"") or "") for k in input_headers}
                out["timestamp"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                out["url_qr"] = url_publica
                out["raw"] = payload
                out_rows.append(out)

        csv_out = io.StringIO(newline=""); w = csv.DictWriter(csv_out, fieldnames=out_headers, delimiter=delim_used)
        w.writeheader(); [w.writerow({k:row.get(k,"") for k in out_headers}) for row in out_rows]

        xlsx_bytes=b""
        if pd is not None:
            import pandas as _pd
            df_out = _pd.DataFrame([{k:r.get(k,"") for k in out_headers} for r in out_rows])
            xlsx_io = io.BytesIO()
            with _pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
                df_out.to_excel(writer, index=False, sheet_name="salida")
            xlsx_bytes = xlsx_io.getvalue()

        st.download_button("⬇️ Descargar ZIP de PNGs", data=zip_buf.getvalue(), file_name="qrs_lote.zip", mime="application/zip")
        st.download_button("⬇️ Descargar CSV con URLs (orden plantilla)", data=csv_out.getvalue().encode("utf-8"), file_name="salida_con_urls.csv", mime="text/csv")
        if xlsx_bytes:
            st.download_button("⬇️ Descargar XLSX con URLs (orden plantilla)", data=xlsx_bytes, file_name="salida_con_urls.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
