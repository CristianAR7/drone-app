import os
from backend import app, db, User, PilotProfile, ServicePackage
import bcrypt
from datetime import date, timedelta

if os.path.exists('instance/site.db'):
    os.remove('instance/site.db')
    print("Base de datos anterior eliminada.")

with app.app_context():
    db.create_all()
    print("Nuevas tablas creadas.")

    client_password = 'password_cliente'
    client_hashed = bcrypt.hashpw(client_password.encode('utf-8'), bcrypt.gensalt())
    client_user = User(username='cliente_test', email='cliente@test.com', password=client_hashed.decode('utf-8'), role='Cliente')
    db.session.add(client_user)
    print(f"Creando usuario Cliente: {client_user.username}")

    pilot_password = 'password_piloto'
    pilot_hashed = bcrypt.hashpw(pilot_password.encode('utf-8'), bcrypt.gensalt())
    pilot_user = User(username='piloto_test', email='piloto@test.com', password=pilot_hashed.decode('utf-8'), role='Piloto')
    
    profile = PilotProfile(
        name='AeroVision Pro', 
        tagline='Cinematografía Aérea Avanzada', 
        location='Madrid, ES', 
        bio='Más de 10 años de experiencia en filmaciones.'
    )
    pilot_user.pilot_profile = profile
    db.session.add(pilot_user)
    print(f"Creando usuario Piloto '{pilot_user.username}' y su perfil '{profile.name}'")

    db.session.commit()
    print("Usuarios y perfil guardados.")

    profile_in_db = PilotProfile.query.first()
    if profile_in_db:
        service1 = ServicePackage(name="Paquete Boda Básico", description="4 horas de cobertura", price=800, pilot_profile_id=profile_in_db.id)
        service2 = ServicePackage(name="Vídeo Inmobiliario", description="Propiedades de hasta 200m²", price=450, pilot_profile_id=profile_in_db.id)
        db.session.add_all([service1, service2])
        db.session.commit()
        print("Servicios añadidos al perfil del piloto.")
    
    print("\n¡Base de datos poblada con éxito!")