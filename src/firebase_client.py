import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

load_dotenv()

def get_firestore_client():
    if not firebase_admin._apps:
        private_key = os.getenv("FIREBASE_PRIVATE_KEY")

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
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
        }

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

    return firestore.client()

if __name__ == "__main__":
    db = get_firestore_client()

    docs = db.collection("aberturas").limit(3).stream()

    for doc in docs:
        dados = doc.to_dict()

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

if __name__ == "__main__":

    aberturas = buscar_aberturas_por_semana("13/04/2026")

    for linha in dados_fake[1:]:
        print("Curso:", linha[0])
        print("Semana:", linha[1])
        print("Webhook:", linha[4])
        print("Tag iniciar F1:", linha[14])
        print("Fluxo 2:", linha[15])
        print("Código abertura:", linha[9])
        print("Cert:", linha[34])
        print("Aulas:", linha[35])
        print("PDF:", linha[36])