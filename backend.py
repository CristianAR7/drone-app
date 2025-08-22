import os
import google.generativeai as genai
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from datetime import datetime, date
from werkzeug.utils import secure_filename

# --- CONFIGURACIÓN ---
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(app.instance_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- INSERTA TU API KEY DE GOOGLE AQUÍ ---
GOOGLE_API_KEY = "AIzaSyCjST_lyf9SH2bU6PLhUVlx0bf3XwDRSJk"
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    model = None

# --- MODELOS DE LA BASE DE DATOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Cliente')
    pilot_profile = db.relationship('PilotProfile', backref='user', uselist=False, cascade="all, delete-orphan")

class PilotProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="Nuevo Piloto")
    tagline = db.Column(db.String(200))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    def to_dict(self):
        return { "id": self.id, "name": self.name, "tagline": self.tagline, "location": self.location, "bio": self.bio, "user_id": self.user_id, "profilePictureUrl": f"https://picsum.photos/seed/{self.id}/300/300" }

# --- CÓDIGO DE INICIALIZACIÓN DE LA BD ---
try:
    with app.app_context():
        db.create_all()
        from setup_db import seed_database
        seed_database()
except Exception as e:
    print(f"Ocurrió un error durante la inicialización de la base de datos: {e}")

# --- RUTAS DE LA API ---
@app.route("/api/pilots")
def get_pilots():
    profiles = PilotProfile.query.all()
    return jsonify([p.to_dict() for p in profiles])

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

@app.route("/api/register", methods=['POST'])
def register():
    data = request.get_json()
    username, email, password, password_confirm, role = data.get('username'), data.get('email'), data.get('password'), data.get('password_confirm'), data.get('role', 'Cliente')
    if not all([username, email, password, password_confirm]): return jsonify({"error": "Todos los campos son requeridos"}), 400
    if password != password_confirm: return jsonify({"error": "Las contraseñas no coinciden"}), 400
    if User.query.filter_by(username=username).first(): return jsonify({"error": "El nombre de usuario ya existe"}), 409
    if User.query.filter_by(email=email).first(): return jsonify({"error": "El email ya está registrado"}), 409
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(username=username, email=email, password=hashed, role=role)
    db.session.add(new_user)
    db.session.commit()
    if new_user.role == 'Piloto':
        profile = PilotProfile(name=new_user.username, user_id=new_user.id)
        db.session.add(profile)
        db.session.commit()
    return jsonify({"message": "Usuario creado con éxito"}), 201

# --- INICIO DEL SERVIDOR (Solo para pruebas locales) ---
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)