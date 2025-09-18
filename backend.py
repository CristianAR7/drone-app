import os
import google.generativeai as genai
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from datetime import datetime

# --- CONFIGURACIÓN ---
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(app.instance_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- INSERTA TU API KEY DE GOOGLE AQUÍ ---
# Asegúrate de tener esta variable de entorno en Render
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Error configurando el modelo de IA: {e}")
        model = None
else:
    print("Advertencia: GOOGLE_API_KEY no encontrada. La búsqueda con IA estará desactivada.")
    model = None

# --- MODELOS DE LA BASE DE DATOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Cliente')
    pilot_profile = db.relationship('PilotProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    bookings_made = db.relationship('Booking', foreign_keys='Booking.client_id', backref='client', lazy=True)

class PilotProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="Nuevo Piloto")
    tagline = db.Column(db.String(200))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    bookings_received = db.relationship('Booking', foreign_keys='Booking.pilot_profile_id', backref='pilot', lazy=True)
    services = db.relationship('ServicePackage', backref='profile', lazy=True, cascade="all, delete-orphan")
    portfolio_items = db.relationship('PortfolioItem', backref='profile', lazy=True, cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "tagline": self.tagline, "location": self.location, "bio": self.bio,
            "user_id": self.user_id,
            "profilePictureUrl": f"https://picsum.photos/seed/{self.id}/300/300",
            "eventPackages": [s.to_dict() for s in self.services],
            "portfolio": [item.to_dict() for item in self.portfolio_items]
        }

class ServicePackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    pilot_profile_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description, "price": self.price}

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_description = db.Column(db.Text, nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pilot_profile_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    def to_dict(self):
        client_user = User.query.get(self.client_id)
        pilot_profile = PilotProfile.query.get(self.pilot_profile_id)
        return {"id": self.id, "job_description": self.job_description, "status": self.status, 
                "client_username": client_user.username, "pilot_name": pilot_profile.name}

class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_url = db.Column(db.String(200), nullable=False)
    item_type = db.Column(db.String(20), nullable=False, default='image')
    pilot_profile_id = db.Column(db.Integer, db.ForeignKey('pilot_profile.id'), nullable=False)
    def to_dict(self):
        return {"id": self.id, "url": self.file_url, "type": self.item_type}

# --- CÓDIGO DE INICIALIZACIÓN DE LA BD ---
with app.app_context():
    db.create_all()
    try:
        from setup_db import seed_database
        seed_database()
    except Exception as e:
        print(f"Omitiendo sembrado o error en setup_db: {e}")

# --- RUTAS DE LA API ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(app.instance_path, 'static', 'uploads'), filename)

@app.route("/api/pilots")
def get_pilots():
    profiles = PilotProfile.query.all()
    return jsonify([p.to_dict() for p in profiles])

@app.route("/api/pilots/<int:profile_id>")
def get_pilot_details(profile_id):
    profile = PilotProfile.query.get(profile_id)
    if not profile: return jsonify({"error": "Perfil no encontrado"}), 404
    return jsonify(profile.to_dict())

@app.route("/api/register", methods=['POST'])
def register():
    data = request.get_json()
    username, email, password, password_confirm, role = data.get('username'), data.get('email'), data.get('password'), data.get('password_confirm'), data.get('role', 'Cliente')
    if not all([username, email, password, password_confirm]): return jsonify({"error": "Todos los campos son requeridos"}), 400
    if password != password_confirm: return jsonify({"error": "Las contraseñas no coinciden"}), 400
    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({"error": "Usuario o email ya existen"}), 409
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username=username, email=email, password=hashed, role=role)
    db.session.add(new_user)
    db.session.commit()
    if new_user.role == 'Piloto':
        profile = PilotProfile(name=new_user.username, user_id=new_user.id)
        db.session.add(profile)
        db.session.commit()
    return jsonify({"message": "Usuario creado con éxito"}), 201
    
@app.route("/api/login", methods=['POST'])
def login():
    data = request.get_json()
    email, password = data.get('email'), data.get('password')
    if not email or not password: return jsonify({"error": "Email y contraseña son requeridos"}), 400
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        pilot_profile_id = user.pilot_profile.id if user.pilot_profile else None
        return jsonify({"message": "Inicio de sesión exitoso", "user": {"id": user.id, "email": user.email, "role": user.role, "username": user.username, "pilot_profile_id": pilot_profile_id}}), 200
    return jsonify({"error": "Credenciales inválidas"}), 401

@app.route("/api/profile", methods=['POST'])
def handle_profile():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if not user or user.role != 'Piloto': return jsonify({"error": "Usuario no es piloto"}), 403
    profile = user.pilot_profile
    profile.name = data.get('name', profile.name)
    profile.tagline = data.get('tagline', profile.tagline)
    profile.location = data.get('location', profile.location)
    profile.bio = data.get('bio', profile.bio)
    db.session.commit()
    return jsonify({"message": "Perfil guardado"})

@app.route('/api/profile/services', methods=['POST'])
def add_service():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if not user or user.role != 'Piloto' or not user.pilot_profile: return jsonify({"error": "Piloto no autorizado"}), 403
    new_service = ServicePackage(name=data.get('name'), description=data.get('description'), price=data.get('price'), pilot_profile_id=user.pilot_profile.id)
    db.session.add(new_service)
    db.session.commit()
    return jsonify({"message": "Servicio añadido"})

@app.route('/api/profile/portfolio', methods=['POST'])
def add_portfolio_item():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if not user or user.role != 'Piloto' or not user.pilot_profile: return jsonify({"error": "Piloto no autorizado"}), 403
    if 'file' not in request.files: return jsonify({"error": "No se ha enviado ningún archivo"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "Ningún archivo seleccionado"}), 400
    if file:
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        public_url = f"/uploads/{filename}"
        new_item = PortfolioItem(file_url=public_url, item_type='image', pilot_profile_id=user.pilot_profile.id)
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"message": "Archivo subido con éxito"})
        
@app.route("/api/book", methods=['POST'])
def create_booking():
    data = request.get_json()
    client = User.query.filter_by(email=data.get('client_email')).first()
    pilot = PilotProfile.query.get(data.get('pilot_id'))
    if not client or not pilot: return jsonify({"error": "Cliente o piloto no encontrado"}), 404
    new_booking = Booking(client_id=client.id, pilot_profile_id=pilot.id, job_description=data.get('job_description'))
    db.session.add(new_booking)
    db.session.commit()
    return jsonify({"message": "Solicitud de reserva enviada"})

@app.route("/api/bookings", methods=['GET'])
def get_bookings():
    user = User.query.filter_by(email=request.args.get('email')).first()
    if not user: return jsonify({"error": "Usuario no encontrado"}), 404
    bookings_list = []
    if user.role == 'Cliente':
        bookings = user.bookings_made
    elif user.role == 'Piloto' and user.pilot_profile:
        bookings = user.pilot_profile.bookings_received
    else:
        bookings = []
    return jsonify([b.to_dict() for b in bookings])

@app.route("/api/bookings/<int:booking_id>/respond", methods=['POST'])
def respond_to_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking: return jsonify({"error": "Reserva no encontrada"}), 404
    booking.status = request.json.get('status')
    db.session.commit()
    return jsonify({"message": f"Reserva {booking.status}"})

# ¡NUEVA RUTA AÑADIDA!
@app.route("/api/search", methods=['POST'])
def search_pilots():
    if not model:
        return jsonify({"error": "La función de búsqueda con IA no está configurada en el servidor."}), 500
    
    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "No se ha proporcionado ninguna consulta."}), 400

    try:
        profiles = PilotProfile.query.all()
        profiles_list = [p.to_dict() for p in profiles]
        
        prompt = f"""
        Eres un asistente experto en la plataforma "DroneConnect". Tu misión es ayudar a los usuarios a encontrar el piloto de dron perfecto.
        A continuación, te proporciono una lista de los perfiles de los pilotos disponibles en formato JSON: {profiles_list}
        ---
        Analiza la siguiente petición de un usuario y recomiéndale el mejor piloto. Justifica brevemente por qué. Responde en español.
        Petición del usuario: "{user_query}"
        """
        response = model.generate_content(prompt)
        return jsonify({"recommendation": response.text})
    except Exception as e:
        return jsonify({"error": f"Ha ocurrido un error con la IA: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)