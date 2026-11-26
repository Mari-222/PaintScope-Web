# PaintScope

Marketplace de subastas de arte (Django 5.2 · MySQL 8 en Docker). Proyecto IC 5821, GR 20, II semestre 2026.


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
