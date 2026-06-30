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
from datetime import datetime, timezone, timedelta, date as _date, time as _time
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Text, DateTime, Time, Integer, Numeric, Boolean, ForeignKey, Uuid, select, delete, update,
)
from dotenv import load_dotenv

load_dotenv()

# Zona horaria del salón y parámetros del calendario de reservas
ZONA_SALON = ZoneInfo("America/Mazatlan")
PASO_SLOT_MIN = 30  # cada cuántos minutos se ofrece un turno
# Horario general del salón (respaldo cuando no se elige empleada). 0=Lunes..6=Domingo
HORARIO_SALON = {0: (9, 19), 1: (9, 19), 2: (9, 19), 3: (9, 19), 4: (9, 19), 5: (9, 14), 6: None}

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
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categorias.id"), nullable=True)


class Empleado(Base):
    """Empleada / manicurista del salón."""
    __tablename__ = "empleados"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Categoria(Base):
    """Categoría de servicios (Acrílico, Manicura, Pedicura, Diseño...)."""
    __tablename__ = "categorias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class HorarioEmpleado(Base):
    """Horario laboral de una empleada para un día de la semana (0=Lunes..6=Domingo)."""
    __tablename__ = "horarios_empleado"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    empleado_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("empleados.id"))
    dia_semana: Mapped[int] = mapped_column(Integer)
    hora_inicio: Mapped[_time] = mapped_column(Time)
    hora_fin: Mapped[_time] = mapped_column(Time)


class Usuario(Base):
    """Usuario del sistema con rol (admin / empleada / clienta)."""
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    empleado_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)


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
    precio_cobrado: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    recordatorio_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
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
    empleado_id: uuid.UUID | None = None,
    origen: str = "whatsapp",
) -> dict:
    """Registra una cita y devuelve sus datos básicos.

    Si la empleada ya tiene una cita que se solapa, la base de datos rechaza el
    INSERT (constraint de no-solapamiento) y se propaga una IntegrityError.
    """
    async with async_session() as session:
        cita = Cita(
            cliente_id=cliente_id,
            servicio_id=servicio_id,
            inicia_en=inicia_en,
            termina_en=termina_en,
            notas=notas,
            empleado_id=empleado_id,
            origen=origen,
        )
        session.add(cita)
        await session.commit()
        return {"id": str(cita.id), "inicia_en": cita.inicia_en.isoformat(), "estado": cita.estado}


# ════════════════════════════════════════════════════════════
# Calendario de reservas: catálogo y disponibilidad
# ════════════════════════════════════════════════════════════
async def catalogo_servicios() -> list[dict]:
    """Servicios activos con su categoría (para el portal de reservas)."""
    async with async_session() as session:
        query = (
            select(Servicio, Categoria.nombre)
            .outerjoin(Categoria, Servicio.categoria_id == Categoria.id)
            .where(Servicio.activo.is_(True))
            .order_by(Servicio.nombre)
        )
        result = await session.execute(query)
        return [
            {
                "id": str(s.id),
                "nombre": s.nombre,
                "categoria": cat or "General",
                "duracion_min": s.duracion_min,
                "precio": float(s.precio) if s.precio is not None else None,
            }
            for s, cat in result.all()
        ]


async def slots_disponibles(servicio_id: str, empleado_id: str | None, fecha: str) -> list[str]:
    """
    Calcula los turnos de inicio disponibles para una fecha dada.

    Considera: la duración del servicio, el horario laboral de la empleada
    (o el horario general del salón si no se elige empleada), las citas ya
    ocupadas y descarta los turnos que ya pasaron si la fecha es hoy.
    """
    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return []

    dow = dia.weekday()  # 0=Lunes..6=Domingo

    async with async_session() as session:
        servicio = await session.get(Servicio, uuid.UUID(servicio_id))
        if servicio is None:
            return []
        duracion = servicio.duracion_min

        ventanas: list[tuple[_time, _time]] = []   # franjas laborales del día
        ocupados: list[tuple[datetime, datetime]] = []  # citas ya tomadas

        if empleado_id:
            eid = uuid.UUID(empleado_id)
            res_h = await session.execute(
                select(HorarioEmpleado).where(
                    HorarioEmpleado.empleado_id == eid,
                    HorarioEmpleado.dia_semana == dow,
                )
            )
            ventanas = [(h.hora_inicio, h.hora_fin) for h in res_h.scalars().all()]

            res_c = await session.execute(
                select(Cita).where(Cita.empleado_id == eid, Cita.estado != "cancelada")
            )
            for c in res_c.scalars().all():
                ocupados.append((c.inicia_en, c.termina_en or c.inicia_en))
        else:
            rango = HORARIO_SALON.get(dow)
            if rango:
                ventanas = [(_time(rango[0]), _time(rango[1]))]

        if not ventanas:
            return []  # no se trabaja ese día

        ahora = datetime.now(ZONA_SALON)
        slots: list[str] = []
        for hora_ini, hora_fin in ventanas:
            actual = datetime.combine(dia, hora_ini, tzinfo=ZONA_SALON)
            cierre = datetime.combine(dia, hora_fin, tzinfo=ZONA_SALON)
            while actual + timedelta(minutes=duracion) <= cierre:
                fin_slot = actual + timedelta(minutes=duracion)
                if actual > ahora:  # no ofrecer turnos en el pasado
                    choca = any(actual < ocu_fin and ocu_ini < fin_slot for ocu_ini, ocu_fin in ocupados)
                    if not choca:
                        slots.append(actual.strftime("%H:%M"))
                actual += timedelta(minutes=PASO_SLOT_MIN)
        return slots


# ════════════════════════════════════════════════════════════
# Funciones para el panel de administración (dashboard)
# ════════════════════════════════════════════════════════════
async def listar_citas(empleado_filtro: str | None = None) -> list[dict]:
    """Lista citas con datos de cliente, servicio y empleada (para el panel).

    Si se pasa empleado_filtro (id), devuelve solo las citas de esa empleada
    (se usa para que cada empleada vea únicamente su agenda).
    """
    async with async_session() as session:
        query = (
            select(Cita, Cliente, Servicio.nombre, Empleado.nombre)
            .join(Cliente, Cita.cliente_id == Cliente.id)
            .outerjoin(Servicio, Cita.servicio_id == Servicio.id)
            .outerjoin(Empleado, Cita.empleado_id == Empleado.id)
            .order_by(Cita.inicia_en.asc())
        )
        if empleado_filtro:
            query = query.where(Cita.empleado_id == uuid.UUID(empleado_filtro))
        result = await session.execute(query)
        citas = []
        for cita, cliente, servicio_nombre, empleado_nombre in result.all():
            citas.append({
                "id": str(cita.id),
                "cliente": cliente.nombre or "Sin nombre",
                "telefono": cliente.telefono,
                "servicio": servicio_nombre or "—",
                "inicia_en": cita.inicia_en.isoformat(),
                "termina_en": cita.termina_en.isoformat() if cita.termina_en else None,
                "estado": cita.estado,
                "empleado_id": str(cita.empleado_id) if cita.empleado_id else None,
                "empleado": empleado_nombre,
                "notas": cita.notas,
            })
        return citas


async def listar_empleados() -> list[dict]:
    """Lista las empleadas activas del salón."""
    async with async_session() as session:
        query = select(Empleado).where(Empleado.activo.is_(True)).order_by(Empleado.nombre)
        result = await session.execute(query)
        return [{"id": str(e.id), "nombre": e.nombre} for e in result.scalars().all()]


def _calcular_turno(hora_inicio: str, duracion_horas) -> tuple:
    """A partir de 'HH:MM' y una duración (1-10 h) devuelve (hora_inicio, hora_fin)."""
    hi = datetime.strptime(hora_inicio, "%H:%M").time()
    dur = max(1, min(10, int(duracion_horas or 8)))
    fin = datetime.combine(_date(2000, 1, 1), hi) + timedelta(hours=dur)
    # No pasar de medianoche
    hf = fin.time() if fin.date() == _date(2000, 1, 1) else _time(23, 59)
    return hi, hf


async def _set_horarios(session, empleado_id, hora_inicio, duracion_horas, dias):
    """Reemplaza el horario de una empleada con un turno uniforme en los días dados."""
    await session.execute(delete(HorarioEmpleado).where(HorarioEmpleado.empleado_id == empleado_id))
    if hora_inicio and dias:
        hi, hf = _calcular_turno(hora_inicio, duracion_horas)
        for d in dias:
            session.add(HorarioEmpleado(
                empleado_id=empleado_id, dia_semana=int(d), hora_inicio=hi, hora_fin=hf,
            ))


async def crear_empleado(nombre: str, hora_inicio: str | None = None,
                         duracion_horas=None, dias: list | None = None) -> dict:
    """Registra una nueva empleada y, opcionalmente, su turno de trabajo."""
    async with async_session() as session:
        emp = Empleado(nombre=nombre)
        session.add(emp)
        await session.flush()
        if hora_inicio and dias:
            await _set_horarios(session, emp.id, hora_inicio, duracion_horas, dias)
        await session.commit()
        return {"id": str(emp.id), "nombre": emp.nombre}


async def crear_empleado_con_login(nombre: str, hora_inicio: str | None, duracion_horas,
                                   dias: list | None, email: str, password_hash: str) -> dict:
    """Crea una empleada + su turno + su usuario de acceso (rol empleada) en UNA transacción.
    Si el correo ya existe, el commit lanza IntegrityError y NO queda empleada huérfana."""
    async with async_session() as session:
        emp = Empleado(nombre=nombre)
        session.add(emp)
        await session.flush()
        if hora_inicio and dias:
            await _set_horarios(session, emp.id, hora_inicio, duracion_horas, dias)
        session.add(Usuario(
            email=email.lower().strip(), password_hash=password_hash,
            rol="empleada", nombre=nombre, empleado_id=emp.id,
        ))
        await session.commit()
        return {"id": str(emp.id), "nombre": emp.nombre}


async def desactivar_empleado(empleado_id: str, activo: bool) -> bool:
    """Da de baja (activo=False) o reactiva (activo=True) a una empleada."""
    async with async_session() as session:
        emp = await session.get(Empleado, uuid.UUID(empleado_id))
        if emp is None:
            return False
        emp.activo = bool(activo)
        await session.commit()
        return True


async def establecer_horario_empleado(empleado_id: str, hora_inicio: str,
                                      duracion_horas, dias: list) -> bool:
    """Define o cambia el turno de una empleada."""
    async with async_session() as session:
        emp = await session.get(Empleado, uuid.UUID(empleado_id))
        if emp is None:
            return False
        await _set_horarios(session, emp.id, hora_inicio, duracion_horas, dias)
        await session.commit()
        return True


async def eliminar_empleado(empleado_id: str) -> bool:
    """Elimina una empleada de forma permanente. Desvincula sus citas y su login,
    y borra sus horarios. (Distinto de 'dar de baja', que solo la desactiva.)"""
    async with async_session() as session:
        emp = await session.get(Empleado, uuid.UUID(empleado_id))
        if emp is None:
            return False
        await session.execute(update(Cita).where(Cita.empleado_id == emp.id).values(empleado_id=None))
        await session.execute(update(Usuario).where(Usuario.empleado_id == emp.id).values(empleado_id=None))
        await session.execute(delete(HorarioEmpleado).where(HorarioEmpleado.empleado_id == emp.id))
        await session.delete(emp)
        await session.commit()
        return True


async def buscar_empleada_disponible(inicia_en: datetime, termina_en: datetime) -> dict:
    """
    Busca una empleada activa que trabaje en esa franja y no tenga una cita que
    se solape. Devuelve:
      {"empleado_id": <id>}                 -> hay una libre (asignar)
      {"empleado_id": None, "hay_personal": True}  -> hay personal ese día pero todas ocupadas
      {"empleado_id": None, "hay_personal": False} -> no hay personal con horario ese día
    """
    dow = inicia_en.weekday()
    ini_t = inicia_en.time()
    fin_t = termina_en.time()
    async with async_session() as session:
        filas = (await session.execute(
            select(Empleado.id, HorarioEmpleado.hora_inicio, HorarioEmpleado.hora_fin)
            .join(HorarioEmpleado, HorarioEmpleado.empleado_id == Empleado.id)
            .where(Empleado.activo.is_(True), HorarioEmpleado.dia_semana == dow)
        )).all()
        candidatas = [eid for (eid, hi, hf) in filas if hi <= ini_t and fin_t <= hf]
        if not candidatas:
            return {"empleado_id": None, "hay_personal": False}
        for eid in candidatas:
            citas = (await session.execute(
                select(Cita).where(Cita.empleado_id == eid, Cita.estado != "cancelada")
            )).scalars().all()
            choca = any(inicia_en < (c.termina_en or c.inicia_en) and c.inicia_en < termina_en for c in citas)
            if not choca:
                return {"empleado_id": str(eid), "hay_personal": True}
        return {"empleado_id": None, "hay_personal": True}


async def citas_por_recordar(horas_antes: int = 24) -> list[dict]:
    """Citas activas dentro de las próximas `horas_antes` horas que aún no se han recordado."""
    ahora = _ahora()
    limite = ahora + timedelta(hours=horas_antes)
    async with async_session() as session:
        query = (
            select(Cita, Cliente.nombre, Cliente.telefono, Servicio.nombre)
            .join(Cliente, Cita.cliente_id == Cliente.id)
            .outerjoin(Servicio, Cita.servicio_id == Servicio.id)
            .where(
                Cita.estado.in_(["pendiente", "confirmada"]),
                Cita.recordatorio_enviado.is_(False),
                Cita.inicia_en > ahora,
                Cita.inicia_en <= limite,
            )
            .order_by(Cita.inicia_en.asc())
        )
        result = await session.execute(query)
        return [
            {
                "id": str(c.id),
                "telefono": tel,
                "cliente": nombre or "",
                "servicio": serv or "tu cita",
                "inicia_en": c.inicia_en.isoformat(),
            }
            for c, nombre, tel, serv in result.all()
        ]


async def marcar_recordatorio_enviado(cita_id: str):
    """Marca una cita como ya recordada para no enviar el recordatorio dos veces."""
    async with async_session() as session:
        await session.execute(
            update(Cita).where(Cita.id == uuid.UUID(cita_id)).values(recordatorio_enviado=True)
        )
        await session.commit()


async def registro_citas(empleado_filtro: str | None = None) -> list[dict]:
    """Historial de citas COMPLETADAS (para el registro). Si se pasa empleado_filtro,
    solo las atendidas por esa empleada (cada empleada ve únicamente las suyas)."""
    async with async_session() as session:
        query = (
            select(Cita, Cliente, Servicio, Empleado.nombre)
            .join(Cliente, Cita.cliente_id == Cliente.id)
            .outerjoin(Servicio, Cita.servicio_id == Servicio.id)
            .outerjoin(Empleado, Cita.empleado_id == Empleado.id)
            .where(Cita.estado == "completada")
            .order_by(Cita.inicia_en.desc())
        )
        if empleado_filtro:
            query = query.where(Cita.empleado_id == uuid.UUID(empleado_filtro))
        result = await session.execute(query)
        registro = []
        for cita, cliente, servicio, emp_nombre in result.all():
            costo = cita.precio_cobrado if cita.precio_cobrado is not None else (servicio.precio if servicio else None)
            registro.append({
                "id": str(cita.id),
                "cliente": cliente.nombre or "Sin nombre",
                "telefono": cliente.telefono,
                "servicio": servicio.nombre if servicio else "—",
                "costo": float(costo) if costo is not None else None,
                "inicia_en": cita.inicia_en.isoformat(),       # horario en que se atendió
                "agendada_en": cita.creado_en.isoformat(),     # fecha en que se agendó
                "empleada": emp_nombre,
            })
        return registro


async def gestionar_empleados() -> list[dict]:
    """Lista TODAS las empleadas (activas e inactivas) con su turno, para administración."""
    async with async_session() as session:
        empleados = (await session.execute(
            select(Empleado).order_by(Empleado.nombre)
        )).scalars().all()
        salida = []
        for e in empleados:
            horarios = (await session.execute(
                select(HorarioEmpleado)
                .where(HorarioEmpleado.empleado_id == e.id)
                .order_by(HorarioEmpleado.dia_semana)
            )).scalars().all()
            dias = [h.dia_semana for h in horarios]
            hora_inicio = horarios[0].hora_inicio.strftime("%H:%M") if horarios else None
            hora_fin = horarios[0].hora_fin.strftime("%H:%M") if horarios else None
            duracion = None
            if horarios:
                ini = datetime.combine(_date(2000, 1, 1), horarios[0].hora_inicio)
                fin = datetime.combine(_date(2000, 1, 1), horarios[0].hora_fin)
                duracion = round((fin - ini).seconds / 3600)
            salida.append({
                "id": str(e.id), "nombre": e.nombre, "activo": e.activo,
                "dias": dias, "hora_inicio": hora_inicio, "hora_fin": hora_fin,
                "duracion_horas": duracion,
            })
        return salida


async def crear_usuario(email: str, password_hash: str, rol: str,
                        nombre: str | None = None, empleado_id: str | None = None) -> dict:
    """Crea un usuario del sistema con su contraseña ya hasheada."""
    async with async_session() as session:
        u = Usuario(
            email=email.lower().strip(),
            password_hash=password_hash,
            rol=rol,
            nombre=nombre,
            empleado_id=uuid.UUID(empleado_id) if empleado_id else None,
        )
        session.add(u)
        await session.commit()
        return {"id": str(u.id), "email": u.email, "rol": u.rol}


def _usuario_dict(u: "Usuario") -> dict:
    return {
        "id": str(u.id), "email": u.email, "password_hash": u.password_hash,
        "rol": u.rol, "nombre": u.nombre,
        "empleado_id": str(u.empleado_id) if u.empleado_id else None,
        "activo": u.activo,
    }


async def obtener_usuario_por_email(email: str) -> dict | None:
    """Busca un usuario activo por email (para el login)."""
    async with async_session() as session:
        result = await session.execute(
            select(Usuario).where(Usuario.email == email.lower().strip(), Usuario.activo.is_(True))
        )
        u = result.scalar_one_or_none()
        return _usuario_dict(u) if u else None


async def obtener_usuario_por_id(usuario_id: str) -> dict | None:
    """Carga un usuario por id (para validar la sesión)."""
    async with async_session() as session:
        u = await session.get(Usuario, uuid.UUID(usuario_id))
        return _usuario_dict(u) if (u and u.activo) else None


async def actualizar_password(usuario_id: str, password_hash: str) -> bool:
    """Cambia la contraseña (ya hasheada) de un usuario."""
    async with async_session() as session:
        u = await session.get(Usuario, uuid.UUID(usuario_id))
        if u is None:
            return False
        u.password_hash = password_hash
        await session.commit()
        return True


async def actualizar_cita(
    cita_id: str,
    estado: str | None = None,
    empleado_id: str | None = None,
) -> bool:
    """Actualiza el estado y/o la empleada asignada de una cita. Devuelve False si no existe."""
    async with async_session() as session:
        cita = await session.get(Cita, uuid.UUID(cita_id))
        if cita is None:
            return False
        if estado is not None:
            cita.estado = estado
        if empleado_id is not None:
            cita.empleado_id = uuid.UUID(empleado_id) if empleado_id else None
        await session.commit()
        return True


# ════════════════════════════════════════════════════════════
# Gestión de citas por la propia clienta (desde WhatsApp)
# El teléfono se toma del remitente: solo puede tocar SUS citas.
# ════════════════════════════════════════════════════════════
async def citas_activas_de(telefono: str) -> list[dict]:
    """Citas futuras y no canceladas de un teléfono (para ver/cambiar/cancelar)."""
    async with async_session() as session:
        query = (
            select(Cita, Servicio.nombre)
            .join(Cliente, Cita.cliente_id == Cliente.id)
            .outerjoin(Servicio, Cita.servicio_id == Servicio.id)
            .where(
                Cliente.telefono == telefono,
                Cita.estado != "cancelada",
                Cita.inicia_en >= _ahora(),
            )
            .order_by(Cita.inicia_en.asc())
        )
        result = await session.execute(query)
        return [
            {
                "id": str(c.id),
                "servicio": nombre or "—",
                "servicio_id": str(c.servicio_id) if c.servicio_id else None,
                "inicia_en": c.inicia_en.isoformat(),
                "estado": c.estado,
            }
            for c, nombre in result.all()
        ]


async def _cita_del_telefono(session, cita_id: str, telefono: str):
    """Devuelve la cita solo si pertenece a ese teléfono (control de propiedad)."""
    result = await session.execute(
        select(Cita).join(Cliente, Cita.cliente_id == Cliente.id)
        .where(Cita.id == uuid.UUID(cita_id), Cliente.telefono == telefono)
    )
    return result.scalar_one_or_none()


async def cancelar_cita(cita_id: str, telefono: str) -> bool:
    async with async_session() as session:
        cita = await _cita_del_telefono(session, cita_id, telefono)
        if cita is None:
            return False
        cita.estado = "cancelada"
        await session.commit()
        return True


async def reagendar_cita(cita_id: str, telefono: str, inicia_en: datetime, termina_en: datetime) -> bool:
    async with async_session() as session:
        cita = await _cita_del_telefono(session, cita_id, telefono)
        if cita is None:
            return False
        cita.inicia_en = inicia_en
        cita.termina_en = termina_en
        await session.commit()
        return True


async def cambiar_servicio_cita(cita_id: str, telefono: str, servicio_id: str, termina_en: datetime) -> bool:
    async with async_session() as session:
        cita = await _cita_del_telefono(session, cita_id, telefono)
        if cita is None:
            return False
        cita.servicio_id = uuid.UUID(servicio_id)
        cita.termina_en = termina_en
        await session.commit()
        return True


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
