# caja_chica.py
import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from firebase_admin import firestore

# Obtener cliente de Firestore (Firebase ya inicializado en app.py)
db = firestore.client()


# FUNCIONES FIRESTORE
def guardar_movimiento(mov):
    db.collection("movimientos").add(mov)

def cargar_movimientos():
    docs = db.collection("movimientos").stream()
    data = []

    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        data.append(item)

    # 🔒 ESQUEMA FIJO (CLAVE)
    columnas = [
        "fecha",
        "usuario",
        "tipo",
        "monto",
        "descripcion",
        "categoria",
        "estado",
        "aprobado_por",
        "comprobante",
        "id",
    ]

    if not data:
        return pd.DataFrame(columns=columnas)

    df = pd.DataFrame(data)

    # 🔒 Asegurar columnas aunque falten en Firestore
    for col in columnas:
        if col not in df.columns:
            df[col] = ""

    return df



def calcular_totales():
    ingresos = 0
    egresos = 0

    docs = db.collection("movimientos").stream()
    for d in docs:
        m = d.to_dict()
        if m.get("tipo") == "ingreso":
            ingresos += m.get("monto", 0)
        if m.get("tipo") == "egreso" and m.get("estado") == "Aprobado":
            egresos += m.get("monto", 0)

    return ingresos, egresos, ingresos - egresos

# =========================
# COMPROBANTES (BASE64)
# =========================
def guardar_comprobante_base64(archivo):
    if not archivo:
        return ""
    contenido = archivo.read()
    return base64.b64encode(contenido).decode("utf-8")

# =========================
# INTERFAZ PRINCIPAL
# =========================
def mostrar_caja_chica():
    usuario = st.session_state.get("usuario_logueado", "desconocido")
    es_jefe = st.session_state.get("auth") == "jefe"

    # Totales
    ingresos, egresos_aprobados, saldo = calcular_totales()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Ingresos", f"S/ {ingresos:,.2f}")
    col2.metric("Total Egresos aprobados", f"S/ {egresos_aprobados:,.2f}")
    col3.metric("Saldo actual", f"S/ {saldo:,.2f}")

    tab_reg, tab_mis, tab_apr = st.tabs(["Registrar", "Mis movimientos", "Aprobaciones"])

    # =========================
    # REGISTRAR
    # =========================
    with tab_reg:
        st.markdown("### Registrar Ingreso (reposición)")
        if not es_jefe:
            st.info("Solo el jefe puede registrar ingresos/reposiciones")
        else:
            with st.form("form_ingreso"):
                monto_ing = st.number_input("Monto S/.", min_value=0.01, step=0.01, format="%.2f")
                desc_ing = st.text_input("Descripción / motivo")
                cat_ing = st.selectbox("Categoría", [
                    "Reposición fondo", "Transferencia banco", "Otros ingresos"
                ])
                comp_ing = st.file_uploader(
                    "Comprobante (opcional)",
                    type=["jpg", "png"],
                    key="comp_ing"
                )

                if st.form_submit_button("Registrar Ingreso", type="primary"):
                    comprobante = guardar_comprobante_base64(comp_ing)
                    mov = {
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "usuario": usuario,
                        "tipo": "ingreso",
                        "monto": monto_ing,
                        "descripcion": desc_ing,
                        "categoria": cat_ing,
                        "comprobante": comprobante,
                        "estado": "Aprobado",
                        "aprobado_por": usuario
                    }
                    guardar_movimiento(mov)
                    st.success("Ingreso registrado correctamente")
                    st.rerun()

        st.divider()

        st.markdown("### Registrar Egreso (gasto)")
        with st.form("form_egreso"):
            monto_egr = st.number_input("Monto S/.", min_value=0.01, step=0.01, format="%.2f")
            desc_egr = st.text_input("Descripción / motivo")
            cat_egr = st.selectbox("Categoría", [
                "Viáticos", "Transporte", "Materiales menores",
                "Limpieza/oficina", "Imprevistos", "Otros"
            ])
            comp_egr = st.file_uploader(
                "Comprobante (foto)",
                type=["jpg", "png"],
                key="comp_egr"
            )

            if st.form_submit_button("Registrar Egreso", type="primary"):
                comprobante = guardar_comprobante_base64(comp_egr)
                mov = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "usuario": usuario,
                    "tipo": "egreso",
                    "monto": monto_egr,
                    "descripcion": desc_egr,
                    "categoria": cat_egr,
                    "comprobante": comprobante,
                    "estado": "Pendiente",
                    "aprobado_por": ""
                }
                guardar_movimiento(mov)
                st.success("Egreso registrado. Espera aprobación del jefe.")
                st.rerun()

    # =========================
    # MIS MOVIMIENTOS
    # =========================
    with tab_mis:
        df = cargar_movimientos()
        if df.empty:
            st.info("No tienes movimientos registrados aún")
        else:
            mios = df[df["usuario"] == usuario]
            st.dataframe(
                mios[["fecha", "tipo", "monto", "descripcion", "categoria", "estado"]]
                .sort_values("fecha", ascending=False),
                use_container_width=True,
                hide_index=True
            )

    # =========================
    # APROBACIONES
    # =========================
    with tab_apr:
        if not es_jefe:
            st.info("Solo el jefe puede aprobar movimientos")
            return

        df = cargar_movimientos()

        # 🔒 BLINDAJE DEFINITIVO
        for col, default in {
            "tipo": "",
            "estado": "",
        }.items():
            if col not in df.columns:
                df[col] = default

        pendientes = df[
            (df["tipo"] == "egreso") &
            (df["estado"] == "Pendiente")
        ]

        if pendientes.empty:
            st.success("No hay gastos pendientes de aprobación")
        else:
            for _, row in pendientes.iterrows():
                with st.expander(f"{row['fecha']} | {row['usuario']} | S/ {row['monto']:.2f}"):
                    st.write("**Descripción:**", row["descripcion"])
                    st.write("**Categoría:**", row["categoria"])

                    if row["comprobante"]:
                        try:
                            st.image(base64.b64decode(row["comprobante"]))
                        except Exception:
                            st.warning("Comprobante no válido")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Aprobar", key=f"apr_{row['id']}"):
                            db.collection("movimientos").document(row["id"]).update({
                                "estado": "Aprobado",
                                "aprobado_por": usuario
                            })
                            st.success("Aprobado")
                            st.rerun()

                    with col2:
                        if st.button("Rechazar", key=f"rec_{row['id']}"):
                            db.collection("movimientos").document(row["id"]).update({
                                "estado": "Rechazado"
                            })
                            st.success("Rechazado")
                            st.rerun()
