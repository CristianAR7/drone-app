import os
import google.generativeai as genai
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import bcrypt

# --- CONFIGURACIÓN ---
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- INSERTA TU API KEY DE GOOGLE AQUÍ ---
GOOGLE_API_KEY = "TU_API_KEY_AQUI"

# ... (Configuración del modelo de IA, sin cambios)
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    model = None

# --- MODELOS DE LA BASE DE DATOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Cliente')
    pilot_profile = db.relationship('PilotProfile', backref='user', uselist=False, cascade="all, delete-orphan")

class PilotProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tagline = db.Column(db.String(200))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "location": self.location,
            "bio": self.bio,
            "profilePictureUrl": f"https://picsum.photos/seed/{self.id}/300/300",
            "hourlyRate": 150, "eventPackages": [], "specialties": ["Bodas", "Inmobiliaria"],
            "rating": 4.5, "reviewsCount": 10
        }

# --- RUTAS DE LA API ---

@app.route("/api/pilots")
def get_pilots():
    profiles = PilotProfile.query.all()
    return jsonify([p.to_dict() for p in profiles])

@app.route("/api/register", methods=['POST'])
def register():
    # ... (sin cambios)
    data = request.get_json()
    email, password, role = data.get('email'), data.get('password'), data.get('role', 'Cliente')
    if not email or not password: return jsonify({"error": "Faltan datos"}), 400
    if User.query.filter_by(email=email).first(): return jsonify({"error": "Email ya registrado"}), 409
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.session.add(User(email=email, password=hashed, role=role))
    db.session.commit()
    return jsonify({"message": "Usuario creado con éxito"}), 201

@app.route("/api/login", methods=['POST'])
def login():
    # ... (sin cambios)
    data = request.get_json()
    email, password = data.get('email'), data.get('password')
    if not email or not password: return jsonify({"error": "Faltan datos"}), 400
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"message": "Inicio de sesión exitoso", "user": {"email": user.email, "role": user.role}}), 200
    return jsonify({"error": "Credenciales inválidas"}), 401

# ¡NUEVA RUTA! Para crear y actualizar el perfil de un piloto
@app.route("/api/profile", methods=['POST'])
def handle_profile():
    data = request.get_json()
    email = data.get('email') # Simulamos autenticación pasando el email

    if not email:
        return jsonify({"error": "Falta el email del usuario para la autenticación"}), 401

    user = User.query.filter_by(email=email).first()

    if not user or user.role != 'Piloto':
        return jsonify({"error": "Usuario no encontrado o no es un piloto"}), 403

    # Buscamos si ya tiene un perfil
    profile = user.pilot_profile

    if not profile:
        # Si no tiene perfil, lo creamos
        profile = PilotProfile(user_id=user.id)
        db.session.add(profile)
    
    # Actualizamos los datos del perfil con lo que nos llega del formulario
    profile.name = data.get('name', profile.name)
    profile.tagline = data.get('tagline', profile.tagline)
    profile.location = data.get('location', profile.location)
    profile.bio = data.get('bio', profile.bio)
    
    db.session.commit()
    
    return jsonify({"message": "Perfil guardado con éxito", "profile": profile.to_dict()})


# --- INICIO DEL SERVIDOR ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)