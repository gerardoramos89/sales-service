# Microservices Agent Architecture

Arquitectura de 3 microservicios independientes, orquestados por un agente
de IA (Claude, con tool use) que actúa como punto de entrada único para
el usuario en lenguaje natural.

Construido usando el mismo dominio de negocio que
[Top 10 Tracker](https://github.com/gerardoramos89/top10-dropi-extension)
(cálculo de rentabilidad en dropshipping), esta vez separado en servicios
independientes, desplegables y escalables por separado.

---

## Tabla de contenido

1. Arquitectura
2. Sobre la interfaz
3. Por qué esto es "microservicios" de verdad
4. El agente como capa de orquestación
5. Modo demo (sin llave de API)
6. Cómo correrlo
7. Probarlo
8. Cómo escalar cada servicio
9. Decisiones de diseño

---

## Arquitectura

Usuario (lenguaje natural) → agent-gateway (FastAPI + Claude agent,
puerto 8000, único punto expuesto) → dos ramas por HTTP:

- analytics-service (puerto 8002, reglas de negocio, sin datos propios)
  → HTTP interno → sales-service (puerto 8001, dueño de los datos:
  productos y ventas)

### Flujo de una consulta típica

Usuario pregunta "¿es rentable mi crema facial?" → agent-gateway →
Claude decide llamar calcular_rentabilidad(p3) → analytics-service →
GET /products/p3 → sales-service → responde datos del producto →
analytics-service calcula {margen: -39.8%, estado: "perdida"} →
agent-gateway → responde "No, tu crema facial te está dando pérdida".

## Sobre la interfaz — ¿cómo se ve esto?

Dos aclaraciones importantes para quien clone este repo:

**Los diagramas de este README no son imágenes.** Son dibujos hechos con
texto — se ven como diagramas al leerlos en GitHub, pero no hay ningún
archivo .png ni .jpg en este repo.

**Ninguno de los 3 microservicios tiene interfaz visual propia, a
propósito.** Son APIs puras: código que responde a peticiones HTTP con
JSON. Se prueban así, por terminal:

    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"mensaje": "¿cuál de mis productos me está dando pérdida?"}'

Como los 3 están construidos con **FastAPI**, cada uno trae su propia
interfaz web de pruebas (Swagger UI) incluida sin código extra. Con los
servicios corriendo, ábrelas en:

    http://localhost:8000/docs   (agent-gateway — el que le habla al usuario)
    http://localhost:8001/docs   (sales-service)
    http://localhost:8002/docs   (analytics-service)

Ahí hay botones y formularios para probar cada endpoint visualmente, sin
necesitar la terminal.

## Por qué esto es "microservicios" de verdad

No es solo carpetas separadas — cada uno de estos tres criterios se cumple:

1. **Proceso independiente.** Cada servicio tiene su propio Dockerfile,
   su propio requirements.txt, y corre en su propio puerto. Se puede
   desplegar, reiniciar o escalar sin tocar los otros dos.
2. **Comunicación por red, no por imports.** analytics-service NO
   importa código de sales-service — le hace una petición HTTP real y
   espera una respuesta JSON. Si mañana sales-service se reescribe en
   otro lenguaje (Go, Node), a analytics-service no le afecta, siempre
   que el contrato HTTP se mantenga.
3. **Responsabilidad única y datos propios por servicio.** sales-service
   es el único dueño de los datos (nadie más los toca directo).
   analytics-service tiene la lógica de negocio pero cero datos propios
   — todo lo que necesita lo pide. agent-gateway no sabe calcular nada
   — solo decide a quién preguntarle qué.

## El agente como capa de orquestación

agent-gateway recibe una pregunta en español y usa a Claude con tool use
para decidir qué servicio(s) llamar — la diferencia clave frente al
primer repo (sales-rag-agent) es que aquí las tools no calculan nada
localmente: cada una es una llamada HTTP a otro proceso
(services/agent-gateway/tools.py). El agente es literalmente la capa de
orquestación entre lenguaje natural y contratos HTTP internos.

Para "¿es rentable mi crema facial y cuánto he vendido de eso?", el
agente encadena dos llamadas (calcular_rentabilidad y resumen_ventas),
cada una viajando por red hasta analytics-service, que a su vez le pide
los datos crudos a sales-service — y combina ambos resultados en una
sola respuesta en lenguaje natural. Ver services/agent-gateway/agent.py.

## Modo demo (sin llave de API)

Para probar todo el flujo de microservicios sin necesitar
ANTHROPIC_API_KEY:

    export AGENT_MODE=mock
    docker compose up --build

Importante: en modo mock, la orquestación HTTP entre servicios sigue
siendo 100% real — agent-gateway de verdad le pide datos a
analytics-service, que de verdad se los pide a sales-service. Lo único
simulado es la decisión de qué herramienta llamar (normalmente tomada
por Claude), reemplazada por reglas simples de palabras clave en
services/agent-gateway/mock_agent.py. Este modo se probó end-to-end: los
3 servicios levantados a la vez, con respuestas correctas.

## Cómo correrlo (modo real, con Claude)

### Con Docker (recomendado — así es como se desplegaría)

    export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    docker compose up --build

Levanta los 3 servicios en su propia red interna (backend), con
agent-gateway como único puerto expuesto al exterior (8000). Los otros
dos (8001, 8002) también quedan mapeados al host en este docker-compose
por conveniencia de desarrollo — en producción normalmente NO se
expondrían al exterior, solo a la red interna.

### Sin Docker (para desarrollo local)

En 3 terminales distintas:

    # Terminal 1 — sales-service
    cd services/sales-service
    pip install -r requirements.txt
    uvicorn main:app --port 8001

    # Terminal 2 — analytics-service
    cd services/analytics-service
    pip install -r requirements.txt
    SALES_SERVICE_URL=http://localhost:8001 uvicorn main:app --port 8002

    # Terminal 3 — agent-gateway
    cd services/agent-gateway
    pip install -r requirements.txt
    SALES_SERVICE_URL=http://localhost:8001 \
    ANALYTICS_SERVICE_URL=http://localhost:8002 \
    ANTHROPIC_API_KEY=sk-ant-xxx \
    uvicorn main:app --port 8000

## Probarlo

    # Directo a un microservicio, sin pasar por el agente
    curl http://localhost:8001/products/p1
    curl http://localhost:8002/rentabilidad/p1

    # A través del agente (lenguaje natural, orquestando ambos servicios)
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"mensaje": "¿cuál de mis productos me está dando pérdida?"}'

Este flujo fue probado extremo a extremo levantando sales-service y
analytics-service juntos y confirmando que la comunicación HTTP entre
ambos devuelve los cálculos correctos (mismos resultados que el modelo
de referencia de sales-rag-agent, lo cual confirma consistencia entre
ambos proyectos).

## Cómo escalar cada servicio

- **sales-service**: hoy JSON estático en disco, sin caché. Para
  escalar: base de datos real (Postgres) con índices sobre producto_id;
  caché de lectura (Redis) si el catálogo es grande y cambia poco.
- **analytics-service**: hoy llama a sales-service en cada request, sin
  caché ni reintentos. Para escalar: caché de corto plazo para productos
  consultados frecuentemente; reintentos con backoff exponencial
  (tenacity) ante fallos transitorios de red; circuit breaker para no
  saturar sales-service si está caído.
- **agent-gateway**: hoy un proceso, llamada síncrona a Claude. Para
  escalar: varias réplicas detrás de un load balancer (es stateless,
  escala horizontalmente sin cambios); streaming de respuesta para UX
  más fluida en peticiones largas.
- **Todos**: docker-compose ya expone /health en los 3 — en Kubernetes
  esto se traduce directo a readinessProbe/livenessProbe.
- **Descubrimiento de servicios**: hoy URLs fijas por variable de
  entorno. Válido hasta unos pocos servicios. A mayor escala: un service
  mesh (Istio/Linkerd) o un registro de servicios (Consul).
- **Seguridad entre servicios**: hoy ninguna — cualquiera en la red
  interna puede llamar a cualquiera. Para escalar: mTLS entre servicios,
  o al menos un token interno compartido; el agent-gateway de cara al
  usuario necesita autenticación real (JWT/OAuth) antes de producción.
- **Observabilidad**: hoy logs sueltos de cada uvicorn. Para escalar:
  tracing distribuido (OpenTelemetry) para seguir una petición a través
  de los 3 servicios — crítico aquí porque una sola pregunta del usuario
  puede generar 2-3 saltos de red.

La razón de que esto se resuelva servicio por servicio (y no con un
cambio genérico) es la misma razón por la que se separaron en 3 procesos
desde el principio: cada punto de arriba se resuelve tocando un solo
servicio, sin arriesgar romper los otros dos.

## Decisiones de diseño y qué faltaría para producción real

- **Por qué HTTP simple y no gRPC/mensajería asíncrona**: para un
  proyecto de este tamaño, HTTP+JSON es más legible y depurable. Con más
  servicios o mayor volumen, gRPC (tipado, más eficiente) o un bus de
  mensajes (Kafka/RabbitMQ) serían el siguiente paso natural.
- **Por qué no hay base de datos real todavía**: mantener el ejemplo
  fácil de clonar y correr en un minuto, sin pedir levantar Postgres
  aparte. El contrato HTTP de sales-service no cambiaría al migrar de
  JSON a Postgres — solo su implementación interna.
- **Qué NO tiene este proyecto (a propósito, para mantenerlo enfocado)**:
  autenticación, rate limiting, circuit breakers, tracing distribuido,
  CI/CD. Todo eso es real y necesario en producción, pero se documenta
  aquí como roadmap explícito en vez de simularlo mal.
