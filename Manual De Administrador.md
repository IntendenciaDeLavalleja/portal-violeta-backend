# 🌲 Manual de Administrador - Camping Arequita

Este manual describe cómo operar el panel administrativo actualizado del Camping Arequita, incluyendo las nuevas funciones de alta manual de reservas/pre-reservas, trazabilidad por origen y mejoras de visualización.

---

## 🔐 1. Acceso y seguridad

El panel utiliza autenticación con protección adicional:

1. Ingresar usuario y contraseña.
2. Resolver captcha simple (suma).
3. Ingresar código de verificación enviado por email (2FA).

Esto reduce el riesgo de acceso no autorizado incluso si la contraseña se ve comprometida.

---

## 🏠 2. Dashboard principal (actualizado)

El inicio del panel muestra indicadores operativos y dos tablas rápidas:

- **Últimas 10 pre-reservas** (ordenadas por creación más reciente).
- **Últimas 10 sugerencias** (ordenadas por creación más reciente).

También mantiene contadores clave de servicios, testimonios, pendientes, huéspedes activos y sugerencias nuevas.

---

## ✨ 3. Comodidades

Permite crear/editar comodidades para asociarlas a servicios del camping.

- Cargar nombres en ES/EN/PT.
- Seleccionar icono.
- Guardar para uso inmediato en la edición de cabañas/parcelas.

---

## 📦 4. Servicios del camping

Gestión de cabañas, parcelas y motorhome:

- Definir slug, precios, capacidad y unidades.
- Asociar comodidades.
- Cargar imágenes (WEBP) según límites definidos por sistema.
- Mantener disponibilidad real para que reservas confirmadas descuenten unidades correctamente.

---

## 📅 5. Pre-reservas (Camping) - nuevas funciones

### 5.1 Alta manual desde administración

En **Pre-reservas** ahora existe el bloque **"Crear registro manual"** para cargar una pre-reserva o reserva confirmada directamente desde el panel.

Campos principales:

- Servicio
- Nombre, email, teléfono
- Huéspedes
- Check-in / Check-out
- Idioma
- Estado inicial (pendiente o confirmado)
- Notas

Reglas de validación:

- Fechas válidas y salida posterior al ingreso.
- Cantidad de huéspedes dentro de capacidad del servicio.
- Si se crea como confirmada, debe existir disponibilidad.

### 5.2 Origen del registro (trazabilidad)

Cada pre-reserva muestra **Origen**:

- **Web**: creada por formulario público.
- **Admin**: creada manualmente por funcionario.

Esta información también se exporta en CSV.

### 5.3 Ciclo de estados

Estados operativos:

- Pendiente
- Confirmado
- Activo (check-in)
- Completado
- Expirado
- Archivado por admin (con motivo)

El sistema mantiene archivado automático de vencidas y auditoría de acciones administrativas.

### 5.4 Listado y paginación

El listado de Pre-reservas ahora muestra:

- **10 registros por página**
- Navegación por páginas manteniendo filtros

Filtros disponibles:

- Estado
- Rango de fecha (check-in)

---

## 🗓️ 6. Reservas de agenda - nuevas funciones

En **Reservas** se incorporó **"Crear reserva manual"** desde administración:

- Selección de turno disponible.
- Carga de CI, nombre, apellido y email.
- Estado inicial (pendiente/confirmada).

Cada reserva registra su **origen (Web/Admin)** y se refleja en listado y exportación.

---

## 💬 7. Sugerencias y testimonios

- **Sugerencias:** revisar, cambiar estado y mantener orden operativo.
- **Testimonios:** publicar/ocultar y editar contenido según políticas del camping.

---

## 🧰 8. Herramientas adicionales

- **Portadas Hero:** gestión de banners principales.
- **Limpieza de media (MinIO):** limpieza de archivos huérfanos.
- **Auditoría:** trazabilidad de acciones administrativas.

---

## ✅ 9. Buenas prácticas operativas

- Confirmar disponibilidad antes de altas manuales confirmadas.
- Registrar motivos al archivar/cancelar para mantener histórico claro.
- Usar filtros y paginación para revisar volumen de pre-reservas.
- Cerrar sesión al terminar.

---

*Manual actualizado el 17 de febrero de 2026 para la Administración del Camping Arequita.*
