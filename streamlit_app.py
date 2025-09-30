# Create a repo zip with the updated Streamlit app (physical size QR, CSV/XLSX handling)
import os, io, zipfile, textwrap, datetime, csv

base_dir = "/mnt/data/app_qr_control_especial_1p5in"
os.makedirs(base_dir, exist_ok=True)
os.makedirs(os.path.join(base_dir, "templates"), exist_ok=True)

# ---------------- streamlit_app.py ----------------
streamlit_app_py = r'''# -*- coding: utf-8 -*-
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
st.title("🔲 Generador de QR (Medicamentos) — 1.5\" físico listo para impresión")

# ========== Constantes (campos base para construir el payload) ==========
HEAD_IN = [
    "Codigo del medicamento","nombre_generico","concentracion","forma_farmaceutica","presentacion",
    "registro_sanitario","lote","fecha_vencimiento","fabricante","id_hospital","conservacion",
    "advertencias","normativa"
]
# Nota: el orden final del archivo de salida ahora se toma de la plantilla del usuario.

# ========== Utilidades de QR ==========
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

def make_qr_physical(
    data: str,
    inches: float = 1.5,          # 1.5 pulgadas de lado
    dpi: int = 300,               # 203 / 300 / 600, etc.
    ecc: str = "Q",
    color: str = "black",
    border: int = 4,
    logo_img: Image.Image | None = None,
    logo_scale: float = 0.20      # 20% del lado del QR como máx.
):
    """
    Genera un QR con tamaño físico controlado (inches × dpi).
    No reescala módulos: calcula box_size entero y rellena con margen blanco
    si hace falta para alcanzar el tamaño exacto en píxeles.
    Devuelve (img, info_dict)
    """
    import qrcode.constants as C
    ecc_map = {"L": C.ERROR_CORRECT_L, "M": C.ERROR_CORRECT_M,
               "Q": C.ERROR_CORRECT_Q, "H": C.ERROR_CORRECT_H}

    target_px = int(round(inches * dpi))  # píxeles objetivo
    # 1ª pasada: descubrir cuántos módulos requiere el payload
    qr_tmp = qrcode.QRCode(version=None, box_size=1, border=border,
                           error_correction=ecc_map.get(ecc, C.ERROR_CORRECT_Q))
    qr_tmp.add_data(data)
    qr_tmp.make(fit=True)
    modules = qr_tmp.modules_count            # módulos del símbolo (sin quiet zone)
    total_modules = modules + 2 * border     # con quiet zone

    # box_size entero que quepa en target_px
    box_size = max(1, target_px // total_modules)
    actual_px = total_modules * box_size

    # 2ª pasada: generar con box_size definitivo
    qr = qrcode.QRCode(version=None, box_size=box_size, border=border,
                       error_correction=ecc_map.get(ecc, C.ERROR_CORRECT_Q))
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=color, back_color="white").convert("RGB")

    # Si quedó un poco más pequeño que target_px, rellenamos con blanco (sin reescalar módulos)
    if actual_px < target_px:
        pad = (target_px - actual_px) // 2
        canvas = Image.new("RGB", (target_px, target_px), "white")
        canvas.paste(img, (pad, pad))
        img = canvas
        actual_px = target_px  # ahora ya coincide

    # Logo centrado (si hay)
    if logo_img is not None:
        img = center_logo(img, logo_img, scale=logo_scale)

    # Métrica para diagnóstico
    mm_per_pixel = 25.4 / dpi
    module_size_mm = box_size * mm_per_pixel

    info = {
        "dpi": dpi,
        "inches": inches,
        "target_px": target_px,
        "actual_px": actual_px,
        "modules": modules,
        "border_modules": border,
        "box_size_px": box_size,
        "module_size_mm": round(module_size_mm, 3),
        "ecc": ecc,
    }
    return img, info

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

    col_size = st.columns(3)
    with col_size[0]:
        inches = st.number_input("Tamaño físico (pulgadas)", min_value=1.0, max_value=3.0, value=1.5, step=0.1)
    with col_size[1]:
        dpi = st.selectbox("DPI de impresión", [203, 300, 600], index=1)
    with col_size[2]:
        border = st.slider("Borde (quiet zone) [módulos]", 2, 10, 4, 1)

    col_logo = st.columns(2)
    with col_logo[0]:
        logo_scale = st.slider("Logo centrado (% del lado)", 8, 30, 20, 1)
    with col_logo[1]:
        logo_file = st.file_uploader("Logo (PNG/JPG/WebP)", type=["png","jpg","jpeg","webp"])

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
        logo_img = Image.open(logo_file).convert("RGBA") if logo_file else None

        img, info = make_qr_physical(
            data=payload,
            inches=inches,
            dpi=dpi,
            ecc=ecc_level,
            color=control_color(None),
            border=border,
            logo_img=logo_img,
            logo_scale=logo_scale/100.0
        )

        st.image(img, caption=f"QR {inches}\" @ {dpi}dpi • ECC {ecc_level}", use_container_width=True)

        # Diagnóstico de legibilidad
        if info["module_size_mm"] < 0.33:
            st.warning(f"El tamaño de módulo es {info['module_size_mm']} mm (< 0.33 mm). "
                       "Para mejor lectura: reduce contenido, sube DPI o usa tamaño físico mayor.")
        else:
            st.info(f"Módulo ≈ {info['module_size_mm']} mm, módulos {info['modules']} + borde {border}")

        # URL pública al PNG del QR (mismo tamaño en px)
        url_publica = public_qr_url(payload, size=info["actual_px"], ecc=ecc_level)
        st.text_input("URL pública del QR", value=url_publica, help="Cópiala y ábrela en cualquier lugar.")

        # Descargar PNG
        bio = io.BytesIO(); img.save(bio, "PNG")
        st.download_button("⬇️ Descargar PNG", data=bio.getvalue(),
                           file_name=f"qr_{nombre}_{lote}.png", mime="image/png")

# ========== Plantilla de ejemplo (opcional) ==========
st.divider(); st.subheader("📄 Plantillas de ejemplo (nuevo cabezote)")
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
    col_tpl[0].download_button("⬇️ Plantilla CSV", data=csv_buf.getvalue().encode("utf-8"),
                               file_name="plantilla_medicamentos_qr_nuevo.csv", mime="text/csv")
    # XLSX
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="xlsxwriter") as writer:
        tpl_df.to_excel(writer, index=False, sheet_name="plantilla")
    col_tpl[1].download_button("⬇️ Plantilla XLSX", data=xlsx_buf.getvalue(),
                               file_name="plantilla_medicamentos_qr_nuevo.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ========== Lote (CSV/XLSX) — salida horizontal con el mismo orden de tu plantilla ==========
st.divider(); st.subheader("📦 Generación masiva (CSV o XLSX)")

uploaded = st.file_uploader("Sube la plantilla CSV/XLSX (usamos exactamente tu orden de columnas)", type=["csv","xlsx","xls"])
modo_batch = st.radio("Contenido del QR (lote)", ["Texto legible", "JSON estructurado"], index=0, horizontal=True)

# Parámetros físicos para el lote
st.markdown("### Parámetros de impresión del lote")
colp = st.columns(3)
with colp[0]:
    inches_batch = st.number_input("Tamaño físico (pulgadas) (lote)", min_value=1.0, max_value=3.0, value=1.5, step=0.1)
with colp[1]:
    dpi_batch = st.selectbox("DPI (lote)", [203, 300, 600], index=1)
with colp[2]:
    border_batch = st.slider("Borde (quiet zone) (lote)", 2, 10, 4, 1)

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
    out_headers = list(input_headers)
    if "timestamp" not in out_headers:
        out_headers.insert(0, "timestamp")
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

                img, info_qr = make_qr_physical(
                    data=payload,
                    inches=inches_batch,
                    dpi=dpi_batch,
                    ecc=ecc_for_batch,
                    color=control_color(None),
                    border=border_batch,
                    logo_img=logo_img_batch,
                    logo_scale=0.20
                )

                # PNG
                png = io.BytesIO(); img.save(png, "PNG")
                base_name = f"{i+1:03d}_{base_row.get('nombre_generico','med').strip().replace(' ','_')}_{base_row.get('lote','').strip()}"
                z.writestr(base_name + ".png", png.getvalue())

                # URL pública con el mismo tamaño en px
                url_publica = public_qr_url(payload, size=info_qr["actual_px"], ecc=ecc_for_batch)

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
'''

with open(os.path.join(base_dir, "streamlit_app.py"), "w", encoding="utf-8") as f:
    f.write(streamlit_app_py)

# ---------------- requirements.txt ----------------
requirements = """streamlit>=1.38,<2
qrcode==7.4.2
pillow>=10.4.0
pandas>=2.2.2
openpyxl>=3.1.5
xlsxwriter>=3.2.0
"""
with open(os.path.join(base_dir, "requirements.txt"), "w", encoding="utf-8") as f:
    f.write(requirements)

# ---------------- README.md ----------------
readme = f"""# QR Medicamentos — 1.5" listo para impresión

App Streamlit para generar códigos QR de medicamentos cumpliendo campos del cabezote actualizado.
Incluye:
- Tamaño físico controlado (**1.5 pulgadas** por defecto) y selección de **DPI**.
- Logo centrado opcional (ECC=H automáticamente si hay logo).
- Carga **CSV (; o ,)** y **XLSX**, salida en el **mismo orden de columnas**.
- Descarga de PNGs (lote), CSV/XLSX con `url_qr` y `raw`.
- Enlaces públicos a la imagen del QR vía QuickChart.

## Despliegue en Streamlit Cloud
1. Sube esta carpeta como repositorio a GitHub.
2. En Streamlit Cloud, crea una app apuntando a `streamlit_app.py`.
3. Asegúrate de que este `requirements.txt` está en la raíz del repo.

## Ejecución local
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
