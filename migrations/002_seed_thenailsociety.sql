-- ════════════════════════════════════════════════════════════════════════
-- The Nail Society Spa — Datos iniciales
--
-- Sólo contiene datos CONFIRMADOS del brief. Lo que está marcado con
-- «PENDIENTE» queda deliberadamente en NULL o con un valor por defecto
-- señalado, a la espera de que el salón lo confirme. Nada inventado se da
-- por bueno en silencio.
-- ════════════════════════════════════════════════════════════════════════

-- ── Sucursales ─────────────────────────────────────────────────────────
-- La dirección de Sur viene del brief. La de Norte: PENDIENTE.
insert into sucursales (nombre, direccion, telefono) values
  ('Sur',   'Av. Aguascalientes Sur #117, Villa Jardín II, 20235, Aguascalientes', '+52 449 273 3769'),
  ('Norte', null, null);


-- ── Categorías ─────────────────────────────────────────────────────────
insert into categorias (nombre) values
  ('Acrílico'),
  ('Gel'),
  ('Esmaltado'),
  ('Pedicura'),
  ('Retiro'),
  ('Spa');


-- ── Servicios ──────────────────────────────────────────────────────────
-- PRECIOS: confirmados, vienen del brief. No se toca ninguno.
-- DURACIONES: estimadas con estándares del sector — PENDIENTE de confirmar
-- por el salón. La duración manda en el cálculo de huecos libres, así que un
-- valor mal puesto genera solapamientos o huecos fantasma.
insert into servicios (nombre, precio, duracion_min, categoria_id) values
  ('Acrílico con tip',         450, 120, (select id from categorias where nombre = 'Acrílico')),
  ('Acrílico en uña natural',  400, 105, (select id from categorias where nombre = 'Acrílico')),
  ('Dipping',                  400,  90, (select id from categorias where nombre = 'Acrílico')),
  ('Gel con diseño',           300,  90, (select id from categorias where nombre = 'Gel')),
  ('Esmaltado gel',            200,  60, (select id from categorias where nombre = 'Gel')),
  ('Gel pies',                 200,  60, (select id from categorias where nombre = 'Pedicura')),
  ('Esmaltado tradicional',    100,  30, (select id from categorias where nombre = 'Esmaltado')),
  ('Retiro acrílico + gel',    250,  45, (select id from categorias where nombre = 'Retiro'));

-- PENDIENTE: masajes y faciales. El brief los menciona ("más masajes y
-- faciales") pero no da nombres ni precios, y Moni y Maribel los atienden.
-- No se inventan: se cargan cuando el salón pase el catálogo.


-- ── Equipo ─────────────────────────────────────────────────────────────
-- Nombres y especialidades: confirmados donde el brief los da.
-- sucursal_id: PENDIENTE en todas — el brief no dice quién atiende dónde.
insert into empleados (nombre, especialidad) values
  ('Lupita',  'uñas'),
  ('Monse',   'uñas'),
  ('Moni',    'masajes y faciales'),
  ('Maribel', 'masajes y faciales'),
  ('Alma',    null),      -- PENDIENTE: especialidad
  ('Dayana',  null),      -- PENDIENTE: especialidad
  ('Hanna',   null);      -- PENDIENTE: especialidad


-- ── Configuración editable del bot ─────────────────────────────────────
insert into configuracion (clave, valor) values
  ('anuncios', ''),
  ('instrucciones_extra', ''),
  ('fallback_message', ''),
  ('error_message', '');


-- ── PENDIENTE: horarios_empleado ───────────────────────────────────────
-- Sin horario cargado, slots_disponibles() no devuelve huecos y no se puede
-- reservar. Se siembra en cuanto el salón confirme su horario de atención.
