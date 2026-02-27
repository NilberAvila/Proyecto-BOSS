
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional, Union
from firebase_admin import firestore

db = firestore.client()

import json
import os
from typing import Dict, Any, Tuple

# ============================================================
# Almacenamiento local (sin Firebase)
# - Obras:    data/obras/obras.json (índice) + data/obras/<codigo>.json (detalle)
# - Insumos:  data/insumos.json
# - Fotos:    data/fotos/
# ============================================================

# Raíz del proyecto (robusto ante ejecución desde otro directorio)
'''
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OBRAS_DIR = DATA_DIR / "obras"
OBRAS_INDEX_PATH = OBRAS_DIR / "obras.json"
INSUMOS_PATH = DATA_DIR / "insumos.json"
FOTOS_DIR = DATA_DIR / "fotos"
TMP_IMG_DIR = DATA_DIR / "tmp_imgs"
'''

'''
def _read_json(path: Union[os.PathLike, str], default: Any) -> Any:
    """Lee JSON. Si el archivo está corrupto, lo respalda para evitar pérdida silenciosa."""
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        # Respaldo del archivo corrupto para diagnóstico
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = path.with_suffix(path.suffix + f".corrupt.{ts}")
        try:
            shutil.copy2(path, backup)
        except Exception:
            pass
        return default
    except Exception:
        return default


def _write_json(path: Union[os.PathLike, str], data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def _obra_path(codigo_obra: str) -> Path:
    return OBRAS_DIR / f"{codigo_obra}.json"
'''

def _ensure_estructura_obra(data: Dict[str, Any]) -> Dict[str, Any]:
    # Mantener compatibilidad con versiones previas
    data = data or {}
    data.setdefault("avance", [])
    data.setdefault("presupuesto_total", 0.0)
    # Nuevo: cronograma valorizado
    data.setdefault("cronograma", [])
    # Nuevo: hitos de pago
    data.setdefault("hitos_pago", [])
    return data


def _new_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


# ==================== DIRECTORIOS ====================

'''
def inicializar_directorios() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OBRAS_DIR, exist_ok=True)
    os.makedirs(FOTOS_DIR, exist_ok=True)

    if not os.path.exists(OBRAS_INDEX_PATH):
        _write_json(OBRAS_INDEX_PATH, {})
    if not os.path.exists(INSUMOS_PATH):
        _write_json(INSUMOS_PATH, [])
'''

# ==================== OBRAS ====================

def cargar_obras() -> Dict[str, str]:
    docs = list(db.collection("obras").stream())

    # Si ya hay obras, devolverlas
    if docs:
        return {d.id: d.id for d in docs}

    # Si NO hay obras, cargarlas desde JSON
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    JSON_DIR = os.path.join(BASE_DIR, "data", "obras")

    obras_json = {
        "Ciudad Pachacútec - Ventanilla": "pachacutec.json",
        "La Rinconada - La Molina": "rinconada.json"
    }

    for codigo, archivo in obras_json.items():
        ruta = os.path.join(JSON_DIR, archivo)

        with open(ruta, encoding="utf-8") as f:
            datos_json = json.load(f)

        # Crear obra base
        agregar_obra(codigo, datos_json.get("nombre", codigo))

        # Guardar datos del JSON
        guardar_datos_obra(codigo, datos_json)

    # Volver a consultar Firestore
    docs = db.collection("obras").stream()
    return {d.id: d.id for d in docs}

def agregar_obra(codigo: str, nombre: str) -> Tuple[bool, str]:
    if not codigo or not nombre:
        return False, "Código o nombre vacío."

    ref = db.collection("obras").document(codigo)
    if ref.get().exists:
        return False, "Ya existe una obra con ese código."

    ref.set({
        "nombre": nombre,
        "avance": [],
        "presupuesto_total": 0.0,
        "cronograma": [],
        "hitos_pago": []
    })
    return True, "Obra creada."

def cargar_datos_obra(codigo_obra: str) -> Dict[str, Any]:
    ref = db.collection("obras").document(codigo_obra)
    doc = ref.get()
    if not doc.exists:
        ref.set({
            "avance": [],
            "presupuesto_total": 0.0,
            "cronograma": [],
            "hitos_pago": []
        })
        return ref.get().to_dict()
    return doc.to_dict()

def guardar_datos_obra(codigo_obra: str, datos: Dict[str, Any]) -> None:
    db.collection("obras").document(codigo_obra).set(datos, merge=True)


# ==================== AVANCES ====================

def agregar_avance(codigo_obra: str, avance_dict: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        ref = db.collection("obras").document(codigo_obra)
        ref.update({
            "avance": firestore.ArrayUnion([avance_dict])
        })
        return True, "Avance guardado."
    except Exception as e:
        return False, str(e)


def obtener_avances_obra(codigo_obra: str) -> List[Dict[str, Any]]:
    datos = cargar_datos_obra(codigo_obra)
    avances = datos.get("avance", [])
    return avances if isinstance(avances, list) else []


def limpiar_avances_obra(codigo_obra: str) -> Tuple[bool, str]:
    """
    Elimina todos los partes diarios (avances) de una obra.
    Mantiene intacta la obra, presupuesto, cronograma y hitos de pago.
    """
    try:
        ref = db.collection("obras").document(codigo_obra)
        ref.update({
            "avance": []
        })
        return True, "Todos los partes diarios han sido eliminados correctamente."
    except Exception as e:
        return False, f"Error al limpiar avances: {str(e)}"


# ==================== PRESUPUESTO ====================

def actualizar_presupuesto_obra(codigo_obra: str, monto: float) -> Tuple[bool, str]:
    try:
        db.collection("obras").document(codigo_obra).update({
            "presupuesto_total": float(monto or 0)
        })
        return True, "Presupuesto actualizado."
    except Exception as e:
        return False, str(e)


def obtener_presupuesto_obra(codigo_obra: str) -> float:
    datos = cargar_datos_obra(codigo_obra)
    try:
        return float(datos.get("presupuesto_total", 0.0) or 0.0)
    except Exception:
        return 0.0


# ==================== INSUMOS ====================

def cargar_insumos() -> List[Dict[str, Any]]:
    docs = db.collection("insumos").stream()
    return [d.to_dict() | {"id": d.id} for d in docs]

def guardar_insumos(insumos: List[Dict[str, Any]]) -> None:
    col = db.collection("insumos")
    batch = db.batch()

    # borramos todos los documentos actuales
    for doc in col.stream():
        batch.delete(doc.reference)

    # volvemos a insertar
    for insumo in insumos:
        ref = col.document()
        batch.set(ref, insumo)

    batch.commit()

def agregar_insumo(nuevo_insumo: Dict[str, Any]) -> None:
    db.collection("insumos").add(nuevo_insumo)

def actualizar_insumo(insumo_id: str, insumo_actualizado: Dict[str, Any]) -> None:
    """
    Actualiza un insumo en Firestore usando su ID de documento.
    """
    db.collection("insumos").document(insumo_id).update(insumo_actualizado)


def eliminar_insumo(insumo_id: str) -> None:
    """
    Elimina un insumo en Firestore usando su ID de documento.
    """
    db.collection("insumos").document(insumo_id).delete()


# ==================== CRONOGRAMA VALORIZADO ====================

def obtener_cronograma_obra(codigo_obra: str) -> List[Dict[str, Any]]:
    datos = cargar_datos_obra(codigo_obra)
    cronograma = datos.get("cronograma", [])
    return cronograma if isinstance(cronograma, list) else []


def agregar_partida_cronograma(codigo_obra: str, partida: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        datos = cargar_datos_obra(codigo_obra)
        datos.setdefault("cronograma", [])
        partida = dict(partida or {})
        partida.setdefault("id", _new_id("crono"))
        datos["cronograma"].append(partida)
        guardar_datos_obra(codigo_obra, datos)
        return True, "Partida agregada."
    except Exception as e:
        return False, str(e)


def actualizar_partida_cronograma(codigo_obra: str, partida_id: str, data_upd: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        datos = cargar_datos_obra(codigo_obra)
        cronograma = datos.get("cronograma", [])
        if not isinstance(cronograma, list):
            cronograma = []
        found = False
        for i, it in enumerate(cronograma):
            if isinstance(it, dict) and it.get("id") == partida_id:
                nuevo = dict(it)
                nuevo.update(data_upd or {})
                cronograma[i] = nuevo
                found = True
                break
        if not found:
            return False, "No se encontró la partida."
        datos["cronograma"] = cronograma
        guardar_datos_obra(codigo_obra, datos)
        return True, "Partida actualizada."
    except Exception as e:
        return False, str(e)


def eliminar_partida_cronograma(codigo_obra: str, partida_id: str) -> Tuple[bool, str]:
    try:
        datos = cargar_datos_obra(codigo_obra)
        cronograma = datos.get("cronograma", [])
        if not isinstance(cronograma, list):
            cronograma = []
        nuevo = [it for it in cronograma if not (isinstance(it, dict) and it.get("id") == partida_id)]
        datos["cronograma"] = nuevo
        guardar_datos_obra(codigo_obra, datos)
        return True, "Partida eliminada."
    except Exception as e:
        return False, str(e)


# ==================== HITOS DE PAGO ====================

def obtener_hitos_pago_obra(codigo_obra: str) -> List[Dict[str, Any]]:
    datos = cargar_datos_obra(codigo_obra)
    hitos = datos.get("hitos_pago", [])
    return hitos if isinstance(hitos, list) else []


def agregar_hito_pago(codigo_obra: str, hito: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        datos = cargar_datos_obra(codigo_obra)
        datos.setdefault("hitos_pago", [])
        hito = dict(hito or {})
        hito.setdefault("id", _new_id("hito"))
        datos["hitos_pago"].append(hito)
        guardar_datos_obra(codigo_obra, datos)
        return True, "Hito agregado."
    except Exception as e:
        return False, str(e)


def actualizar_hito_pago(codigo_obra: str, hito_id: str, data_upd: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        datos = cargar_datos_obra(codigo_obra)
        hitos = datos.get("hitos_pago", [])
        if not isinstance(hitos, list):
            hitos = []
        found = False
        for i, it in enumerate(hitos):
            if isinstance(it, dict) and it.get("id") == hito_id:
                nuevo = dict(it)
                nuevo.update(data_upd or {})
                hitos[i] = nuevo
                found = True
                break
        if not found:
            return False, "No se encontró el hito."
        datos["hitos_pago"] = hitos
        guardar_datos_obra(codigo_obra, datos)
        return True, "Hito actualizado."
    except Exception as e:
        return False, str(e)


def eliminar_hito_pago(codigo_obra: str, hito_id: str) -> Tuple[bool, str]:
    try:
        datos = cargar_datos_obra(codigo_obra)
        hitos = datos.get("hitos_pago", [])
        if not isinstance(hitos, list):
            hitos = []
        nuevo = [it for it in hitos if not (isinstance(it, dict) and it.get("id") == hito_id)]
        datos["hitos_pago"] = nuevo
        guardar_datos_obra(codigo_obra, datos)
        return True, "Hito eliminado."
    except Exception as e:
        return False, str(e)


# ============================================================
# TRABAJOS ADICIONALES (No Contemplados)
# ============================================================

def obtener_trabajos_adicionales(codigo_obra: str) -> List[Dict[str, Any]]:
    """Obtiene todos los trabajos adicionales de una obra."""
    try:
        trabajos = db.collection("trabajos_adicionales").where("codigo_obra", "==", codigo_obra).stream()
        return [{"id": doc.id, **doc.to_dict()} for doc in trabajos]
    except Exception:
        return []


def agregar_trabajo_adicional(codigo_obra: str, trabajo: Dict[str, Any]) -> Tuple[bool, str]:
    """Agrega un nuevo trabajo adicional/no contemplado."""
    try:
        trabajo = dict(trabajo or {})
        trabajo["codigo_obra"] = codigo_obra
        trabajo.setdefault("fecha_creacion", datetime.now().isoformat())
        trabajo.setdefault("estado", "Por cobrar")  # Por cobrar, Aprobado, Cobrado
        
        doc_ref = db.collection("trabajos_adicionales").add(trabajo)
        return True, "Trabajo adicional agregado correctamente."
    except Exception as e:
        return False, str(e)


def actualizar_trabajo_adicional(trabajo_id: str, data_upd: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza un trabajo adicional existente."""
    try:
        db.collection("trabajos_adicionales").document(trabajo_id).update(data_upd)
        return True, "Trabajo adicional actualizado."
    except Exception as e:
        return False, str(e)


def eliminar_trabajo_adicional(trabajo_id: str) -> Tuple[bool, str]:
    """Elimina un trabajo adicional."""
    try:
        db.collection("trabajos_adicionales").document(trabajo_id).delete()
        return True, "Trabajo adicional eliminado."
    except Exception as e:
        return False, str(e)

# ==================== DONACIONES ====================

def obtener_donaciones_obra(obra_codigo: str) -> List[Dict[str, Any]]:
    """Obtiene todas las donaciones registradas para una obra."""
    try:
        docs = db.collection("donaciones").where("obra_codigo", "==", obra_codigo).stream()
        donaciones = []
        for doc in docs:
            donacion = doc.to_dict()
            donacion["id"] = doc.id
            donaciones.append(donacion)
        return donaciones
    except Exception:
        return []


def agregar_donacion(obra_codigo: str, donacion: Dict[str, Any]) -> Tuple[bool, str]:
    """Agrega una nueva donación para una obra."""
    try:
        donacion["obra_codigo"] = obra_codigo
        donacion.setdefault("fecha_registro", datetime.now().isoformat())
        db.collection("donaciones").add(donacion)
        return True, "Donación registrada correctamente."
    except Exception as e:
        return False, str(e)


def actualizar_donacion(obra_codigo: str, donacion_id: str, datos: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza los datos de una donación existente."""
    try:
        datos["fecha_actualización"] = datetime.now().isoformat()
        db.collection("donaciones").document(donacion_id).update(datos)
        return True, "Donación actualizada correctamente."
    except Exception as e:
        return False, str(e)


def eliminar_donacion(donacion_id: str) -> Tuple[bool, str]:
    """Elimina una donación."""
    try:
        db.collection("donaciones").document(donacion_id).delete()
        return True, "Donación eliminada correctamente."
    except Exception as e:
        return False, str(e)


def obtener_donantes_obra(obra_codigo: str) -> List[Dict[str, str]]:
    """Obtiene lista de donantes únicos registrados para una obra."""
    try:
        docs = db.collection("donantes").where("obra_codigo", "==", obra_codigo).stream()
        donantes = []
        for doc in docs:
            donante = doc.to_dict()
            donante["id"] = doc.id
            donantes.append(donante)
        return donantes
    except Exception:
        return []


def agregar_donante(obra_codigo: str, donante: Dict[str, Any]) -> Tuple[bool, str]:
    """Agrega o actualiza información de un donante."""
    try:
        donante["obra_codigo"] = obra_codigo
        donante.setdefault("fecha_registro", datetime.now().isoformat())
        
        # Verificar si ya existe
        nombre = donante.get("nombre", "").strip().lower()
        docs = db.collection("donantes").where("obra_codigo", "==", obra_codigo).stream()
        
        for doc in docs:
            if doc.to_dict().get("nombre", "").strip().lower() == nombre:
                # Actualizar existente
                donante.pop("fecha_registro", None)
                donante["fecha_actualización"] = datetime.now().isoformat()
                db.collection("donantes").document(doc.id).update(donante)
                return True, "Donante actualizado correctamente."
        
        # Crear nuevo
        db.collection("donantes").add(donante)
        return True, "Donante registrado correctamente."
    except Exception as e:
        return False, str(e)


def actualizar_donante(donante_id: str, datos: Dict[str, Any]) -> Tuple[bool, str]:
    """Actualiza la información de un donante."""
    try:
        datos["fecha_actualización"] = datetime.now().isoformat()
        db.collection("donantes").document(donante_id).update(datos)
        return True, "Donante actualizado correctamente."
    except Exception as e:
        return False, str(e)


def eliminar_donante(donante_id: str) -> Tuple[bool, str]:
    """Elimina un donante."""
    try:
        db.collection("donantes").document(donante_id).delete()
        return True, "Donante eliminado correctamente."
    except Exception as e:
        return False, str(e)