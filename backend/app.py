import os
from flask_cors import CORS
from datetime import timedelta
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies, set_access_cookies

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv('FRONT_END_URL')}}, supports_credentials=True)

BACK_END_PORT = int(os.getenv('BACK_END_PORT', '8000'))

app.config['BACK_END_PORT'] = BACK_END_PORT

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///mydb.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['JWT_TOKEN_LOCATION']       = ['cookies']
app.config['JWT_ACCESS_COOKIE_PATH']   = '/api/'      # send access cookie on all /api/* calls
app.config['JWT_COOKIE_SECURE']        = False         # True if you’re running HTTPS in prod
app.config['JWT_COOKIE_SAMESITE']      = 'Lax'         # or 'Strict'
app.config['JWT_COOKIE_CSRF_PROTECT']  = False         # set True + handle CSRF tokens if you like
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
ttl_seconds = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=ttl_seconds)

# Initialize extensions
db  = SQLAlchemy(app)
jwt = JWTManager(app)

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

# Create tables on startup
def init_db():
    with app.app_context():
        db.drop_all()  # Optional: drop all tables first
        db.create_all()

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    u = data.get('username')
    e = data.get('email')
    p = data.get('password')
    if not all([u, e, p]):
        return jsonify(error='Missing fields'), 400
    if User.query.filter((User.username == u) | (User.email == e)).first():
        return jsonify(error='User exists'), 409
    user = User(username=u, email=e)
    user.set_password(p)
    db.session.add(user)
    db.session.commit()
    return jsonify(message='Registered'), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    e = data.get('email')
    p = data.get('password')
    if not all([e, p]):
        return jsonify(error='Missing fields'), 400
    user = User.query.filter_by(email=e).first()
    if user and user.check_password(p):
        token = create_access_token(identity=str(user.id))
        resp = jsonify(message='Login successful')
        set_access_cookies(resp, token)
        return resp, 200
    return jsonify(error='Invalid credentials'), 401

@app.route('/api/authorize', methods=['GET'])
@jwt_required()
def authorize():
    user_id = get_jwt_identity()
    if user_id is None:
        return jsonify(error="Invalid token identity"), 422
    # Discorage caching of this response
    resp = make_response(jsonify(authorized=True, user_id=user_id), 200)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    resp.headers['Pragma']        = 'no-cache'
    resp.headers.pop('ETag', None)
    return resp

@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    resp = make_response(jsonify(message='Logged out'), 200)
    unset_jwt_cookies(resp)
    return resp

@app.route('/api/change-password', methods=['POST'])
@jwt_required()
def change_password():
    uid_str = get_jwt_identity()
    try:
        uid = int(uid_str)
    except ValueError:
        return jsonify(error='Invalid token identity'), 422
    data = request.get_json() or {}
    old = data.get('old_password')
    new = data.get('new_password')
    if not all([old, new]):
        return jsonify(error='Missing fields'), 400
    user = db.session.get(User, uid)
    if not user or not user.check_password(old):
        return jsonify(error='Old password incorrect'), 401
    user.set_password(new)
    db.session.commit()
    return jsonify(message='Password changed'), 200

@app.route('/api/profile', methods=['GET'])
@jwt_required()
def profile():
    uid_str = get_jwt_identity()
    try:
        uid = int(uid_str)
    except ValueError:
        return jsonify(error='Invalid token identity'), 422
    u = db.session.get(User, uid)
    if not u:
        return jsonify(error='User not found'), 404
    return jsonify(id=u.id, username=u.username, email=u.email), 200



if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=BACK_END_PORT, debug=True)