# Buzon Backend

Backend modular con Flask, SQLAlchemy, blueprints, y validación estricta.

## Estructura

- `app/`
  - `routes/`: Endpoints organizados por dominios (public, admin).
  - `services/`: Lógica de negocio.
  - `repositories/`: Capa de acceso a datos.
  - `schemas/`: Serialización y validación con Marshmallow.
  - `models/`: Modelos ORM SQLAlchemy.
  - `utils/`: Utilidades generales.

## Setup

### 1. Crear entorno virtual (venv)

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copiar y renombrar el archivo de ejemplo:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Editar el archivo `.env` con tus credenciales de base de datos, correo y MinIO.

Variables Redis soportadas:

- `REDIS_URL` (opcional, tiene prioridad si se define).
- `REDIS_HOST` (default `redis`).
- `REDIS_PORT` (default `6379`).
- `REDIS_DB` (default `0`).
- `REDIS_PASSWORD` (opcional).

Si usas password en Redis y no defines `REDIS_URL`, la app construye automáticamente:
`redis://:PASSWORD@HOST:PORT/DB`

### 4. Inicializar Base de Datos

Asegurate de que MariaDB esté corriendo y la base de datos `buzon_db` (o la que hayas puesto en .env) exista.

```bash
# Inicializar migraciones (solo la primera vez si no existe carpeta migrations)
flask db init

# Generar script de migración inicial
flask db migrate -m "Initial migration"

# Aplicar cambios a la DB
flask db upgrade
```

Si actualizás desde una versión anterior, ejecutá siempre `flask db upgrade` antes de iniciar la app para evitar errores de columnas faltantes en `pre_reservations` (por ejemplo `archive_reason`, `checked_in_at`, `completed_at`).

### 5. Correr en modo desarrollo
Activar entorno:
```bash
venv\Scripts\activate
```

```bash
flask run
# O usando wsgi.py directamente
python wsgi.py
```

## Rutas y Acceso

El sistema está dividido en dos interfaces principales:

1.  **Tablero Web (Admin Flask)**: 
    - URL: `/admin/`
    - Autenticación: `/admin/login` (Basada en Sesiones y Captcha).
    - Uso: Gestión de trámites, locales y agenda desde el navegador.

2.  **App de Escritorio (Electron)**:
    - Autenticación: `/api/auth/login` (Basada en JSON).
    - Uso: Operaciones administrativas remotas desde la aplicación Electron.

## Comandos útiles

- `flask routes`: Ver todas las rutas registradas.
- `flask db upgrade`: Aplicar migraciones pendientes.

### Comandos Personalizados (CLI)

1.  **Crear Usuario Administrador**:
    Crea un admin (o super admin) con username, email, password y flag.
    ```bash
    flask create-admin nombre-de-admin mail-de-admin contraseña-de-admin true/false-super-admin
    ```

2.  **Inicializar Bucket MinIO**:
    Verifica que la conexión a MinIO funcione y crea el bucket si no existe.
    ```bash
    flask init-bucket
    ```

3.  **Generar Secret Key**:
    Genera un token seguro para pegar en tu `.env`.
    ```bash
    flask rotate-secret
    ```

## Testing

```bash
pytest
```
