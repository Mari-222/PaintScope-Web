# PaintScope

Marketplace de subastas de arte (Django 5.2 · MySQL 8 en Docker). Proyecto IC 5821, GR 20, II semestre 2026.

## Puesta en marcha

```powershell
git clone https://github.com/Mari-222/PaintScope
cd PaintScope
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # ajusta valores si hace falta (el .env NO se sube a GitHub)
docker compose up -d            # MySQL en el puerto 3308; espera ~30 s la primera vez
python manage.py migrate
python manage.py createsuperuser
python manage.py cargar_demo    # opcional: usuarios, evento y subastas de ejemplo
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>. Con `cargar_demo` todas las cuentas usan la contraseña `paintscope123`:
`admin@`, `curador@`, `lucia@` (comprador con tarjeta), `sin-pago@` (comprador sin método de pago),
`elena.montes@` (artista) … todas `@paintscope.demo`.

## Pruebas

```powershell
python manage.py test --settings=config.settings_test   # usa SQLite en memoria, no necesita Docker
```

## Estructura

| App | Qué contiene | Jira |
|---|---|---|
| `usuarios` | Usuario con rol, registro, login, perfil, contraseña, método de pago | PAIN-14, 15, 16, 24 |
| `obras` | Portafolio, postulaciones, curaduría, eventos temáticos, artistas | PAIN-17, 18, 19, 20 |
| `subastas` | Catálogo, dashboard en vivo, pujas, extensión de tiempo, cierre, insignia | PAIN-21, 22, 23, 27 |
| `visitas` | Agenda de visitas guiadas presenciales o virtuales | PAIN-26 |
| `notificaciones` | Avisos dentro de la aplicación | PAIN-28 |
| `panel` | Usuarios, roles, parámetros globales, moderación | PAIN-29 |

Detalle de cada historia, sus criterios de aceptación y las pruebas que las cubren: [`docs/SPRINTS.md`](docs/SPRINTS.md).

## Tareas programadas

Las subastas se abren y cierran solas cuando alguien navega, pero conviene programar también
`python manage.py cerrar_subastas` (cada minuto con el Programador de tareas o cron) para que cierren aunque no haya visitas.
