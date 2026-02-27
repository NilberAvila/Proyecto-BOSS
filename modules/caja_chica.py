# modules/caja_chica.py
import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import io
from firebase_admin import firestore

# Obtener cliente de Firestore
db = firestore.client()

# =========================
# FUNCIONES FIRESTORE
# =========================
def guardar_movimiento(mov):
    db.collection("movimientos").add(mov)

def cargar_movimientos(obra_codigo):
    # Filtrar por obra para seguridad
    docs = db.collection("movimientos").where("obra_codigo", "==", obra_codigo).stream()
    data = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        data.append(item)

    columnas = [
        "fecha", "usuario", "tipo", "monto", "descripcion", 
        "categoria", "estado", "aprobado_por", "comprobante", "id", "obra_codigo"
    ]

    if not data:
        return pd.DataFrame(columns=columnas)

    df = pd.DataFrame(data)
    # Asegurar que existan todas las columnas
    for col in columnas:
        if col not in df.columns:
            df[col] = ""

    return df

def calcular_totales(obra_codigo):
    ingresos = 0
    egresos = 0
    docs = db.collection("movimientos").where("obra_codigo", "==", obra_codigo).stream()
    for d in docs:
        m = d.to_dict()
        if m.get("tipo") == "ingreso":
            ingresos += m.get("monto", 0)
        # Sumar egresos SOLO si están aprobados
        if m.get("tipo") == "egreso" and m.get("estado") == "Aprobado":
            egresos += m.get("monto", 0)
    return ingresos, egresos, ingresos - egresos

def guardar_comprobante_base64(archivo):
    if not archivo:
        return ""
    contenido = archivo.read()
    return base64.b64encode(contenido).decode("utf-8")

# =========================
# INTERFAZ PRINCIPAL
# =========================
def mostrar_caja_chica():
    # --- CSS CORREGIDO (SOLUCIÓN FONDO BLANCO) ---
    st.markdown("""
        <style>
            /* 1. TEXTOS GENERALES (Títulos y etiquetas oscuras) */
            div[data-testid="stMarkdownContainer"] h3,
            div[data-testid="stMarkdownContainer"] h4 { color: #1E293B !important; }
            div[data-testid="stWidgetLabel"] p { color: #1E293B !important; font-weight: bold !important; }
            div[data-testid="stCaptionContainer"] p { color: #475569 !important; }
            
            /* 2. RADIO BUTTONS */
            div[data-testid="stRadio"] label p {
                color: #1E293B !important;
                font-weight: 500 !important;
            }
            div[data-testid="stRadio"] > div { margin-top: -10px; }

            /* 3. MODO YAPE (Quitar flechas) */
            input[type="number"]::-webkit-inner-spin-button,
            input[type="number"]::-webkit-outer-spin-button {
                -webkit-appearance: none;
                margin: 0;
            }
            input[type="number"] { -moz-appearance: textfield; }
            button[data-testid="stNumberInputStepUp"],
            button[data-testid="stNumberInputStepDown"] { display: none !important; }
            
            /* 4. SOLUCIÓN DEFINITIVA PARA EL FONDO DEL MONTO */
            
            /* (A) EL CONTENEDOR (La caja externa) */
            div[data-testid="stNumberInput"] div[data-baseweb="input"] {
                background-color: #262730 !important; /* Gris oscuro fuerte */
                border: 1px solid rgba(0, 0, 0, 0.2) !important;
                border-radius: 0.5rem !important;
            }
            
            /* (B) EL INPUT DONDE ESCRIBES (La causa del problema) */
            /* Forzamos que el propio campo de texto tenga fondo oscuro */
            div[data-testid="stNumberInput"] input[type="number"] {
                background-color: #262730 !important; /* <--- ESTO ES LA CLAVE */
                color: #ffffff !important;            /* Texto BLANCO */
                caret-color: #ffffff !important;      /* Cursor BLANCO */
                -webkit-text-fill-color: #ffffff !important;
                font-size: 1.2rem !important;
                padding-right: 1rem !important;
                font-weight: 500 !important;
            }
            
            /* Placeholder */
            div[data-testid="stNumberInput"] input::placeholder {
                color: rgba(255, 255, 255, 0.5) !important;
            }

            /* 5. IGUALAR LOS OTROS INPUTS AL MISMO ESTILO OSCURO */
            div[data-testid="stTextInput"] div[data-baseweb="input"],
            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                background-color: #262730 !important;
                border: 1px solid rgba(0, 0, 0, 0.2) !important;
                border-radius: 0.5rem !important;
            }
            
            /* Texto blanco para inputs de texto y select */
            div[data-testid="stTextInput"] input,
            div[data-testid="stSelectbox"] div[data-testid="stMarkdownContainer"] p {
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
            }
            
            /* Flecha del select en blanco */
            div[data-testid="stSelectbox"] svg { fill: #ffffff !important; }
        </style>
    """, unsafe_allow_html=True)
    
    usuario = st.session_state.get("usuario_logueado", "desconocido")
    es_jefe = st.session_state.get("auth") == "jefe"
    obra_codigo = st.session_state.get("obra_seleccionada")
    
    if not obra_codigo:
        st.warning("⚠️ Selecciona una obra primero para gestionar su caja chica.")
        return

    # --- MÉTRICAS SUPERIORES ---
    ingresos, egresos_aprobados, saldo = calcular_totales(obra_codigo)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Ingresos", f"S/ {ingresos:,.2f}")
    col2.metric("Total Egresos aprobados", f"S/ {egresos_aprobados:,.2f}")
    
    if saldo < 100 and saldo > 0:
        col3.metric("Saldo actual", f"S/ {saldo:,.2f}", delta="⚠️ Saldo bajo", delta_color="off")
    else:
        col3.metric("Saldo actual", f"S/ {saldo:,.2f}")

    st.divider()

    # --- GESTIÓN DE MENSAJES DE ÉXITO ---
    if st.session_state.get("exito_caja"):
        st.success(st.session_state.exito_caja)
        st.session_state.exito_caja = None 

    # --- PESTAÑAS DINÁMICAS POR ROL ---
    if es_jefe:
        tabs = st.tabs(["📝 Registrar", "⚖️ Solicitudes Pendientes", "📋 Historial"])
        tab_reg, tab_sol, tab_hist = tabs[0], tabs[1], tabs[2]
    else:
        tabs = st.tabs(["📝 Registrar", "📋 Historial"])
        tab_reg, tab_hist = tabs[0], tabs[1]

    # =========================
    # PESTAÑA 1: REGISTRAR
    # =========================
    with tab_reg:
        st.markdown("### Registrar Movimiento")
        
        # LÓGICA PASANTE
        if es_jefe:
            tipo_mov = st.radio("Tipo de movimiento", ["Egreso (Gasto)", "Ingreso (Reposición)"], horizontal=True)
        else:
            st.info("ℹ️ Solo puedes registrar gastos (Egresos). Para reposición de caja, contacta al jefe.")
            tipo_mov = "Egreso (Gasto)"
        
        # FORMULARIO
        with st.form("form_caja", clear_on_submit=True):
            
            # MODO YAPE
            monto = st.number_input("Monto S/.", value=None, placeholder="0.00", format="%.2f")
            
            desc = st.text_input("Descripción / Motivo", placeholder="Ej: Compra de candado")
            
            st.markdown('<p style="margin-bottom: 8px; font-size: 14px; font-weight: 400; color: rgb(49, 51, 63);"><strong>Categoría</strong></p>', unsafe_allow_html=True)
            if tipo_mov == "Ingreso (Reposición)":
                cat = st.selectbox("Categoría", ["Reposición fondo", "Transferencia banco", "Otros ingresos"], label_visibility="collapsed")
            else:
                cat = st.selectbox("Categoría", ["Viáticos", "Transporte", "Materiales menores", "Limpieza/oficina", "Imprevistos", "Otros"], label_visibility="collapsed")

            comp = st.file_uploader("Comprobante (foto/imagen)", type=["jpg", "png", "jpeg"], key="comp_reg")

            if st.form_submit_button("Guardar Movimiento", type="primary", use_container_width=True):
                # Validaciones
                if monto is None or monto <= 0:
                    st.error("❌ Debes escribir un monto mayor a 0.")
                elif tipo_mov.startswith("Egreso") and monto > saldo:
                    st.error(f"❌ No hay saldo suficiente. Saldo disponible: S/ {saldo:.2f}")
                elif not desc:
                    st.error("❌ La descripción es obligatoria.")
                else:
                    comprobante_b64 = guardar_comprobante_base64(comp)
                    es_ingreso = "Ingreso" in tipo_mov
                    
                    # --- LÓGICA DE APROBACIÓN AUTOMÁTICA ---
                    if es_ingreso or es_jefe:
                        nuevo_estado = "Aprobado"
                        aprobado_por_quien = usuario
                        mensaje_exito = "✅ Movimiento registrado y aprobado correctamente."
                    else:
                        nuevo_estado = "Pendiente"
                        aprobado_por_quien = ""
                        mensaje_exito = "⏳ Gasto registrado. Pendiente de aprobación por el jefe."

                    mov = {
                        "obra_codigo": obra_codigo,
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "usuario": usuario,
                        "tipo": "ingreso" if es_ingreso else "egreso",
                        "monto": float(monto),
                        "descripcion": desc,
                        "categoria": cat,
                        "estado": nuevo_estado,
                        "aprobado_por": aprobado_por_quien,
                        "comprobante": comprobante_b64
                    }
                    guardar_movimiento(mov)
                    
                    st.session_state.exito_caja = mensaje_exito
                    st.rerun()

    # =========================
    # PESTAÑA 2: SOLICITUDES PENDIENTES (SÓLO JEFE)
    # =========================
    if es_jefe:
        with tab_sol:
            df = cargar_movimientos(obra_codigo)
            st.markdown("### ⏳ Pendientes de Aprobación")
            pendientes = df[(df["tipo"] == "egreso") & (df["estado"] == "Pendiente")]
            
            if pendientes.empty:
                st.info("✅ No hay gastos pendientes de aprobación.")
            else:
                for _, row in pendientes.iterrows():
                    with st.expander(f"📅 {row['fecha']} | 👤 {row['usuario']} | 💰 S/ {row['monto']:.2f}"):
                        st.write(f"**Descripción:** {row['descripcion']}")
                        st.write(f"**Categoría:** {row['categoria']}")
                        
                        if row["comprobante"]:
                            try:
                                st.image(base64.b64decode(row["comprobante"]), use_container_width=True)
                            except Exception:
                                st.warning("⚠️ Comprobante no válido.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Aprobar", key=f"apr_{row['id']}", use_container_width=True, type="primary"):
                                db.collection("movimientos").document(row["id"]).update({
                                    "estado": "Aprobado",
                                    "aprobado_por": usuario
                                })
                                st.session_state.exito_caja = "✅ Gasto Aprobado."
                                st.rerun()
                        with col2:
                            if st.button("❌ Rechazar", key=f"rec_{row['id']}", use_container_width=True):
                                db.collection("movimientos").document(row["id"]).update({
                                    "estado": "Rechazado",
                                    "aprobado_por": usuario
                                })
                                st.session_state.exito_caja = "⚠️ Gasto Rechazado."
                                st.rerun()

    # =========================
    # PESTAÑA 3: HISTORIAL
    # =========================
    with tab_hist:
        df = cargar_movimientos(obra_codigo)
        st.markdown("### 📋 Historial de Movimientos")
        st.caption("Historial de movimientos procesados (Aprobados o Rechazados).")
        
        if df.empty:
            st.info("📭 Aún no hay movimientos registrados.")
        else:
            df_kardex = df[df["estado"] != "Pendiente"].copy()
            
            if df_kardex.empty:
                st.info("⏳ Todo está pendiente de aprobación.")
            else:
                df_kardex["fecha_dt"] = pd.to_datetime(df_kardex["fecha"], errors="coerce")
                df_kardex = df_kardex.sort_values("fecha", ascending=False)
                df_kardex["Mes"] = df_kardex["fecha_dt"].dt.strftime("%Y-%m") 
                
                meses_disponibles = df_kardex["Mes"].dropna().unique()
                
                c1, c2, c_vacia = st.columns([1, 1, 1])
                with c1:
                    st.markdown('<p style="margin-bottom: 8px; font-size: 14px; font-weight: 400; color: rgb(49, 51, 63);"><strong>📅 Filtrar Mes:</strong></p>', unsafe_allow_html=True)
                    mes_sel = st.selectbox("📅 Filtrar Mes:", options=["Todos"] + list(meses_disponibles), label_visibility="collapsed")
                with c2:
                    st.markdown('<p style="margin-bottom: 8px; font-size: 14px; font-weight: 400; color: rgb(49, 51, 63);"><strong>⚖️ Filtrar Estado:</strong></p>', unsafe_allow_html=True)
                    est_sel = st.selectbox("⚖️ Filtrar Estado:", options=["Todos", "Aprobado", "Rechazado"], label_visibility="collapsed")
                
                if mes_sel != "Todos":
                    df_kardex = df_kardex[df_kardex["Mes"] == mes_sel]
                if est_sel != "Todos":
                    df_kardex = df_kardex[df_kardex["estado"] == est_sel]

                st.divider()

                if not df_kardex.empty:
                    df_export = df_kardex[["fecha", "usuario", "tipo", "monto", "descripcion", "categoria", "estado"]].copy()
                    df_export.columns = ["Fecha", "Responsable", "Tipo", "Monto (S/)", "Descripción", "Categoría", "Estado"]
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_export.to_excel(writer, sheet_name='Kardex', index=False)
                        workbook = writer.book
                        worksheet = writer.sheets['Kardex']
                        fmt_header = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#4A5C6A', 'border': 1})
                        fmt_money = workbook.add_format({'num_format': 'S/ #,##0.00', 'border': 1})
                        fmt_base = workbook.add_format({'border': 1})
                        
                        worksheet.set_column('A:A', 18, fmt_base)
                        worksheet.set_column('B:B', 20, fmt_base)
                        worksheet.set_column('C:C', 12, fmt_base)
                        worksheet.set_column('D:D', 15, fmt_money)
                        worksheet.set_column('E:E', 40, fmt_base)
                        worksheet.set_column('F:F', 20, fmt_base)
                        worksheet.set_column('G:G', 15, fmt_base)
                        
                        for col_num, value in enumerate(df_export.columns.values):
                            worksheet.write(0, col_num, value, fmt_header)
                            
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label=f"📥 Descargar Historial a Excel ({len(df_kardex)} registros)",
                        data=excel_data,
                        file_name=f"Kardex_{obra_codigo}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="primary"
                    )
                    
                    st.markdown("#### 📊 Vista Rápida")
                    st.dataframe(
                        df_export,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Monto (S/)": st.column_config.NumberColumn(format="S/ %.2f")
                        }
                    )
                    
                    st.divider()
                    
                    st.markdown("#### 📖 Vista Detallada (Comprobantes)")
                    for _, row in df_kardex.iterrows():
                        icono = "🟢" if row['tipo'] == 'ingreso' else ("🔴" if row['estado'] == 'Rechazado' else "🔵")
                        t_text = row['tipo'].upper()
                        titulo = f"{icono} {row['fecha']} | {t_text} | S/ {float(row['monto']):.2f} [{row['estado']}]"
                        
                        with st.expander(titulo):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write(f"**Descripción:** {row['descripcion']}")
                                st.write(f"**Categoría:** {row['categoria']}")
                            with c2:
                                st.write(f"**Registrado por:** {row['usuario']}")
                                if row['tipo'] == 'egreso':
                                    st.write(f"**Revisado por:** {row['aprobado_por']}")
                                    
                            if row["comprobante"]:
                                st.markdown("**📷 Comprobante adjunto:**")
                                try:
                                    st.image(base64.b64decode(row["comprobante"]), width=350)
                                except Exception:
                                    st.warning("⚠️ No se pudo cargar la imagen.")
                else:
                    st.info("No hay movimientos que coincidan con los filtros.")