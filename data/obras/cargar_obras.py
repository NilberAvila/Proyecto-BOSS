import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# 📍 Directorio del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔑 Ruta al service account (subimos un nivel)
cred_path = os.path.join(BASE_DIR, "..", "..", "firebase_key.json")

cred = credentials.Certificate(os.path.normpath(cred_path))
firebase_admin.initialize_app(cred)

db = firestore.client()

# 📂 Rutas a los JSON (misma carpeta que el script)
pachacutec_path = os.path.join(BASE_DIR, "pachacutec.json")
rinconada_path = os.path.join(BASE_DIR, "rinconada.json")

with open(pachacutec_path, "r", encoding="utf-8") as f:
    pachacutec = json.load(f)

with open(rinconada_path, "r", encoding="utf-8") as f:
    rinconada = json.load(f)

# 🔥 Subir a Firestore con estructura correcta
db.collection("obras").document("Pachacutec").set(pachacutec)
db.collection("obras").document("Rinconada").set(rinconada)

print("✅ Obras cargadas correctamente en Firestore")
