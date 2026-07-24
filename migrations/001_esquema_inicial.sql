-- ════════════════════════════════════════════════════════════════════════
-- The Nail Society Spa — Esquema inicial
-- Base: el esquema ya probado en producción (ver agent/memory.py:66-176)
-- Deltas nuevos: sucursales, empleados.sucursal_id/especialidad, citas.sucursal_id
-- ════════════════════════════════════════════════════════════════════════

-- Necesaria para el constraint anti-solapamiento: permite combinar el operador
-- de igualdad de uuid (btree) con el de solapamiento de rangos (gist).
create extension if not exists btree_gist;


-- ── Sucursales (NUEVO — el salón tiene dos: Norte y Sur) ───────────────
create table sucursales (
  id        uuid primary key default gen_random_uuid(),
  nombre    text not null unique,
  direccion text,
  telefono  text,
  activo    boolean not null default true
);


-- ── Categorías de servicio ─────────────────────────────────────────────
create table categorias (
  id     uuid primary key default gen_random_uuid(),
  nombre varchar(100) not null unique
);


-- ── Clientas, identificadas por su número de WhatsApp ──────────────────
create table clientes (
  id        uuid primary key default gen_random_uuid(),
  telefono  varchar(50) not null unique,
  nombre    varchar(100),
  creado_en timestamptz not null default now()
);


-- ── Catálogo de servicios ──────────────────────────────────────────────
create table servicios (
  id           uuid primary key default gen_random_uuid(),
  nombre       varchar(100) not null,
  duracion_min integer not null default 60,
  precio       numeric(10, 2),
  activo       boolean not null default true,
  categoria_id uuid references categorias(id)
);


-- ── Especialistas ──────────────────────────────────────────────────────
create table empleados (
  id           uuid primary key default gen_random_uuid(),
  nombre       varchar(100) not null,
  activo       boolean not null default true,
  -- NUEVO: en qué sucursal atiende y a qué se dedica
  sucursal_id  uuid references sucursales(id),
  especialidad text
);


-- ── Horario laboral por especialista y día (0=Lunes .. 6=Domingo) ──────
create table horarios_empleado (
  id          uuid primary key default gen_random_uuid(),
  empleado_id uuid not null references empleados(id) on delete cascade,
  dia_semana  integer not null check (dia_semana between 0 and 6),
  hora_inicio time not null,
  hora_fin    time not null
);
create index idx_horarios_empleado on horarios_empleado (empleado_id);


-- ── Usuarios del sistema (auth propia: PBKDF2 + cookie HMAC) ───────────
create table usuarios (
  id            uuid primary key default gen_random_uuid(),
  email         varchar(150) not null unique,
  password_hash text not null,
  rol           varchar(20) not null,             -- 'admin' | 'empleada'
  nombre        varchar(100),
  empleado_id   uuid references empleados(id),
  activo        boolean not null default true,
  creado_en     timestamptz not null default now()
);


-- ── Citas ──────────────────────────────────────────────────────────────
create table citas (
  id                   uuid primary key default gen_random_uuid(),
  cliente_id           uuid not null references clientes(id),
  servicio_id          uuid references servicios(id),
  empleado_id          uuid references empleados(id),
  sucursal_id          uuid references sucursales(id),   -- NUEVO
  inicia_en            timestamptz not null,
  termina_en           timestamptz,
  estado               varchar(20) not null default 'pendiente',
  origen               varchar(20) not null default 'whatsapp',  -- 'whatsapp' | 'web' | 'panel'
  notas                text,
  precio_cobrado       numeric(10, 2),
  recordatorio_enviado boolean not null default false,
  creado_en            timestamptz not null default now()
);
create index idx_citas_inicia_en  on citas (inicia_en);
create index idx_citas_cliente    on citas (cliente_id);
create index idx_citas_empleado   on citas (empleado_id);
create index idx_citas_sucursal   on citas (sucursal_id);

-- Dos citas de la MISMA especialista no pueden encimarse. Es la última línea de
-- defensa: aunque dos clientas pidan el mismo hueco a la vez (web y WhatsApp),
-- la base rechaza la segunda y la app responde 409.
-- Sólo aplica con empleada asignada y si la cita no está cancelada.
alter table citas add constraint citas_sin_solapamiento
  exclude using gist (
    empleado_id with =,
    tstzrange(inicia_en, termina_en) with &&
  ) where (empleado_id is not null and estado <> 'cancelada');


-- ── Historial de conversación del bot ──────────────────────────────────
create table mensajes (
  id        uuid primary key default gen_random_uuid(),
  telefono  varchar(50) not null,
  role      varchar(20) not null,   -- 'user' | 'assistant'
  content   text not null,
  creado_en timestamptz not null default now()
);
create index idx_mensajes_telefono on mensajes (telefono, creado_en);


-- ── Configuración editable por el salón desde el panel ─────────────────
create table configuracion (
  clave varchar(50) primary key,
  valor text not null default ''
);


-- ── Realtime en citas ──────────────────────────────────────────────────
alter publication supabase_realtime add table citas;


-- ── RLS: activado en todo, SIN políticas para anon ─────────────────────
-- Deliberado. La web React no habla con Supabase: habla con FastAPI, que usa la
-- conexión directa de Postgres (bypassa RLS). La anon key nunca sale al
-- navegador, así que dejar RLS sin políticas cierra la puerta por completo a
-- cualquier acceso público a los datos de las clientas.
alter table sucursales        enable row level security;
alter table categorias        enable row level security;
alter table clientes          enable row level security;
alter table servicios         enable row level security;
alter table empleados         enable row level security;
alter table horarios_empleado enable row level security;
alter table usuarios          enable row level security;
alter table citas             enable row level security;
alter table mensajes          enable row level security;
alter table configuracion     enable row level security;
