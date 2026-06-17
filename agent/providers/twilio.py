# agent/providers/twilio.py — Adaptador para Twilio WhatsApp
# Generado por AgentKit

import os
import logging
import base64
import hmac
import hashlib
import httpx
from fastapi import Request
from agent.providers.base import ProveedorWhatsApp, MensajeEntrante

logger = logging.getLogger("agentkit")


class ProveedorTwilio(ProveedorWhatsApp):
    """Proveedor de WhatsApp usando Twilio."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        # Validación de firma: activada por defecto. Poné VALIDAR_FIRMA_TWILIO=false
        # solo si querés probar el webhook localmente con datos falsos.
        self.validar_firma = os.getenv("VALIDAR_FIRMA_TWILIO", "true").lower() == "true"

    def _url_publica(self, request: Request) -> str:
        """
        Reconstruye la URL pública exacta que Twilio usó para firmar.
        Detrás del proxy de Railway, el esquema/host reales vienen en los headers
        X-Forwarded-Proto y Host (no en request.url, que es interno).
        """
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("host", request.url.netloc)
        url = f"{proto}://{host}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        return url

    def _firma_valida(self, url: str, params: dict, firma: str | None) -> bool:
        """
        Valida la firma de Twilio: HMAC-SHA1 (con el Auth Token como clave) sobre
        la URL + cada par clave/valor del POST ordenado por clave, en base64.
        """
        if not firma or not self.auth_token:
            return False
        data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
        mac = hmac.new(self.auth_token.encode(), data.encode("utf-8"), hashlib.sha1)
        esperado = base64.b64encode(mac.digest()).decode()
        return hmac.compare_digest(esperado, firma)

    async def parsear_webhook(self, request: Request) -> list[MensajeEntrante]:
        """Parsea el payload form-encoded de Twilio, validando primero la firma."""
        form = await request.form()
        params = {k: str(v) for k, v in form.items()}

        # Seguridad: descartar requests que no vengan realmente de Twilio
        if self.validar_firma:
            url = self._url_publica(request)
            firma = request.headers.get("X-Twilio-Signature")
            if not self._firma_valida(url, params, firma):
                logger.warning("Webhook rechazado: firma de Twilio inválida o ausente")
                return []

        texto = params.get("Body", "")
        telefono = params.get("From", "").replace("whatsapp:", "")
        mensaje_id = params.get("MessageSid", "")
        if not texto:
            return []
        return [MensajeEntrante(
            telefono=telefono,
            texto=texto,
            mensaje_id=mensaje_id,
            es_propio=False,
        )]

    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """Envía mensaje via Twilio API."""
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.warning("Variables de Twilio no configuradas")
            return False
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
        data = {
            "From": f"whatsapp:{self.phone_number}",
            "To": f"whatsapp:{telefono}",
            "Body": mensaje,
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=data, headers=headers)
            if r.status_code != 201:
                logger.error(f"Error Twilio: {r.status_code} — {r.text}")
            return r.status_code == 201
