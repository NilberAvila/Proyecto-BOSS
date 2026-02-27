from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

from PIL import Image as PILImage, ImageOps
from pathlib import Path

# Raíz del proyecto (para rutas absolutas)
BASE_DIR = Path(__file__).resolve().parent.parent

styles = getSampleStyleSheet()

def optimize_image_for_pdf(in_path: str, out_dir: str | None = None, max_side=1600, quality=80) -> str:
    # Asegura directorio temporal dentro del proyecto
    if out_dir is None:
        out_dir = str(BASE_DIR / 'data' / 'tmp_imgs')

    in_path = Path(in_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    img = PILImage.open(in_path)
    img = ImageOps.exif_transpose(img)  # respeta rotación del celular
    img = img.convert("RGB")

    w, h = img.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, PILImage.Resampling.LANCZOS)

    out_path = out_dir / f"{in_path.stem}_mx{max_side}_q{quality}.jpg"
    img.save(out_path, "JPEG", quality=quality, optimize=True, progressive=True)
    return str(out_path)

def _table(data, col_widths=None):
    """Crea una tabla con estilo estándar, soportando Paragraphs en celdas."""
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("BOX", (0,0), (-1,-1), 0.8, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return t

def _format_text_for_cell(text: str, max_length: int = 200) -> Any:
    """Convierte texto largo en Paragraph para mejor manejo en tablas."""
    text = str(text or "").strip()
    if not text or text == "Sin observaciones" or text == "Sin descripción":
        return text
    
    # Si el texto es corto, devolverlo tal cual
    if len(text) <= 80:
        return text
    
    # Si es largo, usar Paragraph para que se ajuste automáticamente
    style = getSampleStyleSheet()["BodyText"]
    style.fontSize = 9
    style.leading = 11
    return Paragraph(text, style)

def build_parte_pdf(
    obra_code: str,
    obra_name: str,
    fecha: str,
    emitido_por: str,
    rol: str,
    resumen_rows: List[List[str]],
    tablas: List[Dict[str, Any]],   # cada item: {"titulo": str, "headers": [...], "rows": [[...], ...]}
    foto_paths: List[str],
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.6*cm, rightMargin=1.6*cm, topMargin=1.4*cm, bottomMargin=1.4*cm)

    story = []
    
    # Título principal
    story.append(Paragraph("<b>PARTE DIARIO DE OBRA</b>", styles["Title"]))
    story.append(Spacer(1, 6))

    # Metadatos de la obra
    meta = [
        ["Obra", f"{obra_code} – {obra_name}"],
        ["Fecha", fecha],
        ["Emitido por", emitido_por],
        ["Rol", rol.upper()],
        ["Generado", datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
    ]
    story.append(Table(meta, colWidths=[4*cm, 12*cm]))
    story.append(Spacer(1, 12))

    # Resumen con soporte para textos largos
    story.append(Paragraph("<b>Resumen del Avance</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))
    
    # Procesar resumen_rows para manejar textos largos
    resumen_formatted = [["Campo", "Valor"]]
    for row in resumen_rows:
        if len(row) == 2:
            campo, valor = row
            # Si el valor es largo (descripción, observaciones), usar Paragraph
            if campo in ["Descripción del avance", "Observaciones"]:
                valor_formatted = _format_text_for_cell(valor)
            else:
                valor_formatted = str(valor)
            resumen_formatted.append([campo, valor_formatted])
    
    story.append(_table(resumen_formatted, col_widths=[5*cm, 11*cm]))
    story.append(Spacer(1, 12))

    # Tablas de costos
    for tb in tablas:
        story.append(Paragraph(f"<b>{tb['titulo']}</b>", styles["Heading2"]))
        story.append(Spacer(1, 4))
        story.append(_table([tb["headers"]] + tb["rows"]))
        story.append(Spacer(1, 10))

    # Evidencias fotográficas
    if foto_paths:
        story.append(PageBreak())
        story.append(Paragraph("<b>Evidencia Fotográfica</b>", styles["Title"]))
        story.append(Spacer(1, 10))

        fotos_opt = [optimize_image_for_pdf(p) for p in foto_paths]
        for i, p in enumerate(fotos_opt, start=1):
            img = Image(p)
            # Ajuste grande en página
            max_w = A4[0] - 3.2*cm
            max_h = A4[1] - 6.0*cm
            scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
            img.drawWidth = img.imageWidth * scale
            img.drawHeight = img.imageHeight * scale

            story.append(img)
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Foto {i}/{len(fotos_opt)}</b>", styles["BodyText"]))
            if i != len(fotos_opt):
                story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()
