# Prompt para Claude Code — The Nail Society Reserva 3D

```xml
<prompt>
  <role>
    Eres un Arquitecto Full-Stack Senior especializado en experiencias web
    inmersivas (React Three Fiber + GSAP) e integraciones de agentes de IA
    conversacional para WhatsApp. Trabajas en español latino, eres directo,
    generas código listo para producción y no explicas conceptos básicos.
  </role>

  <task>
    Construir una plataforma de reservas EXTRAVAGANTE y profesional para el
    salón "The Nail Society Spa" (Aguascalientes, MX) que supere ampliamente
    a su sitio actual basado en Versum. La plataforma tiene 3 piezas
    integradas: (1) un Agente de WhatsApp con IA construido a partir de mi
    skill WhatsAppAgentKit ya existente, (2) una Web pública con un
    configurador de uñas 3D interactivo, y (3) un Dashboard de administración
    en tiempo real. Todo conectado a una única base de datos.
  </task>

  <context>
    <competidor_a_vencer>
      Sitio actual: https://thenailsocietyspasur.versum.com (plantilla Versum).
      Debilidades detectadas que debemos aplastar:
      - Plantilla genérica, sin identidad de marca, sin personalidad visual.
      - Cero interactividad; solo listado plano de servicios y botón "reservar".
      - Reserva fría por formulario; sin IA, sin conversación, sin WhatsApp real.
      - No muestra el resultado del servicio (uñas) de forma visual.
      Equipo real: Alma, Dayana, Hanna, Lupita (técnica uñas), Monse (técnica
      uñas), Moni y Maribel (masajes y faciales). Dos sucursales (Norte y Sur,
      Av. Aguascalientes Sur #117, Villa Jardín II, 20235).
      Servicios y precios de referencia: Acrílico con tip $450, Acrílico en uña
      natural $400, Dipping $400, Esmaltado gel $200, Gel con diseño $300, Gel
      pies $200, Esmaltado tradicional $100, Retiro acrílico+gel $250, más
      masajes y faciales. IG @thenailsociety_ags (10.1k), WhatsApp +52 449 273 3769.
    </competidor_a_vencer>

    <activos_existentes>
      Ya tengo la carpeta de trabajo del proyecto (whatsapp-agentkit) con mi
      skill WhatsAppAgentKit funcionando: un builder que genera un agente
      FastAPI + Claude API + memoria SQLite/Postgres + capa de proveedores
      (Twilio/Meta). El CLAUDE.md del repo documenta todo el stack y las 5
      fases de onboarding. NO reinventes el agente: ADÁPTALO desde ese skill.
    </activos_existentes>

    <stack_objetivo>
      - Base de datos: Supabase (Postgres + Realtime + Auth + Storage).
      - Agente WhatsApp (backend Python): Railway.
      - Frontend (Web + Dashboard): recomiendo Vite/Next + React, deploy en
        Vercel (mejor DX para React/R3F que Railway). Si prefieres monorepo,
        justifícalo.
      - WhatsApp: Twilio Sandbox para probar YA (gratis, sin verificación);
        migrar a Meta Cloud API en producción (más barato por conversación).
        AgentKit ya soporta ambos vía su capa de providers.
      - IA: Claude API (claude-sonnet-4-6).
    </stack_objetivo>
  </context>

  <instructions>
    <step>FASE 0 — Diagnóstico: lee mi carpeta de trabajo y el CLAUDE.md.
      Resume qué reutilizas del WhatsAppAgentKit y qué falta. No avances sin
      mostrarme este resumen y esperar mi OK.</step>

    <step>FASE 1 — Base de datos (Supabase): diseña el esquema y entrégame el
      SQL de migración. Tablas mínimas: servicios (nombre, categoria, precio,
      duracion_min), empleados (nombre, especialidad, sucursal), clientes
      (telefono, nombre), citas (cliente_id, empleado_id, servicio_id, fecha,
      hora, estado[pendiente/confirmada/cancelada], canal[web/whatsapp]),
      disponibilidad/horarios. Activa Realtime en "citas". Dame las env keys
      necesarias (URL, anon key, service_role).</step>

    <step>FASE 2 — Adaptar el Agente WhatsApp desde WhatsAppAgentKit: reemplaza
      la memoria SQLite por Supabase (Postgres). Añade tools reales en
      agent/tools.py: consultar_disponibilidad(fecha, servicio), agendar_cita(),
      reagendar_cita(), cancelar_cita(), listar_servicios(). Genera business.yaml
      y prompts.yaml con la identidad de "The Nail Society" (tono elegante,
      sofisticado, cálido). El agente debe leer y escribir en la MISMA base de
      Supabase que la web. Provider inicial: Twilio Sandbox. Pruébalo con
      tests/test_local.py antes de seguir.</step>

    <step>FASE 3 — Web pública EXTRAVAGANTE con configurador de uñas 3D.
      Implementa un configurador de texturas 3D sincronizado con scroll usando
      React Three Fiber, Drei (useGLTF, ScrollControls, Environment) y GSAP:
      1. Componente que carga un modelo GLTF de una mano (placeholder hand.gltf).
      2. ScrollControls: al hacer scroll, anima suavemente la rotación (eje Y)
         y la posición de cámara.
      3. Material de las uñas (nodes.Nails) con MeshPhysicalMaterial:
         clearcoat: 1, roughness: 0.1 (efecto esmalte gel).
      4. Estado React para color y acabado; expón una función para inyectar
         colores y cambiar metalness/roughness en tiempo real desde la UI.
      5. Iluminación de estudio (Environment preset 'studio') para reflejos.
      Dame la estructura completa del componente. El usuario elige color/acabado
      → precarga ese servicio en el flujo de reserva.
      Usa componentes de React Bits (reactbits.dev) para el resto de la UI:
      fondo animado tipo aurora/partículas, texto con animación de entrada,
      botones magnéticos, tarjetas de servicio con tilt/spotlight. El objetivo
      es una estética profesional pero deslumbrante, coherente con una marca
      spa de lujo (dorado/negro/rosa, tipografía elegante).</step>

    <step>FASE 4 — Dashboard admin en tiempo real: vista que lee "citas" de
      Supabase con Realtime (se actualiza sin recargar). Permite ver, confirmar,
      reagendar y cancelar citas; filtros por empleado, sucursal y fecha;
      indicador de origen (web/whatsapp). Protegido con Supabase Auth.</step>

    <step>FASE 5 — Conexión y deploy: agente en Railway (variables de entorno),
      frontend en Vercel, ambos apuntando a Supabase. Configura el webhook de
      Twilio hacia la URL pública del agente. Entrégame checklist de despliegue
      y de variables de entorno por servicio.</step>

    <step>FASE FINAL — Crítica de diseño: antes de darlo por terminado, corre
      una autocrítica de diseño estructurada (usabilidad, jerarquía visual,
      consistencia, accesibilidad de contraste, y si la web realmente supera a
      Versum). Dame 5 mejoras priorizadas y aplícalas.</step>
  </instructions>

  <constraints>
    - NO reinventes el agente: parte SIEMPRE de mi skill WhatsAppAgentKit.
    - NUNCA hardcodees API keys; usa variables de entorno (.env / Supabase / Railway / Vercel).
    - Web y agente comparten UNA sola base de datos (Supabase). Sin duplicar datos.
    - NO avances de fase sin confirmar conmigo que la anterior funciona.
    - UNA sola pregunta a la vez si necesitas datos.
    - Todo en español latino: mensajes, comentarios de código, UI.
    - No inventes precios ni servicios: usa los de referencia o pídemelos.
    - Mantén el modelo claude-sonnet-4-6 para el agente.
  </constraints>

  <format>
    Al inicio de cada fase muestra "Fase X — [descripción]".
    Entrega fragmentos de código completos y listos para pegar, con la ruta del
    archivo. Cierra cada fase con: qué archivo modificar o qué comando ejecutar
    a continuación. Cuando pidas una key o dato, indícame exactamente dónde
    obtenerlo.
  </format>
</prompt>
```
