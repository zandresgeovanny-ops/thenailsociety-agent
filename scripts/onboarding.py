# scripts/onboarding.py — Alta automática de un salón nuevo
# Generado por AgentKit

"""
Monta un cliente nuevo en minutos: crea todas las tablas, aplica el blindaje
de Postgres (extensión + constraint anti-solapamiento + RLS), siembra servicios
y empleadas, y crea el usuario administrador.

Uso:
    1) Configura DATABASE_URL en .env apuntando a la base del cliente nuevo.
    2) Copia config/onboarding.example.yaml -> config/onboarding.yaml y edítalo.
    3) python scripts/onboarding.py            (o pasa otra ruta de yaml)
"""

import os
import sys
import asyncio
from datetime import time

import yaml
from sqlalchemy import select, text

# Permite ejecutar el script desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.memory import (
    engine, async_session, inicializar_db,
    Categoria, Servicio, Empleado, HorarioEmpleado, Usuario,
)
from agent.auth import hash_password

# Horario laboral por defecto para cada empleada: L-V 9-19, Sáb 9-14
HORARIO_DEFECTO = [(d, time(9, 0), time(19, 0)) for d in range(5)] + [(5, time(9, 0), time(14, 0))]

# DDL específico de Postgres/Supabase (no aplica en SQLite local)
DDL_POSTGRES = [
    "create extension if not exists btree_gist;",
    """
    do $$ begin
      if not exists (select 1 from pg_constraint where conname = 'citas_sin_solapamiento') then
        alter table citas add constraint citas_sin_solapamiento
          exclude using gist (empleado_id with =, tstzrange(inicia_en, termina_en) with &&)
          where (empleado_id is not null and estado <> 'cancelada');
      end if;
    end $$;
    """,
    "alter table clientes  enable row level security;",
    "alter table servicios enable row level security;",
    "alter table empleados enable row level security;",
    "alter table categorias enable row level security;",
    "alter table horarios_empleado enable row level security;",
    "alter table citas     enable row level security;",
    "alter table mensajes  enable row level security;",
    "alter table usuarios  enable row level security;",
]


async def main(config_path: str):
    if not os.path.exists(config_path):
        print(f"No encuentro el archivo de configuración: {config_path}")
        print("Copia config/onboarding.example.yaml -> config/onboarding.yaml y edítalo.")
        return

    cfg = yaml.safe_load(open(config_path, encoding="utf-8"))
    negocio = cfg.get("negocio", {}).get("nombre", "el salón")
    print(f"\n=== Onboarding de: {negocio} ===\n")

    # 1) Crear todas las tablas (a partir de los modelos)
    await inicializar_db()
    print("[OK]Tablas creadas")

    # 2) Blindaje de Postgres (extensión, constraint anti-solapamiento, RLS)
    if engine.dialect.name == "postgresql":
        async with engine.begin() as conn:
            for stmt in DDL_POSTGRES:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    print(f"  aviso (DDL): {e}")
        print("[OK]Constraint anti-solapamiento + RLS aplicados")

    async with async_session() as s:
        # 3) Servicios + categorías + empleadas (solo si la base está vacía)
        ya_hay = (await s.execute(select(Servicio).limit(1))).scalars().first()
        if ya_hay:
            print("-Ya había servicios cargados; no se resiembra.")
        else:
            cache_cat: dict[str, object] = {}
            for sv in cfg.get("servicios", []):
                cat_id = None
                cat = sv.get("categoria")
                if cat:
                    if cat not in cache_cat:
                        c = Categoria(nombre=cat)
                        s.add(c)
                        await s.flush()
                        cache_cat[cat] = c.id
                    cat_id = cache_cat[cat]
                s.add(Servicio(
                    nombre=sv["nombre"], duracion_min=sv.get("duracion_min", 60),
                    precio=sv.get("precio"), categoria_id=cat_id,
                ))
            for emp in cfg.get("empleadas", []):
                e = Empleado(nombre=emp["nombre"])
                s.add(e)
                await s.flush()
                for dia, hi, hf in HORARIO_DEFECTO:
                    s.add(HorarioEmpleado(empleado_id=e.id, dia_semana=dia, hora_inicio=hi, hora_fin=hf))
            await s.commit()
            print(f"[OK]{len(cfg.get('servicios', []))} servicios y {len(cfg.get('empleadas', []))} empleadas sembrados")

        # 4) Usuario administrador
        adm = cfg["admin"]
        existe = (await s.execute(
            select(Usuario).where(Usuario.email == adm["email"].lower())
        )).scalar_one_or_none()
        if existe:
            print(f"- El admin {adm['email']} ya existia.")
        else:
            s.add(Usuario(
                email=adm["email"].lower(), password_hash=hash_password(adm["password"]),
                rol="admin", nombre=adm.get("nombre"),
            ))
            await s.commit()
            print(f"[OK]Admin creado: {adm['email']}")

    print(f"\n=== ¡Listo! {negocio} quedó configurado. ===")
    print("Siguiente: configurar variables en Railway, el webhook de Twilio y entrar a /panel.\n")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "config/onboarding.yaml"
    asyncio.run(main(ruta))
