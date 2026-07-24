-- ════════════════════════════════════════════════════════════════════════
-- The Nail Society Spa — Notificaciones en tiempo real de citas (LISTEN/NOTIFY)
--
-- Cada vez que una cita se crea, cambia de estado, se reagenda o se cancela
-- (venga del bot de WhatsApp, de la web o del panel), un trigger emite
-- pg_notify('citas_cambio', ...). El backend escucha ese canal con
-- asyncpg.add_listener y empuja el evento al panel por SSE (Server-Sent Events),
-- para que la agenda se refresque sin recargar.
--
-- Se usa el Session pooler de Supabase (puerto 5432, modo sesión), que sí
-- soporta LISTEN/NOTIFY — el Transaction pooler (6543) NO lo soportaría.
-- ════════════════════════════════════════════════════════════════════════

create or replace function notificar_cambio_cita() returns trigger as $$
declare
  fila record;
  carga json;
begin
  -- En DELETE la fila viva está en OLD; en INSERT/UPDATE, en NEW.
  if (tg_op = 'DELETE') then
    fila := old;
  else
    fila := new;
  end if;

  -- Payload pequeño y suficiente para que el panel sepa qué refrescar.
  -- (pg_notify tiene un límite de 8000 bytes; mantenemos esto mínimo.)
  carga := json_build_object(
    'accion', lower(tg_op),
    'id', fila.id,
    'estado', fila.estado,
    'sucursal_id', fila.sucursal_id,
    'origen', fila.origen
  );

  perform pg_notify('citas_cambio', carga::text);
  return fila;
end;
$$ language plpgsql;

drop trigger if exists trg_notificar_cambio_cita on citas;

create trigger trg_notificar_cambio_cita
  after insert or update or delete on citas
  for each row execute function notificar_cambio_cita();
