"""
Módulo para subir fotos a Cloudinary
Gestiona la subida de imágenes de avances de obra a Cloudinary
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import streamlit as st
from datetime import datetime
from typing import List, Optional, Tuple
from pathlib import Path

# Configuración de Cloudinary desde secrets o variables de entorno
def configurar_cloudinary() -> bool:
    """
    Configura Cloudinary con las credenciales desde st.secrets o variables de entorno
    Retorna True si la configuración es exitosa
    """
    try:
        # Intentar obtener desde st.secrets primero
        cloud_name = None
        api_key = None
        api_secret = None
        
        try:
            cloudinary_config = st.secrets.get("cloudinary", {})
            cloud_name = cloudinary_config.get("cloud_name")
            api_key = cloudinary_config.get("api_key")
            api_secret = cloudinary_config.get("api_secret")
        except Exception:
            pass
        
        # Si no hay en secrets, intentar variables de entorno
        cloud_name = cloud_name or os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = api_key or os.getenv("CLOUDINARY_API_KEY")
        api_secret = api_secret or os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            return False
        
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        return True
    except Exception as e:
        print(f"Error configurando Cloudinary: {e}")
        return False


def subir_foto_cloudinary(
    archivo,
    codigo_obra: str,
    fecha_hoy: str,
    folder: str = "obras_boss"
) -> Tuple[bool, Optional[str], str]:
    """
    Sube una foto a Cloudinary
    
    Args:
        archivo: Archivo subido desde Streamlit (UploadedFile)
        codigo_obra: Código de la obra
        fecha_hoy: Fecha del avance
        folder: Carpeta en Cloudinary donde se almacenarán las fotos
        
    Returns:
        Tuple[bool, Optional[str], str]: (éxito, url_cloudinary, mensaje)
    """
    try:
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:20]
        nombre_archivo = f"{codigo_obra}_{fecha_hoy}_{timestamp}_{archivo.name}"
        
        # Crear ruta completa en Cloudinary: obras_boss/codigo_obra/fecha/nombre_archivo
        public_id = f"{folder}/{codigo_obra}/{fecha_hoy}/{timestamp}"
        
        # Resetear el puntero del archivo
        archivo.seek(0)
        
        # Subir a Cloudinary
        resultado = cloudinary.uploader.upload(
            archivo,
            public_id=public_id,
            folder=folder,
            resource_type="image",
            # Optimizaciones automáticas
            quality="auto:good",
            fetch_format="auto",
            # Tags para organización
            tags=[codigo_obra, fecha_hoy, "obra", "avance"],
            # Metadata adicional
            context=f"obra={codigo_obra}|fecha={fecha_hoy}|nombre={nombre_archivo}"
        )
        
        # Obtener URL segura
        url_cloudinary = resultado.get("secure_url")
        
        if url_cloudinary:
            return True, url_cloudinary, "Foto subida exitosamente a Cloudinary"
        else:
            return False, None, "No se obtuvo URL de Cloudinary"
            
    except Exception as e:
        return False, None, f"Error al subir foto a Cloudinary: {str(e)}"


def subir_fotos_cloudinary(
    archivos_fotos,
    codigo_obra: str,
    fecha_hoy: str
) -> List[str]:
    """
    Sube múltiples fotos a Cloudinary
    
    Args:
        archivos_fotos: Lista de archivos subidos desde Streamlit
        codigo_obra: Código de la obra
        fecha_hoy: Fecha del avance (formato YYYY-MM-DD)
        
    Returns:
        List[str]: Lista de URLs de Cloudinary de las fotos subidas exitosamente
    """
    urls_cloudinary = []
    
    # Verificar configuración de Cloudinary
    if not configurar_cloudinary():
        print("⚠️ Cloudinary no está configurado correctamente")
        return urls_cloudinary
    
    for archivo in archivos_fotos:
        # Validar extensión
        if not validar_extension_imagen(getattr(archivo, "name", "")):
            print(f"⚠️ Archivo {archivo.name} no tiene extensión válida")
            continue
        
        # Subir foto
        exito, url, mensaje = subir_foto_cloudinary(archivo, codigo_obra, fecha_hoy)
        
        if exito and url:
            urls_cloudinary.append(url)
            print(f"✅ {archivo.name} subido a Cloudinary")
        else:
            print(f"❌ Error subiendo {archivo.name}: {mensaje}")
    
    return urls_cloudinary


def validar_extension_imagen(nombre_archivo: str, extensiones_permitidas: List[str] = None) -> bool:
    """
    Valida que el archivo tenga una extensión de imagen permitida
    """
    if extensiones_permitidas is None:
        extensiones_permitidas = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
    
    ext = Path(nombre_archivo).suffix.lower()
    return ext in extensiones_permitidas


def eliminar_foto_cloudinary(url_cloudinary: str) -> Tuple[bool, str]:
    """
    Elimina una foto de Cloudinary dado su URL
    
    Args:
        url_cloudinary: URL completa de la imagen en Cloudinary
        
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    try:
        # Configurar Cloudinary
        if not configurar_cloudinary():
            return False, "Cloudinary no está configurado"
        
        # Extraer public_id de la URL
        # URL típica: https://res.cloudinary.com/[cloud_name]/image/upload/v[version]/[public_id].[format]
        parts = url_cloudinary.split("/upload/")
        if len(parts) < 2:
            return False, "URL de Cloudinary inválida"
        
        # Obtener public_id (sin extensión)
        public_id_with_ext = parts[1].split("/", 1)[1] if "/" in parts[1] else parts[1]
        public_id = public_id_with_ext.rsplit(".", 1)[0]
        
        # Eliminar de Cloudinary
        resultado = cloudinary.uploader.destroy(public_id, resource_type="image")
        
        if resultado.get("result") == "ok":
            return True, "Foto eliminada de Cloudinary"
        else:
            return False, f"No se pudo eliminar: {resultado.get('result')}"
            
    except Exception as e:
        return False, f"Error al eliminar foto: {str(e)}"


def obtener_info_configuracion() -> dict:
    """
    Obtiene información sobre la configuración de Cloudinary (sin exponer credenciales)
    """
    try:
        cloudinary_config = st.secrets.get("cloudinary", {})
        cloud_name = cloudinary_config.get("cloud_name") or os.getenv("CLOUDINARY_CLOUD_NAME")
        
        return {
            "configurado": bool(cloud_name),
            "cloud_name": cloud_name if cloud_name else "No configurado",
            "usando_secrets": bool(st.secrets.get("cloudinary")),
            "usando_env": bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
        }
    except Exception:
        return {
            "configurado": False,
            "cloud_name": "Error al obtener configuración",
            "usando_secrets": False,
            "usando_env": bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
        }
