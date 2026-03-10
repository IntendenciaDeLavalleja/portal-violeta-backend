import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.agenda import Locality, Procedure, AppointmentSlot
from app.models.camping import CampingService, HeroImage, ServiceTestimonial
from datetime import date, time, timedelta

@click.command('seed-data')
@with_appcontext
def seed_data():
    """Popula la base de datos con trámites, localidades y turnos iniciales."""
    
    # 1. Crear Localidades
    municipalidades = [
        "Palacio Municipal (Minas)",
        "Municipio de Solís de Mataojo",
        "Municipio de José Pedro Varela",
        "Municipio de Mariscala"
    ]
    
    locality_objs = []
    for name in municipalidades:
        loc = Locality.query.filter_by(name=name).first()
        if not loc:
            loc = Locality(name=name)
            db.session.add(loc)
        locality_objs.append(loc)
    
    db.session.commit()
    print(f"Localidades creadas: {len(locality_objs)}")

    # 2. Crear Trámites
    tramites = [
        ("Renovación de Libreta de Conducir", "Tránsito", "Cédula vigente, examen médico, libreta anterior."),
        ("Solicitud de Carnet de Manipulación", "Higiene", "Cédula de identidad, foto carnet."),
        ("Pago de Patente de Rodados", "Tributaria", "Número de padrón, recibo anterior."),
        ("Permiso de Construcción", "Arquitectura", "Planos aprobados, firma de profesional."),
        ("Solicitud de Contenedor", "Servicios", "Dirección exacta, recibo de contribución.")
    ]
    
    procedure_objs = []
    for name, cat, desc in tramites:
        proc = Procedure.query.filter_by(name=name).first()
        if not proc:
            proc = Procedure(name=name, category=cat, description=desc)
            db.session.add(proc)
        procedure_objs.append(proc)
    
    db.session.commit()
    print(f"Trámites creados: {len(procedure_objs)}")

    # 3. Crear algunos slots de ejemplo para los próximos 7 días
    slots_count = 0
    today = date.today()
    
    for i in range(1, 8):
        current_date = today + timedelta(days=i)
        # Solo días de semana
        if current_date.weekday() >= 5: continue
        
        for loc in locality_objs:
            for proc in procedure_objs:
                # 3 turnos por mañana
                for hour in [9, 10, 11]:
                    slot_time = time(hour, 0)
                    # Evitar duplicados
                    exists = AppointmentSlot.query.filter_by(
                        locality_id=loc.id, 
                        procedure_id=proc.id,
                        date=current_date,
                        time=slot_time
                    ).first()
                    
                    if not exists:
                        slot = AppointmentSlot(
                            locality_id=loc.id,
                            procedure_id=proc.id,
                            date=current_date,
                            time=slot_time,
                            max_capacity=2
                        )
                        db.session.add(slot)
                        slots_count += 1
                        
    db.session.commit()
    print(f"Slots de agenda creados: {slots_count}")

    # 4. Semilla base para el portal Camping Arequita
    if CampingService.query.count() == 0:
        camping_services = [
            {
                'slug': 'cabana-sierra-premium',
                'service_type': 'cabin',
                'name_es': 'Cabaña Sierra Premium',
                'name_en': 'Sierra Premium Cabin',
                'name_pt': 'Cabana Sierra Premium',
                'description_es': 'Cabaña premium con vista a las sierras y cocina equipada.',
                'description_en': 'Premium cabin with mountain views and equipped kitchen.',
                'description_pt': 'Cabana premium com vista para as serras e cozinha equipada.',
                'price': 3200,
                'capacity': 4,
                'total_units': 8,
                'available_units': 8,
                'is_featured': True,
                'is_active': True,
                'amenities': ['wifi', 'ac', 'kitchen', 'parking'],
            },
            {
                'slug': 'parcela-motorhome-deluxe',
                'service_type': 'motorhome',
                'name_es': 'Parcela Motorhome Deluxe',
                'name_en': 'Deluxe Motorhome Plot',
                'name_pt': 'Parcela Motorhome Deluxe',
                'description_es': 'Parcela con conexión eléctrica, agua y parrillero.',
                'description_en': 'Plot with power, water and BBQ.',
                'description_pt': 'Parcela com energia, água e churrasqueira.',
                'price': 1800,
                'capacity': 4,
                'total_units': 15,
                'available_units': 15,
                'is_featured': True,
                'is_active': True,
                'amenities': ['electricity', 'water', 'bbq', 'parking'],
            },
            {
                'slug': 'parcela-premium-sombra',
                'service_type': 'camping',
                'name_es': 'Parcela Premium con Sombra',
                'name_en': 'Premium Shaded Plot',
                'name_pt': 'Parcela Premium com Sombra',
                'description_es': 'Parcela amplia con sombra natural y acceso a servicios.',
                'description_en': 'Spacious shaded plot with full facilities.',
                'description_pt': 'Parcela ampla com sombra natural e acesso a serviços.',
                'price': 800,
                'capacity': 6,
                'total_units': 30,
                'available_units': 30,
                'is_featured': True,
                'is_active': True,
                'amenities': ['electricity', 'bbq', 'shade', 'bathrooms'],
            },
        ]

        for raw in camping_services:
            service = CampingService(
                slug=raw['slug'],
                service_type=raw['service_type'],
                name_es=raw['name_es'],
                name_en=raw['name_en'],
                name_pt=raw['name_pt'],
                description_es=raw['description_es'],
                description_en=raw['description_en'],
                description_pt=raw['description_pt'],
                price=raw['price'],
                capacity=raw['capacity'],
                total_units=raw['total_units'],
                available_units=raw['available_units'],
                is_featured=raw['is_featured'],
                is_active=raw['is_active'],
            )
            service.amenities = raw['amenities']
            db.session.add(service)

        db.session.commit()
        print('Servicios de camping base creados.')

    if HeroImage.query.count() == 0:
        hero_urls = [
            'https://images.unsplash.com/photo-1571863533956-01c88e79957e?w=1920&q=80',
            'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1920&q=80',
            'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920&q=80',
        ]
        for index, url in enumerate(hero_urls):
            db.session.add(HeroImage(url=url, sort_order=index, is_active=True))
        db.session.commit()
        print('Imágenes de portada base creadas.')

    if ServiceTestimonial.query.count() == 0:
        first_service = CampingService.query.first()
        if first_service:
            db.session.add(ServiceTestimonial(
                service_id=first_service.id,
                author_name='María González',
                comment_es='Excelente experiencia, volveríamos sin dudas.',
                comment_en='Excellent experience, we would definitely come back.',
                comment_pt='Experiência excelente, voltaríamos com certeza.',
                is_published=True,
            ))
            db.session.commit()
            print('Testimonios base creados.')

    print("¡Base de datos populada exitosamente!")
