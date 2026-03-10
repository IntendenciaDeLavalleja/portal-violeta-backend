from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.camping import Amenity
from app.utils.logging_helper import log_activity
from .. import admin_bp

@admin_bp.route('/camping/amenities', methods=['GET', 'POST'])
@login_required
def camping_amenities():
    if request.method == 'POST':
        amenity_id = request.form.get('amenity_id', type=int)
        name_es = (request.form.get('name_es') or '').strip()
        name_en = (request.form.get('name_en') or '').strip()
        name_pt = (request.form.get('name_pt') or '').strip()
        icon = (request.form.get('icon') or '✨').strip()

        if not name_es:
            flash('El nombre en español es obligatorio', 'error')
            return redirect(url_for('admin.camping_amenities'))

        amenity = Amenity.query.get(amenity_id) if amenity_id else Amenity()
        if not amenity and amenity_id:
            flash('Comodidad no encontrada', 'error')
            return redirect(url_for('admin.camping_amenities'))

        amenity.name_es = name_es
        amenity.name_en = name_en
        amenity.name_pt = name_pt
        amenity.icon = icon

        if not amenity_id:
            db.session.add(amenity)
        
        db.session.commit()
        log_activity('AMENITY_UPSERT', f'Comodidad {"actualizada" if amenity_id else "creada"}: {name_es}')
        flash('Comodidad guardada correctamente', 'success')
        return redirect(url_for('admin.camping_amenities'))

    amenities = Amenity.query.order_by(Amenity.name_es.asc()).all()
    emojis = [
        # Agua, Piscina y Río
        "🏊", "🏊‍♂️", "🤽", "🛟", "🌊", "🚣", "🛶", "🚤", "🛥️", "⛴️", "⛵", "⛱️", "🏝️", "⛲", "🛁", "🫧",
        # Naturaleza y Exterior
        "🌳", "🌲", "🌴", "🌵", "🪵", "🌿", "🌱", "🌾", "🍃", "🍂", "🍄", "⛰️", "🏔️", "🏔️", "🌋", "🏕️", "🛖", "🏡", "🛖", "🌞", "🌤️", "🌙", "🌌", "🌠", "🌈",
        # Comida y Fuego
        "🔥", "🍖", "🥓", "🍳", "🥘", "🍕", "🍔", "🥪", "🍱", "🍽️", "🥡", "🥤", "☕", "🍷", "🍺", "🍻", "🍹", "🍾",
        # Instalaciones y Servicios
        "🚿", "🚽", "🧻", "🧼", "🧺", "🔌", "🔋", "💡", "🔦", "📡", "📶", "🛒", "🛍️", "🧹",
        # Entretenimiento y Confort
        "📺", "💻", "🕹️", "📻", "🛏️", "🛌", "🛋️", "🪑", "🧖", "👗", "👕", "👔", "🧸", "🏠", "🚪", "🗝️", "🔐",
        # Deporte y Logistica
        "🚗", "🚌", "🚐", "🚛", "🅿️", "🚲", "🏍️", "🛴", "🛹", "🚶", "🏃", "⚽", "🏀", "🎾", "🎣", "🧩", "🔨", "🛠️", "🩹",
        # Animales
        "🐕", "🐈", "🐾", "🐮", "🐷", "🐔", "🦆", "🐝", "🦋", "🐞"
    ]
    # Deduplicar emojis
    emojis = sorted(list(set(emojis)), key=lambda x: emojis.index(x) if x in emojis else 999)

    return render_template('admin/camping_amenities.html', 
                           amenities=[a.to_dict() for a in amenities], 
                           emojis=emojis)

@admin_bp.route('/camping/amenities/<int:amenity_id>/delete', methods=['POST'])
@login_required
def delete_camping_amenity(amenity_id):
    amenity = Amenity.query.get_or_404(amenity_id)
    name = amenity.name_es
    db.session.delete(amenity)
    db.session.commit()
    log_activity('AMENITY_DELETE', f'Comodidad eliminada: {name}')
    flash('Comodidad eliminada', 'success')
    return redirect(url_for('admin.camping_amenities'))
