from datetime import datetime
from app.extensions import db
from app.models.camping import PreReservation, CampingService


def archive_expired_pre_reservations() -> int:
    now = datetime.utcnow()
    # 1. Expire unconfirmed pending reservations after 48h
    expired = PreReservation.query.filter(
        PreReservation.status == 'pendiente',
        PreReservation.expires_at <= now,
    ).all()

    for reservation in expired:
        reservation.status = 'expirado'
        reservation.archived_at = now
        reservation.archive_reason = 'Expiración automática de 48 horas sin confirmación'

    # 2. Auto-complete finished stays (active -> completed)
    # Check if check_out date has passed (at end of day usually, but let's use current date)
    from datetime import date
    today = date.today()
    finished = PreReservation.query.filter(
        PreReservation.status == 'activo',
        PreReservation.check_out < today
    ).all()

    for res in finished:
        res.status = 'completado'
        res.completed_at = now
        # When completed, units are returned to available
        service = CampingService.query.get(res.service_id)
        if service:
            service.available_units = min(service.total_units, service.available_units + 1)

    db.session.commit()
    return len(expired) + len(finished)


def confirm_pre_reservation(pre_reservation: PreReservation) -> tuple[bool, str]:
    if pre_reservation.status != 'pendiente':
        return False, f'La pre-reserva ya está en estado {pre_reservation.status}'

    if pre_reservation.expires_at <= datetime.utcnow():
        pre_reservation.status = 'expirado'
        pre_reservation.archived_at = datetime.utcnow()
        db.session.commit()
        return False, 'La pre-reserva expiró y fue movida a Expiradas automáticamente'

    service = CampingService.query.filter_by(id=pre_reservation.service_id).with_for_update().first()
    if not service:
        return False, 'Servicio no encontrado'

    if service.available_units <= 0:
        return False, 'No hay disponibilidad para confirmar esta pre-reserva'

    service.available_units = max(0, service.available_units - 1)
    pre_reservation.status = 'confirmado'
    pre_reservation.confirmed_at = datetime.utcnow()
    db.session.commit()
    return True, 'Pre-reserva confirmada'
