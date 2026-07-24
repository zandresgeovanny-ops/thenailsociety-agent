# scripts/simular_twilio.py — Simula un mensaje entrante de Twilio con firma válida
# Generado por AgentKit

"""
Prueba el webhook COMPLETO de The Nail Society sin necesitar un teléfono real.

Reproduce exactamente la firma que Twilio envía en la cabecera X-Twilio-Signature:
    base64( HMAC-SHA1( auth_token, url + pares_del_POST_ordenados_por_clave ) )

Así el webhook se prueba con VALIDAR_FIRMA_TWILIO=true — es decir, validando la
seguridad de verdad, no apagándola. Es el "Nivel 2" del plan de pruebas.

Uso:
    python scripts/simular_twilio.py "quiero una cita el viernes"
    python scripts/simular_twilio.py "hola" --de +524491112233
    python scripts/simular_twilio.py "hola" --url https://mi-app.up.railway.app/webhook

Requiere que el servidor esté corriendo:
    uvicorn agent.main:app --reload --port 8000
"""

import os
import sys
import base64
import hmac
import hashlib
import argparse

import httpx
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto (este script vive en scripts/)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(RAIZ, ".env"))


def firmar(url: str, params: dict, auth_token: str) -> str:
    """Calcula la firma X-Twilio-Signature igual que agent/providers/twilio.py."""
    data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    mac = hmac.new(auth_token.encode(), data.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode()


def main():
    parser = argparse.ArgumentParser(description="Simula un webhook de Twilio con firma válida")
    parser.add_argument("mensaje", help="Texto que 'envía' el cliente por WhatsApp")
    parser.add_argument("--url", default="http://localhost:8000/webhook",
                        help="URL del webhook (local o Railway). Default: http://localhost:8000/webhook")
    parser.add_argument("--de", default="+524491234567",
                        help="Número del cliente simulado. Default: +524491234567")
    args = parser.parse_args()

    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not auth_token:
        print("ERROR: falta TWILIO_AUTH_TOKEN en el .env")
        sys.exit(1)

    # Payload form-encoded tal como lo manda Twilio
    params = {
        "Body": args.mensaje,
        "From": f"whatsapp:{args.de}",
        "To": f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER', '+14155238886')}",
        "MessageSid": "SMsimulado00000000000000000000000",
    }

    firma = firmar(args.url, params, auth_token)
    headers = {"X-Twilio-Signature": firma}

    print(f">> POST {args.url}")
    print(f"   De: {args.de}")
    print(f"   Mensaje: {args.mensaje!r}")
    print(f"   Firma: {firma}")
    print()

    try:
        r = httpx.post(args.url, data=params, headers=headers, timeout=60)
    except httpx.ConnectError:
        print("ERROR: no pude conectar. ¿Está corriendo el servidor?")
        print("       uvicorn agent.main:app --reload --port 8000")
        sys.exit(1)

    print(f"<< {r.status_code}  {r.text}")
    if r.status_code == 200:
        print("\nOK — el webhook aceptó el mensaje (firma válida).")
        print("Mira los logs del servidor para ver la respuesta del agente.")
    else:
        print("\nAlgo falló. Revisa los logs del servidor.")


if __name__ == "__main__":
    main()
