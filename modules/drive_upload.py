import base64
import requests

# Mapeo de códigos de obra locales a códigos Apps Script
OBRA_CODE_MAP = {
    # La Molina / Rinconada -> OBR-001
    "rinconada": "OBR-001",
    "la_molina": "OBR-001",
    "molina": "OBR-001",
    
    # Ventanilla / Pachacutec -> OBR-002
    "pachacutec": "OBR-002",
    "ventanilla": "OBR-002",
    
    # Test obra -> OBR-002 (por defecto)
    "test01": "OBR-002",
}

def _normalize_obra_code(obra_code: str) -> str:
    """Convierte código de obra local al formato esperado por Apps Script."""
    obra_lower = str(obra_code or "").strip().lower()
    
    # Si ya está en formato OBR-XXX, devolverlo tal cual
    if obra_lower.startswith("obr-"):
        return obra_code.upper()
    
    # Buscar en el mapeo
    mapped = OBRA_CODE_MAP.get(obra_lower)
    if mapped:
        return mapped
    
    # Fallback: intentar buscar coincidencias parciales
    for key, value in OBRA_CODE_MAP.items():
        if key in obra_lower or obra_lower in key:
            return value
    
    # Por defecto, usar OBR-002 si no se encuentra
    return "OBR-002"

def upload_pdf_base64(webapp_url: str, token: str, obra_code: str, filename: str, pdf_bytes: bytes) -> dict:
    # Normalizar el código de obra al formato Apps Script
    obra_code_normalized = _normalize_obra_code(obra_code)
    
    payload = {
        "token": token,
        "obraCode": obra_code_normalized,
        "fileName": filename,
        "pdfBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
    }
    r = requests.post(webapp_url, json=payload, timeout=180)
    r.raise_for_status()
    return r.json()
