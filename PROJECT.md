# Desarrolla el MVP de TaskKin

Actúa como arquitecto de software y desarrollador full-stack senior. Debes diseñar e implementar el MVP de **TaskKin**, una plataforma API-first que permite que agentes de inteligencia artificial publiquen tareas para que personas verificadas las realicen, aporten evidencias y reciban un pago después de validar el resultado.

## 1. Visión del producto

TaskKin es una capa de ejecución humana para agentes de IA.

Un agente debe poder:

1. Crear una tarea mediante API.
2. Indicar requisitos, presupuesto máximo y fecha límite.
3. Recibir una estimación automática del precio.
4. Publicar la tarea.
5. Esperar a que un trabajador la acepte.
6. Recibir evidencias del trabajo realizado.
7. Validar, rechazar o solicitar una revisión.
8. Liberar el pago.
9. Recibir el resultado mediante API o webhook.

Un trabajador debe poder:

1. Registrarse.
2. Completar un perfil básico.
3. Consultar tareas disponibles.
4. Aceptar una tarea.
5. Enviar el resultado y las evidencias.
6. Consultar el estado de la validación.
7. Acumular reputación.
8. Consultar su saldo y pagos.

El MVP no debe incluir un token propio. Todos los importes se expresarán inicialmente en EUR. Los pagos reales pueden simularse mediante un ledger interno. La integración con Stripe o USDC debe quedar preparada mediante interfaces desacopladas, pero no es necesaria para la primera versión funcional.

## 2. Posicionamiento

TaskKin no es una plataforma para evasión de CAPTCHA, creación de cuentas, spam, fraude, KYC delegado ni acciones destinadas a evitar controles de seguridad.

El producto inicial se centra en:

* Pruebas manuales de sitios web.
* Verificación de información pública.
* Evaluación humana de contenido.
* Traducción y revisión lingüística.
* Recogida de evidencias estructuradas.
* Verificaciones físicas sencillas.
* Escalado human-in-the-loop para agentes de IA.

## 3. Objetivo del MVP

Construye una versión funcional que demuestre este flujo completo:

```text
Agente crea una tarea
        ↓
El sistema calcula un precio recomendado
        ↓
La tarea se publica
        ↓
Un trabajador la acepta
        ↓
El trabajador entrega resultado y evidencias
        ↓
El solicitante aprueba o rechaza
        ↓
El sistema actualiza saldo y reputación
        ↓
El solicitante recibe un webhook
```

La aplicación debe poder ejecutarse localmente mediante Docker Compose.

## 4. Stack tecnológico

Utiliza:

### Backend

* Python 3.12
* FastAPI
* SQLAlchemy 2
* PostgreSQL
* Alembic
* Pydantic 2
* Celery
* Redis
* Pytest
* HTTPX
* JWT para autenticación
* Ruff
* MyPy

### Frontend

* Next.js
* TypeScript
* React
* Tailwind CSS
* React Query
* Zod

### Infraestructura

* Docker
* Docker Compose
* MinIO para almacenar evidencias
* Mailpit para probar correos locales
* GitHub Actions para CI

Mantén el frontend sencillo. La prioridad es demostrar el flujo de negocio y disponer de una API limpia.

## 5. Tipos de usuario

Implementa tres roles.

### Requester

Persona, empresa o agente responsable de crear tareas.

Puede:

* Crear una organización.
* Crear API keys.
* Depositar saldo simulado.
* Crear y publicar tareas.
* Consultar candidatos y asignaciones.
* Revisar entregas.
* Aprobar o rechazar entregas.
* Consultar pagos y disputas.
* Configurar webhooks.

### Worker

Persona que realiza las tareas.

Puede:

* Crear y editar su perfil.
* Definir ubicación, idiomas y habilidades.
* Consultar tareas compatibles.
* Aceptar una tarea.
* Enviar texto, archivos, fotografías o enlaces.
* Consultar saldo.
* Consultar su reputación.

### Admin

Puede:

* Revisar usuarios.
* Suspender cuentas.
* Revisar tareas marcadas.
* Aprobar o rechazar categorías.
* Resolver disputas.
* Consultar el registro de auditoría.

## 6. Entidades principales

Diseña las siguientes entidades.

### User

```text
id
email
password_hash
role
status
created_at
updated_at
```

### Organization

```text
id
name
owner_user_id
status
created_at
```

### OrganizationMember

```text
organization_id
user_id
role
```

### APIKey

```text
id
organization_id
name
key_hash
key_prefix
last_used_at
revoked_at
created_at
```

Nunca almacenes una API key en texto plano.

### WorkerProfile

```text
id
user_id
display_name
bio
country
city
latitude_approx
longitude_approx
languages
skills
verification_status
availability_status
created_at
updated_at
```

La ubicación debe ser aproximada. No almacenes una dirección exacta en el MVP.

### Task

```text
id
organization_id
created_by_user_id
title
description
category
status
currency
offered_price
maximum_budget
estimated_minutes
deadline_at
location_mode
country
city
required_skills
required_languages
evidence_requirements
safety_risk_level
moderation_status
created_at
updated_at
published_at
```

Estados mínimos:

```text
draft
pending_moderation
open
assigned
submitted
approved
rejected
disputed
cancelled
expired
```

### TaskAssignment

```text
id
task_id
worker_id
status
accepted_at
submitted_at
completed_at
cancelled_at
```

Solo debe existir una asignación activa por tarea en el MVP.

### Submission

```text
id
assignment_id
worker_id
text_result
structured_result
status
submitted_at
reviewed_at
review_notes
```

### Evidence

```text
id
submission_id
evidence_type
storage_key
file_name
mime_type
file_size
sha256
metadata
created_at
```

Tipos de evidencia:

```text
image
video
document
url
text
json
```

### Wallet

```text
id
owner_type
owner_id
currency
available_balance
reserved_balance
created_at
updated_at
```

### LedgerEntry

```text
id
wallet_id
task_id
entry_type
amount
balance_after
reference
created_at
```

Tipos:

```text
deposit
reserve
release
refund
payment
platform_fee
adjustment
```

El ledger debe ser append-only.

### ReputationEvent

```text
id
user_id
task_id
event_type
score
weight
metadata
created_at
```

### WebhookEndpoint

```text
id
organization_id
url
secret
enabled
created_at
```

### WebhookDelivery

```text
id
webhook_endpoint_id
event_type
payload
status
attempt_count
next_attempt_at
response_status
created_at
```

### AuditEvent

```text
id
actor_type
actor_id
action
resource_type
resource_id
metadata
created_at
```

## 7. Categorías iniciales

Incluye únicamente estas categorías:

```text
website_testing
content_review
translation_review
data_verification
local_business_verification
image_collection
custom_safe_task
```

No permitas categorías relacionadas con:

* CAPTCHA.
* Evasión de controles anti-bot.
* Creación o verificación de cuentas.
* Uso de números de teléfono de terceros.
* KYC.
* Documentos de identidad.
* Credenciales.
* Reseñas falsas.
* Manipulación de redes sociales.
* Compras reguladas.
* Vigilancia de personas.
* Acceso a propiedades privadas.
* Actividades ilegales.

## 8. Motor de moderación

Implementa un sistema de moderación basado inicialmente en reglas.

Debe analizar:

* Título.
* Descripción.
* Categoría.
* Evidencias solicitadas.
* Ubicación.
* Enlaces incluidos.

Debe devolver:

```json
{
  "decision": "allow",
  "risk_level": "low",
  "matched_rules": [],
  "explanation": "No prohibited patterns detected"
}
```

Decisiones posibles:

```text
allow
manual_review
reject
```

Define las reglas en configuración y no directamente dentro de los controladores.

Crea una interfaz:

```python
class ModerationService(Protocol):
    async def evaluate_task(
        self,
        task: TaskModerationInput,
    ) -> ModerationResult:
        ...
```

Debe ser posible sustituir posteriormente el motor de reglas por un modelo de IA.

## 9. Motor de precios

El precio lo puede sugerir un agente, pero el sistema debe imponer límites.

Calcula un precio recomendado:

```text
precio =
    tiempo_estimado_en_horas × tarifa_base
    × multiplicador_de_especialización
    × multiplicador_de_urgencia
    + coste_de_desplazamiento
```

Valores iniciales:

```text
tarifa_base = 15 EUR/hora
mínimo_por_tarea = 3 EUR
comisión_plataforma = 15%
```

Multiplicador de especialización:

```text
normal = 1.0
skilled = 1.25
expert = 1.75
```

Multiplicador de urgencia:

```text
más de 48 horas = 1.0
entre 12 y 48 horas = 1.15
menos de 12 horas = 1.35
menos de 2 horas = 1.75
```

El precio ofrecido debe cumplir:

```text
minimum_allowed_price <= offered_price <= maximum_budget
```

Crea una interfaz independiente:

```python
class PricingService(Protocol):
    async def calculate(
        self,
        pricing_input: PricingInput,
    ) -> PricingResult:
        ...
```

Respuesta:

```json
{
  "recommended_price": 12.5,
  "minimum_price": 8.0,
  "maximum_price": 20.0,
  "estimated_worker_payment": 10.63,
  "platform_fee": 1.87,
  "explanation": {
    "base_cost": 8.0,
    "urgency_multiplier": 1.15,
    "skill_multiplier": 1.25
  }
}
```

Usa `Decimal` para todos los cálculos monetarios. Nunca uses `float`.

## 10. Reputación

No utilices únicamente una media de estrellas.

Calcula métricas separadas:

```text
quality_score
reliability_score
on_time_score
instruction_score
dispute_rate
completed_tasks
cancelled_tasks
```

Mantén los eventos individuales en `ReputationEvent`.

La puntuación visible debe usar una media bayesiana:

```text
bayesian_score =
    (global_mean × minimum_weight + worker_mean × worker_count)
    / (minimum_weight + worker_count)
```

Valores iniciales:

```text
global_mean = 4.0
minimum_weight = 10
```

Actualiza reputación cuando:

* Una entrega es aprobada.
* Una entrega es rechazada.
* Una tarea se entrega tarde.
* El trabajador cancela después de aceptar.
* Se resuelve una disputa.
* El solicitante cancela incorrectamente.

El sistema debe mantener reputación tanto para trabajadores como para solicitantes.

## 11. Pagos y escrow simulado

Implementa un ledger interno transaccional.

Cuando se publica una tarea:

1. Verifica que la organización tenga saldo.
2. Reserva el precio total.
3. Mueve el importe de disponible a reservado.

Cuando se aprueba:

1. Resta el importe reservado.
2. Añade el pago neto al trabajador.
3. Registra la comisión de plataforma.
4. Emite un evento webhook.

Cuando se cancela antes de ser aceptada:

1. Libera la reserva.
2. Devuelve el importe al saldo disponible.

Cuando hay una disputa:

1. El importe permanece reservado.
2. Solo un administrador puede liberarlo o devolverlo.

Todas las operaciones monetarias deben:

* Ejecutarse en una transacción.
* Bloquear las filas necesarias.
* Ser idempotentes.
* Dejar una entrada en el ledger.
* Dejar una entrada en auditoría.

Crea una abstracción:

```python
class PaymentProvider(Protocol):
    async def reserve(self, command: ReserveFundsCommand) -> PaymentResult:
        ...

    async def release(self, command: ReleaseFundsCommand) -> PaymentResult:
        ...

    async def refund(self, command: RefundFundsCommand) -> PaymentResult:
        ...
```

Implementa inicialmente:

```text
InternalLedgerPaymentProvider
```

Prepara stubs para:

```text
StripePaymentProvider
USDCX402PaymentProvider
```

No implementes pagos reales todavía.

## 12. API REST

Crea una API versionada bajo:

```text
/api/v1
```

### Autenticación

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
GET  /auth/me
```

### Organizaciones

```text
POST /organizations
GET  /organizations
GET  /organizations/{organization_id}
POST /organizations/{organization_id}/api-keys
GET  /organizations/{organization_id}/api-keys
DELETE /organizations/{organization_id}/api-keys/{api_key_id}
```

### Wallets

```text
GET  /organizations/{organization_id}/wallet
POST /organizations/{organization_id}/wallet/deposits/simulate
GET  /organizations/{organization_id}/wallet/ledger
GET  /workers/me/wallet
GET  /workers/me/wallet/ledger
```

### Pricing

```text
POST /pricing/estimate
```

### Tareas

```text
POST /tasks
GET  /tasks
GET  /tasks/{task_id}
PATCH /tasks/{task_id}
POST /tasks/{task_id}/publish
POST /tasks/{task_id}/cancel
```

Filtros:

```text
status
category
country
city
minimum_price
maximum_price
required_skill
deadline_before
```

### Trabajadores

```text
GET   /workers/me
PATCH /workers/me
GET   /workers/me/assignments
GET   /workers/me/reputation
```

### Asignaciones

```text
POST /tasks/{task_id}/accept
GET  /assignments/{assignment_id}
POST /assignments/{assignment_id}/cancel
```

### Entregas

```text
POST /assignments/{assignment_id}/submissions
POST /submissions/{submission_id}/evidence/presign
POST /submissions/{submission_id}/submit
POST /submissions/{submission_id}/approve
POST /submissions/{submission_id}/reject
POST /submissions/{submission_id}/dispute
```

### Webhooks

```text
POST   /organizations/{organization_id}/webhooks
GET    /organizations/{organization_id}/webhooks
PATCH  /organizations/{organization_id}/webhooks/{webhook_id}
DELETE /organizations/{organization_id}/webhooks/{webhook_id}
POST   /organizations/{organization_id}/webhooks/{webhook_id}/test
```

### Administración

```text
GET  /admin/tasks/pending-moderation
POST /admin/tasks/{task_id}/approve
POST /admin/tasks/{task_id}/reject
GET  /admin/disputes
POST /admin/disputes/{task_id}/resolve
```

## 13. API para agentes

Permite autenticación mediante:

```text
Authorization: Bearer <api_key>
```

Una organización debe poder crear tareas sin utilizar la interfaz web.

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer tk_live_example" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: task-2026-001" \
  -d '{
    "title": "Test checkout on Android",
    "description": "Complete the checkout flow without submitting payment and report any usability problems.",
    "category": "website_testing",
    "estimated_minutes": 20,
    "maximum_budget": "15.00",
    "currency": "EUR",
    "deadline_at": "2026-07-20T12:00:00Z",
    "location_mode": "remote",
    "required_languages": ["en"],
    "evidence_requirements": [
      {
        "type": "image",
        "minimum_count": 3
      },
      {
        "type": "json",
        "schema": {
          "issues": "array",
          "completed": "boolean"
        }
      }
    ]
  }'
```

Respuesta:

```json
{
  "id": "uuid",
  "status": "draft",
  "pricing": {
    "recommended_price": "9.50",
    "minimum_price": "7.00"
  },
  "moderation": {
    "decision": "allow",
    "risk_level": "low"
  }
}
```

## 14. Webhooks

Implementa estos eventos:

```text
task.published
task.accepted
task.submitted
task.approved
task.rejected
task.disputed
task.cancelled
payment.reserved
payment.released
payment.refunded
```

Cada webhook debe incluir:

```json
{
  "id": "event_uuid",
  "type": "task.submitted",
  "created_at": "ISO-8601",
  "data": {}
}
```

Firma el contenido con HMAC SHA-256:

```text
X-TaskKin-Signature
X-TaskKin-Timestamp
X-TaskKin-Event-ID
```

Implementa:

* Reintentos con backoff exponencial.
* Máximo de cinco intentos.
* Idempotencia.
* Registro de la respuesta HTTP.
* Posibilidad de reenviar manualmente.

## 15. MCP server

Añade un servidor MCP básico que permita a un agente utilizar TaskKin.

Herramientas mínimas:

```text
taskkin_estimate_price
taskkin_create_task
taskkin_publish_task
taskkin_get_task
taskkin_cancel_task
taskkin_list_tasks
taskkin_review_submission
```

Ejemplo conceptual:

```python
@mcp.tool()
async def taskkin_create_task(
    title: str,
    description: str,
    category: str,
    estimated_minutes: int,
    maximum_budget: Decimal,
    deadline_at: datetime,
) -> dict:
    """Create a human task in TaskKin."""
```

El servidor MCP debe consumir la API REST. No debe acceder directamente a la base de datos.

Incluye configuración para ejecución mediante:

```text
stdio
```

y deja preparada la estructura para HTTP.

## 16. Frontend

Crea dos interfaces mínimas.

### Portal del solicitante

Pantallas:

```text
/login
/requester/dashboard
/requester/tasks
/requester/tasks/new
/requester/tasks/{id}
/requester/wallet
/requester/api-keys
/requester/webhooks
```

El dashboard debe mostrar:

* Tareas abiertas.
* Tareas asignadas.
* Tareas pendientes de revisión.
* Gasto total.
* Saldo disponible.
* Últimos eventos.

La pantalla de una tarea debe mostrar:

* Estado.
* Precio.
* Trabajador asignado.
* Timeline.
* Evidencias.
* Botones para aprobar, rechazar o abrir disputa.

### Portal del trabajador

Pantallas:

```text
/worker/dashboard
/worker/tasks
/worker/tasks/{id}
/worker/assignments
/worker/profile
/worker/wallet
/worker/reputation
```

El trabajador debe poder:

* Filtrar tareas.
* Consultar requisitos.
* Aceptar una tarea.
* Subir evidencias.
* Enviar la entrega.
* Ver su pago estimado.

## 17. Evidencias

Utiliza MinIO con URLs prefirmadas.

Flujo:

1. El cliente solicita una URL prefirmada.
2. El backend valida tamaño y tipo de archivo.
3. El cliente sube directamente a MinIO.
4. El cliente confirma la subida.
5. El backend calcula o valida el hash.
6. La evidencia queda asociada a la entrega.

Restricciones iniciales:

```text
imagen: máximo 10 MB
vídeo: máximo 100 MB
documento: máximo 20 MB
```

Tipos permitidos:

```text
image/jpeg
image/png
image/webp
video/mp4
application/pdf
application/json
text/plain
```

No permitas archivos ejecutables.

Elimina metadatos EXIF sensibles cuando sea posible o almacena solamente los campos necesarios.

## 18. Seguridad

Implementa:

* Hash de contraseñas con Argon2.
* JWT de corta duración.
* Refresh tokens rotables.
* API keys almacenadas mediante hash.
* Rate limiting.
* Validación estricta de entrada.
* Control de acceso por rol y organización.
* Cabeceras de seguridad.
* CORS configurable.
* Protección contra enumeración de recursos.
* Logs sin secretos.
* Auditoría de operaciones sensibles.
* Idempotency keys.
* Bloqueo pesimista en operaciones de saldo.
* Sanitización de nombres de archivos.
* Límites de tamaño.
* Validación de URLs de webhook contra SSRF.

Los webhooks no deben poder apuntar a:

```text
localhost
127.0.0.0/8
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
169.254.0.0/16
::1
redes privadas IPv6
```

En desarrollo debe existir una opción explícita para permitir localhost.

## 19. Arquitectura del backend

Utiliza una arquitectura modular.

Estructura recomendada:

```text
backend/
├── app/
│   ├── api/
│   │   ├── dependencies/
│   │   └── v1/
│   ├── auth/
│   ├── organizations/
│   ├── workers/
│   ├── tasks/
│   ├── assignments/
│   ├── submissions/
│   ├── evidence/
│   ├── moderation/
│   ├── pricing/
│   ├── reputation/
│   ├── payments/
│   ├── webhooks/
│   ├── audit/
│   ├── common/
│   ├── infrastructure/
│   ├── db/
│   ├── config.py
│   └── main.py
├── migrations/
├── tests/
└── pyproject.toml
```

Dentro de cada módulo utiliza:

```text
models.py
schemas.py
repository.py
service.py
router.py
exceptions.py
```

No añadas capas innecesarias. Evita duplicar lógica en routers, servicios y repositorios.

Los routers deben:

* Validar la petición.
* Invocar servicios.
* Convertir excepciones de dominio en respuestas HTTP.

Los servicios deben:

* Implementar reglas de negocio.
* Controlar transacciones.
* Emitir eventos.

Los repositorios deben:

* Encapsular consultas.
* No contener reglas de negocio.

## 20. Eventos internos

Crea un bus de eventos interno sencillo.

Eventos:

```text
TaskCreated
TaskPublished
TaskAccepted
SubmissionCreated
SubmissionSubmitted
SubmissionApproved
SubmissionRejected
DisputeOpened
FundsReserved
FundsReleased
FundsRefunded
```

Inicialmente puede ser un dispatcher dentro del mismo proceso.

Las tareas asíncronas deben utilizar Celery para:

* Envío de webhooks.
* Reintentos.
* Expiración de tareas.
* Generación de miniaturas.
* Limpieza de archivos huérfanos.
* Cálculo agregado de reputación.

Evita introducir Kafka en el MVP.

## 21. Máquina de estados

Centraliza las transiciones permitidas.

Ejemplo:

```python
ALLOWED_TASK_TRANSITIONS = {
    TaskStatus.DRAFT: {
        TaskStatus.PENDING_MODERATION,
        TaskStatus.CANCELLED,
    },
    TaskStatus.PENDING_MODERATION: {
        TaskStatus.OPEN,
        TaskStatus.REJECTED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.OPEN: {
        TaskStatus.ASSIGNED,
        TaskStatus.CANCELLED,
        TaskStatus.EXPIRED,
    },
    TaskStatus.ASSIGNED: {
        TaskStatus.SUBMITTED,
        TaskStatus.CANCELLED,
        TaskStatus.DISPUTED,
    },
    TaskStatus.SUBMITTED: {
        TaskStatus.APPROVED,
        TaskStatus.REJECTED,
        TaskStatus.DISPUTED,
    },
}
```

Ningún controlador debe modificar el estado directamente sin pasar por el servicio correspondiente.

## 22. Idempotencia

Implementa `Idempotency-Key` para:

```text
crear tarea
publicar tarea
aceptar tarea
enviar entrega
aprobar entrega
realizar operaciones de saldo
```

Guarda:

```text
organization_id
idempotency_key
request_hash
response_status
response_body
created_at
expires_at
```

Si se reutiliza una clave con un cuerpo diferente, devuelve error `409 Conflict`.

## 23. Reglas de concurrencia

Debes impedir:

* Que dos trabajadores acepten la misma tarea.
* Que una tarea sea aprobada dos veces.
* Que el saldo se libere dos veces.
* Que una tarea cancelada sea aceptada.
* Que una entrega sea modificada después de enviarse.
* Que se gasten fondos reservados.

Utiliza transacciones y bloqueos de filas.

Incluye pruebas específicas de concurrencia.

## 24. Testing

Implementa:

### Pruebas unitarias

* PricingService.
* ModerationService.
* Máquina de estados.
* Cálculo de reputación.
* Firma de webhooks.
* Ledger.

### Pruebas de integración

* Crear y publicar tarea.
* Aceptar tarea.
* Enviar entrega.
* Aprobar y liberar pago.
* Rechazar entrega.
* Abrir disputa.
* Cancelar tarea.
* Expirar tarea.
* Reintentar webhook.
* Autenticación mediante API key.

### Prueba end-to-end principal

```text
1. Crear requester.
2. Crear organización.
3. Simular depósito de 100 EUR.
4. Crear tarea.
5. Publicarla.
6. Crear worker.
7. Aceptar tarea.
8. Subir evidencia.
9. Enviar entrega.
10. Aprobar entrega.
11. Comprobar ledger.
12. Comprobar reputación.
13. Comprobar webhook.
```

Los tests deben ejecutarse con:

```bash
make test
```

Objetivo mínimo:

```text
80% de cobertura en backend
```

No persigas cobertura artificial. Prioriza reglas de negocio y operaciones monetarias.

## 25. Observabilidad

Incluye:

* Logs JSON.
* Correlation ID.
* Request ID.
* Event ID.
* Métricas básicas Prometheus.
* Endpoint `/health`.
* Endpoint `/ready`.
* Endpoint `/metrics`.

Métricas:

```text
tasks_created_total
tasks_published_total
tasks_accepted_total
tasks_completed_total
tasks_disputed_total
webhook_deliveries_total
webhook_failures_total
reserved_funds_total
released_funds_total
```

## 26. Docker Compose

El proyecto debe arrancar con:

```bash
docker compose up --build
```

Servicios:

```text
backend
frontend
postgres
redis
celery-worker
celery-beat
minio
mailpit
```

Incluye:

```text
.env.example
Makefile
README.md
```

Comandos:

```bash
make up
make down
make migrate
make seed
make test
make lint
make format
make logs
```

## 27. Datos de demostración

Crea un comando de seed que genere:

* Un administrador.
* Una organización de demostración.
* Un requester.
* Cinco trabajadores.
* Diez tareas abiertas.
* Dos tareas asignadas.
* Una tarea pendiente de aprobación.
* Saldos simulados.
* Eventos de reputación.
* Un webhook local.

Credenciales de desarrollo:

```text
admin@taskkin.local
requester@taskkin.local
worker1@taskkin.local
```

Utiliza una contraseña únicamente válida en desarrollo y documentada en el README.

## 28. Interfaz visual

Utiliza una interfaz clara y funcional.

No inviertas tiempo en una identidad visual sofisticada.

Requisitos:

* Diseño responsive.
* Estados de carga.
* Estados vacíos.
* Mensajes de error útiles.
* Confirmación antes de acciones irreversibles.
* Timeline de la tarea.
* Distinción clara entre saldo disponible y reservado.
* Badges de estado.
* Navegación diferente según rol.

## 29. No objetivos del MVP

No implementes todavía:

* Token propio.
* Blockchain propia.
* DAO.
* Gobernanza descentralizada.
* Matching avanzado mediante IA.
* Aplicación móvil nativa.
* Chat en tiempo real.
* Videollamadas.
* Geolocalización precisa.
* Verificación biométrica.
* KYC completo.
* Pagos internacionales reales.
* Subastas.
* Múltiples trabajadores por tarea.
* Consenso entre trabajadores.
* Seguros.
* Integración contable.
* Marketplace global.
* Microservicios.
* Kubernetes.

Mantén el MVP como monolito modular.

## 30. Criterios de aceptación

El MVP se considera terminado cuando:

1. Puede arrancarse localmente con Docker Compose.
2. Un requester puede crear una organización.
3. Puede generar una API key.
4. Puede añadir saldo simulado.
5. Un agente puede crear una tarea mediante API.
6. El sistema calcula un precio recomendado.
7. El sistema modera la tarea.
8. La tarea puede publicarse.
9. Un trabajador puede aceptarla.
10. Puede enviar una entrega con evidencias.
11. El requester puede aprobarla.
12. El ledger transfiere correctamente los fondos simulados.
13. La reputación se actualiza.
14. Se entrega un webhook firmado.
15. El mismo flujo funciona mediante el servidor MCP.
16. Las operaciones críticas son idempotentes.
17. Las pruebas automáticas principales pasan.
18. El README permite levantar el sistema desde cero.

## 31. Forma de trabajo

Trabaja por iteraciones pequeñas.

Orden recomendado:

### Fase 1: base técnica

* Repositorio.
* Docker Compose.
* Configuración.
* PostgreSQL.
* Migraciones.
* Autenticación.
* CI.

### Fase 2: dominio principal

* Usuarios.
* Organizaciones.
* Trabajadores.
* Tareas.
* Máquina de estados.
* Moderación.
* Pricing.

### Fase 3: ejecución

* Asignaciones.
* Entregas.
* Evidencias.
* MinIO.
* Revisión.

### Fase 4: dinero y confianza

* Wallet.
* Ledger.
* Escrow.
* Reputación.
* Auditoría.

### Fase 5: integración con agentes

* API keys.
* Idempotencia.
* Webhooks.
* MCP.

### Fase 6: frontend y demo

* Portal requester.
* Portal worker.
* Panel admin.
* Seeds.
* Documentación.
* Test end-to-end.

Después de cada fase:

1. Ejecuta tests.
2. Ejecuta lint.
3. Actualiza el README.
4. Revisa migraciones.
5. Comprueba que Docker Compose continúa funcionando.

## 32. Reglas de código

* Aplica DRY sin crear abstracciones prematuras.
* Usa nombres explícitos.
* Evita funciones largas.
* Separa efectos externos de reglas de negocio.
* Usa tipado estricto.
* No utilices diccionarios sin tipar para modelos del dominio.
* Usa enums para estados y categorías.
* Usa `Decimal` para dinero.
* Usa UTC internamente.
* Usa UUID para identificadores públicos.
* No expongas IDs secuenciales.
* Añade comentarios solo cuando expliquen una decisión no evidente.
* No dupliques validaciones entre API y dominio.
* No captures excepciones genéricas sin necesidad.
* No ocultes errores.
* No añadas dependencias sin justificar.
* Mantén las integraciones externas detrás de interfaces.

## 33. Entregables

Genera:

```text
README.md
ARCHITECTURE.md
SECURITY.md
API.md
docker-compose.yml
.env.example
Makefile
backend/
frontend/
mcp-server/
.github/workflows/ci.yml
```

En `ARCHITECTURE.md`, documenta:

* Componentes.
* Modelo de dominio.
* Decisiones técnicas.
* Máquina de estados.
* Flujo de pagos.
* Flujo de webhooks.
* Límites del MVP.
* Posibles evoluciones.

En `SECURITY.md`, documenta:

* Modelo de amenazas.
* Abuso de tareas.
* Fraude de trabajadores.
* Robo de API keys.
* Manipulación de evidencias.
* SSRF en webhooks.
* Doble gasto.
* Acceso entre organizaciones.
* Medidas implementadas.
* Riesgos pendientes.

## 34. Primera tarea

Antes de escribir código:

1. Propón la estructura final del repositorio.
2. Define el modelo de dominio.
3. Presenta las decisiones arquitectónicas.
4. Identifica los cinco riesgos técnicos principales.
5. Divide el desarrollo en pull requests pequeñas.
6. Después empieza a implementar la Fase 1.

No generes todo el proyecto en un único archivo ni en una única respuesta masiva. Implementa el sistema incrementalmente, manteniendo siempre una versión ejecutable.
