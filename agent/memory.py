# agent/memory.py — Memoria y datos del agente (PostgreSQL / Supabase)
# Generado por AgentKit

"""
Capa de datos del agente. Persiste el historial de conversaciones y las citas
en PostgreSQL (Supabase en producción) o SQLite (local, para pruebas).

El esquema está normalizado: clientes, servicios, empleados y citas se relacionan
por llaves foráneas, y las fechas se guardan como timestamp con zona horaria.
"""

import os
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Text, DateTime, Integer, Numeric, Boolean, ForeignKey, Uuid, select,
)
from dotenv import load_dotenv

load_dotenv()

# ════════════════════════════════════════════════════════════
# Configuración de la base de datos
# ════════════════════════════════════════════════════════════
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

# Normalizar la URL de Postgres (Supabase/Railway) al driver asíncrono asyncpg
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Argumentos de conexión específicos de asyncpg cuando usamos Postgres
connect_args: dict = {}
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    # asyncpg no entiende los parámetros estilo libpq en la query (ej. ?sslmode=require);
    # los quitamos y manejamos el SSL acá.
    if "?" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.split("?", 1)[0]
    connect_args = {
        "ssl": "require",           # Supabase exige conexión cifrada
        "statement_cache_size": 0,  # necesario para el pooler (pgbouncer) de Supabase
    }

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _ahora() -> datetime:
    """Fecha/hora actual con zona horaria (UTC)."""
    return datetime.now(timezone.utc)


# ════════════════════════════════════════════════════════════
# Modelos (deben coincidir con el esquema creado en Supabase)
# ════════════════════════════════════════════════════════════
class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    """Historial de conversación por número de teléfono."""
    __tablename__ = "mensajes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Cliente(Base):
    """Clienta o cliente, identificado por su número de WhatsApp."""
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    telefono: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


class Servicio(Base):
    """Servicio que ofrece el salón."""
    __tablename__ = "servicios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100))
    duracion_min: Mapped[int] = mapped_column(Integer, default=60)
    precio: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Empleado(Base):
    """Empleada / manicurista del salón."""
    __tablename__ = "empleados"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Cita(Base):
    """Cita agendada, relacionada con cliente, servicio y (opcional) empleada."""
    __tablename__ = "citas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    servicio_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("servicios.id"), nullable=True)
    empleado_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    inicia_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    termina_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    origen: Mapped[str] = mapped_column(String(20), default="whatsapp")
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


async def inicializar_db():
    """Crea las tablas que falten (idempotente; en Supabase ya existen vía migraciones)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ════════════════════════════════════════════════════════════
# Historial de conversación
# ════════════════════════════════════════════════════════════
async def guardar_mensaje(telefono: str, role: str, content: str):
    """Guarda un mensaje en el historial de conversación."""
    async with async_session() as session:
        session.add(Mensaje(telefono=telefono, role=role, content=content))
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    """Recupera los últimos N mensajes de una conversación, en orden cronológico."""
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.creado_en.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = list(result.scalars().all())
        mensajes.reverse()  # los más recientes venían primero
        return [{"role": m.role, "content": m.content} for m in mensajes]


async def limpiar_historial(telefono: str):
    """Borra todo el historial de una conversación."""
    async with async_session() as session:
        result = await session.execute(select(Mensaje).where(Mensaje.telefono == telefono))
        for m in result.scalars().all():
            await session.delete(m)
        await session.commit()


# ════════════════════════════════════════════════════════════
# Clientes, servicios y citas
# ════════════════════════════════════════════════════════════
async def buscar_o_crear_cliente(telefono: str, nombre: str | None = None) -> uuid.UUID:
    """Devuelve el id del cliente; lo crea si no existe. Completa el nombre si faltaba."""
    async with async_session() as session:
        result = await session.execute(select(Cliente).where(Cliente.telefono == telefono))
        cliente = result.scalar_one_or_none()
        if cliente is None:
            cliente = Cliente(telefono=telefono, nombre=nombre)
            session.add(cliente)
        elif nombre and not cliente.nombre:
            cliente.nombre = nombre
        await session.commit()
        return cliente.id


async def listar_servicios() -> list[dict]:
    """Lista los servicios activos del salón (catálogo en vivo desde la DB)."""
    async with async_session() as session:
        query = select(Servicio).where(Servicio.activo.is_(True)).order_by(Servicio.nombre)
        result = await session.execute(query)
        return [
            {
                "id": str(s.id),
                "nombre": s.nombre,
                "duracion_min": s.duracion_min,
                "precio": float(s.precio) if s.precio is not None else None,
            }
            for s in result.scalars().all()
        ]


async def guardar_cita(
    cliente_id: uuid.UUID,
    servicio_id: uuid.UUID | None,
    inicia_en: datetime,
    termina_en: datetime | None = None,
    notas: str | None = None,
) -> dict:
    """Registra una cita y devuelve sus datos básicos."""
    async with async_session() as session:
        cita = Cita(
            cliente_id=cliente_id,
            servicio_id=servicio_id,
            inicia_en=inicia_en,
            termina_en=termina_en,
            notas=notas,
        )
        session.add(cita)
        await session.commit()
        return {"id": str(cita.id), "inicia_en": cita.inicia_en.isoformat(), "estado": cita.estado}


async def obtener_citas(telefono: str) -> list[dict]:
    """Recupera las citas de un cliente (con el nombre del servicio)."""
    async with async_session() as session:
        query = (
            select(Cita, Servicio.nombre)
            .join(Cliente, Cita.cliente_id == Cliente.id)
            .outerjoin(Servicio, Cita.servicio_id == Servicio.id)
            .where(Cliente.telefono == telefono)
            .order_by(Cita.inicia_en.desc())
        )
        result = await session.execute(query)
        return [
            {"servicio": nombre, "inicia_en": c.inicia_en.isoformat(), "estado": c.estado}
            for c, nombre in result.all()
        ]
