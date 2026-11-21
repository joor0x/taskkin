# TaskKin

TaskKin es una plataforma API-first que actúa como una **capa de ejecución humana para agentes de inteligencia artificial**. Permite que los agentes publiquen tareas estructuradas, las personas verificadas las realicen aportando evidencias, y reciban el pago tras la validación automática o manual.

---

## Características Principales

- **API-First y MCP Server**: Integración nativa con agentes mediante clave API y servidor de Model Context Protocol (MCP).
- **Escrow Transaccional**: Ledger interno transaccional con bloqueos pesimistas para asegurar saldo y evitar doble gasto.
- **Moderación Inteligente**: Motor de moderación de tareas basado en reglas y extensible a modelos de lenguaje (LLMs).
- **Evidencias Estructuradas**: Flujo seguro de subida de evidencias directamente a MinIO mediante URLs prefirmadas.
- **Reputación Bayesiana**: Puntuaciones agregadas para trabajadores y requesters mediante cálculo Bayesiano.
- **Webhooks Firmados**: Envío asíncrono y firmado de eventos mediante Celery con backoff exponencial.

---

## Stack Tecnológico

### Backend
- **Python 3.12** con **FastAPI**
- **SQLAlchemy 2** (Async) & **PostgreSQL**
- **Alembic** (Migraciones de base de datos)
- **Celery** & **Redis** (Cola de tareas asíncronas)
- **Pytest** (Tests unitarios, de integración y E2E)
- **JWT & Argon2** (Seguridad y hashing de contraseñas)

### Frontend
- **Next.js 14 / 15** (TypeScript, React, App Router)
- **Tailwind CSS**
- **React Query & Zod**

---

## Requisitos Previos

Asegúrate de tener instalados:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Make](https://www.gnu.org/software/make/) (opcional, pero recomendado)

---

## Cómo Empezar

### 1. Clonar el repositorio y configurar variables de entorno
Crea un archivo `.env` a partir del archivo de ejemplo:
```bash
cp .env.example .env
```

### 2. Levantar la aplicación completa
Para iniciar todos los servicios (Postgres, Redis, MinIO, Mailpit, Backend y Frontend):
```bash
make up
# o directamente: docker compose up -d
```

### 3. Ejecutar las migraciones
Aplica las migraciones en la base de datos de PostgreSQL:
```bash
make migrate
```

### 4. Generar datos de prueba (Seed)
Para poblar el sistema con usuarios ficticios (Admin, Requesters, Workers), tareas en diferentes estados y transacciones:
```bash
make seed
```

---

## Credenciales de Desarrollo

Tras ejecutar `make seed`, podrás iniciar sesión en el portal web con las siguientes cuentas de prueba:

- **Administrador**: `admin@taskkin.local` / `password123`
- **Solicitante (Requester)**: `requester@taskkin.local` / `password123`
- **Trabajador (Worker)**: `worker1@taskkin.local` / `password123`

---

## Comandos Disponibles (Makefile)

El proyecto incluye un `Makefile` con atajos para facilitar el desarrollo local:

| Comando | Descripción |
|---------|-------------|
| `make up` | Levanta todos los servicios en segundo plano |
| `make down` | Detiene y elimina los contenedores activos |
| `make build` | Reconstruye las imágenes de Docker |
| `make migrate` | Aplica todas las migraciones de base de datos pendientes |
| `make seed` | Puebla la base de datos con información de prueba |
| `make test` | Ejecuta la suite de pruebas unitarias y de integración con cobertura |
| `make lint` | Ejecuta Ruff y MyPy para validar estilo y tipado |
| `make format` | Ejecuta Ruff format para autoformatear el código |
| `make logs` | Muestra los logs en vivo de los contenedores |
| `make shell` | Abre una terminal interactiva dentro del contenedor de Backend |

---

## Enlaces Útiles (Local)

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Documentación de la API (Swagger UI)**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (User: `minioadmin` / Pass: `minioadminpassword`)
- **Mailpit (Visualizador de correos)**: [http://localhost:8025](http://localhost:8025)
