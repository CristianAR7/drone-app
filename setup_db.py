from backend import app, db, User, PilotProfile, ServicePackage
import bcrypt

def seed_database():
    with app.app_context():
        if User.query.count() > 0:
            print("Base de datos ya contiene datos. Proceso de sembrado omitido.")
            return

        print("Base de datos vacía. Poblando con datos de prueba...")
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
            bio='Más de 10 años de experiencia en filmaciones.'
        )
        pilot_user.pilot_profile = profile
        
        db.session.add(client_user)
        db.session.add(pilot_user)
        db.session.commit()
        print("Usuarios y perfil guardados.")

        profile_in_db = PilotProfile.query.first()
        if profile_in_db:
            service1 = ServicePackage(name="Paquete Boda Básico", description="4 horas de cobertura", price=800, pilot_profile_id=profile_in_db.id)
            db.session.add(service1)
            db.session.commit()
            print("Servicios añadidos al perfil del piloto.")
    
        print("\n¡Base de datos poblada con éxito!")