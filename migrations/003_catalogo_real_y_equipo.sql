-- ════════════════════════════════════════════════════════════════════════
-- The Nail Society Spa — Catálogo real, equipo por sucursal y horarios
--
-- Fuente de precios y duraciones: catálogo Versum del salón
-- (thenailsocietyspanorte.versum.com). Se DEDUPLICA: Versum tiene ~83
-- entradas con muchos duplicados (una por empleada/sucursal); aquí queda un
-- catálogo limpio de servicios distintos.
--
-- Duraciones marcadas «(est.)» no venían fiables en Versum (p.ej. Gel Organic
-- aparecía como 1 min, error de captura); se estiman por analogía y el salón
-- las ajusta desde el panel → Servicios.
-- ════════════════════════════════════════════════════════════════════════

-- ── Dirección real de Norte (sacada del sitio) ─────────────────────────
update sucursales
   set direccion = 'Bulevar Luis Donaldo Colosio Murrieta 400, 20110, Aguascalientes'
 where nombre = 'Norte';


-- ── Reconstrucción de categorías y catálogo (aún sin citas: seguro) ─────
delete from servicios;
delete from categorias;

insert into categorias (nombre) values
  ('Acrílico'), ('Gel'), ('Esmaltado'), ('Manicure'),
  ('Pedicure'), ('Podología'), ('Spa'), ('Retiro');

insert into servicios (nombre, precio, duracion_min, categoria_id) values
  -- Acrílico y uñas esculturales
  ('Acrílico con tip',           450,  90, (select id from categorias where nombre='Acrílico')),
  ('Acrílico en uña natural',    400,  90, (select id from categorias where nombre='Acrílico')),
  ('Uña escultural',             450,  90, (select id from categorias where nombre='Acrílico')),
  ('Dipping',                    400,  90, (select id from categorias where nombre='Acrílico')),
  ('Builder',                    300,  60, (select id from categorias where nombre='Acrílico')),
  ('Poligel',                    400, 120, (select id from categorias where nombre='Acrílico')),
  ('Rubber (sin producto previo)',300, 30, (select id from categorias where nombre='Acrílico')),
  ('Retoque de acrílico',        400,  90, (select id from categorias where nombre='Acrílico')),
  -- Gel
  ('Esmaltado en gel',           200,  60, (select id from categorias where nombre='Gel')),
  ('Esmaltado en gel con diseño',300,  90, (select id from categorias where nombre='Gel')),
  ('Esmaltado en gel pies',      200,  60, (select id from categorias where nombre='Gel')),
  ('Gel Organic',                250,  90, (select id from categorias where nombre='Gel')),   -- (est.)
  ('Shellac',                    200,  60, (select id from categorias where nombre='Gel')),
  -- Esmaltado tradicional
  ('Esmaltado tradicional',      100,  30, (select id from categorias where nombre='Esmaltado')),
  -- Manicure
  ('Manicure express',           330,  60, (select id from categorias where nombre='Manicure')),
  ('Manicure básico',            370,  90, (select id from categorias where nombre='Manicure')),
  ('Manicure de lujo',           400,  90, (select id from categorias where nombre='Manicure')),
  ('Manicure infantil',          300,  60, (select id from categorias where nombre='Manicure')), -- (est.)
  -- Pedicure
  ('Pedicure express',           400,  60, (select id from categorias where nombre='Pedicure')),
  ('Pedicure básico',            450,  90, (select id from categorias where nombre='Pedicure')),
  ('Pedicure de lujo',           500,  90, (select id from categorias where nombre='Pedicure')),
  ('Pedicure infantil',          300,  60, (select id from categorias where nombre='Pedicure')), -- (est.)
  -- Podología
  ('Terminación podológica básica',250, 30, (select id from categorias where nombre='Podología')),
  ('Terminación podológica de lujo',300, 45, (select id from categorias where nombre='Podología')), -- (est.)
  -- Spa: masajes y faciales
  ('Masaje relajante básico',    550,  60, (select id from categorias where nombre='Spa')),
  ('Masaje relajante de lujo',   650,  90, (select id from categorias where nombre='Spa')),
  ('Masaje linfático',           490,  60, (select id from categorias where nombre='Spa')),
  ('Masaje de espalda',          350,  40, (select id from categorias where nombre='Spa')),
  ('Masaje de tejido profundo',  650,  60, (select id from categorias where nombre='Spa')),
  ('Masaje de manos y pies',     350,  50, (select id from categorias where nombre='Spa')),
  ('Masaje facial',              250,  30, (select id from categorias where nombre='Spa')),
  ('Facial básico',              500,  75, (select id from categorias where nombre='Spa')),
  ('Facial de lujo',             600,  90, (select id from categorias where nombre='Spa')),
  ('Parafina',                   150,  30, (select id from categorias where nombre='Spa')),
  -- Retiros
  ('Retiro de acrílico + gel',   250,  90, (select id from categorias where nombre='Retiro')),
  ('Retiro de acrílico',         100,  60, (select id from categorias where nombre='Retiro')), -- (est.)
  ('Retiro de gel',               50,  30, (select id from categorias where nombre='Retiro')); -- (est.)


-- ── Equipo: asignación de sucursal y especialidad ──────────────────────
-- SUR (equipo ya sembrado en 002): Alma, Dayana, Hanna, Lupita, Monse,
-- Moni, Maribel.
update empleados set sucursal_id = (select id from sucursales where nombre='Sur')
 where nombre in ('Alma','Dayana','Hanna','Lupita','Monse','Moni','Maribel');

update empleados set especialidad='uñas'               where nombre in ('Lupita','Monse');
update empleados set especialidad='masajes y faciales' where nombre in ('Moni','Maribel');
-- Alma, Dayana, Hanna: especialidad pendiente de confirmar → queda NULL.

-- NORTE (equipo nuevo, no venía en el brief inicial):
insert into empleados (nombre, especialidad, sucursal_id) values
  ('Angélica Mata', 'podología (gerente)', (select id from sucursales where nombre='Norte')),
  ('Ale',      null, (select id from sucursales where nombre='Norte')),
  ('Fany',     null, (select id from sucursales where nombre='Norte')),
  ('Alexa',    null, (select id from sucursales where nombre='Norte')),
  ('Barbie',   null, (select id from sucursales where nombre='Norte')),
  ('Nathaly',  null, (select id from sucursales where nombre='Norte')),
  ('Mar',      null, (select id from sucursales where nombre='Norte')),
  ('Ruth',     null, (select id from sucursales where nombre='Norte'));


-- ── Horarios por sucursal (dia_semana: 0=Lunes … 6=Domingo) ────────────
-- SUR:   Lun–Vie 10:00–20:00, Sáb 10:00–18:00, Dom cerrado.
-- NORTE: Lun–Sáb 10:00–20:00, Dom cerrado.
-- Se aplican a todas las empleadas de cada sucursal. El salón afina turnos
-- individuales después desde el panel.
insert into horarios_empleado (empleado_id, dia_semana, hora_inicio, hora_fin)
select e.id, d.dia, time '10:00',
       case when d.dia = 5 then time '18:00' else time '20:00' end
  from empleados e
  join sucursales s on e.sucursal_id = s.id
  cross join generate_series(0, 5) as d(dia)
 where s.nombre = 'Sur';

insert into horarios_empleado (empleado_id, dia_semana, hora_inicio, hora_fin)
select e.id, d.dia, time '10:00', time '20:00'
  from empleados e
  join sucursales s on e.sucursal_id = s.id
  cross join generate_series(0, 5) as d(dia)
 where s.nombre = 'Norte';
