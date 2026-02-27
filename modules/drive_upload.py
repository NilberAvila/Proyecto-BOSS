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

def crear_carpeta_obra(webapp_url: str, token: str, nombre_obra: str, codigo_obra: str) -> dict:
    """
    Crea una carpeta en Google Drive para la obra.
    
    Args:
        webapp_url: URL del Google Apps Script WebApp
        token: Token de autenticación
        nombre_obra: Nombre descriptivo de la obra
        codigo_obra: Código único de la obra
    
    Returns:
        dict con status, folderId, folderUrl
    """
    payload = {
        "action": "createFolder",
        "token": token,
        "folderName": f"{codigo_obra} - {nombre_obra}",
        "obraCode": codigo_obra
    }
    r = requests.post(webapp_url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def upload_pdf_base64(webapp_url: str, token: str, obra_code: str, filename: str, pdf_bytes: bytes, folder_id: str = None) -> dict:
    """
    Sube un PDF a Google Drive.
    
    Args:
        webapp_url: URL del Google Apps Script WebApp
        token: Token de autenticación
        obra_code: Código de la obra
        filename: Nombre del archivo PDF
        pdf_bytes: Contenido del PDF en bytes
        folder_id: ID de la carpeta de Drive (opcional, usa carpeta por defecto si no se proporciona)
    
    Returns:
        dict con status, fileId, fileUrl
    """
    # Normalizar el código de obra al formato Apps Script
    obra_code_normalized = _normalize_obra_code(obra_code)
    
    payload = {
        "action": "uploadPDF",
        "token": token,
        "obraCode": obra_code_normalized,
        "fileName": filename,
        "pdfBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
    }
    
    # Agregar folder_id si se proporciona
    if folder_id:
        payload["folderId"] = folder_id
    
    r = requests.post(webapp_url, json=payload, timeout=180)
    r.raise_for_status()
    return r.json()

