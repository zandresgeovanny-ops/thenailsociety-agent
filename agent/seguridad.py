# agent/seguridad.py — Utilidades de seguridad (límite de intentos)
# Generado por AgentKit

"""
Límite de intentos en memoria por IP (anti fuerza bruta en el login y
anti-spam en las reservas públicas). Suficiente para un solo proceso (Railway).
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException

_intentos: dict[str, list[float]] = defaultdict(list)


def _ip(request: Request) -> str:
    # Detrás de UN proxy de confianza (Railway), la IP real del cliente es la
    # ÚLTIMA que el proxy agrega a X-Forwarded-For. El cliente puede falsificar
    # las primeras entradas, así que NUNCA tomamos la primera (eso permitía
    # evadir el límite rotando IPs falsas).
    reenviado = request.headers.get("x-forwarded-for")
    if reenviado:
        partes = [p.strip() for p in reenviado.split(",") if p.strip()]
        if partes:
            return partes[-1]
    return request.client.host if request.client else "desconocida"


def limitar(request: Request, clave: str, maximo: int, ventana_seg: int):
    """Lanza 429 si una IP supera `maximo` intentos de `clave` en `ventana_seg` segundos."""
    ip = _ip(request)
    llave = f"{clave}:{ip}"
    ahora = time.time()
    _intentos[llave] = [t for t in _intentos[llave] if ahora - t < ventana_seg]
    if len(_intentos[llave]) >= maximo:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera un momento e inténtalo de nuevo.")
    _intentos[llave].append(ahora)
