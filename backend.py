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
GOOGLE_API_KEY = "TU_API_KEY_AQUI"
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    def to_dict(self):
        return { "id": self.id, "name": self.name, "user_id": self.user_id }

# --- CÓDIGO DE INICIALIZACIÓN DE LA BASE DE DATOS ---
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

# --- INICIO DEL SERVIDOR ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Importamos la función de nuestro script de setup y la ejecutamos.
        from setup_db import seed_database
        seed_database()
        
    app.run(debug=True, host='0.0.0.0', port=5000)