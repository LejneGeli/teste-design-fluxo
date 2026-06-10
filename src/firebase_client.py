import os
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv()


def get_firestore_client():
    if not firebase_admin._apps:
        private_key = os.getenv("FIREBASE_PRIVATE_KEY")

        if not private_key:
            raise ValueError("FIREBASE_PRIVATE_KEY não foi encontrada.")

        cred_dict = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": private_key.replace("\\n", "\n"),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com"),
        }

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    return firestore.client()


def buscar_aberturas_por_semana(semana):
    db = get_firestore_client()

    docs = (
        db.collection("aberturas")
        .where(filter=FieldFilter("semana", "==", semana))
        .stream()
    )

    return [doc.to_dict() for doc in docs]


if __name__ == "__main__":
    aberturas = buscar_aberturas_por_semana("13/04/2026")

    print("Total:", len(aberturas))

    for abertura in aberturas:
        print(abertura.get("nomeCurso"), "-", abertura.get("semana"))

def buscar_curso_por_codigo(codigo):
    db = get_firestore_client()

    docs = (
        db.collection("cursos")
        .where(filter=FieldFilter("codigo", "==", codigo))
        .limit(1)
        .stream()
    )

    for doc in docs:
        return doc.to_dict()

    return None