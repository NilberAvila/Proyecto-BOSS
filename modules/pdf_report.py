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
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("BOX", (0,0), (-1,-1), 0.8, colors.black),
        ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return t

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
    story.append(Paragraph("<b>PARTE DIARIO DE OBRA</b>", styles["Title"]))
    story.append(Spacer(1, 6))

    meta = [
        ["Obra", f"{obra_code} – {obra_name}"],
        ["Fecha", fecha],
        ["Emitido por", emitido_por],
        ["Rol", rol],
        ["Generado", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]
    story.append(Table(meta, colWidths=[4*cm, 12*cm]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Resumen</b>", styles["Heading2"]))
    story.append(_table([["Campo", "Valor"]] + resumen_rows, col_widths=[5*cm, 11*cm]))
    story.append(Spacer(1, 10))

    for tb in tablas:
        story.append(Paragraph(f"<b>{tb['titulo']}</b>", styles["Heading2"]))
        story.append(_table([tb["headers"]] + tb["rows"]))
        story.append(Spacer(1, 10))

    # Evidencias
    story.append(PageBreak())
    story.append(Paragraph("<b>Evidencia fotográfica</b>", styles["Title"]))
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
        story.append(Paragraph(f"Foto {i}", styles["BodyText"]))
        if i != len(fotos_opt):
            story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()
