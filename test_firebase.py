import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

docs = list(db.collection("obras").stream())
print("Cantidad de obras:", len(docs))

for d in docs:
    print(d.id, d.to_dict())
