# scripts/reset_password.py — Restablecer la contraseña de un usuario
# Generado por AgentKit

"""
Úsalo si la dueña (admin) olvidó su contraseña y no puede entrar.
Requiere DATABASE_URL en .env apuntando a la base del salón.

    python scripts/reset_password.py admin@mdnails.com NuevaClaveSegura123
"""

import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from agent.memory import async_session, Usuario
from agent.auth import hash_password


async def main(email: str, nueva: str):
    if len(nueva) < 8:
        print("La nueva contraseña debe tener al menos 8 caracteres.")
        return
    async with async_session() as s:
        u = (await s.execute(
            select(Usuario).where(Usuario.email == email.lower().strip())
        )).scalar_one_or_none()
        if u is None:
            print(f"No existe el usuario: {email}")
            return
        u.password_hash = hash_password(nueva)
        await s.commit()
        print(f"[OK] Contraseña de {email} restablecida.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python scripts/reset_password.py <email> <nueva_contraseña>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
