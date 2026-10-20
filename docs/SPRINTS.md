# Sprints de PaintScope: qué se construyó y dónde

Los criterios de aceptación salen de las historias del Jira (proyecto PAIN). Cada fila indica el código
y la prueba automática que la verifica (`python manage.py test --settings=config.settings_test`).

## Sprint 1 · Autenticación y perfil (12–24 oct) · cerrado

| Historia | Criterio | Dónde | Prueba |
|---|---|---|---|
| PAIN-14 Registro | Pide nombre, correo, contraseña y rol (Artista o Comprador) | `usuarios/forms.py` `RegistroForm` | `RegistroTests` |
| | Valida que el correo no exista | `RegistroForm.clean_email` | `test_correo_duplicado…` |
| | Queda autenticado | `usuarios/views.py` `registro_view` | `test_registro_crea_cuenta…` |
| PAIN-15 Inicio de sesión | Valida credenciales, error y reintento | `login_view` | `LoginTests` |
| | Redirige al panel según el rol | `destino_por_rol` | `test_redirige_al_panel_segun_rol` |
| PAIN-16 Gestión de perfil | Ver y editar nombre, correo y teléfono | `perfil_view`, `PerfilForm` | `PerfilTests` |
| | Cambiar contraseña de forma segura | `cambiar_password` (mantiene la sesión) | `test_cambia_contrasena…` |
| PAIN-37 / 38 Prototipo | Pantallas por rol y tema de color por rol | `usuarios/context_processors.py`, `static/css/paintscope.css` | recorrido manual |

## Sprint 2 · Portafolio, postulaciones, curaduría y eventos (23 oct – 7 nov)

| Historia | Criterio | Dónde | Prueba |
|---|---|---|---|
| PAIN-17 Carga de obras | Título, descripción, técnica, dimensiones e imagen | `obras/forms.py` `ObraForm` | `PortafolioTests` |
| | Se guarda como «Borrador» | `obras/views.py` `obra_nueva` | `test_guarda_obra_en_estado_borrador` |
| | Campo faltante se señala y no guarda | `ObraForm` | `test_campo_obligatorio_faltante…` |
| PAIN-18 Postulación | Obra propia + evento con convocatoria abierta; queda «Pendiente de revisión» | `obras/services.py` `postular` | `PostulacionTests` |
| | Convocatoria cerrada no permite postular | `Evento.convocatoria_abierta` | `test_convocatoria_cerrada…` |
| PAIN-19 Evaluación | Revisar información e imágenes | `obras/views.py` `evaluar` | `EvaluacionTests` |
| | Aprobar con precio base o rechazar con motivo | `services.aprobar` / `services.rechazar` | `test_aprobar…`, `test_rechazar…` |
| | El artista recibe notificación dentro de la app | `notificaciones/servicio.py` | `test_…_notifica` |
| PAIN-20 Eventos temáticos | Crear con nombre, temática, temporada y fechas; editar y publicar | `obras/views.py` `evento_*` | `EventosTests` |
| | Obras aprobadas se asocian a un evento publicado | `evento_incluir_obra` | `test_asocia_obra_aprobada…` |

## Sprint 3 · Subastas, visitas, notificaciones y administración (5–21 nov)

| Historia | Criterio | Dónde | Prueba |
|---|---|---|---|
| PAIN-21 Dashboard | Activas con puja más alta y tiempo restante | `subastas/views.py` `en_vivo` | `ConsultasTests` |
| | Actualización ≤ 3 s | `static/js/subastas.js` consulta `api_dashboard` cada 2 s | `test_api_devuelve_estado_en_json` |
| PAIN-22 Pujar | Monto mayor a la puja actual; registra y actualiza precio | `subastas/services.py` `registrar_puja` | `PujaTests` |
| | Monto inválido se rechaza y pide uno mayor | `PujaRechazada` | `test_monto_igual_o_menor…` |
| PAIN-23 Extensión | Puja en los últimos minutos suma horas (por defecto 5 min / +6 h) | `registrar_puja` + `panel/parametros.py` | `ExtensionDinamicaTests` |
| PAIN-24 Sin método de pago | Bloquea la puja y lo indica; se registra desde el perfil | `usuarios/models.py` `MetodoPago` | `test_sin_metodo_de_pago…`, `MetodoPagoTests` |
| PAIN-26 Agendar visita | Horarios por tipo, confirmación, sugerencia de otras fechas | `visitas/services.py` | `VisitasTests` |
| PAIN-27 Insignia | Se otorga al superar el umbral de ventas y se ve en el perfil | `subastas/services.py` `evaluar_insignia` | `InsigniaTests` |
| PAIN-28 Notificaciones | Pantalla in-app; puja superada, aprobación/rechazo, cierre, visita | `notificaciones/` | `NotificacionesTests`, `CierreTests` |
| PAIN-29 Panel de administración | Ver, crear, editar y suspender usuarios; roles y permisos; parámetros | `panel/` | `UsuariosPanelTests`, `ParametrosTests` |
| | Confirmación adicional si el usuario tiene actividad en curso (CU-08) | `panel/views.py` `_actividad_activa` | `test_suspender_con_actividad…` |

## Decisiones y supuestos (conviene comentarlos con el profesor)

- **Stack**: Django + MySQL en lugar de Rails (el ERS dice Rails; hay que actualizar Supuestos y Restricciones).
- **Pago y envío (RF-11)** quedó fuera, como indicó el profesor. Solo existe el método de pago exigido por RF-16, y se guardan
  únicamente los últimos 4 dígitos. No se hacen cobros.
- **Tiempo real**: polling cada 2 s en lugar de WebSockets; cumple RNF-03 (≤ 3 s) con mucho menos complejidad.
- **Curador asignado**: todos los curadores ven las postulaciones pendientes; quien evalúa queda registrado como curador de la obra.
- **Quién puja**: solo el rol Comprador (RF-09). En el prototipo el artista también veía «Mis pujas»; se siguió el ERS.
- **Eliminar obra del catálogo** (anexo A del ERS) se implementó como «Retirar del catálogo», reversible, desde Moderación.
- **Fuera de alcance** por no estar en el ERS ni en el Jira: Favoritos y Seguir artistas (aparecen en el prototipo).
- **Zona horaria**: `America/Costa_Rica`.
