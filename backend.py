import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import bcrypt

# --- CONFIGURACIÓN ---
app = Flask(__name__)
CORS(app)

# ¡MODIFICADO! Ahora se conecta a la base de datos externa desde una variable de entorno
# La URL la pondremos en Render, no aquí.
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada!")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
        return {
            "id": self.id, "name": self.name, "user_id": self.user_id,
            "profilePictureUrl": f"https://picsum.photos/seed/{self.id}/300/300"
        }

# --- CÓDIGO DE INICIALIZACIÓN DE LA BASE DE DATOS ---
with app.app_context():
    db.create_all() # Esto creará las tablas en Supabase si no existen

# --- RUTAS DE LA API ---
@app.route("/api/pilots")
def get_pilots():
    try:
        profiles = PilotProfile.query.all()
        return jsonify([p.to_dict() for p in profiles])
    except Exception as e:
        return jsonify({"error": f"Error de base de datos: {str(e)}"}), 500

@app.route("/api/register", methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'Cliente')

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
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        return jsonify({"message": "Inicio de sesión exitoso", "user": {"username": user.username, "role": user.role}}), 200
    return jsonify({"error": "Credenciales inválidas"}), 401