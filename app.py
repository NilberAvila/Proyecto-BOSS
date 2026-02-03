#Conexción a base de datos FIREBASE
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import os
import json

# Inicializar Firebase UNA SOLA VEZ
def inicializar_firebase():
    """
    Inicializa Firebase usando las credenciales desde st.secrets o firebase_key.json
    Compatible con Streamlit Cloud y desarrollo local
    """
    try:
        # Verificar si ya está inicializado
        firebase_admin.get_app()
        return firestore.client()
    except ValueError:
        # No está inicializado, proceder con la configuración
        pass
    
    try:
        # Método 1: Intentar usar st.secrets (para Streamlit Cloud)
        if "firebase" in st.secrets:
            firebase_config = st.secrets["firebase"]
            cred_dict = {
                "type": firebase_config.get("type", "service_account"),
                "project_id": firebase_config["project_id"],
                "private_key_id": firebase_config["private_key_id"],
                "private_key": firebase_config["private_key"],
                "client_email": firebase_config["client_email"],
                "client_id": firebase_config["client_id"],
                "auth_uri": firebase_config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": firebase_config.get("token_uri", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": firebase_config.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": firebase_config["client_x509_cert_url"],
                "universe_domain": firebase_config.get("universe_domain", "googleapis.com")
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return firestore.client()
    except Exception as e:
        print(f"⚠️ No se pudo cargar Firebase desde st.secrets: {e}")
    
    try:
        # Método 2: Usar firebase_key.json local (para desarrollo)
        if os.path.exists("firebase_key.json"):
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
            return firestore.client()
    except Exception as e:
        print(f"⚠️ No se pudo cargar Firebase desde firebase_key.json: {e}")
    
    # Si llegamos aquí, ningún método funcionó
    st.error("""
    ❌ **Error al inicializar Firebase**
    
    Por favor configura las credenciales de Firebase:
    - **Streamlit Cloud**: Ve a Settings > Secrets y agrega las credenciales de Firebase
    - **Local**: Asegúrate de tener el archivo `firebase_key.json` en la raíz del proyecto
    """)
    st.stop()

# Inicializar Firebase y obtener cliente de Firestore
db = inicializar_firebase()

import urllib.parse
import streamlit as st
from datetime import date
import pandas as pd
import os
from pathlib import Path
import unicodedata
from typing import Optional, Tuple, Dict, List, Any
from modules.caja_chica import mostrar_caja_chica
import json
import requests
import base64



# Raíz del proyecto (robusto ante ejecución desde otro directorio)
BASE_DIR = Path(__file__).resolve().parent

def _path(*parts: str) -> str:
    return str(BASE_DIR.joinpath(*parts))

def mostrar_logo_dinamico():
    """
    Muestra el logo apropiado según el tema usando CSS media queries.
    En modo claro: muestra logo_dark.png (logo oscuro/negro)
    En modo oscuro: muestra logo.png (logo claro/blanco)
    """
    logo_dark = _path("img", "logo_dark.png")
    logo_light = _path("img", "logo.png")
    
    if not os.path.exists(logo_light) or not os.path.exists(logo_dark):
        # Si falta alguno, mostrar el que existe
        if os.path.exists(logo_light):
            st.image(logo_light, use_container_width=True)
        elif os.path.exists(logo_dark):
            st.image(logo_dark, use_container_width=True)
        return
    
    # Usar HTML con media queries para cambiar entre logos
    st.markdown(
        f"""
        <style>
            .logo-container {{
                display: flex;
                justify-content: center;
                width: 100%;
            }}
            .logo-light {{
                display: block;
            }}
            .logo-dark {{
                display: none;
            }}
            @media (prefers-color-scheme: light) {{
                .logo-light {{
                    display: none;
                }}
                .logo-dark {{
                    display: block;
                }}
            }}
        </style>
        <div class="logo-container">
            <img class="logo-light" src="data:image/png;base64,{_get_image_base64(logo_light)}" style="max-width: 100%; height: auto;" />
            <img class="logo-dark" src="data:image/png;base64,{_get_image_base64(logo_dark)}" style="max-width: 100%; height: auto;" />
        </div>
        """,
        unsafe_allow_html=True
    )

def _get_image_base64(image_path: str) -> str:
    """Convierte una imagen a base64 para uso en HTML."""
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(
    page_title="Control de Obras BOSS 2026",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== IMPORTS DE MÓDULOS ====================
from modules.logic import (
    guardar_fotos_avance,
    crear_avance_dict,
    preparar_historial_avances,
    validar_insumo,
    validar_obra,
    validar_insumo_duplicado,
    validar_costos_parte_diario,
    calcular_cantidad_hh,
    calcular_parcial,
    obtener_precio_insumo,
    validar_parte_diario_completo,
    calcular_totales_costos,
    calcular_resumen_presupuesto,
    calcular_eficiencia_rendimiento,
    obtener_estado_rendimiento,
    calcular_eficiencia_promedio_obra,
    validar_partida_cronograma,
    construir_curva_s_planificada,
    construir_curva_s_real,
    construir_tabla_curvas,
    calcular_resumen_cronograma,
    calcular_resumen_hitos,
    validar_hito_pago,
    validar_donacion,
    calcular_valor_donacion,
    calcular_resumen_donaciones,
    impacto_donacion_en_presupuesto
)
from modules.database import (
    cargar_obras,
    agregar_obra,
    agregar_avance,
    cargar_insumos,
    agregar_insumo,
    actualizar_insumo,
    eliminar_insumo,
    actualizar_presupuesto_obra,
    obtener_presupuesto_obra,
    obtener_avances_obra,
    obtener_cronograma_obra,
    agregar_partida_cronograma,
    actualizar_partida_cronograma,
    eliminar_partida_cronograma,
    obtener_hitos_pago_obra,
    agregar_hito_pago,
    actualizar_hito_pago,
    eliminar_hito_pago,
    obtener_trabajos_adicionales,
    agregar_trabajo_adicional,
    actualizar_trabajo_adicional,
    eliminar_trabajo_adicional,
    obtener_donaciones_obra,
    agregar_donacion,
    actualizar_donacion,
    eliminar_donacion,
    obtener_donantes_obra,
    agregar_donante,
    actualizar_donante,
    eliminar_donante
)

# ==================== HELPERS ====================
def _norm_txt(s: str) -> str:
    s = str(s or "").strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _map_freq(label: str) -> str:
    """Mapea etiquetas UI a códigos internos."""
    t = str(label or "").strip().lower()
    if t.startswith("d"):
        return "D"  # Diario
    if t.startswith("m"):
        return "M"  # Mensual
    return "W"      # Semanal (default)

def _freq_label(code: str) -> str:
    return {"D": "Diario", "W": "Semanal", "M": "Mensual"}.get(code, "Semanal")

def _parse_ts(x):
    try:
        return pd.to_datetime(x).normalize()
    except Exception:
        return None

def _autofreq_from_cronograma(items: list) -> str:
    """
    Elige automáticamente la vista:
    - <= 45 días: Diario
    - <= 210 días: Semanal
    - > 210 días: Mensual
    """
    if not items:
        return "W"

    starts, ends = [], []
    for it in items:
        s = _parse_ts(it.get("fecha_inicio"))
        e = _parse_ts(it.get("fecha_fin"))
        if s is not None and e is not None:
            starts.append(s)
            ends.append(e)

    if not starts or not ends:
        return "W"

    span_days = int((max(ends) - min(starts)).days) + 1
    if span_days <= 45:
        return "D"
    if span_days <= 210:
        return "W"
    return "M"

def _resample_sum(df: pd.DataFrame, freq_code: str) -> pd.DataFrame:
    """Re-muestrea sumando por periodo (manteniendo fecha como inicio del periodo)."""
    if df.empty:
        return df
    df = df.copy()
    df.index = pd.to_datetime(df.index).normalize()

    if freq_code == "D":
        return df

    if freq_code == "W":
        # Semana iniciando lunes (fecha = lunes)
        out = df.resample("W-MON", label="left", closed="left").sum()
        out.index = out.index.normalize()
        return out

    # Mensual (fecha = 1er día del mes)
    out = df.resample("MS").sum()
    out.index = out.index.normalize()
    return out

def _build_plan_df(crono_items: list, freq_code: str) -> pd.DataFrame:
    """
    Construye PV por periodo desde cronograma:
    distribuye monto_planificado uniforme entre días [inicio..fin].
    Retorna columns: fecha, plan_dia
    """
    if not crono_items:
        return pd.DataFrame(columns=["fecha", "plan_dia"])

    series = pd.Series(dtype="float64")

    for it in crono_items:
        s = _parse_ts(it.get("fecha_inicio"))
        e = _parse_ts(it.get("fecha_fin"))
        try:
            monto = float(it.get("monto_planificado", 0) or 0)
        except Exception:
            monto = 0.0

        if s is None or e is None or monto <= 0:
            continue
        if e < s:
            continue

        days = pd.date_range(s, e, freq="D")
        if len(days) == 0:
            continue

        daily = monto / len(days)
        s_part = pd.Series(daily, index=days)
        series = series.add(s_part, fill_value=0) if not series.empty else s_part

    if series.empty:
        return pd.DataFrame(columns=["fecha", "plan_dia"])

    df = series.to_frame("plan_dia")
    df.index.name = "fecha"
    df = _resample_sum(df, freq_code)
    return df.reset_index()

def _extract_total_from_avance(av: dict) -> float:
    """
    Intenta obtener el costo ejecutado del avance (AC) de forma robusta.
    Soporta distintos nombres de llave según tu modules.logic.
    """
    tot = av.get("totales")
    if isinstance(tot, dict):
        for k in ("total_ejecutado", "total_general_ejecutado", "total", "total_general", "total_costos"):
            v = tot.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        # fallback: suma valores numéricos del dict
        s = 0.0
        for v in tot.values():
            if isinstance(v, (int, float)):
                s += float(v)
        return float(s)

    # fallback si el avance trae un campo directo
    for k in ("total_ejecutado", "total_general_ejecutado", "total", "total_general", "monto", "costo"):
        v = av.get(k)
        if isinstance(v, (int, float)):
            return float(v)

    return 0.0

def _build_real_df(avances: list, freq_code: str) -> pd.DataFrame:
    """
    Construye AC por periodo desde avances (partes diarios).
    Retorna columns: fecha, real_dia
    """
    if not avances:
        return pd.DataFrame(columns=["fecha", "real_dia"])

    rows = []
    for av in avances:
        f = av.get("fecha") or av.get("Fecha") or av.get("date")
        ts = _parse_ts(f)
        if ts is None:
            continue
        total = _extract_total_from_avance(av)
        if total <= 0:
            continue
        rows.append((ts, float(total)))

    if not rows:
        return pd.DataFrame(columns=["fecha", "real_dia"])

    df = pd.DataFrame(rows, columns=["fecha", "real_dia"]).groupby("fecha", as_index=True).sum()
    df = _resample_sum(df, freq_code)
    df = df.reset_index()
    return df

def render_curva_s(cronograma_all: list, avances: list, rol: str = "jefe"):
    """
    Renderiza Curva S sin selector visible (vista automática).
    - JEFE: Plan = Aprobado; Real = partes diarios.
    - PASANTE: además muestra Plan (Pendiente - borrador) para que "vea algo" incluso si aún no aprueban.
    """
    cronograma_all = cronograma_all or []
    avances = avances or []

    # Normaliza defaults
    for it in cronograma_all:
        it.setdefault("estado", "Aprobado")
        it.setdefault("creado_por", "jefe")

    cron_aprob = [it for it in cronograma_all if it.get("estado") == "Aprobado"]
    cron_pend = [it for it in cronograma_all if it.get("estado") != "Aprobado"]

    # Vista automática (pero con opción avanzada opcional)
    freq_code = _autofreq_from_cronograma(cron_aprob or cron_pend)
    st.caption(f"Vista automática: {_freq_label(freq_code)}")

    # KPIs rápidos (para que sea obvio por qué no grafica)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Partidas Aprobadas (Plan)", len(cron_aprob))
    with k2:
        st.metric("Partidas Pendientes", len(cron_pend))
    with k3:
        st.metric("Partes Diarios (Real)", len(avances))

    if not cron_aprob and cron_pend and rol == "jefe":
        st.warning("Hay partidas Pendientes. La Curva S del Plan solo considera partidas Aprobadas.")
    if not cron_aprob and cron_pend and rol == "pasante":
        st.info("Tus partidas están Pendientes. Se mostrará 'Plan (Pendiente - borrador)' hasta que el JEFE apruebe.")

    plan_df = _build_plan_df(cron_aprob, freq_code)
    real_df = _build_real_df(avances, freq_code)

    borr_df = pd.DataFrame(columns=["fecha", "plan_pend_dia"])
    if rol == "pasante" and cron_pend:
        tmp = _build_plan_df(cron_pend, freq_code)
        if not tmp.empty:
            borr_df = tmp.rename(columns={"plan_dia": "plan_pend_dia"})

    # Si no hay nada, informar claro
    has_any = (not plan_df.empty) or (not real_df.empty) or (rol == "pasante" and not borr_df.empty)
    if not has_any:
        st.info("No hay datos suficientes para graficar. Debes tener: (a) cronograma aprobado y/o (b) partes diarios con costos.")
        return

    # Merge y acumulados
    df = None
    if not plan_df.empty:
        df = plan_df.copy()
    else:
        df = pd.DataFrame(columns=["fecha", "plan_dia"])

    if not real_df.empty:
        df = pd.merge(df, real_df, on="fecha", how="outer")
    if rol == "pasante" and not borr_df.empty:
        df = pd.merge(df, borr_df, on="fecha", how="outer")

    df = df.fillna(0).sort_values("fecha")
    df = df.set_index("fecha")

    if "plan_dia" not in df.columns:
        df["plan_dia"] = 0.0
    if "real_dia" not in df.columns:
        df["real_dia"] = 0.0
    if rol == "pasante" and "plan_pend_dia" not in df.columns:
        df["plan_pend_dia"] = 0.0

    out = pd.DataFrame(index=df.index)
    out["Plan (Aprobado)"] = df["plan_dia"].cumsum()
    out["Real (Partes diarios)"] = df["real_dia"].cumsum()

    if rol == "pasante":
        out["Plan (Pendiente - borrador)"] = df["plan_pend_dia"].cumsum()

    st.line_chart(out, use_container_width=True)

    with st.expander("Ver detalle por periodo", expanded=False):
        det = df.copy()
        det["plan_acum"] = df["plan_dia"].cumsum()
        det["real_acum"] = df["real_dia"].cumsum()
        if rol == "pasante" and "plan_pend_dia" in df.columns:
            det["plan_pend_acum"] = df["plan_pend_dia"].cumsum()
        st.dataframe(det.reset_index(), use_container_width=True, hide_index=True)
        # ==================== HELPERS KPI  ====================

# Crear carpeta si no existe (no toca tu database)
for folder in ["obras_kpi"]:
    os.makedirs(_path(folder), exist_ok=True)

def _kpi_file_path(obra_codigo: str) -> str:
    return _path("obras_kpi", f"{obra_codigo}.json")

def kpi_cargar_config(obra_codigo: str) -> dict:
    archivo = _kpi_file_path(obra_codigo)
    plantilla = {"avance_programado": 0.0}

    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, dict):
                return plantilla
            datos.setdefault("avance_programado", 0.0)
            return datos
        except Exception:
            return plantilla
    return plantilla

def kpi_guardar_config(obra_codigo: str, datos: dict):
    archivo = _kpi_file_path(obra_codigo)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False, default=str)

def semaforo_presupuesto(pct):
    if pct is None:
        return ("#95a5a6", "SIN DATOS")
    if pct <= 95:
        return ("#2ecc71", f"VERDE ({pct:.1f}%)")
    if pct <= 100:
        return ("#f1c40f", f"ÁMBAR ({pct:.1f}%)")
    return ("#e74c3c", f"ROJO ({pct:.1f}%)")

def semaforo_tiempo(avance_real, avance_programado):
    # Si no han ingresado meta, no mostramos nada concreto
    if avance_programado <= 0:
        return None, "Definir Programado"

    diferencia = avance_real - avance_programado

    # Verde: Obra al día o adelantada (>=0)
    # Ámbar: Retraso leve (hasta -5%)
    # Rojo: Retraso crítico (< -5%)
    if diferencia >= 0:
        color = "#2ecc71"
        estado = "A TIEMPO / ADELANTADO"
    elif diferencia >= -5:
        color = "#f1c40f"
        estado = "RETRASO LEVE (Recuperable)"
    else:
        color = "#e74c3c"
        estado = "RETRASO CRÍTICO (Peligro)"

    return color, estado

def calcular_avance_real_total(avances: list) -> float:
    total = 0.0
    for av in avances or []:
        v = av.get("avance_pct", av.get("avance", 0))
        try:
            total += float(v or 0)
        except Exception:
            pass
    return float(total)

def ui_kpi_dashboard(presupuesto_total: float, gasto_acumulado: float, avance_real_total: float, avance_programado: float):
    pct_financiero = None
    if presupuesto_total and float(presupuesto_total) > 0:
        pct_financiero = (float(gasto_acumulado) / float(presupuesto_total)) * 100.0

    color_fin, estado_fin = semaforo_presupuesto(pct_financiero)
    color_tiempo, estado_tiempo = semaforo_tiempo(avance_real_total, float(avance_programado))

    st.subheader("Tablero de Control (KPIs)")
    col_kpi1, col_kpi2 = st.columns(2)

    # === SEMÁFORO 1: FINANCIERO ===
    with col_kpi1:
        st.markdown("#### 💰 Control de Costos")
        c1, c2 = st.columns(2)
        c1.metric("Presupuesto Total", f"S/ {float(presupuesto_total):,.0f}" if float(presupuesto_total) > 0 else "—")
        c2.metric("Gasto Ejecutado", f"S/ {float(gasto_acumulado):,.0f}")

        if pct_financiero is not None:
            st.progress(min(pct_financiero / 100, 1.0))

        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid rgba(255,255,255,0.1);border-radius:8px;border-left: 6px solid {color_fin};background:rgba(0,0,0,0.2);">
              <div>
                <div style="font-size:12px;opacity:0.8;">RENTABILIDAD</div>
                <div style="font-size:16px;font-weight:bold;color:{color_fin}">{estado_fin}</div>
              </div>
            </div>
            """, unsafe_allow_html=True
        )

    # === SEMÁFORO 2: TIEMPO ===
    with col_kpi2:
        st.markdown("#### 📅 Control de Avance Físico")

        if color_tiempo:
            c1, c2 = st.columns(2)
            c1.metric("Avance REAL", f"{float(avance_real_total):.1f}%")
            delta_val = float(avance_real_total) - float(avance_programado)
            c2.metric("Meta PROGRAMADA", f"{float(avance_programado):.1f}%", delta=f"{delta_val:.1f}% Diferencia")

            st.progress(min(float(avance_real_total) / 100, 1.0))

            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid rgba(255,255,255,0.1);border-radius:8px;border-left: 6px solid {color_tiempo};background:rgba(0,0,0,0.2);">
                  <div>
                    <div style="font-size:12px;opacity:0.8;">CUMPLIMIENTO DE PLAZOS</div>
                    <div style="font-size:16px;font-weight:bold;color:{color_tiempo}">{estado_tiempo}</div>
                    <div style="font-size:12px;margin-top:4px;">
                       Real: <b>{float(avance_real_total):.1f}%</b> vs Prog: <b>{float(avance_programado):.1f}%</b>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True
            )
        else:
            st.info("👈 Ingresa el 'Avance Programado' en la barra lateral para ver este semáforo.")



# ==================== RESTRICCIÓN DE OBRAS POR PASANTE ====================
# Ajusta aquí si en tu empresa cambian los usuarios o nombres
PASANTE_OBRA_KEYWORDS = {
    # pasante-pachacutec => obra Ventanilla / Pachacutec
    "pasante-pachacutec": ["pachacutec", "ventanilla"],
    # pasante-rinconada => obra La Molina / Rinconada
    "pasante-rinconada": ["rinconada", "molina", "la molina"],
}

def obtener_obra_asignada_pasante(obras: dict, usuario: str):
    """
    Devuelve (codigo_obra, nombre_obra) asignado al pasante según su usuario.
    Busca por keywords en código o nombre (sin tildes, case-insensitive).
    """
    if not isinstance(usuario, str) or not usuario.startswith("pasante-"):
        return None, None

    kws = PASANTE_OBRA_KEYWORDS.get(usuario)
    if not kws:
        # Fallback: usa el tag del usuario pasante-<tag>
        kws = [usuario.split("pasante-", 1)[1]]

    kws = [_norm_txt(k) for k in kws if str(k).strip()]

    best_score = 0
    best_cod = None
    best_nom = None

    for cod, nom in (obras or {}).items():
        cod_n = _norm_txt(cod)
        nom_n = _norm_txt(nom)

        score = 0
        for kw in kws:
            if kw in cod_n:
                score += 3
            if kw in nom_n:
                score += 2

        if score > best_score:
            best_score = score
            best_cod = cod
            best_nom = nom

    if best_score <= 0:
        return None, None
    return best_cod, best_nom

# ==================== PDF / DRIVE HELPERS ====================
def _get_drive_conf() -> Tuple[Optional[str], Optional[str]]:
    """Obtiene (webapp_url, token) desde st.secrets o variables de entorno."""
    webapp_url = None
    token = None
    try:
        drive = st.secrets.get("drive", {})
        webapp_url = drive.get("webapp_url") or None
        token = drive.get("token") or None
    except Exception:
        pass

    webapp_url = webapp_url or os.getenv("BOSS_WEBAPP_URL")
    token = token or os.getenv("BOSS_TOKEN")
    return webapp_url, token


def _safe_pdf_filename(s: str) -> str:
    s = str(s or "").strip()
    s = "".join(c for c in s if c.isalnum() or c in ["-", "_", "."])
    return s or "reporte.pdf"


def _avance_to_pdf_bytes(obra_codigo: str, obra_nombre: str, avance: dict, rol: str) -> Optional[bytes]:
    """Convierte un avance (parte diario) a PDF (bytes)."""
    try:
        from modules.pdf_report import build_parte_pdf
    except Exception as e:
        st.error(f"No se pudo importar el generador PDF (pdf_report). Revisa requirements.txt. Detalle: {e}")
        return None

    fecha = str((avance or {}).get("fecha") or "")
    emitido_por = str((avance or {}).get("responsable") or "usuario")

    partida = (avance or {}).get("partida") if isinstance((avance or {}).get("partida"), dict) else {}
    tot = (avance or {}).get("totales") if isinstance((avance or {}).get("totales"), dict) else {}

    resumen_rows = [
        ["Avance del día", f"{(avance or {}).get('avance', 0)} %"],
        ["Partida", str(partida.get("nombre", ""))],
        ["Cantidad ejecutada", f"{partida.get('cantidad_ejecutada', 0)} {partida.get('unidad', '')}".strip()],
        ["Horas Hombre (HH)", str(partida.get("horas_hombre", 0))],
        ["Total Mano de Obra (S/)", f"{float(tot.get('mano_de_obra', 0) or 0):,.2f}"],
        ["Total Materiales (S/)", f"{float(tot.get('materiales', 0) or 0):,.2f}"],
        ["Total Equipos (S/)", f"{float(tot.get('equipos', 0) or 0):,.2f}"],
        ["Total Otros (S/)", f"{float(tot.get('otros', 0) or 0):,.2f}"],
        ["TOTAL GENERAL (S/)", f"{float(tot.get('total_general_ejecutado', 0) or tot.get('total_general', 0) or 0):,.2f}"],
    ]

    def _tabla_costos(titulo: str, items: list) -> Dict[str, Any]:
        headers = ["Descripción", "Cantidad", "P. Unit.", "Parcial (S/)"]
        rows = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            desc = it.get("Descripción") or it.get("descripcion") or it.get("nombre") or ""
            cant = it.get("Cantidad", it.get("cantidad", 0)) or 0
            pu = it.get("Precio Unit.", it.get("precio_unit", 0)) or 0
            parc = it.get("Parcial (S/)", it.get("parcial", 0)) or 0
            try:
                cant = float(cant)
            except Exception:
                cant = 0.0
            try:
                pu = float(pu)
            except Exception:
                pu = 0.0
            try:
                parc = float(parc)
            except Exception:
                parc = 0.0
            rows.append([str(desc), f"{cant:,.2f}", f"{pu:,.2f}", f"{parc:,.2f}"])
        return {"titulo": titulo, "headers": headers, "rows": rows}

    costos = (avance or {}).get("costos") if isinstance((avance or {}).get("costos"), dict) else {}
    tablas = [
        _tabla_costos("Mano de Obra", costos.get("mano_de_obra", [])),
        _tabla_costos("Materiales", costos.get("materiales", [])),
        _tabla_costos("Equipos", costos.get("equipos", [])),
        _tabla_costos("Otros", costos.get("otros", [])),
    ]
    tablas = [t for t in tablas if t.get("rows")]

    # Fotos: convertir rutas relativas a absolutas o manejar URLs de Cloudinary
    foto_paths = []
    for p in (avance or {}).get("fotos", []) or []:
        try:
            p = str(p)
            if not p:
                continue
            
            # Si es URL de Cloudinary, omitir en PDFs por ahora (mejora futura: descargar temp)
            if p.startswith("http://") or p.startswith("https://"):
                continue
            
            abs_p = (BASE_DIR / p).resolve() if not os.path.isabs(p) else Path(p)
            if abs_p.exists():
                foto_paths.append(str(abs_p))
        except Exception:
            continue

    try:
        return build_parte_pdf(
            obra_code=obra_codigo,
            obra_name=obra_nombre,
            fecha=fecha,
            emitido_por=emitido_por,
            rol=rol,
            resumen_rows=resumen_rows,
            tablas=tablas,
            foto_paths=foto_paths,
        )
    except Exception as e:
        st.error(f"Error al generar PDF: {e}")
        return None


def _render_pdf_panel():
    """Panel post-guardado para descargar/subir PDF."""
    if not st.session_state.get("show_pdf_panel"):
        return

    meta = st.session_state.get("pdf_meta") or {}
    avance = st.session_state.get("pdf_avance") or {}

    obra_codigo = meta.get("obra_codigo")
    obra_nombre = meta.get("obra_nombre")
    rol = meta.get("rol", "jefe")

    if not obra_codigo or not obra_nombre or not avance:
        st.session_state.show_pdf_panel = False
        return

    st.markdown("---")
    st.subheader("📄 Parte diario en PDF")

    if st.session_state.get("pdf_bytes") is None:
        st.session_state.pdf_bytes = _avance_to_pdf_bytes(obra_codigo, obra_nombre, avance, rol=rol)

    pdf_bytes = st.session_state.get("pdf_bytes")
    if not pdf_bytes:
        st.info("No se pudo generar el PDF con los datos actuales.")
        return

    fecha = str(avance.get("fecha") or "")
    filename = _safe_pdf_filename(f"PARTE_{obra_codigo}_{fecha}.pdf")

    # Preparar mensaje de WhatsApp
    partida = (avance or {}).get("partida") if isinstance((avance or {}).get("partida"), dict) else {}
    totales = (avance or {}).get("totales") if isinstance((avance or {}).get("totales"), dict) else {}
    
    c1, c2, c3 = st.columns([2, 2, 1])
    
    with c1:
        st.download_button(
            "⬇️ Descargar PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )
    
    with c2:
        webapp_url, token = _get_drive_conf()
        disabled = not (webapp_url and token)
        help_txt = "Configura [drive] en .streamlit/secrets.toml (webapp_url y token) o variables de entorno." if disabled else None
        if st.button("☁️ Subir a Google Drive", use_container_width=True, disabled=disabled, help=help_txt):
            try:
                from modules.drive_upload import upload_pdf_base64
                with st.spinner("Subiendo a Google Drive..."):
                    resp = upload_pdf_base64(webapp_url, token, obra_codigo, filename, pdf_bytes)
                    
                    if isinstance(resp, dict):
                        if resp.get("ok"):
                            file_id = resp.get("fileId", "")
                            st.success(f"✅ PDF subido exitosamente a Google Drive")
                            if file_id:
                                st.info(f"📁 File ID: {file_id}")
                        else:
                            error_msg = resp.get("error", "Error desconocido")
                            st.error(f"❌ Error del servidor: {error_msg}")
                    else:
                        st.warning(f"⚠️ Respuesta inesperada del servidor: {resp}")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error de conexión: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error al subir a Drive: {str(e)}")
                st.caption("Verifica tu conexión a internet y la configuración de Apps Script")
    
    with c3:
        if st.button("Ocultar", use_container_width=True):
            st.session_state.show_pdf_panel = False
            st.session_state.pdf_meta = {}
            st.session_state.pdf_avance = {}
            st.session_state.pdf_bytes = None
            st.session_state.parte_enviado = False

    st.markdown("---")

# ==================== CONFIGURACIÓN INICIAL ====================

# ==================== AUTENTICACIÓN ====================
def check_password():
    def password_entered():
        users = st.secrets.get("users", {}) if hasattr(st, "secrets") else {}
        if not users:
            users = {
                "jefe_user": os.environ.get("BOSS_JEFE_USER", "jefe"),
                "jefe_pass": os.environ.get("BOSS_JEFE_PASS", "1234"),
                "pasante_user_prefix": os.environ.get("BOSS_PASANTE_PREFIX", "pas"),
                "pasante_pass": os.environ.get("BOSS_PASANTE_PASS", "1234"),
            }
        if (st.session_state.get("password") == users["jefe_pass"] and
                st.session_state.get("user") == users["jefe_user"]):
            st.session_state["auth"] = "jefe"
            st.session_state["usuario_logueado"] = st.session_state.get("user")
        elif (st.session_state.get("password") == users["pasante_pass"] and
              str(st.session_state.get("user", "")).startswith(users["pasante_user_prefix"])):
            st.session_state["auth"] = st.session_state.get("user")
            st.session_state["usuario_logueado"] = st.session_state.get("user")
        else:
            st.session_state["auth"] = False

    if "auth" not in st.session_state:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            mostrar_logo_dinamico()

        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.markdown("<h1 style='text-align:center;'>CONTROL DE OBRAS 2026</h1>", unsafe_allow_html=True)
            st.text_input("Usuario", key="user")
            st.text_input("Contraseña", type="password", key="password")
            st.button("INGRESAR", on_click=password_entered, use_container_width=True)
        return False

    if not st.session_state["auth"]:
        st.error("Usuario o contraseña incorrecta")
        return False
    return True

if not check_password():
    st.stop()


# ==================== INICIALIZACIÓN DE SESSION STATE ====================
# Inicializar variables de session_state si no existen
if "whatsapp_enviado" not in st.session_state:
    st.session_state.whatsapp_enviado = False
if "abrir_whatsapp_modal" not in st.session_state:
    st.session_state.abrir_whatsapp_modal = False
if "temp_nuevo_avance" not in st.session_state:
    st.session_state.temp_nuevo_avance = {}
if "temp_obra_nombre" not in st.session_state:
    st.session_state.temp_obra_nombre = ""
if "show_pdf_panel" not in st.session_state:
    st.session_state.show_pdf_panel = False
if "pdf_meta" not in st.session_state:
    st.session_state.pdf_meta = {}
if "pdf_avance" not in st.session_state:
    st.session_state.pdf_avance = {}
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "parte_enviado" not in st.session_state:
    st.session_state.parte_enviado = False
# ==================== INTERFAZ PRINCIPAL ====================
# ==================== MODO JEFE ====================
if st.session_state["auth"] == "jefe":
    with st.sidebar:
        mostrar_logo_dinamico()
        st.divider()

        obras = cargar_obras()

        if "obra_seleccionada" not in st.session_state:
            st.session_state.obra_seleccionada = None

        st.subheader("Seleccionar Obra")
        opciones_obras = ["-- Seleccionar --"] + [f"{nombre}" for codigo, nombre in obras.items()]
        codigos_obras = [None] + list(obras.keys())

        indice_actual = 0
        if st.session_state.obra_seleccionada:
            try:
                indice_actual = codigos_obras.index(st.session_state.obra_seleccionada)
            except ValueError:
                indice_actual = 0

        obra_seleccionada_idx = st.selectbox(
            "Obra:",
            range(len(opciones_obras)),
            format_func=lambda x: opciones_obras[x],
            index=indice_actual,
            key="selector_obra"
        )

        nuevo_codigo = codigos_obras[obra_seleccionada_idx]
        if nuevo_codigo != st.session_state.obra_seleccionada:
            st.session_state.obra_seleccionada = nuevo_codigo
            st.session_state.mostrar_form_obra = False
            st.session_state.mostrar_insumos = False
            st.rerun()
                    # ==================== KPI: Avance Programado ====================
        if st.session_state.obra_seleccionada:
            cfg_kpi = kpi_cargar_config(st.session_state.obra_seleccionada)

            st.divider()
            st.markdown("### 📅 Cronograma (Input Manual)")
            nuevo_programado = st.number_input(
                "¿Cuánto % debería llevar la obra HOY?",
                min_value=0.0,
                max_value=100.0,
                value=float(cfg_kpi.get("avance_programado", 0.0)),
                step=1.0,
                help="Ingresa el porcentaje programado acumulado según el cronograma oficial."
            )

            if nuevo_programado != float(cfg_kpi.get("avance_programado", 0.0)):
                cfg_kpi["avance_programado"] = nuevo_programado
                kpi_guardar_config(st.session_state.obra_seleccionada, cfg_kpi)
                st.success("¡Meta actualizada!")
                st.rerun()


        if st.button("➕ Agregar Nueva Obra", key="agregar_obra_btn", use_container_width=True):
            st.session_state.mostrar_form_obra = True
            st.rerun()

        st.divider()

        if st.button("� Reportes", use_container_width=True):
            st.session_state.mostrar_reportes = True
            st.rerun()

    # ==================== SECCIÓN: REPORTES DE PRACTICANTES (SOLO CUANDO SE HACE CLIC EN EL BOTÓN) ====================
    if st.session_state.get("mostrar_reportes"):
        
        # Botón para volver
        if st.button("← Volver al Panel Principal", use_container_width=False):
            st.session_state.mostrar_reportes = False
            st.rerun()
        
        st.markdown("# 📊 REVISIÓN DE REPORTES DE PRACTICANTES")
        st.caption("Control y seguimiento detallado de los partes diarios de cada practicante")
        
        # Obtener obras disponibles
        obras = cargar_obras()
        
        if obras:
            nombres_obras = list(obras.values())
            codigos_obras = list(obras.keys())
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                obra_seleccionada_nombre = st.selectbox(
                    "🏗️ Seleccionar obra para revisar reportes:",
                    ["-- Seleccionar --"] + nombres_obras,
                    key="select_obra_reportes"
                )
            
            if obra_seleccionada_nombre != "-- Seleccionar --":
                # Obtener el código de la obra seleccionada
                obra_idx = nombres_obras.index(obra_seleccionada_nombre)
                obra_codigo = codigos_obras[obra_idx]
                
                # Obtener TODOS los avances (partes diarios) de esta obra desde Firebase
                avances_obra = obtener_avances_obra(obra_codigo)
                
                if not avances_obra:
                    st.info(f"📭 No hay reportes registrados para la obra **{obra_seleccionada_nombre}**")
                    st.write("Los practicantes deben crear partes diarios para que aparezcan aquí.")
                else:
                    # Organizar por practicante
                    reportes_por_practicante = {}
                    
                    for avance in avances_obra:
                        responsable = avance.get("responsable", "Desconocido")
                        fecha = avance.get("fecha", "")
                        avance_pct = avance.get("avance", 0)
                        observaciones = avance.get("observaciones", "")
                        fotos = avance.get("fotos", [])
                        estado = avance.get("estado", "Aprobado")  # Nuevo: estado del reporte
                        
                        # Obtener información de la partida
                        partida_info = avance.get("partida", {})
                        actividad = partida_info.get("nombre", "Sin actividad especificada")
                        cantidad_ejecutada = partida_info.get("cantidad_ejecutada", 0)
                        unidad = partida_info.get("unidad", "")
                        horas = partida_info.get("jornal_horas", 8)
                        rendimiento = partida_info.get("rendimiento", 0)
                        
                        # Obtener totales de costos
                        totales = avance.get("totales", {})
                        total_mo = totales.get("mano_de_obra", 0)
                        total_mat = totales.get("materiales", 0)
                        total_ejecutado = float(total_mo or 0) + float(total_mat or 0)
                        
                        # Costos detallados
                        costos = avance.get("costos", {})
                        
                        if responsable not in reportes_por_practicante:
                            reportes_por_practicante[responsable] = []
                        
                        reportes_por_practicante[responsable].append({
                            "dia": fecha,
                            "actividad": actividad,
                            "horas": horas,
                            "avance": avance_pct,
                            "cantidad_ejecutada": cantidad_ejecutada,
                            "unidad": unidad,
                            "rendimiento": rendimiento,
                            "observaciones": observaciones,
                            "fotos": fotos,
                            "estado": estado,
                            "total_mo": total_mo,
                            "total_mat": total_mat,
                            "total_ejecutado": total_ejecutado,
                            "costos": costos,
                        })
                    
                    # Obtener lista de practicantes únicos
                    practicantes = list(reportes_por_practicante.keys())
                    practicantes.sort()
                    
                    # ==================== RESUMEN GENERAL ====================
                    st.markdown("### 📈 Resumen General")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("👷 Practicantes", len(practicantes))
                    
                    with col2:
                        total_reportes = sum(len(reportes) for reportes in reportes_por_practicante.values())
                        st.metric("📋 Total Reportes", total_reportes)
                    
                    with col3:
                        # Contar reportes pendientes
                        reportes_pendientes = sum(
                            1 for reportes in reportes_por_practicante.values() 
                            for r in reportes if r.get("estado") == "Pendiente"
                        )
                        st.metric("⏳ Pendientes", reportes_pendientes)
                    
                    with col4:
                        # Calcular total de horas trabajadas
                        total_horas = sum(
                            r["horas"] for reportes in reportes_por_practicante.values() 
                            for r in reportes
                        )
                        st.metric("⏱️ Total Horas", f"{total_horas} h")
                    
                    st.divider()
                    
                    # ==================== VISTA DE PRACTICANTES ====================
                    col_izq, col_der = st.columns([1, 3])
                    
                    # Columna izquierda - Lista de practicantes
                    with col_izq:
                        st.markdown("### 👥 Practicantes")
                        
                        # Filtro de estado
                        filtro_estado = st.radio(
                            "Filtrar por estado:",
                            ["Todos", "Pendiente", "Aprobado"],
                            key="filtro_estado_practicantes"
                        )
                        
                        st.divider()
                        
                        for p in practicantes:
                            reportes = reportes_por_practicante[p]
                            
                            # Calcular estadísticas
                            pendientes = sum(1 for r in reportes if r.get("estado") == "Pendiente")
                            total = len(reportes)
                            
                            # Determinar si mostrar según filtro
                            mostrar = (
                                filtro_estado == "Todos" or
                                (filtro_estado == "Pendiente" and pendientes > 0) or
                                (filtro_estado == "Aprobado" and pendientes == 0)
                            )
                            
                            if mostrar:
                                # Botón con indicador de estado
                                if pendientes > 0:
                                    label = f"⚠️ {p} ({pendientes})"
                                else:
                                    label = f"✅ {p}"
                                
                                if st.button(label, key=f"btn_{p}", use_container_width=True):
                                    st.session_state.ver_practicante = p
                    
                    # Columna derecha - Detalle del practicante seleccionado
                    with col_der:
                        if "ver_practicante" in st.session_state:
                            p = st.session_state.ver_practicante
                            
                            st.markdown(f"### 📋 Reportes de **{p}**")
                            
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                # Filtro de fecha
                                ordenar = st.radio(
                                    "Ordenar por fecha:",
                                    ["Más reciente primero", "Más antiguo primero"],
                                    horizontal=True,
                                    key="orden_fecha"
                                )
                            
                            with col2:
                                if st.button("← Volver", use_container_width=True):
                                    del st.session_state.ver_practicante
                                    st.rerun()
                            
                            st.divider()
                            
                            if p in reportes_por_practicante:
                                reportes = reportes_por_practicante[p]
                                
                                # Ordenar reportes
                                reverse = ordenar == "Más reciente primero"
                                reportes_ordenados = sorted(reportes, key=lambda x: x["dia"], reverse=reverse)
                                
                                # ==================== ESTADÍSTICAS DEL PRACTICANTE ====================
                                st.markdown("#### 📊 Estadísticas del Practicante")
                                
                                col1, col2, col3, col4, col5 = st.columns(5)
                                
                                with col1:
                                    st.metric("📋 Reportes", len(reportes))
                                
                                with col2:
                                    total_horas_p = sum(r["horas"] for r in reportes)
                                    st.metric("⏱️ Horas", f"{total_horas_p} h")
                                
                                with col3:
                                    avance_total_p = sum(r["avance"] for r in reportes)
                                    st.metric("📈 Avance", f"{avance_total_p}%")
                                
                                with col4:
                                    total_gastado_p = sum(r["total_ejecutado"] for r in reportes)
                                    st.metric("💰 Total Gastado", f"S/. {total_gastado_p:,.2f}")
                                
                                with col5:
                                    pendientes_p = sum(1 for r in reportes if r.get("estado") == "Pendiente")
                                    st.metric("⏳ Pendientes", pendientes_p)
                                
                                st.divider()
                                
                                # ==================== DETALLE DE REPORTES ====================
                                st.markdown("#### 📄 Detalle de Reportes")
                                
                                for i, reporte in enumerate(reportes_ordenados):
                                    # Determinar color según estado
                                    if reporte.get("estado") == "Pendiente":
                                        icono_estado = "⏳"
                                        color_estado = "🟡"
                                    else:
                                        icono_estado = "✅"
                                        color_estado = "🟢"
                                    
                                    titulo_expander = f"{icono_estado} {reporte['dia']} - {reporte['actividad']} ({color_estado} {reporte.get('estado', 'Aprobado')})"
                                    
                                    with st.expander(titulo_expander, expanded=(i==0)):
                                        
                                        # Información general
                                        st.markdown("##### 📋 Información General")
                                        col1, col2, col3 = st.columns(3)
                                        
                                        with col1:
                                            st.write(f"**📅 Fecha:** {reporte['dia']}")
                                            st.write(f"**🏗️ Actividad:** {reporte['actividad']}")
                                        
                                        with col2:
                                            st.write(f"**⏱️ Horas:** {reporte['horas']} h")
                                            st.write(f"**📈 Avance:** {reporte['avance']}%")
                                        
                                        with col3:
                                            st.write(f"**📏 Metrado:** {reporte['cantidad_ejecutada']} {reporte['unidad']}")
                                            st.write(f"**⚡ Rendimiento:** {reporte['rendimiento']}")
                                        
                                        # Costos detallados
                                        st.markdown("##### 💰 Costos Ejecutados")
                                        col1, col2, col3 = st.columns(3)
                                        
                                        with col1:
                                            st.metric("Mano de Obra", f"S/. {reporte['total_mo']:,.2f}")
                                        with col2:
                                            st.metric("Materiales", f"S/. {reporte['total_mat']:,.2f}")
                                        with col3:
                                            st.metric("💰 TOTAL", f"S/. {reporte['total_ejecutado']:,.2f}")
                                        
                                        st.markdown(f"**💵 TOTAL EJECUTADO: S/. {reporte['total_ejecutado']:,.2f}**")
                                        
                                        # Detalle de costos por categoría
                                        costos = reporte.get("costos", {})
                                        
                                        if costos:
                                            st.markdown("##### 📊 Detalle de Costos")
                                            
                                            tabs_costos = st.tabs(["Mano de Obra", "Materiales"])
                                            
                                            with tabs_costos[0]:
                                                if costos.get("mano_de_obra"):
                                                    st.dataframe(
                                                        pd.DataFrame(costos["mano_de_obra"]),
                                                        use_container_width=True,
                                                        hide_index=True
                                                    )
                                                else:
                                                    st.info("No hay costos de mano de obra")
                                            
                                            with tabs_costos[1]:
                                                if costos.get("materiales"):
                                                    st.dataframe(
                                                        pd.DataFrame(costos["materiales"]),
                                                        use_container_width=True,
                                                        hide_index=True
                                                    )
                                                else:
                                                    st.info("No hay costos de materiales")
                                            
                                            with tabs_costos[2]:
                                                if costos.get("equipos"):
                                                    st.dataframe(
                                                        pd.DataFrame(costos["equipos"]),
                                                        use_container_width=True,
                                                        hide_index=True
                                                    )
                                                else:
                                                    st.info("No hay costos de equipos")
                                            
                                            with tabs_costos[3]:
                                                if costos.get("otros"):
                                                    st.dataframe(
                                                        pd.DataFrame(costos["otros"]),
                                                        use_container_width=True,
                                                        hide_index=True
                                                    )
                                                else:
                                                    st.info("No hay otros costos")
                                        
                                        # Observaciones
                                        if reporte.get("observaciones"):
                                            st.markdown("##### 📝 Observaciones")
                                            st.write(reporte["observaciones"])
                                        
                                        # Fotos
                                        fotos = reporte.get("fotos", [])
                                        if fotos:
                                            st.markdown(f"##### 📷 Fotos del Avance ({len(fotos)} fotos)")
                                            cols_fotos = st.columns(min(len(fotos), 3))
                                            
                                            for idx, foto_path in enumerate(fotos):
                                                target_col = cols_fotos[idx % 3]
                                                try:
                                                    # Verificar si es URL de Cloudinary
                                                    if str(foto_path).startswith("http://") or str(foto_path).startswith("https://"):
                                                        target_col.image(foto_path, use_container_width=True)
                                                    elif foto_path and os.path.exists(foto_path):
                                                        target_col.image(foto_path, use_container_width=True)
                                                    else:
                                                        target_col.warning(f"❌ Foto no encontrada")
                                                except Exception as e:
                                                    target_col.error(f"Error: {e}")
                                        
                                        # Acciones según estado
                                        st.divider()
                                        
                                        if reporte.get("estado") == "Pendiente":
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                if st.button(
                                                    "✅ Aprobar Reporte",
                                                    key=f"aprobar_{p}_{i}",
                                                    use_container_width=True,
                                                    type="primary"
                                                ):
                                                    st.success(f"✅ Reporte del {reporte['dia']} aprobado")
                                                    st.info("💡 Funcionalidad pendiente: actualizar estado en Firebase")
                                                    # TODO: Implementar actualización de estado en Firebase
                                            
                                            with col2:
                                                if st.button(
                                                    "❌ Rechazar Reporte",
                                                    key=f"rechazar_{p}_{i}",
                                                    use_container_width=True
                                                ):
                                                    st.warning(f"⚠️ Reporte del {reporte['dia']} rechazado")
                                                    st.info("💡 Funcionalidad pendiente: eliminar reporte de Firebase")
                                                    # TODO: Implementar eliminación en Firebase
                                        else:
                                            st.success(f"✅ Reporte aprobado el {reporte['dia']}")
                            else:
                                st.info("No hay reportes para este practicante")
                        else:
                            st.info("👈 Selecciona un practicante de la lista para ver sus reportes detallados")
            else:
                st.info("👆 Selecciona una obra para ver los reportes de los practicantes")
        else:
            st.warning("⚠️ No hay obras registradas en el sistema")
        
        # Salir de esta sección para que no muestre el resto del código del jefe
        st.stop()
    
    # ==================== TÍTULO PRINCIPAL (SOLO SE MUESTRA CUANDO NO ESTÁN LOS REPORTES) ====================
    st.title("Modo Jefe de Obra")

    # ==================== SECCIÓN: AGREGAR NUEVA OBRA ====================
    if "mostrar_form_obra" in st.session_state and st.session_state.mostrar_form_obra:
        st.subheader("➕ Agregar Nueva Obra")

        with st.form("form_nueva_obra"):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_codigo = st.text_input("Código de la Obra", placeholder="ej: obra2026")
            with col2:
                nuevo_nombre = st.text_input("Nombre de la Obra", placeholder="ej: Edificio Central – San Isidro")

            presupuesto_nuevo = st.number_input(
                "Presupuesto Total (S/.)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                help="Presupuesto inicial asignado a la obra",
            )

            if st.form_submit_button("Guardar", use_container_width=True):
                obras_actuales = cargar_obras()
                es_valido, mensaje = validar_obra(nuevo_codigo, nuevo_nombre, obras_actuales)

                if not es_valido:
                    st.error(f"❌ {mensaje}")
                else:
                    exito, mensaje_db = agregar_obra(nuevo_codigo, nuevo_nombre)
                    if exito:
                        ok_pres, msg_pres = actualizar_presupuesto_obra(nuevo_codigo, presupuesto_nuevo)
                        if not ok_pres:
                            st.warning(f"⚠️ Obra creada, pero no se pudo guardar el presupuesto: {msg_pres}")
                        st.success(f"Obra '{nuevo_nombre}' agregada exitosamente")
                        st.session_state.mostrar_form_obra = False
                        st.rerun()
                    else:
                        st.error(f"❌ {mensaje_db}")

        if st.button("Volver", use_container_width=True):
            st.session_state.mostrar_form_obra = False
            st.rerun()

    # ==================== SECCIÓN: GESTIÓN DE EMPLEADOS ====================
    elif "mostrar_empleados" in st.session_state and st.session_state.mostrar_empleados:
        st.header("👷 Gestión de Empleados (Mano de Obra)")

        if st.button("← Volver", use_container_width=False):
            st.session_state.mostrar_empleados = False
            st.rerun()

        # Cargar empleados desde Firebase
        empleados_docs = db.collection("empleados").stream()
        empleados = [{"id": d.id, **d.to_dict()} for d in empleados_docs]

        st.subheader("Agregar Nuevo Empleado")
        
        with st.form("form_nuevo_empleado"):
            col1, col2 = st.columns(2)
            with col1:
                nombre_emp = st.text_input("Nombre Completo", placeholder="ej: Juan Pérez López")
                cargo_emp = st.text_input("Cargo", placeholder="ej: Operario, Oficial, Peón")
            with col2:
                dni_emp = st.text_input("DNI", placeholder="ej: 12345678")
                numero_emp = st.text_input("Número de Contacto", placeholder="ej: 987654321")

            if st.form_submit_button("Agregar Empleado", use_container_width=True, type="primary"):
                if not nombre_emp.strip():
                    st.error("❌ El nombre es requerido")
                elif not cargo_emp.strip():
                    st.error("❌ El cargo es requerido")
                elif not dni_emp.strip():
                    st.error("❌ El DNI es requerido")
                elif len(dni_emp.strip()) != 8 or not dni_emp.strip().isdigit():
                    st.error("❌ El DNI debe tener 8 dígitos")
                else:
                    nuevo_empleado = {
                        "nombre": nombre_emp.strip(),
                        "cargo": cargo_emp.strip(),
                        "dni": dni_emp.strip(),
                        "numero": numero_emp.strip(),
                        "fecha_registro": date.today().isoformat()
                    }
                    db.collection("empleados").add(nuevo_empleado)
                    st.success(f"✅ Empleado {nombre_emp} agregado correctamente")
                    st.rerun()

        if empleados:
            st.subheader("Listado de Empleados")
            df_emp = pd.DataFrame(empleados)
            df_emp = df_emp[["nombre", "cargo", "dni", "numero"]]
            df_emp.columns = ["Nombre", "Cargo", "DNI", "Teléfono"]
            st.dataframe(df_emp, use_container_width=True, hide_index=True)

            st.subheader("Eliminar Empleado")
            nombres_emp = [f"{e['nombre']} - {e['cargo']} (DNI: {e['dni']})" for e in empleados]
            
            if nombres_emp:
                emp_seleccionado = st.selectbox("Selecciona un empleado para eliminar:", nombres_emp)
                idx_sel = nombres_emp.index(emp_seleccionado)
                emp_id = empleados[idx_sel]["id"]

                st.warning(f"**Se eliminará:** {empleados[idx_sel]['nombre']}")
                if st.button("🗑️ Eliminar empleado", use_container_width=True, type="secondary"):
                    db.collection("empleados").document(emp_id).delete()
                    st.success("✅ Empleado eliminado correctamente")
                    st.rerun()
        else:
            st.info("⚠️ No hay empleados registrados. Agrega uno usando el formulario de arriba.")

    # ==================== SECCIÓN: TRABAJOS ADICIONALES (NO CONTEMPLADOS) ====================
    elif st.session_state.get("mostrar_trabajos_adicionales"):
        
        if st.button("← Volver al Panel Principal", use_container_width=False):
            st.session_state.mostrar_trabajos_adicionales = False
            st.rerun()
        
        st.header("🔧 Trabajos Adicionales (No Contemplados)")
        st.caption("Control de trabajos que no estaban en el presupuesto original")
        
        obras = cargar_obras()
        
        if not obras:
            st.warning("No hay obras disponibles.")
        else:
            # Tabs para gestión
            tab1, tab2, tab3 = st.tabs(["Agregar", "Ver Todos", "Resumen"])
            
            # TAB 1: AGREGAR NUEVO TRABAJO ADICIONAL
            with tab1:
                st.subheader("Registrar Nuevo Trabajo Adicional")
                
                col1, col2 = st.columns(2)
                with col1:
                    obra_sel = st.selectbox("Seleccionar Obra:", list(obras.values()), key="obra_trab_adic")
                    obra_codigo = [k for k, v in obras.items() if v == obra_sel][0]
                
                with col2:
                    st.write("")
                
                col1, col2 = st.columns(2)
                with col1:
                    descripcion = st.text_input("Descripción del trabajo", placeholder="ej: Cambio de muros vecino")
                with col2:
                    fecha_trab = st.date_input("Fecha del trabajo")
                
                col1, col2 = st.columns(2)
                with col1:
                    metrado = st.number_input("Metrado ejecutado", min_value=0.0, step=0.1)
                with col2:
                    unidad_trab = st.text_input("Unidad", placeholder="ej: M2, KG, UND")
                
                col1, col2 = st.columns(2)
                with col1:
                    costo_incurrido = st.number_input("Costo incurrido (S/.)", min_value=0.0, step=1.0)
                with col2:
                    precio_cobro = st.number_input("Precio a cobrar al cliente (S/.)", min_value=0.0, step=1.0)
                
                observaciones_trab = st.text_area("Observaciones o justificación del trabajo")
                
                if st.button("✅ Guardar Trabajo Adicional", use_container_width=True, type="primary"):
                    if not descripcion or not metrado or not costo_incurrido:
                        st.error("❌ Completa los campos obligatorios")
                    else:
                        trabajo_nuevo = {
                            "descripcion": descripcion,
                            "fecha": fecha_trab.isoformat(),
                            "metrado": metrado,
                            "unidad": unidad_trab,
                            "costo_incurrido": costo_incurrido,
                            "precio_cobro": precio_cobro if precio_cobro > 0 else costo_incurrido,
                            "estado": "Por cobrar",
                            "observaciones": observaciones_trab,
                            "ganancia": (precio_cobro if precio_cobro > 0 else costo_incurrido) - costo_incurrido
                        }
                        exito, msg = agregar_trabajo_adicional(obra_codigo, trabajo_nuevo)
                        if exito:
                            st.success("✅ Trabajo adicional registrado correctamente")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {msg}")
            
            # TAB 2: VER TODOS LOS TRABAJOS
            with tab2:
                st.subheader("Listado de Trabajos Adicionales")
                
                obra_sel_2 = st.selectbox("Filtrar por Obra:", ["Todas"] + list(obras.values()), key="obra_filtro_trab")
                
                if obra_sel_2 == "Todas":
                    trabajos_todos = []
                    for cod in obras.keys():
                        trabajos_todos.extend(obtener_trabajos_adicionales(cod))
                else:
                    obra_codigo_2 = [k for k, v in obras.items() if v == obra_sel_2][0]
                    trabajos_todos = obtener_trabajos_adicionales(obra_codigo_2)
                
                if not trabajos_todos:
                    st.info("📋 No hay trabajos adicionales registrados.")
                else:
                    for trabajo in trabajos_todos:
                        with st.expander(f"🔧 {trabajo['descripcion']} - {trabajo['estado']}", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.write(f"**Fecha:** {trabajo['fecha']}")
                                st.write(f"**Metrado:** {trabajo['metrado']} {trabajo['unidad']}")
                            
                            with col2:
                                st.write(f"**Costo Incurrido:** S/. {trabajo['costo_incurrido']:.2f}")
                                st.write(f"**Precio Cobro:** S/. {trabajo['precio_cobro']:.2f}")
                            
                            with col3:
                                ganancia = trabajo.get('ganancia', trabajo['precio_cobro'] - trabajo['costo_incurrido'])
                                st.write(f"**Ganancia:** S/. {ganancia:.2f}")
                                st.write(f"**Estado:** {trabajo['estado']}")
                            
                            if trabajo.get('observaciones'):
                                st.write(f"**Notas:** {trabajo['observaciones']}")
                            
                            # Acciones
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Marcar Aprobado", key=f"aprob_{trabajo['id']}", use_container_width=True):
                                    actualizar_trabajo_adicional(trabajo['id'], {"estado": "Aprobado"})
                                    st.success("Marcado como aprobado")
                                    st.rerun()
                            
                            with col2:
                                if st.button("💰 Marcar Cobrado", key=f"cobr_{trabajo['id']}", use_container_width=True):
                                    actualizar_trabajo_adicional(trabajo['id'], {"estado": "Cobrado"})
                                    st.success("Marcado como cobrado")
                                    st.rerun()
                            
                            with col3:
                                if st.button("🗑️ Eliminar", key=f"elim_{trabajo['id']}", use_container_width=True, type="secondary"):
                                    eliminar_trabajo_adicional(trabajo['id'])
                                    st.success("Trabajo eliminado")
                                    st.rerun()
            
            # TAB 3: RESUMEN DE TRABAJOS ADICIONALES
            with tab3:
                st.subheader("📊 Resumen Financiero")
                
                obra_sel_3 = st.selectbox("Seleccionar Obra:", list(obras.values()), key="obra_resumen_trab")
                obra_codigo_3 = [k for k, v in obras.items() if v == obra_sel_3][0]
                
                trabajos_resumen = obtener_trabajos_adicionales(obra_codigo_3)
                
                if not trabajos_resumen:
                    st.info("No hay trabajos adicionales para esta obra.")
                else:
                    # Cálculos
                    total_costo = sum([t['costo_incurrido'] for t in trabajos_resumen])
                    total_cobro = sum([t['precio_cobro'] for t in trabajos_resumen])
                    total_ganancia = total_cobro - total_costo
                    
                    cobrados = [t for t in trabajos_resumen if t['estado'] == 'Cobrado']
                    total_cobrado = sum([t['precio_cobro'] for t in cobrados])
                    
                    por_cobrar = [t for t in trabajos_resumen if t['estado'] != 'Cobrado']
                    total_por_cobrar = sum([t['precio_cobro'] for t in por_cobrar])
                    
                    # Métricas
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Costo", f"S/. {total_costo:.2f}", help="Costo total incurrido")
                    with col2:
                        st.metric("Total Cobro", f"S/. {total_cobro:.2f}", help="Total a cobrar al cliente")
                    with col3:
                        st.metric("Ganancia Total", f"S/. {total_ganancia:.2f}", help="Diferencia ganancia")
                    with col4:
                        if total_cobro > 0:
                            margen = (total_ganancia / total_cobro) * 100
                            st.metric("Margen %", f"{margen:.1f}%")
                    
                    st.divider()
                    
                    # Desglose por estado
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"🟢 **Cobrados:** {len(cobrados)}")
                        st.write(f"Monto: S/. {total_cobrado:.2f}")
                    with col2:
                        st.write(f"🟡 **Pendientes:** {len(por_cobrar)}")
                        st.write(f"Monto: S/. {total_por_cobrar:.2f}")
                    with col3:
                        st.write(f"📊 **Total Trabajos:** {len(trabajos_resumen)}")
                        st.write(f"Ganancia: S/. {total_ganancia:.2f}")
                    
                    # Tabla detallada
                    st.divider()
                    st.write("**Detalle de Trabajos Adicionales:**")
                    
                    df_trabajos = pd.DataFrame([{
                        "Descripción": t['descripcion'],
                        "Metrado": f"{t['metrado']} {t['unidad']}",
                        "Costo": f"S/. {t['costo_incurrido']:.2f}",
                        "Cobro": f"S/. {t['precio_cobro']:.2f}",
                        "Ganancia": f"S/. {t['precio_cobro'] - t['costo_incurrido']:.2f}",
                        "Estado": t['estado']
                    } for t in trabajos_resumen])
                    
                    st.dataframe(df_trabajos, use_container_width=True, hide_index=True)

    # ==================== SECCIÓN: VISTA DE OBRA SELECCIONADA ====================
    elif st.session_state.obra_seleccionada:
        obra_codigo = st.session_state.obra_seleccionada
        obra_nombre = obras.get(obra_codigo, "Obra no encontrada")

        st.header(f"{obra_nombre}")
        _render_pdf_panel()

        # ==================== BOTONES DE GESTIÓN POR OBRA ====================
        col_empl, col_sep = st.columns([1, 5])
        
        with col_empl:
            if st.button("👷 Gestión de Empleados", use_container_width=True, key="btn_empleados_obra"):
                st.session_state.mostrar_empleados_obra = True
                st.rerun()

        # ==================== VISTA DE EMPLEADOS DE LA OBRA ====================
        if st.session_state.get("mostrar_empleados_obra"):
            if st.button("← Volver", use_container_width=False, key="volver_empleados_obra"):
                st.session_state.mostrar_empleados_obra = False
                st.rerun()
            
            st.subheader("👷 Gestión de Empleados - " + obra_nombre)
            
            empleados = []
            try:
                docs = db.collection("empleados").where("codigo_obra", "==", obra_codigo).stream()
                empleados = [{"id": doc.id, **doc.to_dict()} for doc in docs]
            except Exception:
                empleados = []
            
            tab_empl1, tab_empl2 = st.tabs(["Agregar", "Listar"])
            
            with tab_empl1:
                st.write("**Agregar Nuevo Empleado**")
                nombre_emp = st.text_input("Nombre", placeholder="Juan Pérez", key="nombre_emp_obra")
                cargo_emp = st.text_input("Cargo", placeholder="Albañil, Ayudante", key="cargo_emp_obra")
                dni_emp = st.text_input("DNI", placeholder="12345678", key="dni_emp_obra")
                jornal_emp = st.number_input("Jornal Diario (S/.)", min_value=0.0, step=10.0, key="jornal_emp_obra")
                
                if st.button("✅ Agregar", use_container_width=True, type="primary", key="btn_agregar_emp_obra"):
                    if not nombre_emp or not cargo_emp or not dni_emp or jornal_emp <= 0:
                        st.error("❌ Completa todos los campos")
                    else:
                        emp_data = {
                            "codigo_obra": obra_codigo,
                            "nombre": nombre_emp,
                            "cargo": cargo_emp,
                            "dni": dni_emp,
                            "jornal_diario": jornal_emp
                        }
                        db.collection("empleados").add(emp_data)
                        st.success("✅ Empleado agregado")
                        st.rerun()
            
            with tab_empl2:
                st.write("**Empleados de la Obra**")
                if empleados:
                    for emp in empleados:
                        st.write(f"👤 {emp['nombre']} - {emp['cargo']} (DNI: {emp['dni']}) - S/. {emp['jornal_diario']:.2f}/día")
                else:
                    st.info("No hay empleados.")
            
            st.divider()

        # ==================== PANEL NORMAL DE LA OBRA ====================
        if not st.session_state.get("mostrar_empleados_obra"):

            presupuesto = obtener_presupuesto_obra(obra_codigo)
        else:
            presupuesto = {}

        avances = obtener_avances_obra(obra_codigo)
        donaciones_obra = obtener_donaciones_obra(obra_codigo)
        impacto_don = impacto_donacion_en_presupuesto(presupuesto, donaciones_obra)
        presupuesto_ampliado = impacto_don["presupuesto_ampliado"]
        resumen = calcular_resumen_presupuesto(presupuesto_ampliado, avances)

        st.markdown("### 💰 Resumen de Presupuesto")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            delta_don = f"+S/. {impacto_don['total_donaciones']:,.2f}" if impacto_don["total_donaciones"] > 0 else None
            st.metric(
                "Presupuestado",
                f"S/. {resumen['presupuestado']:,.2f}",
                delta=delta_don,
                help="Presupuesto total (incluye donaciones)"
            )

        with col2:
            st.metric(
                "Gastado",
                f"S/. {resumen['gastado']:,.2f}",
                delta=f"{resumen['porcentaje_gastado']:.1f}%",
                delta_color="inverse",
                help="Total acumulado de gastos ejecutados"
            )

        with col3:
            st.metric("Disponible", f"S/. {resumen['disponible']:,.2f}", help="Presupuesto restante")

        with col4:
            porcentaje = resumen['porcentaje_gastado']
            if porcentaje < 50:
                estado = "🟢 Saludable"
            elif porcentaje < 80:
                estado = "🟡 Moderado"
            elif porcentaje < 100:
                estado = "🟠 Crítico"
            else:
                estado = "🔴 Excedido"
            st.metric("Estado", estado, help="Estado del presupuesto según el porcentaje gastado")

        with col5:
            st.metric(
                "Donaciones",
                f"S/. {impacto_don['total_donaciones']:,.2f}",
                help="Total de donaciones registradas"
            )

        st.progress(min(resumen['porcentaje_gastado'] / 100, 1.0))

        st.divider()

        eficiencia_promedio = calcular_eficiencia_promedio_obra(avances)
        emoji_rendimiento, texto_rendimiento, _ = obtener_estado_rendimiento(eficiencia_promedio)

        st.markdown("### 📊 Rendimiento de Mano de Obra")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Eficiencia Promedio", f"{eficiencia_promedio:.1f}%", help="Promedio de eficiencias de partes diarios")

        with col2:
            st.metric("Estado", f"{emoji_rendimiento} {texto_rendimiento}", help="Verde: ≥100% | Ámbar: 80-99% | Rojo: <80%")

        with col3:
            if eficiencia_promedio >= 100:
                st.metric("Superávit", f"+{(eficiencia_promedio - 100):.1f}%")
            else:
                st.metric("Déficit", f"-{(100 - eficiencia_promedio):.1f}%")

        with col4:
            if eficiencia_promedio >= 100:
                recomendacion = "✅ Mantener"
            elif eficiencia_promedio >= 80:
                recomendacion = "⚠️ Supervisar"
            else:
                recomendacion = "🚨 Evaluar"
            st.metric("Acción", recomendacion)

        if eficiencia_promedio > 0:
            st.progress(min(eficiencia_promedio / 100, 1.0))

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Parte Diario", "Historial de Avances", "Cronograma Valorizado", "Caja Chica", "Donaciones"])

        st.divider()

        # ==================== TAB 1: PARTE DIARIO (JEFE) ====================
        with tab1:
            st.subheader("Parte Diario del Día")
            hoy = date.today()

            if "form_parte_diario_counter" not in st.session_state:
                st.session_state.form_parte_diario_counter = 0

            if "insumos_mo_confirmados" not in st.session_state:
                st.session_state.insumos_mo_confirmados = []
            if "insumos_mat_confirmados" not in st.session_state:
                st.session_state.insumos_mat_confirmados = []

            counter = st.session_state.form_parte_diario_counter

            st.markdown("### Información General")
            col1, col2 = st.columns(2)
            with col1:
                nombre_default = st.session_state.get("usuario_logueado", "Usuario")
                responsable = st.text_input("Tu nombre", value=nombre_default, key=f"responsable_input_{counter}")
            with col2:
                avance = st.slider("Avance logrado hoy (%)", 0, 30, 5, key=f"avance_input_{counter}")

            col1, col2 = st.columns(2)
            with col1:
                name_partida = st.text_input(
                    "Nombre de la partida o actividad realizada hoy",
                    placeholder="ej: Cimentación, Estructura, Albañilería, etc.",
                    key=f"name_partida_input_{counter}"
                )
            with col2:
                col1b, col2b = st.columns(2)
                with col1b:
                    cantidad_ejecutada = st.number_input(
                        "Metrado Ejecutado",
                        min_value=0.0,
                        step=0.1,
                        placeholder="Ingresa la cantidad realizada",
                        key=f"cantidad_ejecutada_{counter}"
                    )
                with col2b:
                    unidad_medida = st.text_input(
                        "Unidad",
                        placeholder="ej: M3, KG, UND, HH",
                        key=f"unidad_input_{counter}"
                    )

            col1, col2 = st.columns(2)
            with col1:
                horas_mano_obra = st.number_input("Jornada Laboral (h)", min_value=0, step=1, value=8, key=f"horas_input_{counter}")
            with col2:
                rendimiento_partida = st.number_input(
                    "Rendimiento Esperado de la Partida (por día)",
                    min_value=0.0,
                    step=0.1,
                    value=6.0,
                    help="Rendimiento en unidad/día. Se ajusta proporcionalmente si la jornada no es de 8 horas.",
                    key=f"rendimiento_input_{counter}"
                )

            st.markdown("### Costos")

            # Cargar empleados
            empleados_docs = db.collection("empleados").stream()
            empleados = [{"id": d.id, **d.to_dict()} for d in empleados_docs]

            tab_mo, tab_insumos = st.tabs(["Mano de Obra", "Materiales"])

            with tab_mo:
                st.markdown("#### Ingresar Mano de Obra")
                
                if not empleados:
                    st.warning("⚠️ No hay empleados registrados. Ve a 'Gestión de Empleados' para agregar trabajadores.")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        nombres_empleados = [f"{e['nombre']} - {e['cargo']}" for e in empleados]
                        empleado_seleccionado = st.selectbox(
                            "Seleccionar Empleado",
                            nombres_empleados,
                            key="empleado_mo"
                        )
                        idx_emp = nombres_empleados.index(empleado_seleccionado)
                        empleado_data = empleados[idx_emp]
                    with col2:
                        sueldo_dia = st.number_input(
                            "Sueldo del Día (S/.)",
                            min_value=0.0,
                            step=10.0,
                            value=80.0,
                            format="%.2f",
                            key="sueldo_mo"
                        )

                    if st.button("Confirmar Mano de Obra", use_container_width=True, type="primary", key="btn_confirmar_mo"):
                        if sueldo_dia <= 0:
                            st.error("❌ El sueldo del día debe ser mayor a 0")
                        else:
                            item = {
                                "Empleado": empleado_data['nombre'],
                                "Cargo": empleado_data['cargo'],
                                "DNI": empleado_data['dni'],
                                "Sueldo del Día": sueldo_dia,
                                "Parcial (S/)": sueldo_dia
                            }
                            st.session_state.insumos_mo_confirmados.append(item)
                            st.success(f"✓ {empleado_data['nombre']} agregado")
                            st.rerun()

            with tab_insumos:
                st.markdown("#### Ingresar Material")
                col1, col2, col3 = st.columns(3)
                with col1:
                    desc_insumo = st.text_input("Descripción", placeholder="ej: Cemento, Alquiler Mezcladora, etc.", key="desc_insumo")
                with col2:
                    cant_insumo = st.number_input("Cantidad", min_value=0.0, step=0.01, format="%.4f", key="cant_insumo")
                with col3:
                    precio_insumo = st.number_input("Precio Unit. (S/.)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key="precio_insumo")

                if st.button("Confirmar Material", use_container_width=True, type="primary", key="btn_confirmar_insumo"):
                    if rendimiento_partida <= 0:
                        st.error("❌ El rendimiento de la partida debe ser mayor a 0")
                    elif not unidad_medida.strip():
                        st.error("❌ Debes especificar la unidad de medida")
                    elif cant_insumo <= 0:
                        st.error("❌ La cantidad debe ser mayor a 0")
                    elif not desc_insumo.strip():
                        st.error("❌ Debes ingresar una descripción")
                    elif precio_insumo <= 0:
                        st.error("❌ El precio debe ser mayor a 0")
                    else:
                        parcial_insumo = calcular_parcial(cant_insumo, precio_insumo)
                        item = {
                            "Descripción": desc_insumo,
                            "Cantidad": cant_insumo,
                            "Precio Unit.": precio_insumo,
                            "Parcial (S/)": parcial_insumo
                        }
                        st.session_state.insumos_mat_confirmados.append(item)
                        st.success(f"✓ {desc_insumo} agregado")
                        st.rerun()

            # Listas confirmadas
            if st.session_state.insumos_mo_confirmados:
                st.markdown("#### Mano de Obra Confirmada")
                st.dataframe(pd.DataFrame(st.session_state.insumos_mo_confirmados), use_container_width=True, hide_index=True)
                if st.button("🗑️ Limpiar Mano de Obra", key="limpiar_mo"):
                    st.session_state.insumos_mo_confirmados = []
                    st.rerun()

            if st.session_state.insumos_mat_confirmados:
                st.markdown("#### Materiales Confirmados")
                st.dataframe(pd.DataFrame(st.session_state.insumos_mat_confirmados), use_container_width=True, hide_index=True)
                if st.button("🗑️ Limpiar Materiales", key="limpiar_insumos"):
                    st.session_state.insumos_mat_confirmados = []
                    st.rerun()

            st.markdown("### 📊 Resumen de Costos Consolidado")
            total_mo = sum([item["Parcial (S/)"] for item in st.session_state.insumos_mo_confirmados])
            total_insumos = sum([item["Parcial (S/)"] for item in st.session_state.insumos_mat_confirmados])
            total_general = total_mo + total_insumos

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mano de Obra", f"S/. {total_mo:.2f}")
            with col2:
                st.metric("Materiales", f"S/. {total_insumos:.2f}")
            with col3:
                st.metric("💰 TOTAL", f"S/. {total_general:.2f}", delta_color="normal")

            st.markdown("### Finalizar Parte Diario")
            obs = st.text_area("Observaciones", key=f"obs_final_{counter}")
            fotos = st.file_uploader("Fotos del avance", accept_multiple_files=True, type=["jpg", "png", "jpeg"], key=f"fotos_final_{counter}")

            st.session_state["cantidad_ejecutada_cache"] = cantidad_ejecutada
            st.session_state["unidad_medida_cache"] = unidad_medida
            st.session_state["total_general_cache"] = total_general

            if 0 < len(fotos) < 3:
                st.warning("⚠️ Debes subir mínimo 3 fotos")

            @st.dialog("Confirmar Envío de Parte Diario")
            def confirmar_envio_modal():

                st.warning("⚠️ ¿Estás seguro de enviar el parte diario?")
                st.write("Esta acción guardará el registro y limpiará todos los campos.")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button(
                        "✅ SÍ, ENVIAR",
                        use_container_width=True,
                        type="primary",
                        key="si_enviar_jefe"
                    ):
                        #  Seguridad: valores por defecto
                        cantidad_ejecutada_cache = st.session_state.get("cantidad_ejecutada_cache", 0)
                        total_general_cache = st.session_state.get("total_general_cache", 0)

                        totales = calcular_totales_costos(
                            st.session_state.insumos_mo_confirmados,
                            st.session_state.insumos_mat_confirmados,
                            [],
                            [],
                            cantidad_ejecutada=1  # Ya no se multiplica, total directo
                        )
                        
                        # Sobrescribir total_general_ejecutado con el total real
                        totales["total_general_ejecutado"] = total_general_cache

                        rutas_fotos = guardar_fotos_avance(obra_codigo, fotos, hoy)

                        nuevo_avance = crear_avance_dict(
                            fecha=hoy,
                            responsable=responsable,
                            avance_pct=avance,
                            observaciones=obs,
                            rutas_fotos=rutas_fotos,
                            nombre_partida=name_partida,
                            rendimiento_partida=rendimiento_partida,
                            unidad_medida=st.session_state.get("unidad_medida_cache", unidad_medida),
                            horas_mano_obra=horas_mano_obra,
                            cantidad_ejecutada=cantidad_ejecutada_cache,
                            insumos_mo=st.session_state.insumos_mo_confirmados,
                            insumos_mat=st.session_state.insumos_mat_confirmados,
                            insumos_eq=[],
                            insumos_otros=[],
                            totales=totales
                        )

                        exito, mensaje_db = agregar_avance(obra_codigo, nuevo_avance)
                        if not exito:
                            st.error(f"❌ Error al guardar: {mensaje_db}")
                            return

                        # ==========================
                        # 🧠 GUARDAR PARA WHATSAPP
                        # ==========================
                        st.session_state.temp_nuevo_avance = nuevo_avance
                        st.session_state.temp_obra_nombre = obra_nombre
                        st.session_state.abrir_whatsapp_modal = True

                        # ==========================
                        # 📄 TU PDF (INTACTO)
                        # ==========================
                        st.session_state.show_pdf_panel = True
                        st.session_state.pdf_meta = {
                            "obra_codigo": obra_codigo,
                            "obra_nombre": obra_nombre,
                            "rol": "jefe"
                        }
                        st.session_state.pdf_avance = nuevo_avance
                        st.session_state.pdf_bytes = None

                        # 🧹 LIMPIEZA ORIGINAL
                        # ==========================
                        st.session_state.insumos_mo_confirmados = []
                        st.session_state.insumos_mat_confirmados = []
                        st.session_state.form_parte_diario_counter += 1
                        st.session_state.parte_enviado = True

                        st.success("✅ ¡Parte diario enviado correctamente!")
                        st.balloons()
                        st.rerun()

                with c2:
                    if st.button("❌ CANCELAR", use_container_width=True, type="secondary"):
                        st.rerun()


            @st.dialog("Notificar por WhatsApp")
            def whatsapp_modal():
                PAISES_WHATSAPP = {
                    " Perú (+51)": "51",
                    " Chile (+56)": "56",
                    " México (+52)": "52",
                    " Argentina (+54)": "54",
                    " Colombia (+57)": "57",
                    " Brasil (+55)": "55",
                    " España (+34)": "34",
                }

                LONGITUD_NUMERO = {
                    " Perú (+51)": 9,
                    " Chile (+56)": 9,
                    " México (+52)": 10,
                    " Argentina (+54)": 10,
                    " Colombia (+57)": 10,
                    " Brasil (+55)": 11,
                    " España (+34)": 9,
                }

                c1, c2 = st.columns([1, 2])

                with c1:
                    opciones_paises = list(PAISES_WHATSAPP.keys())
                    pais_seleccionado = st.selectbox(
                        "🌍 País",
                        options=opciones_paises,
                        index=opciones_paises.index(
                            st.session_state.get("whatsapp_pais", " Perú (+51)")
                        )
                    )
                st.session_state.whatsapp_pais = pais_seleccionado
                
                with c2:
                    numero_local = st.text_input(
                        "📱 Número",
                        placeholder="Ej: 958555917"
                    )

                nuevo_avance = st.session_state.get("temp_nuevo_avance", {})
                obra_nombre = st.session_state.get("temp_obra_nombre", "")
                fecha = nuevo_avance.get("fecha")
                avance_pct = nuevo_avance.get("avance", 0)
                totales = nuevo_avance.get("totales", {})

                st.success("📱 Notificación por WhatsApp")

                import re

                codigo_pais = PAISES_WHATSAPP[pais_seleccionado]
                numero_local_limpio = re.sub(r"\D", "", numero_local)

                longitud_esperada = LONGITUD_NUMERO.get(pais_seleccionado)
                longitud_actual = len(numero_local_limpio)

                if longitud_actual > 0 and longitud_actual != longitud_esperada:
                    st.warning(
                        f"⚠️ El número para {pais_seleccionado} debe tener "
                        f"{longitud_esperada} dígitos"
                    )
                    st.stop()

                # 👇 CAMPO PARA OBSERVACIONES (ÚNICO)
                observaciones_whatsapp = st.text_area(
                    "📝 Observaciones para WhatsApp",
                    value=st.session_state.get("whatsapp_obs", ""),
                    placeholder="Escribe aquí las observaciones que deseas enviar por WhatsApp...",
                    help="Estas observaciones se incluirán en el mensaje de WhatsApp"
                )

                numero_whatsapp_final = f"{codigo_pais}{numero_local_limpio}"
                st.session_state.whatsapp_obs = observaciones_whatsapp

                # ==========================
                # CONSTRUCCIÓN DEL MENSAJE
                # ==========================
                mensaje = (
                    f"*Parte Diario Enviado*\n\n"
                    f"*Obra:* {obra_nombre}\n"
                    f"*Fecha:* {fecha}\n"
                    f"*Avance:* {avance_pct}%\n"
                    f"*Total Ejecutado:* S/. {float(totales.get('total_general_ejecutado', 0) or 0):,.2f}"
                )

                #  AGREGAR OBSERVACIONES SI HAY
                if observaciones_whatsapp and observaciones_whatsapp.strip():
                    mensaje += f"\n\n*Observaciones:*\n{observaciones_whatsapp.strip()}"

                # ==========================
                # UI
                # ==========================
                if not st.session_state.get("whatsapp_enviado", False):
                    if numero_local_limpio:
                        import urllib.parse
                        mensaje_encoded = urllib.parse.quote(mensaje)
                        url_whatsapp = f"https://wa.me/{numero_whatsapp_final}?text={mensaje_encoded}"

                        st.caption(f"📞 Se enviará a: {numero_whatsapp_final}")
                        
                        # 👇 VISTA PREVIA DEL MENSAJE
                        with st.expander("📄 Vista previa del mensaje"):
                            st.text(mensaje)

                        st.link_button(
                            "📱 Enviar Notificación por WhatsApp",
                            url_whatsapp,
                            use_container_width=True,
                            type="primary"
                        )

                        if st.button("❌ Cerrar", use_container_width=True):
                            st.session_state.abrir_whatsapp_modal = False
                            st.session_state.whatsapp_enviado = True
                            st.rerun()
                    else:
                        st.warning("⚠️ Ingresa un número de WhatsApp para continuar")
                else:
                    st.success("✅ Notificación enviada por WhatsApp")



            # Verificar si ya se envió el parte diario (evitar doble envío)
            # BOTÓN ENVIAR PARTE DIARIO

            if st.session_state.get("parte_enviado"):
                st.info("✅ Parte diario ya enviado. Usa los botones de arriba para descargar PDF o enviar WhatsApp.")

                if st.button("🔄 Limpiar y crear nuevo parte diario", use_container_width=True):
                    st.session_state.parte_enviado = False
                    st.session_state.show_pdf_panel = False
                    st.session_state.pdf_meta = {}
                    st.session_state.pdf_avance = {}
                    st.session_state.pdf_bytes = None
                    st.rerun()

            else:
                if st.button(
                    "📤 ENVIAR PARTE DIARIO",
                    use_container_width=True,
                    type="primary",
                    key="enviar_final"
                ):

                    es_valido, errores = validar_parte_diario_completo(
                        responsable, avance, rendimiento_partida, unidad_medida, fotos
                    )

                    costos_validos, mensaje_costos = validar_costos_parte_diario(
                        st.session_state.insumos_mo_confirmados,
                        st.session_state.insumos_mat_confirmados,
                        [],
                        []
                    )

                    if not es_valido:
                        for error in errores:
                            st.error(f"❌ {error}")

                    elif not costos_validos:
                        st.error(f"❌ {mensaje_costos}")

                    else:
                        confirmar_envio_modal()


            # ===============================
            # 🚨 PARTE 3 – CONTROLADOR WHATSAPP
            # ===============================

            if st.session_state.get("abrir_whatsapp_modal", False):
                whatsapp_modal()

        # ==================== TAB 2: HISTORIAL DE AVANCES (JEFE) ====================
        with tab2:
            st.subheader("Historial de Avances")
            historial = preparar_historial_avances(obra_codigo)

            if historial:
                for item in historial:
                    with st.expander(f"📅 {item['fecha_fmt']} - {item['responsable']} ({item['avance_pct']}%)"):
                        st.markdown("### Información General")
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.write("**Responsable:**", item["responsable"])
                            st.write("**Avance del día:**", f"{item['avance_pct']}%")
                        with c2:
                            partida = item.get("partida", {})
                            if isinstance(partida, dict):
                                st.write(f"**Partida:** {partida.get('nombre', 'N/A')}")
                                st.write(f"**Rendimiento:** {partida.get('rendimiento', 0):.2f} {partida.get('unidad', '')}/día")
                        with c3:
                            partida = item.get("partida", {})
                            if isinstance(partida, dict):
                                st.write(f"**Cantidad Ejecutada:** {partida.get('cantidad_ejecutada', 0):.2f} {partida.get('unidad', '')}")
                                st.write(f"**Jornal:** {partida.get('jornal_horas', 0)} horas")

                        partida = item.get("partida", {})
                        if isinstance(partida, dict):
                            cant = partida.get("cantidad_ejecutada", 0)
                            rend = partida.get("rendimiento", 0)
                            hrs = partida.get("jornal_horas", 0)
                            if rend > 0 and hrs > 0 and cant > 0:
                                eff = calcular_eficiencia_rendimiento(cant, rend, hrs)
                                emoji, texto, _ = obtener_estado_rendimiento(eff)
                                st.markdown("---")
                                st.markdown(f"### {emoji} Eficiencia de Rendimiento: {eff:.1f}%")

                        costos = item.get("costos", {})
                        totales = item.get("totales", {})

                        if costos and any(costos.values()):
                            st.markdown("### Costos del Día")
                            if costos.get("mano_de_obra"):
                                st.markdown("#### Mano de Obra")
                                st.dataframe(pd.DataFrame(costos["mano_de_obra"]), use_container_width=True, hide_index=True)
                            if costos.get("materiales"):
                                st.markdown("#### Materiales")
                                st.dataframe(pd.DataFrame(costos["materiales"]), use_container_width=True, hide_index=True)

                            if totales:
                                total_mo = float(totales.get('mano_de_obra', 0) or 0)
                                total_mat = float(totales.get('materiales', 0) or 0)
                                total_general = total_mo + total_mat
                                st.markdown("#### Resumen de Totales")
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    st.metric("Mano de Obra", f"S/. {total_mo:.2f}")
                                with c2:
                                    st.metric("Materiales", f"S/. {total_mat:.2f}")
                                with c3:
                                    st.metric("💰 TOTAL", f"S/. {total_general:.2f}")

                        if item.get("obs"):
                            st.markdown("### 📝 Observaciones")
                            st.write(item["obs"])

                        if item.get("fotos"):
                            st.markdown("### 📷 Fotos del avance")
                            cols = st.columns(min(len(item["fotos"]), 3))
                            for i, foto_path in enumerate(item["fotos"]):
                                target = cols[i % 3]
                                try:
                                    # Verificar si es URL de Cloudinary
                                    if str(foto_path).startswith("http://") or str(foto_path).startswith("https://"):
                                        # Es una URL de Cloudinary, mostrar directamente
                                        target.image(foto_path, use_container_width=True)
                                    elif foto_path and os.path.exists(foto_path):
                                        # Es ruta local
                                        target.image(foto_path, caption=os.path.basename(foto_path))
                                    else:
                                        target.warning(f"No se encontró la imagen: {os.path.basename(foto_path) if foto_path else 'Archivo no especificado'}")
                                except Exception:
                                    target.error("Error al cargar foto")
            else:
                st.info("No hay partes diarios registrados para esta obra aún.")

        # ==================== TAB 3: CRONOGRAMA VALORIZADO (JEFE) ====================
        with tab3:
            st.markdown("## 📊 Cronograma Valorizado y Control de Avance")
            st.caption("Gestiona el cronograma de la obra, visualiza la Curva S y controla los hitos de pago")

            # Cargar datos
            cronograma_all = obtener_cronograma_obra(obra_codigo) or []
            hitos = obtener_hitos_pago_obra(obra_codigo) or []

            for it in cronograma_all:
                it.setdefault("estado", "Aprobado")
                it.setdefault("creado_por", "jefe")
            for h in hitos:
                h.setdefault("estado", "Pendiente")
                h.setdefault("creado_por", "jefe")

            cronograma_aprob = [it for it in cronograma_all if it.get("estado") == "Aprobado"]
            resumen_crono = calcular_resumen_cronograma(cronograma_aprob, avances)

            # ========== RESUMEN EJECUTIVO ==========
            st.markdown("### 📈 Resumen Ejecutivo del Proyecto")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "💰 Plan Total",
                    f"S/. {resumen_crono['pv_total']:,.2f}",
                    help="Monto total planificado del cronograma"
                )
            with col2:
                delta_ac = resumen_crono['ac_total'] - resumen_crono['pv_total']
                st.metric(
                    "💵 Real Ejecutado",
                    f"S/. {resumen_crono['ac_total']:,.2f}",
                    delta=f"S/. {delta_ac:,.2f}",
                    delta_color="inverse" if delta_ac > 0 else "normal",
                    help="Monto total ejecutado hasta la fecha"
                )
            with col3:
                porc_avance = (resumen_crono['ac_total'] / resumen_crono['pv_total'] * 100) if resumen_crono['pv_total'] > 0 else 0
                st.metric(
                    "📊 Avance Físico",
                    f"{porc_avance:.1f}%",
                    help="Porcentaje de avance del proyecto"
                )
            with col4:
                spi = resumen_crono.get("spi", 0)
                if spi == 0:
                    estado_txt = "⚪ Sin datos"
                    estado_color = "off"
                elif spi <= 0.95:
                    estado_txt = "🟢 En control"
                    estado_color = "normal"
                elif spi <= 1.05:
                    estado_txt = "🟡 Atención"
                    estado_color = "off"
                else:
                    estado_txt = "🔴 Sobrecosto"
                    estado_color = "inverse"
                
                st.metric(
                    "Estado del Proyecto",
                    estado_txt,
                    delta=f"Índice: {spi:.2f}" if spi > 0 else None,
                    delta_color=estado_color,
                    help="Verde: ≤0.95 | Amarillo: 0.96-1.05 | Rojo: >1.05"
                )

            # Barra de progreso
            if resumen_crono['pv_total'] > 0:
                progress_val = min(resumen_crono['ac_total'] / resumen_crono['pv_total'], 1.0)
                st.progress(progress_val)
                st.caption(f"Avance: S/. {resumen_crono['ac_total']:,.2f} de S/. {resumen_crono['pv_total']:,.2f}")

            st.divider()

            # ========== PESTAÑAS PARA ORGANIZAR CONTENIDO ==========
            tab_partidas, tab_curva, tab_hitos = st.tabs([
                "📋 Partidas del Cronograma",
                "📈 Curva S (Plan vs Real)",
                "💰 Hitos de Pago",
            ])

            # ===== TAB: PARTIDAS =====
            with tab_partidas:
                st.markdown("### Gestión de Partidas del Cronograma")
                
                # Mostrar solicitudes pendientes si las hay
                pendientes = [p for p in cronograma_all if p.get("estado") == "Pendiente"]
                if pendientes:
                    st.warning(f"⚠️ Tienes **{len(pendientes)}** solicitud(es) pendiente(s) de aprobación del pasante")
                    
                    with st.expander(f"🔔 Ver {len(pendientes)} Solicitud(es) Pendiente(s)", expanded=True):
                        for i, pend in enumerate(pendientes):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.markdown(f"**{pend.get('nombre', 'Sin nombre')}**")
                                st.caption(f"📅 {pend.get('fecha_inicio')} → {pend.get('fecha_fin')} | S/. {float(pend.get('monto_planificado', 0)):,.2f}")
                                if pend.get('descripcion'):
                                    st.caption(f"📝 {pend.get('descripcion')}")
                                st.caption(f"👤 Solicitado por: {pend.get('creado_por', 'desconocido')}")
                            with col2:
                                if st.button("✅ Aprobar", key=f"aprobar_pend_{i}", use_container_width=True, type="primary"):
                                    payload = dict(pend)
                                    payload["estado"] = "Aprobado"
                                    ok, msg = actualizar_partida_cronograma(obra_codigo, pend.get("id"), payload)
                                    if ok:
                                        st.success("✅ Partida aprobada")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {msg}")
                            with col3:
                                if st.button("❌ Rechazar", key=f"rechazar_pend_{i}", use_container_width=True):
                                    ok, msg = eliminar_partida_cronograma(obra_codigo, pend.get("id"))
                                    if ok:
                                        st.success("✅ Solicitud rechazada")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {msg}")
                            st.divider()

                st.markdown("#### ➕ Agregar Nueva Partida")
                
                if "form_crono_counter" not in st.session_state:
                    st.session_state.form_crono_counter = 0

                with st.form(key=f"form_add_crono_{st.session_state.form_crono_counter}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        crono_nombre = st.text_input("📋 Nombre de la Partida*", placeholder="Ej: Cimentación, Acabados, Instalaciones Eléctricas")
                    with c2:
                        crono_monto = st.number_input("💵 Monto Planificado (S/.)*", min_value=0.0, step=100.0, format="%.2f")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        crono_inicio = st.date_input("📅 Fecha de Inicio*", value=date.today())
                    with c2:
                        crono_fin = st.date_input("📅 Fecha de Fin*", value=date.today())

                    crono_desc = st.text_area("📝 Descripción (opcional)", placeholder="Detalles adicionales sobre la partida...", height=80)

                    if st.form_submit_button("✅ Agregar Partida (Aprobado)", use_container_width=True, type="primary"):
                        ok, msg = validar_partida_cronograma(crono_nombre, crono_inicio, crono_fin, crono_monto)
                        if not ok:
                            st.error(f"❌ {msg}")
                        else:
                            partida = {
                                "nombre": crono_nombre.strip(),
                                "fecha_inicio": str(crono_inicio),
                                "fecha_fin": str(crono_fin),
                                "monto_planificado": float(crono_monto),
                                "descripcion": crono_desc.strip(),
                                "estado": "Aprobado",
                                "creado_por": st.session_state.get("usuario_logueado", "jefe"),
                            }
                            ok2, msg2 = agregar_partida_cronograma(obra_codigo, partida)
                            if ok2:
                                st.success("✅ Partida agregada correctamente")
                                st.session_state.form_crono_counter += 1
                                st.rerun()
                            else:
                                st.error(f"❌ {msg2}")

                st.divider()

                # Lista de partidas
                cronograma_all = obtener_cronograma_obra(obra_codigo) or []
                for it in cronograma_all:
                    it.setdefault("estado", "Aprobado")
                    it.setdefault("creado_por", "jefe")

                if not cronograma_all:
                    st.info("📭 No hay partidas registradas. Agrega la primera partida para comenzar tu cronograma.")
                else:
                    st.markdown(f"#### 📊 Listado de Partidas ({len(cronograma_all)} total)")
                    
                    # Filtros
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        filtro_estado = st.selectbox(
                            "Filtrar por estado:",
                            ["Todos", "Aprobado", "Pendiente"],
                            key="filtro_estado_partidas"
                        )
                    
                    partidas_filtradas = cronograma_all if filtro_estado == "Todos" else [p for p in cronograma_all if p.get("estado") == filtro_estado]
                    
                    # Tabla de partidas
                    dfc = pd.DataFrame(partidas_filtradas)
                    if not dfc.empty:
                        cols_mostrar = ["nombre", "fecha_inicio", "fecha_fin", "monto_planificado", "estado", "creado_por"]
                        cols_existentes = [c for c in cols_mostrar if c in dfc.columns]
                        
                        st.dataframe(
                            dfc[cols_existentes].rename(columns={
                                "nombre": "Partida",
                                "fecha_inicio": "Inicio",
                                "fecha_fin": "Fin",
                                "monto_planificado": "Monto (S/.)",
                                "estado": "Estado",
                                "creado_por": "Creado por",
                            }),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Monto (S/.)": st.column_config.NumberColumn(format="S/. %.2f")
                            }
                        )
                    
                    st.markdown("#### ✏️ Editar / Eliminar Partida")
                    
                    if "idx_partida_crono" not in st.session_state:
                        st.session_state.idx_partida_crono = 0

                    opciones = [
                        f"{it.get('nombre', '(sin nombre)')} - S/. {float(it.get('monto_planificado', 0) or 0):,.2f} [{it.get('estado', 'Aprobado')}]"
                        for it in cronograma_all
                    ]

                    sel = st.selectbox(
                        "Selecciona una partida para editar:",
                        opciones,
                        index=min(st.session_state.idx_partida_crono, len(opciones) - 1),
                        key="sel_partida_crono"
                    )
                    st.session_state.idx_partida_crono = opciones.index(sel)

                    partida_sel = cronograma_all[st.session_state.idx_partida_crono]
                    partida_id = partida_sel.get("id")

                    with st.form("form_edit_crono"):
                        c1, c2 = st.columns(2)
                        with c1:
                            n_nombre = st.text_input("Nombre", value=partida_sel.get("nombre", ""))
                        with c2:
                            n_monto = st.number_input(
                                "Monto (S/.)",
                                min_value=0.0,
                                step=100.0,
                                format="%.2f",
                                value=float(partida_sel.get("monto_planificado", 0.0) or 0.0)
                            )
                        
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            n_inicio = st.date_input("Inicio", value=pd.to_datetime(partida_sel.get("fecha_inicio", date.today())).date())
                        with c2:
                            n_fin = st.date_input("Fin", value=pd.to_datetime(partida_sel.get("fecha_fin", date.today())).date())
                        with c3:
                            n_estado = st.selectbox(
                                "Estado",
                                ["Pendiente", "Aprobado"],
                                index=0 if partida_sel.get("estado") == "Pendiente" else 1
                            )

                        n_desc = st.text_area("Descripción", value=partida_sel.get("descripcion", ""), height=80)

                        colx, coly = st.columns(2)
                        with colx:
                            guardar = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")
                        with coly:
                            eliminar = st.form_submit_button("🗑️ Eliminar Partida", use_container_width=True)

                    if guardar:
                        ok, msg = validar_partida_cronograma(n_nombre, n_inicio, n_fin, n_monto)
                        if not ok:
                            st.error(f"❌ {msg}")
                        else:
                            payload = {
                                "nombre": n_nombre.strip(),
                                "fecha_inicio": str(n_inicio),
                                "fecha_fin": str(n_fin),
                                "monto_planificado": float(n_monto),
                                "descripcion": n_desc.strip(),
                                "estado": n_estado,
                                "creado_por": partida_sel.get("creado_por", "jefe"),
                            }
                            ok2, msg2 = actualizar_partida_cronograma(obra_codigo, partida_id, payload)
                            if ok2:
                                st.success("✅ Partida actualizada correctamente")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg2}")

                    if eliminar:
                        ok3, msg3 = eliminar_partida_cronograma(obra_codigo, partida_id)
                        if ok3:
                            st.success("✅ Partida eliminada correctamente")
                            st.session_state.idx_partida_crono = 0
                            st.rerun()
                        else:
                            st.error(f"❌ {msg3}")

            # ===== TAB: CURVA S =====
            with tab_curva:
                st.markdown("### 📈 Curva S - Análisis de Avance del Proyecto")
                st.caption("Compara el avance planificado vs real. Solo se consideran partidas **Aprobadas** en el plan.")

                cronograma_all = obtener_cronograma_obra(obra_codigo) or []
                render_curva_s(cronograma_all, avances, rol="jefe")


            # ===== TAB: HITOS DE PAGO =====
            with tab_hitos:
                st.markdown("### 💰 Gestión de Hitos de Pago")
                st.caption("Registra y controla los hitos de pago del proyecto (valorizaciones, adelantos, liquidaciones)")

                if "form_hito_counter" not in st.session_state:
                    st.session_state.form_hito_counter = 0

                with st.form(key=f"form_add_hito_{st.session_state.form_hito_counter}"):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c1:
                        h_desc = st.text_input("Descripción", placeholder="Ej: Valorización N°01")
                    with c2:
                        h_fecha = st.date_input("📅 Fecha Estimada*", value=date.today())
                    with c3:
                        h_monto = st.number_input("Monto (S/.)", min_value=0.0, step=0.01, format="%.2f")

                    h_estado = st.selectbox(
                        "Estado",
                        ["Pendiente", "Pagado"],
                        help="Marca como Pagado si ya se procesó el pago"
                    )

                    h_obs = st.text_area(
                        "📝 Observación (opcional)",
                        placeholder="Sustento enviado, OC aprobada, documento por adjuntar, etc.",
                        height=80
                    )

                    if st.form_submit_button(f"✅ Agregar Hito ({h_estado})", use_container_width=True, type="primary"):
                        ok, msg = validar_hito_pago(h_desc, h_fecha, h_monto)
                        if not ok:
                            st.error(f"❌ {msg}")
                        else:
                            hito = {
                                "descripcion": h_desc.strip(),
                                "fecha": str(h_fecha),
                                "monto": float(h_monto),
                                "estado": h_estado,
                                "observacion": h_obs.strip(),
                                "creado_por": st.session_state.get("usuario_logueado", "jefe"),
                            }
                            ok2, msg2 = agregar_hito_pago(obra_codigo, hito)
                            if ok2:
                                st.success("✅ Hito de pago registrado correctamente")
                                st.session_state.form_hito_counter += 1
                                st.rerun()
                            else:
                                st.error(f"❌ {msg2}")

                st.divider()

                # Lista de hitos
                hitos = obtener_hitos_pago_obra(obra_codigo) or []
                for h in hitos:
                    h.setdefault("estado", "Pendiente")
                    h.setdefault("creado_por", "jefe")

                if not hitos:
                    st.info("📭 No hay hitos de pago registrados. Agrega el primer hito para comenzar el seguimiento.")
                else:
                    # Resumen de hitos
                    resumen_h = calcular_resumen_hitos(hitos)
                    
                    st.markdown("#### 💼 Resumen Financiero de Hitos")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "💰 Total Hitos",
                            f"S/. {resumen_h['total_hitos']:,.2f}",
                            help="Suma total de todos los hitos de pago"
                        )
                    with col2:
                        st.metric(
                            "✅ Pagado",
                            f"S/. {resumen_h['pagado']:,.2f}",
                            help="Monto de hitos ya pagados"
                        )
                    with col3:
                        st.metric(
                            "⏳ Pendiente",
                            f"S/. {resumen_h['pendiente']:,.2f}",
                            help="Monto de hitos pendientes por pagar"
                        )
                    with col4:
                        porc_pagado = (resumen_h['pagado'] / resumen_h['total_hitos'] * 100) if resumen_h['total_hitos'] > 0 else 0
                        st.metric(
                            "📊 % Pagado",
                            f"{porc_pagado:.1f}%",
                            help="Porcentaje de hitos pagados"
                        )
                    
                    # Barra de progreso
                    if resumen_h['total_hitos'] > 0:
                        progress_hitos = resumen_h['pagado'] / resumen_h['total_hitos']
                        st.progress(progress_hitos)
                        st.caption(f"S/. {resumen_h['pagado']:,.2f} de S/. {resumen_h['total_hitos']:,.2f} pagados")

                    st.markdown(f"#### 📋 Listado de Hitos ({len(hitos)} total)")
                    
                    # Filtro
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        filtro_hitos = st.selectbox(
                            "Filtrar por estado:",
                            ["Todos", "Pendiente", "Pagado"],
                            key="filtro_hitos"
                        )
                    
                    hitos_filtrados = hitos if filtro_hitos == "Todos" else [h for h in hitos if h.get("estado") == filtro_hitos]
                    
                    # Tabla de hitos
                    if hitos_filtrados:
                        dfh = pd.DataFrame(hitos_filtrados)
                        cols_mostrar = ["descripcion", "fecha", "monto", "estado", "observacion"]
                        cols_existentes = [c for c in cols_mostrar if c in dfh.columns]
                        
                        st.dataframe(
                            dfh[cols_existentes].rename(columns={
                                "descripcion": "Descripción",
                                "fecha": "Fecha",
                                "monto": "Monto (S/.)",
                                "estado": "Estado",
                                "observacion": "Observación",
                            }),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Monto (S/.)": st.column_config.NumberColumn(format="S/. %.2f"),
                                "Estado": st.column_config.TextColumn(
                                    width="small",
                                )
                            }
                        )
                    else:
                        st.info(f"No hay hitos con estado '{filtro_hitos}'")

                    st.markdown("#### ✏️ Editar / Cambiar Estado / Eliminar Hito")
                    
                    if "idx_hito_sel" not in st.session_state:
                        st.session_state.idx_hito_sel = 0

                    opciones_h = [
                        f"{h.get('descripcion', '(sin descripción)')} - S/. {float(h.get('monto', 0) or 0):,.2f} [{h.get('estado', 'Pendiente')}]"
                        for h in hitos
                    ]
                    
                    sel_h = st.selectbox(
                        "Selecciona un hito para editar:",
                        opciones_h,
                        index=min(st.session_state.idx_hito_sel, len(opciones_h) - 1),
                        key="sel_hito"
                    )
                    st.session_state.idx_hito_sel = opciones_h.index(sel_h)

                    h_sel = hitos[st.session_state.idx_hito_sel]
                    h_id = h_sel.get("id")

                    # Botón rápido para marcar como pagado
                    if h_sel.get("estado") == "Pendiente":
                        if st.button("✅ Marcar como PAGADO", use_container_width=True, type="primary"):
                            payload = dict(h_sel)
                            payload["estado"] = "Pagado"
                            ok, msg = actualizar_hito_pago(obra_codigo, h_id, payload)
                            if ok:
                                st.success("✅ Hito marcado como Pagado")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")

                    with st.form("form_edit_hito"):
                        c1, c2 = st.columns(2)
                        with c1:
                            e_desc = st.text_input("Descripción", value=h_sel.get("descripcion", ""))
                        with c2:
                            e_monto = st.number_input(
                                "Monto (S/.)",
                                min_value=0.0,
                                step=100.0,
                                format="%.2f",
                                value=float(h_sel.get("monto", 0.0) or 0.0)
                            )
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            e_fecha = st.date_input("Fecha", value=pd.to_datetime(h_sel.get("fecha", date.today())).date())
                        with c2:
                            e_estado = st.selectbox(
                                "Estado",
                                ["Pendiente", "Pagado"],
                                index=0 if h_sel.get("estado") == "Pendiente" else 1
                            )

                        e_obs = st.text_area("Observación", value=h_sel.get("observacion", ""), height=80)

                        colx, coly = st.columns(2)
                        with colx:
                            guardar_h = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")
                        with coly:
                            eliminar_h = st.form_submit_button("🗑️ Eliminar Hito", use_container_width=True)

                    if guardar_h:
                        ok, msg = validar_hito_pago(e_desc, e_fecha, e_monto)
                        if not ok:
                            st.error(f"❌ {msg}")
                        else:
                            payload = {
                                "descripcion": e_desc.strip(),
                                "fecha": str(e_fecha),
                                "monto": float(e_monto),
                                "estado": e_estado,
                                "observacion": e_obs.strip(),
                                "creado_por": h_sel.get("creado_por", "jefe"),
                            }
                            ok2, msg2 = actualizar_hito_pago(obra_codigo, h_id, payload)
                            if ok2:
                                st.success("✅ Hito actualizado correctamente")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg2}")

                    if eliminar_h:
                        ok3, msg3 = eliminar_hito_pago(obra_codigo, h_id)
                        if ok3:
                            st.success("✅ Hito eliminado correctamente")
                            st.session_state.idx_hito_sel = 0
                            st.rerun()
                        else:
                            st.error(f"❌ {msg3}")

            # ===== TAB: CAJA CHICA =====
            with tab4:
                st.markdown("### 💰 Caja Chica")
                mostrar_caja_chica()

            # ===== TAB: DONACIONES (PRINCIPAL) =====
            with tab5:
                st.markdown("### 🎁 Gestión de Donaciones")
                st.caption("Registro de aportes externos efectivo o material/insumo que amplían los recursos del proyecto")

                obra_codigo_tab = st.session_state.get("obra_seleccionada", "")
                presupuesto_actual = obtener_presupuesto_obra(obra_codigo_tab)
                donaciones_obra = obtener_donaciones_obra(obra_codigo_tab) or []

                if "form_donacion_counter" not in st.session_state:
                    st.session_state.form_donacion_counter = 0

                # ========== REGISTRAR NUEVA DONACIÓN ==========
                st.markdown("#### ➕ Registrar Nueva Donación")

                tipo_donacion = st.selectbox(
                    "📦 Tipo de Donación",
                    ["Efectivo", "Insumo"],
                    key="tipo_donacion"
                )

                nombre_donante = st.text_input(
                    "👤 Nombre del Donante/Entidad",
                    placeholder="Ej: empresa X, persona Y",
                    key=f"don_nombre_{st.session_state.form_donacion_counter}"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    cantidad_donacion = st.number_input(
                        "💵 Cantidad / Monto",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        help="Si es Efectivo: monto en S/. | Si es Insumo: cantidad de unidades",
                        key=f"don_cantidad_{st.session_state.form_donacion_counter}"
                    )
                with col2:
                    unidad_especie = st.text_input(
                        "📏 Unidad (si es Insumo)",
                        placeholder="Ej: sacos, bolsas, metros, etc.",
                        disabled=tipo_donacion.lower().startswith("efectivo"),
                        key=f"don_unidad_{st.session_state.form_donacion_counter}"
                    )
                with col3:
                    valor_unitario = st.number_input(
                        "💰 Valor Unitario (Insumo)",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        help="Valor de mercado por unidad",
                        disabled=tipo_donacion.lower().startswith("efectivo"),
                        key=f"don_valor_unit_{st.session_state.form_donacion_counter}"
                    )

                descripcion_donacion = st.text_area(
                    "📝 Descripción del Aporte",
                    placeholder="Detalle del material, condiciones, etc.",
                    height=80,
                    key=f"don_desc_{st.session_state.form_donacion_counter}"
                )

                if st.button("✅ Registrar Donación", use_container_width=True, type="primary", key=f"btn_reg_don_{st.session_state.form_donacion_counter}"):
                    tipo_val = "Efectivo" if tipo_donacion.lower().startswith("efectivo") else "Insumo"

                    es_valido, msg_error = validar_donacion(
                        nombre_donante,
                        tipo_val,
                        cantidad_donacion,
                        valor_unitario if tipo_val == "Insumo" else None
                    )

                    if not es_valido:
                        st.error(f"❌ {msg_error}")
                    else:
                        valor_total = calcular_valor_donacion(tipo_val, cantidad_donacion, valor_unitario)

                        nueva_donacion = {
                            "nombre_donante": nombre_donante.strip(),
                            "tipo_donacion": tipo_val,
                            "cantidad": cantidad_donacion,
                            "unidad": unidad_especie.strip() if tipo_val == "Insumo" else "",
                            "valor_unitario": valor_unitario if tipo_val == "Insumo" else 0,
                            "valor_total": valor_total,
                            "descripcion": descripcion_donacion.strip(),
                            "fecha": str(date.today()),
                            "estado": "Registrada"
                        }

                        ok, msg = agregar_donacion(obra_codigo_tab, nueva_donacion)
                        if ok:
                            st.success("✅ Donación registrada correctamente")
                            st.session_state.form_donacion_counter += 1
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

                st.divider()

                # ========== RESUMEN DE DONACIONES ==========
                st.markdown("#### 📊 Resumen de Donaciones")

                if donaciones_obra:
                    resumen = calcular_resumen_donaciones(donaciones_obra)
                    impacto = impacto_donacion_en_presupuesto(presupuesto_actual, donaciones_obra)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "💵 Efectivo Donado",
                            f"S/. {resumen['total_efectivo']:,.2f}",
                            help="Dinero en efectivo recibido"
                        )
                    with col2:
                        st.metric(
                            "📦 Material/Insumo",
                            f"S/. {resumen['total_especie']:,.2f}",
                            help="Valor de mercado de materiales/insumos donados"
                        )
                    with col3:
                        st.metric(
                            "🎁 Total Donaciones",
                            f"S/. {resumen['total_general']:,.2f}",
                            help="Aporte total en valor"
                        )
                    with col4:
                        st.metric(
                            "📋 Cantidad de Donaciones",
                            resumen['cantidad_donaciones'],
                            help="Número total de donaciones registradas"
                        )

                    st.divider()

                    # ========== IMPACTO EN PRESUPUESTO ==========
                    st.markdown("#### 📈 Impacto en Presupuesto")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(
                            "Presupuesto Original",
                            f"S/. {impacto['presupuesto_original']:,.2f}"
                        )
                    with col2:
                        st.metric(
                            "Total Donaciones",
                            f"S/. {impacto['total_donaciones']:,.2f}",
                            delta=f"+{impacto['porcentaje_ampliacion']:.1f}%"
                        )
                    with col3:
                        st.metric(
                            "Presupuesto Ampliado",
                            f"S/. {impacto['presupuesto_ampliado']:,.2f}",
                            delta_color="normal"
                        )
                    with col4:
                        st.metric(
                            "Ampliación %",
                            f"{impacto['porcentaje_ampliacion']:.1f}%",
                            help="Porcentaje de aumento al presupuesto original"
                        )

                    # Barra de progreso
                    if impacto['presupuesto_original'] > 0:
                        pct_ampliacion = impacto['porcentaje_ampliacion'] / 100
                        st.progress(min(pct_ampliacion, 1.0))
                        st.caption(f"Presupuesto ampliado de S/. {impacto['presupuesto_original']:,.0f} a S/. {impacto['presupuesto_ampliado']:,.0f}")

                    st.divider()

                    # ========== LISTADO DE DONACIONES ==========
                    st.markdown(f"#### 📋 Historial de Donaciones ({len(donaciones_obra)} registradas)")

                    # Filtros
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        filtro_tipo_don = st.selectbox(
                            "Filtrar por tipo:",
                            ["Todas", "Efectivo", "Insumo"],
                            key="filtro_tipo_donacion"
                        )

                    donaciones_filtradas = donaciones_obra
                    if filtro_tipo_don != "Todas":
                        donaciones_filtradas = [d for d in donaciones_obra if d.get("tipo_donacion") == filtro_tipo_don]

                    # Tabla de donaciones
                    if donaciones_filtradas:
                        df_don = pd.DataFrame(donaciones_filtradas)
                        cols_mostrar = ["fecha", "nombre_donante", "tipo_donacion", "cantidad", "unidad", "valor_total", "descripcion"]
                        cols_existentes = [c for c in cols_mostrar if c in df_don.columns]

                        st.dataframe(
                            df_don[cols_existentes].rename(columns={
                                "fecha": "Fecha",
                                "nombre_donante": "Donante",
                                "tipo_donacion": "Tipo",
                                "cantidad": "Cantidad",
                                "unidad": "Unidad",
                                "valor_total": "Valor (S/.)",
                                "descripcion": "Descripción",
                            }),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Valor (S/.)": st.column_config.NumberColumn(format="S/. %.2f")
                            }
                        )
                    else:
                        st.info("No hay donaciones registradas con este filtro")

                    # ========== EDITAR/ELIMINAR DONACIÓN ==========
                    st.markdown("#### ✏️ Editar o Eliminar Donación")

                    if "idx_donacion_sel" not in st.session_state:
                        st.session_state.idx_donacion_sel = 0

                    opciones_don = [
                        f"{d.get('fecha', '')} - {d.get('nombre_donante', '')} ({d.get('tipo_donacion', '')}) - S/. {float(d.get('valor_total', 0)):,.2f}"
                        for d in donaciones_obra
                    ]

                    if opciones_don:
                        sel_don = st.selectbox(
                            "Selecciona una donación:",
                            opciones_don,
                            index=min(st.session_state.idx_donacion_sel, len(opciones_don) - 1),
                            key="sel_donacion"
                        )
                        st.session_state.idx_donacion_sel = opciones_don.index(sel_don)

                        don_sel = donaciones_obra[st.session_state.idx_donacion_sel]
                        don_id = don_sel.get("id")

                        with st.form("form_edit_donacion"):
                            col1, col2 = st.columns(2)
                            with col1:
                                e_donante = st.text_input("Donante", value=don_sel.get("nombre_donante", ""))
                                e_tipo = st.selectbox(
                                    "Tipo",
                                    ["Efectivo", "Insumo"],
                                    index=0 if don_sel.get("tipo_donacion") == "Efectivo" else 1
                                )
                            with col2:
                                e_cantidad = st.number_input(
                                    "Cantidad",
                                    min_value=0.0,
                                    step=0.01,
                                    format="%.2f",
                                    value=float(don_sel.get("cantidad", 0) or 0)
                                )
                                if e_tipo == "Insumo":
                                    e_unidad = st.text_input("Unidad", value=don_sel.get("unidad", ""))
                                    e_valor_unit = st.number_input(
                                        "Valor Unitario",
                                        min_value=0.0,
                                        step=0.01,
                                        format="%.2f",
                                        value=float(don_sel.get("valor_unitario", 0) or 0)
                                    )
                                else:
                                    e_unidad = ""
                                    e_valor_unit = 0

                            e_desc = st.text_area("Descripción", value=don_sel.get("descripcion", ""), height=80)

                            colx, coly = st.columns(2)
                            with colx:
                                guardar_don = st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary")
                            with coly:
                                eliminar_don = st.form_submit_button("🗑️ Eliminar Donación", use_container_width=True)

                        if guardar_don:
                            es_valido, msg_error = validar_donacion(
                                e_donante,
                                e_tipo,
                                e_cantidad,
                                e_valor_unit if e_tipo == "Insumo" else None
                            )

                            if not es_valido:
                                st.error(f"❌ {msg_error}")
                            else:
                                valor_total = calcular_valor_donacion(e_tipo, e_cantidad, e_valor_unit)
                                payload = {
                                    "nombre_donante": e_donante.strip(),
                                    "tipo_donacion": e_tipo,
                                    "cantidad": e_cantidad,
                                    "unidad": e_unidad.strip() if e_tipo == "Insumo" else "",
                                    "valor_unitario": e_valor_unit if e_tipo == "Insumo" else 0,
                                    "valor_total": valor_total,
                                    "descripcion": e_desc.strip(),
                                }
                                ok, msg = actualizar_donacion(obra_codigo_tab, don_id, payload)
                                if ok:
                                    st.success("✅ Donación actualizada correctamente")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")

                        if eliminar_don:
                            ok, msg = eliminar_donacion(don_id)
                            if ok:
                                st.success("✅ Donación eliminada correctamente")
                                st.session_state.idx_donacion_sel = 0
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                else:
                    st.info("📭 No hay donaciones registradas para esta obra. ¡Agrega la primera donación!")

           
    # ==================== PANTALLA DE BIENVENIDA ====================
    else:
        st.markdown("""
        ## Bienvenido al Sistema de Control de Obras

        ### Selecciona una obra del panel lateral para comenzar

        ---

        ### Resumen General
        """)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Obras", len(obras))
        with col2:
            st.metric("Última Actualización", date.today().strftime("%d/%m/%Y"))

# ==================== MODO PASANTE ====================
else:
    with st.sidebar:
        mostrar_logo_dinamico()
        st.divider()

        obras = cargar_obras()
        usuario_pasante = st.session_state.get("auth", "")

        obra_cod, obra_nom = obtener_obra_asignada_pasante(obras, usuario_pasante)
        if not obra_cod:
            st.error(
                "Este pasante no tiene una obra asignada (no se encontró coincidencia). "
                "Verifica que el código o nombre de la obra contenga: "
                "'ventanilla/pachacutec' o 'molina/rinconada'."
            )
            st.stop()

        if "obra_seleccionada" not in st.session_state or st.session_state.obra_seleccionada != obra_cod:
            st.session_state.obra_seleccionada = obra_cod
            st.session_state.mostrar_form_obra = False
            st.session_state.mostrar_insumos = False
            st.rerun()

        st.subheader("Obra asignada")
        st.info(f"{obra_nom}")
        st.caption("Rol: PASANTE (solo puede ver su obra asignada)")

                # ==================== KPI: Meta Programada ====================
        cfg_kpi = kpi_cargar_config(obra_cod)
        st.sidebar.markdown(f"**Meta Programada Hoy:** {float(cfg_kpi.get('avance_programado', 0.0)):.1f}%")


    st.title("Modo Pasante")

    if st.session_state.obra_seleccionada:
        obra_codigo = st.session_state.obra_seleccionada
        obra_nombre = obras.get(obra_codigo, "Obra no encontrada")
        st.header(f"{obra_nombre}")
        _render_pdf_panel()

        presupuesto = obtener_presupuesto_obra(obra_codigo)
        avances = obtener_avances_obra(obra_codigo)
        donaciones_obra = obtener_donaciones_obra(obra_codigo)
        impacto_don = impacto_donacion_en_presupuesto(presupuesto, donaciones_obra)
        presupuesto_ampliado = impacto_don["presupuesto_ampliado"]
        resumen = calcular_resumen_presupuesto(presupuesto_ampliado, avances)

        st.markdown("### 💰 Resumen de Presupuesto (lectura)")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            delta_don = f"+S/. {impacto_don['total_donaciones']:,.2f}" if impacto_don["total_donaciones"] > 0 else None
            st.metric("Presupuestado", f"S/. {resumen['presupuestado']:,.2f}", delta=delta_don)
        with col2:
            st.metric("Gastado", f"S/. {resumen['gastado']:,.2f}", delta=f"{resumen['porcentaje_gastado']:.1f}%")
        with col3:
            st.metric("Disponible", f"S/. {resumen['disponible']:,.2f}")
        with col4:
            porcentaje = resumen['porcentaje_gastado']
            if porcentaje < 50:
                estado = "🟢 Saludable"
            elif porcentaje < 80:
                estado = "🟡 Moderado"
            elif porcentaje < 100:
                estado = "🟠 Crítico"
            else:
                estado = "🔴 Excedido"
            st.metric("Estado", estado)

        with col5:
            st.metric("Donaciones", f"S/. {impacto_don['total_donaciones']:,.2f}")

        st.progress(min(resumen['porcentaje_gastado'] / 100, 1.0))
        st.divider()

        eficiencia_promedio = calcular_eficiencia_promedio_obra(avances)
        emoji_rendimiento, texto_rendimiento, _ = obtener_estado_rendimiento(eficiencia_promedio)

        st.markdown("### 📊 Rendimiento de Mano de Obra (lectura)")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Eficiencia Promedio", f"{eficiencia_promedio:.1f}%")
        with c2:
            st.metric("Estado", f"{emoji_rendimiento} {texto_rendimiento}")
        with c3:
            if eficiencia_promedio >= 100:
                st.metric("Superávit", f"+{eficiencia_promedio - 100:.1f}%")
            else:
                st.metric("Déficit", f"-{100 - eficiencia_promedio:.1f}%")

        if eficiencia_promedio > 0:
            st.progress(min(eficiencia_promedio / 100, 1.0))
        st.divider()

        tab1, tab2, tab3 = st.tabs(["Parte Diario", "Historial de Avances", "Cronograma Valorizado"])

        # ==================== TAB 1: PARTE DIARIO (PASANTE) ====================
        with tab1:
            st.subheader("Parte Diario del Día")
            hoy = date.today()

            if "form_parte_diario_counter" not in st.session_state:
                st.session_state.form_parte_diario_counter = 0

            if "insumos_mo_confirmados" not in st.session_state:
                st.session_state.insumos_mo_confirmados = []
            if "insumos_mat_confirmados" not in st.session_state:
                st.session_state.insumos_mat_confirmados = []

            counter = st.session_state.form_parte_diario_counter

            st.markdown("### Información General")
            col1, col2 = st.columns(2)

            with col1:
                nombre_default = st.session_state.get("usuario_logueado", "Usuario")
                responsable = st.text_input("Tu nombre", value=nombre_default, key=f"responsable_input_pas_{counter}")

            with col2:
                avance = st.slider("Avance logrado hoy (%)", 0, 30, 5, key=f"avance_input_pas_{counter}")

            col1, col2 = st.columns(2)
            with col1:
                name_partida = st.text_input(
                    "Nombre de la partida o actividad realizada hoy",
                    placeholder="ej: Cimentación, Estructura, Albañilería, etc.",
                    key=f"name_partida_input_pas_{counter}"
                )
            with col2:
                c21, c22 = st.columns(2)
                with c21:
                    cantidad_ejecutada = st.number_input(
                        "Metrado Ejecutado",
                        min_value=0.0,
                        step=0.1,
                        placeholder="Ingresa la cantidad realizada",
                        key=f"cantidad_ejecutada_pas_{counter}"
                    )
                with c22:
                    unidad_medida = st.text_input(
                        "Unidad",
                        placeholder="ej: M3, KG, UND, HH",
                        key=f"unidad_input_pas_{counter}"
                    )

            col1, col2 = st.columns(2)
            with col1:
                horas_mano_obra = st.number_input("Jornada Laboral (h)", min_value=0, step=1, value=8, key=f"horas_input_pas_{counter}")
            with col2:
                rendimiento_partida = st.number_input(
                    "Rendimiento Esperado de la Partida (por día)",
                    min_value=0.0,
                    step=0.1,
                    value=6.0,
                    help="Rendimiento en unidad/día. Se ajusta proporcionalmente si la jornada no es de 8 horas.",
                    key=f"rendimiento_input_pas_{counter}"
                )

            st.markdown("### Costos")

            # Cargar empleados
            empleados_docs = db.collection("empleados").stream()
            empleados = [{"id": d.id, **d.to_dict()} for d in empleados_docs]

            tab_mo, tab_insumos = st.tabs(["Mano de Obra", "Insumos (General)"])

            with tab_mo:
                st.markdown("#### Ingresar Mano de Obra")
                
                if not empleados:
                    st.warning("⚠️ No hay empleados registrados. Consulta con el jefe de obra.")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        nombres_empleados = [f"{e['nombre']} - {e['cargo']}" for e in empleados]
                        empleado_seleccionado = st.selectbox(
                            "Seleccionar Empleado",
                            nombres_empleados,
                            key=f"empleado_mo_pas_{counter}"
                        )
                        idx_emp = nombres_empleados.index(empleado_seleccionado)
                        empleado_data = empleados[idx_emp]
                    with col2:
                        sueldo_dia = st.number_input(
                            "Sueldo del Día (S/.)",
                            min_value=0.0,
                            step=10.0,
                            value=80.0,
                            format="%.2f",
                            key=f"sueldo_mo_pas_{counter}"
                        )

                    if st.button("Confirmar Mano de Obra", use_container_width=True, type="primary", key=f"btn_confirmar_mo_pas_{counter}"):
                        if sueldo_dia <= 0:
                            st.error("❌ El sueldo del día debe ser mayor a 0")
                        else:
                            item = {
                                "Empleado": empleado_data['nombre'],
                                "Cargo": empleado_data['cargo'],
                                "DNI": empleado_data['dni'],
                                "Sueldo del Día": sueldo_dia,
                                "Parcial (S/)": sueldo_dia
                            }
                            st.session_state.insumos_mo_confirmados.append(item)
                            st.success(f"✓ {empleado_data['nombre']} agregado")
                            st.rerun()

            with tab_insumos:
                st.markdown("#### Ingresar Insumo (Material, Equipo u Otro)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    desc_insumo = st.text_input("Descripción", placeholder="ej: Cemento, Alquiler Mezcladora, etc.", key=f"desc_insumo_pas_{counter}")
                with col2:
                    cant_insumo = st.number_input("Cantidad", min_value=0.0, step=0.01, format="%.4f", key=f"cant_insumo_pas_{counter}")
                with col3:
                    precio_insumo = st.number_input("Precio Unit. (S/.)", min_value=0.0, step=0.01, value=0.0, format="%.2f", key=f"precio_insumo_pas_{counter}")

                if st.button("Confirmar Insumo", use_container_width=True, type="primary", key=f"btn_confirmar_insumo_pas_{counter}"):
                    if rendimiento_partida <= 0:
                        st.error("❌ El rendimiento de la partida debe ser mayor a 0")
                    elif not unidad_medida.strip():
                        st.error("❌ Debes especificar la unidad de medida")
                    elif cant_insumo <= 0:
                        st.error("❌ La cantidad debe ser mayor a 0")
                    elif not desc_insumo.strip():
                        st.error("❌ Debes ingresar una descripción")
                    elif precio_insumo <= 0:
                        st.error("❌ El precio debe ser mayor a 0")
                    else:
                        parcial_insumo = calcular_parcial(cant_insumo, precio_insumo)
                        st.session_state.insumos_mat_confirmados.append({
                            "Descripción": desc_insumo,
                            "Cantidad": cant_insumo,
                            "Precio Unit.": precio_insumo,
                            "Parcial (S/)": parcial_insumo
                        })
                        st.success(f"✓ {desc_insumo} agregado")
                        st.rerun()
            # ==================== LISTAS CONFIRMADAS (PASANTE) ====================
            if st.session_state.insumos_mo_confirmados:
                st.markdown("#### Mano de Obra Confirmada")
                st.dataframe(pd.DataFrame(st.session_state.insumos_mo_confirmados), use_container_width=True, hide_index=True)
                if st.button("🗑️ Limpiar Mano de Obra", key=f"limpiar_mo_pas_{counter}"):
                    st.session_state.insumos_mo_confirmados = []
                    st.rerun()

            if st.session_state.insumos_mat_confirmados:
                st.markdown("#### Insumos Confirmados")
                st.dataframe(pd.DataFrame(st.session_state.insumos_mat_confirmados), use_container_width=True, hide_index=True)
                if st.button("🗑️ Limpiar Insumos", key=f"limpiar_insumos_pas_{counter}"):
                    st.session_state.insumos_mat_confirmados = []
                    st.rerun()

            # ==================== RESUMEN DE COSTOS ====================
            st.markdown("### 📊 Resumen de Costos Consolidado")
            total_mo = sum([item["Parcial (S/)"] for item in st.session_state.insumos_mo_confirmados])
            total_insumos = sum([item["Parcial (S/)"] for item in st.session_state.insumos_mat_confirmados])
            total_general = total_mo + total_insumos

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Mano de Obra", f"S/. {total_mo:.2f}")
            with col2:
                st.metric("Insumos", f"S/. {total_insumos:.2f}")
            with col3:
                st.metric("💰 TOTAL", f"S/. {total_general:.2f}", delta_color="normal")

            st.markdown("### Finalizar Parte Diario")
            obs = st.text_area("Observaciones", key=f"obs_final_pas_{counter}")
            fotos = st.file_uploader("Fotos del avance", accept_multiple_files=True, type=["jpg", "png", "jpeg"], key=f"fotos_final_pas_{counter}")

            st.session_state["cantidad_ejecutada_cache"] = cantidad_ejecutada
            st.session_state["unidad_medida_cache"] = unidad_medida
            st.session_state["total_general_cache"] = total_general

            if 0 < len(fotos) < 3:
                st.warning("⚠️ Debes subir mínimo 3 fotos")

            @st.dialog("Confirmar Envío de Parte Diario (Pasante)")
            def confirmar_envio_modal_pasante():
                st.warning("⚠️ ¿Estás seguro de enviar el parte diario?")
                st.write("Esta acción guardará el registro y limpiará todos los campos.")

                c1, c2 = st.columns(2)

                with c1:
                    if st.button(
                        "✅ SÍ, ENVIAR",
                        use_container_width=True,
                        type="primary",
                        key=f"si_enviar_pas_{counter}"
                    ):
                        #  Seguridad: valores por defecto
                        cantidad_ejecutada_cache = st.session_state.get("cantidad_ejecutada_cache", 0)
                        total_general_cache = st.session_state.get("total_general_cache", 0)

                        totales = calcular_totales_costos(
                            st.session_state.insumos_mo_confirmados,
                            st.session_state.insumos_mat_confirmados,
                            [],
                            [],
                            cantidad_ejecutada=1  # Ya no se multiplica, total directo
                        )
                        
                        # Sobrescribir total_general_ejecutado con el total real
                        totales["total_general_ejecutado"] = total_general_cache

                        rutas_fotos = guardar_fotos_avance(
                            obra_codigo,
                            fotos,
                            hoy
                        )

                        # 🧱 AVANCE REGISTRADO POR PASANTE
                        nuevo_avance = crear_avance_dict(
                            fecha=hoy,
                            responsable=responsable,
                            avance_pct=avance,
                            observaciones=obs,
                            rutas_fotos=rutas_fotos,
                            nombre_partida=name_partida,
                            rendimiento_partida=rendimiento_partida,
                            unidad_medida=st.session_state.get(
                                "unidad_medida_cache",
                                unidad_medida
                            ),
                            horas_mano_obra=horas_mano_obra,
                            cantidad_ejecutada=cantidad_ejecutada_cache,
                            insumos_mo=st.session_state.insumos_mo_confirmados,
                            insumos_mat=st.session_state.insumos_mat_confirmados,
                            insumos_eq=[],
                            insumos_otros=[],
                            totales=totales
                        )

                        #  Guardar SOLO avance (no toca presupuesto / hitos)
                        exito, mensaje_db = agregar_avance(
                            obra_codigo,
                            nuevo_avance
                        )

                        if not exito:
                            st.error(f"❌ Error al guardar: {mensaje_db}")
                            return

                        if not exito:
                            st.error(f"❌ Error al guardar: {mensaje_db}")
                            return

                        # ==========================
                        # GUARDAR PARA WHATSAPP
                        # ==========================
                        st.session_state.temp_nuevo_avance = nuevo_avance
                        st.session_state.temp_obra_nombre = obra_nombre
                        st.session_state.abrir_whatsapp_modal = True

                        # ==========================
                        #  PDF (INTACTO)
                        # ==========================
                        st.session_state.show_pdf_panel = True
                        st.session_state.pdf_meta = {
                            "obra_codigo": obra_codigo,
                            "obra_nombre": obra_nombre,
                            "rol": "pasante"
                        }
                        st.session_state.pdf_avance = nuevo_avance
                        st.session_state.pdf_bytes = None

                        # ==========================
                        #  LIMPIEZA DE ESTADO
                        # ==========================
                        st.session_state.insumos_mo_confirmados = []
                        st.session_state.insumos_mat_confirmados = []
                        st.session_state.form_parte_diario_counter += 1
                        st.session_state.parte_enviado = True

                        st.success("✅ Parte diario enviado correctamente (Pasante)")
                        st.balloons()
                        st.rerun()

                with c2:
                    if st.button(
                        "❌ CANCELAR",
                        use_container_width=True,
                        type="secondary",
                        key=f"cancelar_pas_{counter}"
                    ):
                        st.rerun()



            @st.dialog("Notificar por WhatsApp")
            def whatsapp_modal():

                nuevo_avance = st.session_state.get("temp_nuevo_avance", {})
                obra_nombre = st.session_state.get("temp_obra_nombre", "")
                fecha = nuevo_avance.get("fecha")
                avance_pct = nuevo_avance.get("avance", 0)
                totales = nuevo_avance.get("totales", {})

                import urllib.parse

                mensaje = (
                    f" *Parte Diario Enviado*\n\n"
                    f" *Obra:* {obra_nombre}\n"
                    f" *Fecha:* {fecha}\n"
                    f" *Avance:* {avance_pct}%\n"
                    f" *Total Ejecutado:* S/. {float(totales.get('total_general_ejecutado', 0) or 0):,.2f}"
                )

                mensaje_encoded = urllib.parse.quote(mensaje)
                numero_whatsapp = "51958555917"
                url_whatsapp = f"https://wa.me/{numero_whatsapp}?text={mensaje_encoded}"

                # ==========================
                # UI
                # ==========================
                st.success("📱 Notificación por WhatsApp")

                if not st.session_state.whatsapp_enviado:
                    if st.link_button(
                        "📱 Enviar Notificación por WhatsApp",
                        url_whatsapp,
                        type="primary",
                        use_container_width=True
                    ):
                        # ⚠️ link_button no dispara eventos
                        pass

                    # Botón auxiliar para marcar como enviado
                    if st.button("✅ Ya envié el mensaje", use_container_width=True):
                        st.session_state.whatsapp_enviado = True
                        st.rerun()

                else:
                    st.success("✅ Notificación enviada por WhatsApp")

                if st.button("❌ Cerrar", use_container_width=True, type="secondary"):
                    st.session_state.abrir_whatsapp_modal = False
                    st.session_state.whatsapp_enviado = False
                    st.rerun()
            # ===============================
            # BOTÓN ENVIAR PARTE DIARIO (PASANTE)
            # ===============================
            
            if st.session_state.get("parte_enviado"):
                st.info("✅ Parte diario ya enviado. Usa los botones de arriba para descargar PDF o enviar WhatsApp.")

                if st.button("🔄 Limpiar y crear nuevo parte diario", use_container_width=True, key="limpiar_parte_pas"):
                    st.session_state.parte_enviado = False
                    st.session_state.show_pdf_panel = False
                    st.session_state.pdf_meta = {}
                    st.session_state.pdf_avance = {}
                    st.session_state.pdf_bytes = None
                    st.rerun()

            else:
                if st.button(
                    "📤 ENVIAR PARTE DIARIO",
                    use_container_width=True,
                    type="primary",
                    key=f"enviar_final_pas_{counter}"
                ):
                    es_valido, errores = validar_parte_diario_completo(
                        responsable, avance, rendimiento_partida, unidad_medida, fotos
                    )

                    costos_validos, mensaje_costos = validar_costos_parte_diario(
                        st.session_state.insumos_mo_confirmados,
                        st.session_state.insumos_mat_confirmados,
                        [],
                        []
                    )

                    if not es_valido:
                        for error in errores:
                            st.error(f"❌ {error}")

                    elif not costos_validos:
                        st.error(f"❌ {mensaje_costos}")

                    else:
                        confirmar_envio_modal_pasante()

            # ===============================
            # CONTROLADOR WHATSAPP (PASANTE)
            # ===============================
            if st.session_state.get("abrir_whatsapp_modal", False):
                whatsapp_modal()
        # ==================== TAB 2: HISTORIAL (PASANTE) ====================
        with tab2:
            st.subheader("Historial de Avances")
            historial = preparar_historial_avances(obra_codigo)

            if historial:
                for item in historial:
                    with st.expander(f"📅 {item['fecha_fmt']} - {item['responsable']} ({item['avance_pct']}%)"):
                        st.write("**Responsable:**", item["responsable"])
                        st.write("**Avance del día:**", f"{item['avance_pct']}%")
                        if item.get("obs"):
                            st.markdown("### 📝 Observaciones")
                            st.write(item["obs"])
                        if item.get("fotos"):
                            st.markdown("### 📷 Fotos del avance")
                            cols = st.columns(min(len(item["fotos"]), 3))
                            for i, foto_path in enumerate(item["fotos"]):
                                target = cols[i % 3]
                                if foto_path and os.path.exists(foto_path):
                                    target.image(foto_path, caption=os.path.basename(foto_path))
                                else:
                                    target.warning(f"No se encontró la imagen: {os.path.basename(foto_path) if foto_path else 'Archivo no especificado'}")
            else:
                st.info("No hay partes diarios registrados para esta obra aún.")

        # ==================== TAB 3: CRONOGRAMA (PASANTE) ====================
        with tab3:
            st.subheader("Cronograma Valorizado (Pasante)")
            st.caption("Puedes registrar Partidas e Hitos como PENDIENTE. El JEFE los aprueba/edita. Puedes eliminar lo que tú mismo registraste si te equivocas (recomendado: solo si sigue Pendiente).")

            usuario_actual = st.session_state.get("usuario_logueado") or st.session_state.get("auth") or "pasante"

            cronograma_all = obtener_cronograma_obra(obra_codigo) or []
            hitos_all = obtener_hitos_pago_obra(obra_codigo) or []

            for it in cronograma_all:
                it.setdefault("estado", "Aprobado")
                it.setdefault("creado_por", "jefe")
            for h in hitos_all:
                h.setdefault("estado", "Pendiente")
                h.setdefault("creado_por", "jefe")

            st.markdown("### 1) Partidas del Cronograma (Solicitudes)")
            if "form_crono_counter_pas" not in st.session_state:
                st.session_state.form_crono_counter_pas = 0

            with st.form(key=f"form_add_crono_pas_{st.session_state.form_crono_counter_pas}"):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    crono_nombre = st.text_input("Partida", placeholder="Ej: Cimentación")
                with c2:
                    crono_inicio = st.date_input("Inicio", value=date.today())
                with c3:
                    crono_fin = st.date_input("Fin", value=date.today())
                with c4:
                    crono_monto = st.number_input("Monto (S/.)", min_value=0.0, step=0.01, format="%.2f")
                crono_desc = st.text_input("Descripción (opcional)", placeholder="Ej: concreto f'c 210")

                if st.form_submit_button("Enviar Solicitud (Pendiente)", use_container_width=True, type="primary"):
                    ok, msg = validar_partida_cronograma(crono_nombre, crono_inicio, crono_fin, crono_monto)
                    if not ok:
                        st.error(f"❌ {msg}")
                    else:
                        partida = {
                            "nombre": crono_nombre.strip(),
                            "fecha_inicio": str(crono_inicio),
                            "fecha_fin": str(crono_fin),
                            "monto_planificado": float(crono_monto),
                            "descripcion": crono_desc.strip(),
                            "estado": "Pendiente",
                            "creado_por": usuario_actual,
                        }
                        ok2, msg2 = agregar_partida_cronograma(obra_codigo, partida)
                        if ok2:
                            st.success("✅ Solicitud enviada (Pendiente).")
                            st.session_state.form_crono_counter_pas += 1
                            st.rerun()
                        else:
                            st.error(f"❌ {msg2}")

            cronograma_all = obtener_cronograma_obra(obra_codigo) or []
            for it in cronograma_all:
                it.setdefault("estado", "Aprobado")
                it.setdefault("creado_por", "jefe")

            if cronograma_all:
                dfc = pd.DataFrame(cronograma_all)
                cols_pref = ["estado", "creado_por", "nombre", "fecha_inicio", "fecha_fin", "monto_planificado", "descripcion"]
                cols = [c for c in cols_pref if c in dfc.columns] + [c for c in dfc.columns if c not in cols_pref]
                st.dataframe(
                    dfc[cols].rename(columns={
                        "estado": "Estado",
                        "creado_por": "Creado por",
                        "nombre": "Partida",
                        "fecha_inicio": "Inicio",
                        "fecha_fin": "Fin",
                        "monto_planificado": "Monto Planificado (S/.)",
                        "descripcion": "Descripción",
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Aún no hay partidas registradas en la obra.")

            propias_pendientes = [it for it in cronograma_all if it.get("creado_por") == usuario_actual and it.get("estado") == "Pendiente"]
            if propias_pendientes:
                st.markdown("#### Eliminar Partida (solo tus solicitudes Pendiente)")
                opciones_del = [
                    f"{i+1}. {it.get('nombre','(sin nombre)')} | {it.get('fecha_inicio','')} → {it.get('fecha_fin','')} | S/. {float(it.get('monto_planificado',0) or 0):.2f}"
                    for i, it in enumerate(propias_pendientes)
                ]
                if "idx_del_crono_pas" not in st.session_state:
                    st.session_state.idx_del_crono_pas = 0

                sel_del = st.selectbox(
                    "Selecciona tu partida Pendiente",
                    opciones_del,
                    index=min(st.session_state.idx_del_crono_pas, len(opciones_del)-1),
                    key="sel_del_crono_pas"
                )
                st.session_state.idx_del_crono_pas = opciones_del.index(sel_del)
                item_del = propias_pendientes[st.session_state.idx_del_crono_pas]
                pid = item_del.get("id")

                if st.button("🗑️ Eliminar Partida Seleccionada", use_container_width=True, type="secondary", key="btn_del_crono_pas"):
                    if not pid:
                        st.error("❌ No se encontró ID para eliminar esta partida.")
                    else:
                        okd, msgd = eliminar_partida_cronograma(obra_codigo, pid)
                        if okd:
                            st.success("✅ Partida eliminada.")
                            st.session_state.idx_del_crono_pas = 0
                            st.rerun()
                        else:
                            st.error(f"❌ {msgd}")

            st.divider()

            st.markdown("### 2) Curva S (Plan vs Real)")
            render_curva_s(obtener_cronograma_obra(obra_codigo) or [], avances, rol="pasante")

            st.divider()

            st.markdown("### 3) Hitos de Pago (Solicitudes)")
            st.caption("Se guardan como Pendiente. Puedes eliminar solo los que tú creaste y estén Pendiente.")

            if "form_hito_counter_pas" not in st.session_state:
                st.session_state.form_hito_counter_pas = 0

            with st.form(key=f"form_add_hito_pas_{st.session_state.form_hito_counter_pas}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    h_desc = st.text_input("Descripción", placeholder="Ej: Valorización N°01")
                with c2:
                    h_fecha = st.date_input("Fecha", value=date.today())
                with c3:
                    h_monto = st.number_input("Monto (S/.)", min_value=0.0, step=0.01, format="%.2f")

                h_obs = st.text_input("Observación (opcional)", placeholder="Ej: Sustento enviado / OC pendiente")

                if st.form_submit_button("Agregar Hito (Pendiente)", use_container_width=True, type="primary"):
                    ok, msg = validar_hito_pago(h_desc, h_fecha, h_monto)
                    if not ok:
                        st.error(f"❌ {msg}")
                    else:
                        hito = {
                            "descripcion": h_desc.strip(),
                            "fecha": str(h_fecha),
                            "monto": float(h_monto),
                            "estado": "Pendiente",
                            "observacion": h_obs.strip(),
                            "creado_por": usuario_actual,
                        }
                        ok2, msg2 = agregar_hito_pago(obra_codigo, hito)
                        if ok2:
                            st.success("✅ Hito registrado (Pendiente).")
                            st.session_state.form_hito_counter_pas += 1
                            st.rerun()
                        else:
                            st.error(f"❌ {msg2}")

            hitos_all = obtener_hitos_pago_obra(obra_codigo) or []
            for h in hitos_all:
                h.setdefault("estado", "Pendiente")
                h.setdefault("creado_por", "jefe")

            if hitos_all:
                dfh = pd.DataFrame(hitos_all)
                cols_pref = ["descripcion", "fecha", "monto", "estado", "observacion", "creado_por"]
                cols = [c for c in cols_pref if c in dfh.columns] + [c for c in dfh.columns if c not in cols_pref]
                st.dataframe(
                    dfh[cols].rename(columns={
                        "descripcion": "Hito",
                        "fecha": "Fecha",
                        "monto": "Monto (S/.)",
                        "estado": "Estado",
                        "observacion": "Observación",
                        "creado_por": "Creado por",
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Aún no hay hitos registrados en la obra.")

            propias_h_pend = [h for h in hitos_all if h.get("creado_por") == usuario_actual and h.get("estado") == "Pendiente"]
            if propias_h_pend:
                st.markdown("#### Eliminar Hito (solo tus Pendientes)")
                opciones_hdel = [
                    f"{i+1}. {it.get('descripcion','(sin descripción)')} | {it.get('fecha','')} | S/. {float(it.get('monto',0) or 0):.2f}"
                    for i, it in enumerate(propias_h_pend)
                ]
                if "idx_del_hito_pas" not in st.session_state:
                    st.session_state.idx_del_hito_pas = 0

                sel_hdel = st.selectbox(
                    "Selecciona tu hito Pendiente",
                    opciones_hdel,
                    index=min(st.session_state.idx_del_hito_pas, len(opciones_hdel)-1),
                    key="sel_del_hito_pas"
                )
                st.session_state.idx_del_hito_pas = opciones_hdel.index(sel_hdel)
                h_del = propias_h_pend[st.session_state.idx_del_hito_pas]
                hid = h_del.get("id")

                if st.button("🗑️ Eliminar Hito Seleccionado", use_container_width=True, type="secondary", key="btn_del_hito_pas"):
                    if not hid:
                        st.error("❌ No se encontró ID para eliminar este hito.")
                    else:
                        okd, msgd = eliminar_hito_pago(obra_codigo, hid)
                        if okd:
                            st.success("✅ Hito eliminado.")
                            st.session_state.idx_del_hito_pas = 0
                            st.rerun()
                        else:
                            st.error(f"❌ {msgd}")

    else:
        st.markdown("## Bienvenido (Modo Pasante)\nSelecciona una obra desde el panel lateral para comenzar.")

#=====================================================
#==================== CSS PCERRAR SESIÓN  ====================
st.sidebar.markdown("""
<style>
    /* Solo botones "primary" en el sidebar */
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #e74c3c !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== BOTÓN CERRAR SESIÓN ====================
st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión", 
                    use_container_width=True, 
                    type="primary",  # Cambiado a "primary"
                    help="Salir del sistema"):
    # Limpiar todas las variables de sesión
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
    
