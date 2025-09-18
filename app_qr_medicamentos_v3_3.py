# -*- coding: utf-8 -*-
"""
Generador de QR Medicamentos — v3.3 (Solo QR) — FIX2
- Corrige SyntaxError en build_table_data_url
- Corrige claves mal citadas en filas (fecha_fabricacion, fecha_vencimiento, fabricante, importador)
"""
import io, json, base64, urllib.parse, zipfile
from typing import Dict, Any, Tuple

import streamlit as st
from PIL import Image
import qrcode
import qrcode.constants

try:
    import pandas as pd
except Exception:
    pd = None

ECC_MAP = {"L (7%)": qrcode.constants.ERROR_CORRECT_L,
           "M (15%)": qrcode.constants.ERROR_CORRECT_M,
           "Q (25%)": qrcode.constants.ERROR_CORRECT_Q,
           "H (30%)": qrcode.constants.ERROR_CORRECT_H}

CAP_BYTES = {"Q (25%)": 1850, "M (15%)": 2200, "L (7%)": 2800}

def make_qr(text: str, box_size: int, border: int, fill_color: str, ecc_label: str):
    ecc = ECC_MAP.get(ecc_label, qrcode.constants.ERROR_CORRECT_Q)
    qr = qrcode.QRCode(version=None, box_size=box_size, border=border, error_correction=ecc)
    qr.add_data(text)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill_color, back_color="white").convert("RGB")

def build_text_payload(d: Dict[str, Any], compact: bool = False) -> str:
    if compact:
        L = [
            f"MEDICAMENTO: {d.get('nombre_generico', '')} {d.get('concentracion', '')}",
            f"FORMA: {d.get('forma_farmaceutica', '')} - {d.get('presentacion', '')}",
            f"REG. SANITARIO: {d.get('registro_sanitario', '')}",
            f"LOTE: {d.get('lote', '')}",
            f"FABRICACION: {d.get('fecha_fabricacion', '')}",
            f"VENCIMIENTO: {d.get('fecha_vencimiento', '')}",
            f"FABRICANTE: {d.get('fabricante', '')}",
        ]
        return "\n".join([s for s in L if s.strip() and not s.endswith(": ")])
    L = []
    add = L.append
    add("=== INFORMACIÓN DEL MEDICAMENTO ===")
    add(f"MEDICAMENTO: {d.get('nombre_generico', '')} {d.get('concentracion', '')}")
    add(f"FORMA FARMACÉUTICA: {d.get('forma_farmaceutica', '')}")
    add(f"PRESENTACIÓN: {d.get('presentacion', '')}")
    add(f"TIPO DE CONTROL: {d.get('control', '')}")
    add(f"REGISTRO SANITARIO: {d.get('registro_sanitario', '')}")
    add("")
    add("=== INFORMACIÓN DEL LOTE ===")
    add(f"LOTE: {d.get('lote', '')}")
    add(f"FECHA FABRICACIÓN: {d.get('fecha_fabricacion', '')}")
    add(f"FECHA VENCIMIENTO: {d.get('fecha_vencimiento', '')}")
    add("")
    add("=== FABRICACIÓN ===")
    add(f"FABRICANTE: {d.get('fabricante', '')}")
    add(f"IMPORTADOR: {d.get('importador', '')}")
    if d.get("id_hospital") or d.get("fecha_reempaque"):
        add("")
        add("=== REEMPAQUE ===")
        if d.get('id_hospital'):
            add(f"ENTIDAD: {d.get('id_hospital', '')}")
        if d.get('fecha_reempaque'):
            add(f"FECHA REEMPAQUE: {d.get('fecha_reempaque', '')}")
    if d.get("conservacion"):
        add("")
        add("=== CONSERVACIÓN ===")
        add(f"{d.get('conservacion')}")
    if d.get("advertencias"):
        add("")
        add("=== ADVERTENCIAS ===")
        add(f"{d.get('advertencias')}")
    add("")
    add("Normativa: Resolución 1478/2006 - Circular 01/2016 FNE")
    return "\n".join([line for line in L if line.strip()])

def build_json_payload(d: Dict[str, Any]) -> str:
    payload = {
        "version": "1.0",
        "tipo": "medicamento_controlado",
        "normativa": ["Resolución 1478/2006", "Circular 01/2016 FNE"],
        "medicamento": {
            "nombre_generico": d.get("nombre_generico", ""),
            "concentracion": d.get("concentracion", ""),
            "forma_farmaceutica": d.get("forma_farmaceutica", ""),
            "presentacion": d.get("presentacion", ""),
            "tipo_control": d.get("control", ""),
            "registro_sanitario": d.get("registro_sanitario", "")
        },
        "lote": {
            "codigo": d.get("lote", ""),
            "fecha_fabricacion": d.get("fecha_fabricacion", ""),
            "fecha_vencimiento": d.get("fecha_vencimiento", "")
        },
        "fabricacion": {
            "fabricante": d.get("fabricante", ""),
            "importador": d.get("importador", "")
        },
        "reempaque": {
            "entidad": d.get("id_hospital", ""),
            "fecha": d.get("fecha_reempaque", "")
        },
        "conservacion": d.get("conservacion", ""),
        "advertencias": d.get("advertencias", ""),
        "fecha_generacion": "2024"
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

def escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_table_data_url(d: Dict[str, Any], accent: str = "#00a859", base64_mode: bool = False) -> str:
    """Construye una mini página HTML (tabla) y la empaqueta como data:URL (URL-encode o base64)."""
    rows = [
        ("🏥 Medicamento", f"{d.get('nombre_generico', '')} {d.get('concentracion', '')}"),
        ("💊 Forma/Presentación", f"{d.get('forma_farmaceutica', '')} - {d.get('presentacion', '')}"),
        ("🔒 Control", d.get("control", "")),
        ("📋 Registro sanitario", d.get("registro_sanitario", "")),
        ("🏷️ Lote", d.get("lote", "")),
        ("📅 Fabricación", d.get("fecha_fabricacion", "")),
        ("⏰ Vencimiento", d.get("fecha_vencimiento", "")),
        ("🏭 Fabricante", d.get("fabricante", "")),
        ("📦 Importador", d.get("importador", "")),
    ]
    if d.get("id_hospital"):
        rows.append(("🏥 Entidad", d.get("id_hospital", "")))
    if d.get("fecha_reempaque"):
        rows.append(("📦 Reempaque", d.get("fecha_reempaque", "")))
    if d.get("conservacion"):
        rows.append(("❄️ Conservación", d.get("conservacion", "")))
    if d.get("advertencias"):
        rows.append(("⚠️ Advertencias", d.get("advertencias", "")))
    rows.append(("📜 Normativa", "Res 1478/2006 - Circ 01/2016 FNE"))
    rows = [(k, v) for k, v in rows if (v is not None and str(v).strip() != "")]

    # Usamos f-string multilinea (sin barras invertidas) para evitar SyntaxError
    html = f"""<!doctype html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Información del Medicamento</title>
<style>
body{{font:14px -apple-system,system-ui,Arial;margin:15px;line-height:1.4;background:#f8f9fa}}
.header{{background:{accent};color:white;padding:12px;border-radius:8px;text-align:center;margin-bottom:15px;font-weight:bold}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
th,td{{padding:10px;border-bottom:1px solid #eee;text-align:left}}
th{{background:#f1f3f4;font-weight:600;width:35%;font-size:13px}}
td{{font-size:14px}}
tr:last-child th,tr:last-child td{{border-bottom:none}}
.med-name{{font-size:16px;font-weight:bold;color:{accent}}}
</style>
</head><body>
<div class="header">MEDICAMENTO DE CONTROL ESPECIAL</div>
<table>
"""
    if rows:
        html += f'<tr><th>{escape_html(rows[0][0])}</th><td class="med-name">{escape_html(rows[0][1])}</td></tr>'
        for k, v in rows[1:]:
            html += f'<tr><th>{escape_html(k)}</th><td>{escape_html(v)}</td></tr>'
    html += "</table></body></html>"

    if base64_mode:
        b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
        return f"data:text/html;base64,{b64}"
    return "data:text/html," + urllib.parse.quote(html, safe="/:;,+-_.!~*'()#?=&")

def pick_payload(d: Dict[str, Any], mode: str, accent_hex: str) -> Tuple[str, str]:
    if mode == "Mini página (tabla)":
        payload = build_table_data_url(d, accent=accent_hex, base64_mode=False)
        if len(payload.encode("utf-8")) <= 1800:
            return payload, "Mini página (tabla)"
        payload = build_table_data_url(d, accent=accent_hex, base64_mode=True)
        if len(payload.encode("utf-8")) <= 2200:
            return payload, "Mini página (base64)"
        return build_text_payload(d, compact=False), "Texto legible (fallback)"
    elif mode == "Texto legible":
        payload = build_text_payload(d, compact=False)
        if len(payload.encode("utf-8")) <= 2500:
            return payload, "Texto legible"
        return build_text_payload(d, compact=True), "Texto compacto"
    elif mode == "JSON estructurado":
        payload = build_json_payload(d)
        if len(payload.encode("utf-8")) <= 2200:
            return payload, "JSON"
        return build_text_payload(d, compact=False), "Texto legible (fallback)"
    else:
        url = d.get("url_qr", "").strip()
        if url:
            return url, "URL personalizada"
        return build_text_payload(d, compact=False), "Texto legible (sin URL)"

def safe_make_qr(payload: str, fill_color: str, ecc_first: str = "Q (25%)", box_size: int = 10, border: int = 4):
    order = [ecc_first, "M (15%)", "L (7%)"]
    for ecc in order:
        try:
            cap = CAP_BYTES.get(ecc, 1850)
            payload_bytes = payload.encode("utf-8")
            if len(payload_bytes) > cap:
                continue
            img = make_qr(payload, box_size=box_size, border=border, fill_color=fill_color, ecc_label=ecc)
            return img, ecc
        except Exception:
            continue
    try:
        basic_text = f"MEDICAMENTO: {payload[:100]}..." if len(payload) > 100 else payload[:200]
        img = make_qr(basic_text, box_size=box_size, border=border, fill_color=fill_color, ecc_label="L (7%)")
        return img, "L (7%) - Básico"
    except Exception:
        emergency_text = "Error: Información muy extensa para QR"
        img = make_qr(emergency_text, box_size=box_size, border=border, fill_color=fill_color, ecc_label="L (7%)")
        return img, "L (7%) - Error"

def image_bytes(img: Image.Image, fmt="PNG") -> bytes:
    bio = io.BytesIO()
    img.save(bio, fmt)
    bio.seek(0)
    return bio.read()

def render_qr_only(data: Dict[str, Any], qr_mode: str, qr_color: str, ecc_choice: str,
                   qr_size: int = 512, border: int = 4):
    control = (data.get("control") or "Psicotrópico").lower()
    if qr_color == "Negro":
        fill_color = "black"
    elif qr_color == "Verde (Psicotrópico)":
        fill_color = "#00a859"
    elif qr_color == "Amarillo (Estupefaciente)":
        fill_color = "#ffcc00"
    else:
        fill_color = "#ffcc00" if "estupe" in control else "#00a859"
    accent_hex = "#ffcc00" if "estupe" in control else "#00a859"
    box_size = max(1, qr_size // 50)
    payload, used_mode = pick_payload(data, qr_mode, accent_hex)
    qr_img, used_ecc = safe_make_qr(payload, fill_color=fill_color, ecc_first=ecc_choice,
                                    box_size=box_size, border=border)
    try:
        resampling = Image.Resampling.NEAREST
    except Exception:
        resampling = 0
    qr_img = qr_img.resize((qr_size, qr_size), resampling)
    return qr_img, used_mode, used_ecc

# ---------------- UI ----------------
st.set_page_config(page_title="Generador QR Medicamentos v3.3", page_icon="🔲", layout="centered")
st.title("🔲 Generador de QR para Medicamentos — v3.3")
st.markdown("*Genera códigos QR con información completa del medicamento para lectura con cámara o pistola*")

with st.sidebar:
    st.header("⚙️ Configuración del QR")
    st.markdown("#### Contenido del QR")
    qr_mode = st.radio(
        "Tipo de información",
        ["Mini página (tabla)", "Texto legible", "JSON estructurado", "URL personalizada"],
        index=0,
        help="Mini página: HTML con tabla visual\nTexto: Información legible\nJSON: Datos estructurados\nURL: Enlace personalizado"
    )
    if qr_mode == "URL personalizada":
        url_qr = st.text_input("URL completa", placeholder="https://ejemplo.com/medicamento/123")
    else:
        url_qr = ""
    st.markdown("#### Apariencia del QR")
    qr_color = st.radio("Color del QR", ["Automático según control", "Negro", "Verde (Psicotrópico)", "Amarillo (Estupefaciente)"], index=0)
    qr_size = st.slider("Tamaño del QR (píxeles)", 256, 1024, 512, 64)
    border = st.slider("Borde (módulos)", 1, 10, 4, 1)
    st.markdown("#### Corrección de errores")
    ecc_choice = st.selectbox("Nivel ECC", ["Q (25%)", "M (15%)", "L (7%)", "H (30%)"], index=0,
                              help="Mayor ECC = más resistente a daños, pero QR más denso")
    st.markdown("---")
    cols = ["nombre_generico","concentracion","forma_farmaceutica","presentacion","lote","fecha_fabricacion","fecha_vencimiento","registro_sanitario","fabricante","importador","id_hospital","fecha_reempaque","conservacion","advertencias","control","url_qr"]
    csv_template = ",".join(cols) + "\n" + "CLONAZEPAM,2 mg,Tableta,Blíster x10,ABC123,04/2024,12/2025,INVIMA 2019M-000000-R1,Laboratorio XYZ S.A.,Import Pharma SAS,Hospital ABC,04/2024,Conservar <25°C,Venta bajo fórmula médica,Psicotrópico,\n"
    st.download_button("📄 Descargar plantilla CSV", data=csv_template.encode("utf-8"), file_name="plantilla_medicamentos_qr.csv", mime="text/csv")

with st.form("medicamento_form"):
    st.subheader("📋 Información del Medicamento")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Información básica**")
        nombre = st.text_input("Nombre genérico*", "CLONAZEPAM")
        concentracion = st.text_input("Concentración*", "2 mg")
        forma = st.text_input("Forma farmacéutica*", "Tableta")
        presentacion = st.text_input("Presentación*", "Blíster x10")
        st.markdown("**Lote y fechas**")
        lote = st.text_input("Lote*", "ABC123")
        fecha_fab = st.text_input("Fecha fabricación (MM/AAAA)*", "04/2024")
        fecha_ven = st.text_input("Fecha vencimiento (MM/AAAA)*", "12/2025")
    with col2:
        st.markdown("**Regulatorio**")
        regsan = st.text_input("Registro sanitario*", "INVIMA 2019M-000000-R1")
        control = st.selectbox("Tipo de control*", ["Psicotrópico", "Estupefaciente"], index=0)
        st.markdown("**Fabricación**")
        fabricante = st.text_input("Fabricante*", "Laboratorio XYZ S.A.")
        importador = st.text_input("Importador", "Import Pharma SAS")
        st.markdown("**Reempaque (opcional)**")
        entidad = st.text_input("Entidad/Hospital", "Hospital ABC")
        fecha_reempaque = st.text_input("Fecha reempaque (MM/AAAA)", "04/2024")
    st.markdown("**Información adicional**")
    col3, col4 = st.columns(2)
    with col3:
        conservacion = st.text_area("Conservación", "Conservar a temperatura ambiente (<25°C), protegido de la luz y humedad.", height=80)
    with col4:
        advertencias = st.text_area("Advertencias", "Venta bajo fórmula médica. Manténgase fuera del alcance de los niños. Puede causar dependencia.", height=80)
    generate_btn = st.form_submit_button("🔲 Generar Código QR", type="primary")

def image_bytes(img, fmt="PNG"):  # helper
    bio = io.BytesIO(); img.save(bio, fmt); bio.seek(0); return bio.read()

if generate_btn:
    required_fields = {'Nombre genérico': nombre,'Concentración': concentracion,'Forma farmacéutica': forma,'Presentación': presentacion,'Lote': lote,'Fecha fabricación': fecha_fab,'Fecha vencimiento': fecha_ven,'Registro sanitario': regsan,'Fabricante': fabricante}
    missing_fields = [field for field, value in required_fields.items() if not value.strip()]
    if missing_fields:
        st.error(f"❌ Faltan campos obligatorios: {', '.join(missing_fields)}")
    else:
        data = {'nombre_generico': nombre,'concentracion': concentracion,'forma_farmaceutica': forma,'presentacion': presentacion,'lote': lote,'fecha_fabricacion': fecha_fab,'fecha_vencimiento': fecha_ven,'registro_sanitario': regsan,'fabricante': fabricante,'importador': importador,'id_hospital': entidad,'fecha_reempaque': fecha_reempaque,'conservacion': conservacion,'advertencias': advertencias,'control': control,'url_qr': url_qr}
        try:
            with st.spinner("Generando código QR..."):
                qr_img, used_mode, used_ecc = render_qr_only(data, qr_mode, qr_color, ecc_choice, qr_size, border)
            st.success("✅ Código QR generado exitosamente")
            col1, col2 = st.columns([2, 1])
            with col1:
                st.image(qr_img, caption=f"QR: {used_mode} | ECC: {used_ecc}", use_column_width=True)
            with col2:
                st.info(f"**Detalles del QR:**\n- Tamaño: {qr_size}×{qr_size}px\n- Modo: {used_mode}\n- ECC: {used_ecc}\n- Borde: {border} módulos")
            filename = f"qr_{nombre.lower().replace(' ', '_')}_{lote}.png"
            st.download_button("⬇️ Descargar QR PNG", data=image_bytes(qr_img), file_name=filename, mime="image/png")
            with st.expander("🔍 Vista previa del contenido del QR"):
                payload, _ = pick_payload(data, qr_mode, "#00a859")
                if qr_mode == "Mini página (tabla)" and payload.startswith("data:text/html"):
                    st.code("Contenido HTML (no se muestra por extensión)")
                elif qr_mode == "JSON estructurado":
                    try:
                        json_obj = json.loads(payload); st.json(json_obj)
                    except Exception:
                        st.text(payload)
                else:
                    st.text(payload)
        except Exception as e:
            st.error(f"❌ Error generando QR: {str(e)}")
            st.info("💡 Intenta reducir la información o cambiar el nivel de corrección de errores")

st.markdown("---")
st.subheader("📦 Procesamiento por Lotes")
uploaded_file = st.file_uploader("Subir archivo CSV con múltiples medicamentos", type=["csv"], help="Usa la plantilla CSV de arriba para el formato correcto")
if uploaded_file is not None:
    if pd is None:
        st.error("❌ Se requiere pandas para procesamiento por lotes: `pip install pandas`")
    else:
        try:
            df = pd.read_csv(uploaded_file, dtype=str).fillna("")
            st.info(f"📊 Se encontraron {len(df)} medicamentos en el archivo")
            with st.expander("👁️ Vista previa de datos"):
                st.dataframe(df.head())
            if st.button("🔲 Generar QRs por lotes", type="primary"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    progress_bar = st.progress(0); status_text = st.empty()
                    success_count = 0; error_count = 0
                    for idx, row in df.iterrows():
                        try:
                            status_text.text(f"Procesando {idx + 1}/{len(df)}: {row.get('nombre_generico', 'Sin nombre')}")
                            row_data = row.to_dict(); row_data.setdefault('control', 'Psicotrópico'); row_data.setdefault('url_qr', "")
                            qr_img, used_mode, used_ecc = render_qr_only(row_data, qr_mode, qr_color, ecc_choice, qr_size, border)
                            img_buffer = io.BytesIO(); qr_img.save(img_buffer, 'PNG')
                            filename = f"qr_{idx + 1:03d}_{row.get('nombre_generico', 'med').lower().replace(' ', '_')}.png"
                            zip_file.writestr(filename, img_buffer.getvalue()); success_count += 1
                        except Exception as e:
                            st.warning(f"⚠️ Error en fila {idx + 1}: {str(e)}"); error_count += 1
                        progress_bar.progress((idx + 1) / len(df))
                    status_text.text("✅ Procesamiento completado")
                if success_count > 0:
                    st.success(f"✅ Generados {success_count} QRs exitosamente")
                    if error_count > 0: st.warning(f"⚠️ {error_count} errores durante el procesamiento")
                    st.download_button("⬇️ Descargar ZIP con todos los QRs", data=zip_buffer.getvalue(), file_name=f"qrs_medicamentos_{success_count}_items.zip", mime="application/zip")
                else:
                    st.error("❌ No se pudo generar ningún QR")
        except Exception as e:
            st.error(f"❌ Error procesando archivo CSV: {str(e)}")

st.markdown("---")
with st.expander("ℹ️ Información sobre los modos de QR"):
    st.markdown("""
### Modos de contenido del QR

**🌐 Mini página (tabla):**  
Genera una página HTML con tabla visual. Ideal para lectura en smartphones. Se ve profesional y organizado.

**📝 Texto legible:**  
Información en texto plano. Compatible con cualquier lector QR. Fácil de copiar y pegar.

**🔧 JSON estructurado:**  
Datos en formato JSON. Ideal para sistemas automatizados y para integraciones con software hospitalario.

**🔗 URL personalizada:**  
Redirige a una página web. Recomendado cuando la cantidad de información es muy grande (evita QRs densos).
""")
