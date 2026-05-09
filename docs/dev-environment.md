# Entorno virtual y dependencias — `besoccer-scraper`

## 1. Propósito

Este documento sirve como guía operativa para crear, activar, actualizar y validar el entorno virtual del proyecto `besoccer-scraper`.

Debe usarse desde la raíz del proyecto:

```text
Scraping-F-tbol-Datos/
```

La guía está alineada con la arquitectura actual del proyecto:

- PostgreSQL como base principal.
- Railway como proveedor inicial de base de datos.
- `.env` como gobierno de configuración.
- CLI reproducible.
- Dependencias controladas desde `pyproject.toml` o `requirements.txt`.

---

## 2. Supuestos base

Antes de instalar dependencias, se asume que existen estos archivos mínimos:

```text
README.md
pyproject.toml
.env.example
docs/
src/besoccer_scraper/
sql/postgres/
```

El entorno virtual debe quedar dentro del proyecto como:

```text
.venv/
```

Ese directorio debe estar ignorado en `.gitignore`.

---

## 3. Preparar dependencias del sistema en Ubuntu / WSL

Ejecutar desde terminal Ubuntu/WSL:

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  libpq-dev
```

Validar versión de Python:

```bash
python3 --version
```

Versión recomendada:

```text
Python 3.10+
```

Si el sistema tiene `python3.10` disponible, se puede usar explícitamente:

```bash
python3.10 --version
```

---

## 4. Crear entorno virtual

Desde la raíz del proyecto:

```bash
cd Scraping-F-tbol-Datos
python3 -m venv .venv
```

Activar el entorno virtual:

```bash
source .venv/bin/activate
```

Validar que Python apunta al entorno virtual:

```bash
which python
python --version
```

Salida esperada aproximada:

```text
.../Scraping-F-tbol-Datos/.venv/bin/python
Python 3.10.x
```

Para salir del entorno virtual:

```bash
deactivate
```

---

## 5. Crear entorno virtual en Windows PowerShell

Solo si se trabaja directamente en Windows, no en WSL:

```powershell
cd Scraping-F-tbol-Datos
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación del entorno:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Después volver a activar:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 6. Actualizar herramientas base de Python

Con el entorno virtual activo:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Validar:

```bash
python -m pip --version
```

---

## 7. Instalación recomendada con `pyproject.toml`

La ruta preferida para el proyecto es instalar el paquete en modo editable.

Instalación base:

```bash
python -m pip install -e .
```

Instalación con dependencias de desarrollo, si el `pyproject.toml` define extras:

```bash
python -m pip install -e ".[dev]"
```

Validar que el paquete se puede importar:

```bash
python -c "import besoccer_scraper; print('besoccer_scraper import OK')"
```

Validar CLI:

```bash
besoccer --help
```

Si el comando `besoccer` todavía no existe, usar temporalmente:

```bash
python -m besoccer_scraper.main --help
```

---

## 8. Instalación alternativa con `requirements.txt`

Si el proyecto trabaja con `requirements.txt`, instalar así:

```bash
python -m pip install -r requirements.txt
```

Si existe archivo de desarrollo:

```bash
python -m pip install -r requirements-dev.txt
```

Validar instalación:

```bash
python -m pip check
python -c "import besoccer_scraper; print('besoccer_scraper import OK')"
```

---

## 9. `requirements.txt` base sugerido

Este bloque cubre las necesidades actuales de la arquitectura: configuración por `.env`, CLI, PostgreSQL, HTTP, parsing, retries, logging, caché simple y fallback con navegador.

Crear o actualizar `requirements.txt`:

```bash
cat > requirements.txt <<'REQEOF'
# Configuración y settings
pydantic>=2.7,<3
pydantic-settings>=2.3,<3
python-dotenv>=1.0,<2

# CLI y salida en terminal
typer>=0.12,<1
rich>=13.7,<15

# Base de datos PostgreSQL
SQLAlchemy>=2.0,<3
psycopg[binary,pool]>=3.2,<4

# HTTP, scraping y parsing
httpx>=0.27,<1
beautifulsoup4>=4.12,<5
lxml>=5.2,<7

# Reintentos, backoff y utilidades
tenacity>=8.3,<10
python-slugify>=8.0,<9
python-dateutil>=2.9,<3
structlog>=24.1,<26

# Browser fallback controlado
playwright>=1.44,<2
REQEOF
```

Instalar:

```bash
python -m pip install -r requirements.txt
```

---

## 10. `requirements-dev.txt` sugerido

Crear o actualizar `requirements-dev.txt`:

```bash
cat > requirements-dev.txt <<'REQDEVEOF'
# Testing
pytest>=8.2,<9
pytest-cov>=5,<8
pytest-mock>=3.14,<4

# Calidad de código
ruff>=0.5,<1
mypy>=1.10,<2

# Utilidades para desarrollo
ipython>=8.25,<10
REQDEVEOF
```

Instalar:

```bash
python -m pip install -r requirements-dev.txt
```

---

## 11. Instalar navegador de Playwright

Playwright solo debe usarse como fallback controlado, no como ruta principal del scraping.

Instalar Chromium:

```bash
python -m playwright install chromium
```

En Ubuntu/WSL, si faltan dependencias del sistema:

```bash
python -m playwright install-deps chromium
```

Validar instalación:

```bash
python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    print('Playwright Chromium OK')
    browser.close()
PY
```

---

## 12. Configurar `.env`

Crear `.env` desde la plantilla:

```bash
cp .env.example .env
```

Editar:

```bash
nano .env
```

Variables mínimas para validar el entorno:

```env
APP_ENV=local
LOG_LEVEL=INFO
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
DB_SSL_MODE=require
PIPELINE_MODE=historical
RUN_MODE=discovery_and_scrape
ACTIVE_LEAGUES=premier
START_YEAR=2025
YEARS_BACK=1
BATCH_SIZE=10
ONLY_PENDING=true
RESUME=true
RUN_LOCK_ENABLED=true
```

Importante:

```text
Nunca subir `.env` real al repositorio.
```

---

## 13. Validar conexión y migraciones

Con el entorno virtual activo y `.env` configurado:

```bash
besoccer db check
besoccer db migrate
besoccer db status
```

Si el comando `besoccer` aún no está registrado:

```bash
python -m besoccer_scraper.main db check
python -m besoccer_scraper.main db migrate
python -m besoccer_scraper.main db status
```

Resultado esperado:

```text
Conexión PostgreSQL OK
Migraciones aplicadas o sin pendientes
Estado de DB OK
```

---

## 14. Ejecutar tests

Todos los tests:

```bash
pytest -q
```

Solo unitarios:

```bash
pytest tests/unit -q
```

Solo integración:

```bash
pytest tests/integration -q
```

Solo contratos de parsers:

```bash
pytest tests/contract -q
```

Con cobertura:

```bash
pytest --cov=besoccer_scraper --cov-report=term-missing
```

---

## 15. Comandos de actualización segura

Ver paquetes desactualizados:

```bash
python -m pip list --outdated
```

Actualizar herramientas base:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Actualizar una dependencia específica:

```bash
python -m pip install --upgrade nombre_paquete
```

Actualizar dependencias desde `requirements.txt`:

```bash
python -m pip install --upgrade -r requirements.txt
```

Actualizar dependencias de desarrollo:

```bash
python -m pip install --upgrade -r requirements-dev.txt
```

Después de actualizar, validar:

```bash
python -m pip check
besoccer db check
pytest -q
```

Guardar snapshot local de versiones instaladas:

```bash
python -m pip freeze > requirements.lock.txt
```

Recomendación:

```text
Actualizar dependencias una por una cuando el proyecto ya esté conectado a Postgres y tenga tests de migraciones/repositorios.
```

---

## 16. Reinstalación limpia del entorno

Si el entorno virtual queda corrupto o con dependencias mezcladas:

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

Si se usa `requirements.txt`:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Validar:

```bash
python -m pip check
pytest -q
```

---

## 17. Problemas comunes

### `besoccer: command not found`

Causas probables:

- el entorno virtual no está activo;
- el paquete no fue instalado en modo editable;
- falta configurar el entrypoint en `pyproject.toml`.

Solución:

```bash
source .venv/bin/activate
python -m pip install -e .
python -m besoccer_scraper.main --help
```

---

### Error instalando `psycopg`

En Ubuntu/WSL, instalar dependencias del sistema:

```bash
sudo apt update
sudo apt install -y libpq-dev build-essential
```

Luego reinstalar:

```bash
python -m pip install --upgrade "psycopg[binary,pool]"
```

---

### Error de conexión a PostgreSQL

Revisar `.env`:

```bash
grep DATABASE_URL .env
```

Validar que:

- la URL sea de PostgreSQL;
- usuario, password, host, puerto y base sean correctos;
- Railway tenga la base activa;
- si Railway exige SSL, `DB_SSL_MODE=require` esté configurado.

---

### Playwright dice que no encuentra navegador

Instalar Chromium:

```bash
python -m playwright install chromium
```

En Linux/WSL:

```bash
python -m playwright install-deps chromium
```

---

### Tests de integración fallan por DB

Revisar que exista una base de pruebas o que el `.env` apunte a una base segura para testing.

No correr tests de integración destructivos contra producción.

---

## 18. Flujo recomendado para un día normal de desarrollo

```bash
cd Scraping-F-tbol-Datos
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
besoccer db check
besoccer db status
pytest -q
```

Si hubo cambios en migraciones:

```bash
besoccer db migrate
besoccer db status
pytest tests/integration/test_db_migrations.py -q
```

---

## 19. Checklist de entorno listo

```text
[ ] .venv creado
[ ] .venv activado
[ ] pip/setuptools/wheel actualizados
[ ] requirements instalados
[ ] .env creado desde .env.example
[ ] DATABASE_URL configurado
[ ] besoccer --help responde
[ ] besoccer db check responde
[ ] besoccer db migrate ejecuta sin error
[ ] pytest -q pasa o falla por errores conocidos del código, no por entorno
```

---

## 20. Regla final

El entorno virtual solo prepara el proyecto para ejecutarse.

La fuente de verdad operativa sigue siendo:

```text
.env + PostgreSQL + migraciones + CLI + job_runs/job_logs + locks
```
