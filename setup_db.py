#
# ESTE ARCHIVO AHORA SE LLAMA setup_db.py
#
from backend import app, db, User, PilotProfile, ServicePackage, Availability
import bcrypt
from datetime import date, timedelta

def seed_database():
    with app.app_context():
        print("--- Iniciando el proceso de sembrado de la base de datos ---")
        
        # Comprobamos si ya existen usuarios para no duplicar
        if User.query.count() > 0:
            print("La base de datos ya contiene datos. Proceso de sembrado omitido.")
            return

        print("Base de datos vacía. Poblando con datos de prueba...")

        # Creamos cliente y piloto
        client_password = 'password_cliente'
        client_hashed = bcrypt.hashpw(client_password.encode('utf-8'), bcrypt.gensalt())
        client_user = User(username='cliente_test', email='cliente@test.com', password=client_hashed.decode('utf-8'), role='Cliente')
        
        pilot_password = 'password_piloto'
        pilot_hashed = bcrypt.hashpw(pilot_password.encode('utf-8'), bcrypt.gensalt())
        pilot_user = User(username='piloto_test', email='piloto@test.com', password=pilot_hashed.decode('utf-8'), role='Piloto')
        
        profile = PilotProfile(
            name='AeroVision Pro', 
            tagline='Cinematografía Aérea Avanzada', 
            location='Madrid, ES', 
            bio='Más de 10 años de experiencia.'
        )
        pilot_user.pilot_profile = profile
        
        db.session.add(client_user)
        db.session.add(pilot_user)
        db.session.commit()
        print("Usuarios y perfil guardados.")

        profile_in_db = PilotProfile.query.first()
        if profile_in_db:
            service1 = ServicePackage(name="Paquete Boda Básico", price=800, description="4h de cobertura", pilot_profile_id=profile_in_db.id)
            service2 = ServicePackage(name="Vídeo Inmobiliario", price=450, description="Hasta 200m²", pilot_profile_id=profile_in_db.id)
            db.session.add_all([service1, service2])
            
            today = date.today()
            db.session.add(Availability(date=today + timedelta(days=5), pilot_profile_id=profile_in_db.id))
            db.session.add(Availability(date=today + timedelta(days=6), pilot_profile_id=profile_in_db.id))
            db.session.add(Availability(date=today + timedelta(days=10), pilot_profile_id=profile_in_db.id))
            
            db.session.commit()
            print("Servicios y disponibilidad añadidos.")
        
        print("\n¡Base de datos poblada con éxito!")