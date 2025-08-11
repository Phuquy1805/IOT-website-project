import os
import json
from flask_cors import CORS
from flask_mqtt import Mqtt
from datetime import timedelta, datetime
import secrets
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, func, CheckConstraint, ForeignKey, Index
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from flask import Flask, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies, set_access_cookies

from utils.email import send_registration_email
from utils.topic import topic

load_dotenv()
app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": os.getenv('FRONT_END_URL')}}, supports_credentials=True)

BACK_END_PORT = int(os.getenv('BACK_END_PORT', '8000'))

app.config['BACK_END_PORT'] = BACK_END_PORT

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///mydb.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_ACCESS_COOKIE_PATH'] = '/api/'
app.config['JWT_COOKIE_SECURE'] = False        # True if HTTPS
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
ttl_seconds = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=ttl_seconds)

app.config['MQTT_BROKER_URL'] = os.getenv('MQTT_BROKER_URL')
app.config['MQTT_BROKER_PORT'] = int(os.getenv('MQTT_BROKER_PORT', 1883))
app.config['MQTT_KEEPALIVE'] = 60


MQTT_TOPIC_CAPTURE              = topic("camera-captures")
MQTT_TOPIC_FINGERPRINT_LOG      = topic("fingerprint", "log")
MQTT_TOPIC_SERVO_LOG            = topic("servo", "log")
MQTT_TOPIC_LCD_LOG              = topic("lcd", "log")
MQTT_TOPIC_FINGERPRINT_COMMAND  = topic("fingerprint", "command")
MQTT_TOPIC_SERVO_COMMAND        = topic("servo", "command")
MQTT_TOPIC_LCD_COMMAND          = topic("lcd", "command")


# Initialize extensions
db  = SQLAlchemy(app)
jwt = JWTManager(app)
mqtt = Mqtt(app)

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

# Define Capture model to store captured images
class Capture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.Integer, nullable=False, index=True)
    url = db.Column(db.String(2048), unique=True, nullable=False)
    thumb_url = db.Column(db.String(2048), unique=True)
    description = db.Column(db.String(255))
    
    def to_dict(self) -> dict:
        return {"id": self.id, "timestamp": self.timestamp, "url": self.url, "thumb_url": self.thumb_url , "description": self.description}
    
    @classmethod
    def get_last_capture(cls) -> "Capture | None":
        stmt = select(cls).order_by(cls.timestamp.desc()).limit(1)
        return db.session.execute(stmt).scalar_one_or_none()
    
    @classmethod
    def get_captures(cls, start_timestamp: int, end_timestamp: int) -> list["Capture"]:
        if start_timestamp is None or end_timestamp is None:
            raise ValueError("start_timestamp and end_timestamp are required")
        if end_timestamp < start_timestamp:
            raise ValueError("end_timestamp must be >= start_timestamp")

        stmt = select(cls).where(cls.timestamp >= start_timestamp, cls.timestamp <= end_timestamp).order_by(cls.timestamp.asc(), cls.id.asc())
        return list(db.session.execute(stmt).scalars().all())


class OTPRequest(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String, index=True, nullable=False)
    otp_code   = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)

    @classmethod
    def create(cls, email, db):
        code = f"{secrets.randbelow(10**6):06d}"
        expires = datetime.now() + timedelta(minutes=10)
        otp = cls(email=email, otp_code=code, expires_at=expires)
        db.session.add(otp)
        db.session.commit()
        return code

class Command(db.Model):
    
    id            = db.Column(db.Integer, primary_key=True)
    created_at    = db.Column(db.BigInteger, nullable=False, index=True)        # epoch seconds UTC
    user_id       = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)
    command_type  = db.Column(db.String(32), nullable=False)                    # 'servo.open' | 'servo.close' | 'lcd.set'
    topic         = db.Column(db.String(255), nullable=True)                    # e.g. '/MQTT_PREFIX/door'
    payload       = db.Column(db.Text, nullable=True)                           # e.g. 'OPEN' or LCD text
    status        = db.Column(db.String(16), nullable=False, default='sent')    # 'sent'|'error'
    note          = db.Column(db.Text, nullable=True)                           # error detail, optional

    user          = relationship("User", lazy="joined")

    __table_args__ = (
        CheckConstraint("status IN ('sent','error','pending')", name="ck_command_status"),
        Index("ix_command_user_created", "user_id", "created_at"),
        Index("ix_command_type_created", "command_type", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "command_type": self.command_type,
            "topic": self.topic,
            "payload": self.payload,
            "status": self.status,
            "note": self.note,
        }

class Log(db.Model):

    id               = db.Column(db.Integer, primary_key=True)
    created_at       = db.Column(db.BigInteger, nullable=False, index=True)
    log_type         = db.Column(db.String(32), nullable=False)
    description      = db.Column(db.Text, nullable=True)
    payload          = db.Column(db.Text, nullable=True)
    topic            = db.Column(db.String(255), nullable=True)
    command_id       = db.Column(db.Integer, ForeignKey('command.id', ondelete="SET NULL"), nullable=True)
    related_log_id   = db.Column(db.Integer, ForeignKey('log.id',     ondelete="SET NULL"), nullable=True)

    command          = relationship("Command", lazy="joined")
    related_log      = relationship("Log", remote_side=[id], lazy="joined")

    __table_args__ = (
        # at most one parent: command OR log (both NULL allowed)
        CheckConstraint("(command_id IS NULL) OR (related_log_id IS NULL)", name="ck_log_at_most_one_parent"),
        Index("ix_log_type_created", "log_type", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at,
            "log_type": self.log_type,
            "description": self.description,
            "payload": self.payload,
            "topic": self.topic,
            "command_id": self.command_id,
            "related_log_id": self.related_log_id,
        }

# Create tables on startup
def init_db():
    with app.app_context():
        # db.drop_all()  # REMEMBER TO DELETE THIS
        db.create_all()

# Fired on successful connect
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe(MQTT_TOPIC_CAPTURE)
    mqtt.subscribe(MQTT_TOPIC_FINGERPRINT_LOG)
    mqtt.subscribe(MQTT_TOPIC_SERVO_LOG)
    mqtt.subscribe(MQTT_TOPIC_LCD_LOG)


@mqtt.on_topic(MQTT_TOPIC_CAPTURE)
def handle_capture_topic(client, userdata, message):
    try:
        obj = json.loads(message.payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        app.logger.warning(f"Invalid JSON on {MQTT_TOPIC_CAPTURE}: %s", e)
        return

    if "timestamp" not in obj or "url" not in obj:
        app.logger.warning("Missing required keys (timestamp, url): %r", obj)
        return

    try:
        ts  = int(obj["timestamp"])
        url = str(obj["url"])
        thumb_url = str(obj["thumb_url"])
        desc = obj.get("description")
    except (TypeError, ValueError) as e:
        app.logger.warning("Bad field types: %s | payload=%r", e, obj)
        return

    with app.app_context():
        cap = Capture(timestamp=ts, url=url, thumb_url=thumb_url, description=desc)
        db.session.add(cap)
        try:
            db.session.commit()
            app.logger.info("Stored capture id=%s url=%s", cap.id, cap.url)
        except IntegrityError:
            db.session.rollback()
            app.logger.info("Duplicate capture (url) ignored: %s", url)
        except Exception as e:
            db.session.rollback()
            app.logger.exception("DB insert failed: %s", e)

@mqtt.on_topic(MQTT_TOPIC_SERVO_LOG)
def handle_servo_log(client, userdata, message):
    try:
        obj = json.loads(message.payload.decode())
    except json.JSONDecodeError:
        app.logger.warning("Bad JSON on servo/log")
        return

    if "created_at" not in obj or "log_type" not in obj:
        app.logger.warning("Missing keys in servo/log: %r", obj)
        return

    cmd_id  = obj.get("command_id")
    rel_id  = obj.get("related_log_id")

    if cmd_id and rel_id:
        app.logger.warning(
            "servo/log violates parent rule: BOTH command_id=%s AND related_log_id=%s",
            cmd_id, rel_id
        )
        return

    with app.app_context():
        log = Log(
            created_at     = int(obj["created_at"]),
            log_type       = obj.get("log_type"),
            description    = obj.get("description"),
            payload        = obj.get("payload"),
            topic          = obj.get("topic"),
            command_id     = cmd_id,
            related_log_id = rel_id,
        )
        db.session.add(log)
        try:
            db.session.commit()
            app.logger.info("Stored servo log id=%s", log.id)
        except Exception as e:
            db.session.rollback()
            app.logger.exception("DB insert failed: %s", e)

# HANDLER CHO FINGERPRINT LOG 
@mqtt.on_topic(MQTT_TOPIC_FINGERPRINT_LOG)
def handle_fingerprint_log(client, userdata, message):
    try:
        obj = json.loads(message.payload.decode("utf-8"))
    except json.JSONDecodeError:
        app.logger.warning("Bad JSON on fingerprint/log")
        return

    if "created_at" not in obj or "log_type" not in obj:
        app.logger.warning("Missing keys in fingerprint/log: %r", obj)
        return

    cmd_id = obj.get("command_id")

    with app.app_context():
        log = Log(
            created_at     = int(obj["created_at"]),
            log_type       = obj.get("log_type"),
            description    = obj.get("description"),
            payload        = obj.get("payload"),
            topic          = MQTT_TOPIC_FINGERPRINT_LOG,
            command_id     = cmd_id,
        )
        db.session.add(log)
        try:
            db.session.commit()
            app.logger.info("Stored fingerprint log id=%s", log.id)
        except Exception as e:
            db.session.rollback()
            app.logger.exception("DB insert failed for fingerprint log: %s", e)


@mqtt.on_topic(MQTT_TOPIC_FINGERPRINT_LOG)
def handle_fingerprint_log(client, userdata, message):
    try:
        obj = json.loads(message.payload.decode("utf-8"))
    except json.JSONDecodeError:
        app.logger.warning("Bad JSON on fingerprint/log")
        return

    if "created_at" not in obj or "log_type" not in obj:
        app.logger.warning("Missing keys in fingerprint/log: %r", obj)
        return

    cmd_id = obj.get("command_id")

    with app.app_context():
        log = Log(
            created_at     = int(obj["created_at"]),
            log_type       = obj.get("log_type"),
            description    = obj.get("description"),
            payload        = obj.get("payload"),
            topic          = MQTT_TOPIC_FINGERPRINT_LOG,
            command_id     = cmd_id,
        )
        db.session.add(log)
        try:
            db.session.commit()
            app.logger.info("Stored fingerprint log id=%s", log.id)
        except Exception as e:
            db.session.rollback()
            app.logger.exception("DB insert failed for fingerprint log: %s", e)

# POST /api/servo
@app.route('/api/servo', methods=['POST'])
@jwt_required()
def servo_command():
    # 0) caller identity ----------------------------------------------------
    try:
        uid = int(get_jwt_identity() or -1)
    except ValueError:
        return jsonify(error='Invalid token identity'), 422

    # 1) request body -------------------------------------------------------
    data   = request.get_json() or {}
    action = (data.get('action') or '').lower()
    if action not in ('open', 'close'):
        return jsonify(error="action must be 'open' or 'close'"), 400

    created_at   = int(datetime.utcnow().timestamp())
    command_type = f"servo.{action}"

    # 2) create row first, flush to get ID ----------------------------------
    cmd = Command(
        created_at   = created_at,
        user_id      = uid,
        command_type = command_type,
        topic        = MQTT_TOPIC_SERVO_COMMAND,
        status       = 'pending'          # temporary
    )
    db.session.add(cmd)
    db.session.flush()                    # allocates cmd.id without commit

    # 3) build payload & publish -------------------------------------------
    payload = json.dumps({"cmd_id": cmd.id, "action": action})
    published_ok = mqtt.publish(MQTT_TOPIC_SERVO_COMMAND, payload, qos=0)

    # 4) finalise row -------------------------------------------------------
    cmd.payload = payload
    cmd.status  = 'sent' if published_ok else 'error'
    cmd.note    = None   if published_ok else 'mqtt.publish() returned False'
    db.session.commit()

    return (
        jsonify(
            id      = cmd.id,
            status  = cmd.status,
            topic   = cmd.topic,
            payload = cmd.payload
        ),
        200 if published_ok else 500
    )


@app.route('/api/fingerprint/register', methods=['POST'])
@jwt_required()
def fingerprint_register_command():
    # 0) caller identity ----------------------------------------------------
    try:
        uid = int(get_jwt_identity() or -1)
    except ValueError:
        return jsonify(error='Invalid token identity'), 422

    created_at   = int(datetime.now().timestamp())
    command_type = "fingerprint.enroll"

    # 2) create row first, flush to get ID ----------------------------------
    cmd = Command(
        created_at   = created_at,
        user_id      = uid,
        command_type = command_type,
        topic        = MQTT_TOPIC_FINGERPRINT_COMMAND,
        status       = 'pending'
    )
    db.session.add(cmd)
    db.session.flush()

    # 3) build payload & publish -------------------------------------------
    payload = json.dumps({"cmd_id": cmd.id, "action": "enroll"})
    published_ok = mqtt.publish(MQTT_TOPIC_FINGERPRINT_COMMAND, payload, qos=1) # Dùng qos=1 để đảm bảo lệnh đến

    # 4) finalise row -------------------------------------------------------
    cmd.payload = payload
    cmd.status  = 'sent' if published_ok else 'error'
    cmd.note    = None   if published_ok else 'mqtt.publish() returned False'
    db.session.commit()

    return (
        jsonify(
            id      = cmd.id,
            status  = cmd.status,
            topic   = cmd.topic,
            payload = cmd.payload
        ),
        200 if published_ok else 500
    )



# Authentication routes
@app.route('/api/register/send-otp', methods=['POST'])
def register_send_otp():
    data = request.get_json() or {}
    form_username = data.get('username')
    form_email = data.get('email')
    form_password = data.get('password')
    if not all([form_username, form_email, form_password]):
        return jsonify(error='Missing fields'), 400
    if User.query.filter((User.username == form_username) | (User.email == form_email)).first():
        return jsonify(error='User exists'), 409
    code = OTPRequest.create(form_email, db)
    send_registration_email(form_email, form_username ,code)
    return jsonify(message='OTP sent'), 200


@app.route('/api/register/verify', methods=['POST'])
def register_verify():
    data = request.get_json() or {}
    form_username = data.get('username')
    form_email = data.get('email')
    form_password = data.get('password')
    form_otp = data.get('otp')
    if not all([form_username, form_email, form_password, form_otp]):
        return jsonify(error='Missing fields'), 400 
    if User.query.filter((User.username == form_username) | (User.email == form_email)).first():
        return jsonify(error='User exists'), 409
    
    otp = OTPRequest.query.filter_by(
        email=form_email, otp_code=form_otp, used=False
    ).first()
    if not otp or otp.expires_at < datetime.now():
        return jsonify(error='Invalid or expired OTP'), 401

    # mark this one used & create the user
    otp.used = True
    user = User(username=form_username, email=form_email)
    user.set_password(form_password)
    db.session.add(user)

    # --- CLEANUP: remove other expired or already-used OTPs for this email ---
    OTPRequest.query.filter(
        OTPRequest.email == form_email,
        (OTPRequest.used == True) | (OTPRequest.expires_at < datetime.now())
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify(message='Registration complete'), 201


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

@app.route('/api/captures/latest', methods=['GET'])
def latest_capture():
    cap = Capture.get_last_capture()
    if not cap:
        return jsonify(error="No capture available"), 404
    resp = jsonify(cap.to_dict())
    resp.headers['Cache-Control'] = 'no-store'
    return resp, 200

@app.route('/api/captures', methods=['GET'])
def list_captures():
    start = request.args.get('start', type=int)
    end   = request.args.get('end',   type=int)
    if start is None or end is None:
        return jsonify(error="start and end are required"), 400
    if end < start:
        return jsonify(error="end must be >= start"), 400

    limit  = request.args.get('limit',  default=30, type=int)
    offset = request.args.get('offset', default=0,  type=int)
    limit  = max(1, min(limit, 100))
    offset = max(0, offset)
    order  = request.args.get('order', 'desc').lower()  # 'asc' | 'desc'

    base = select(Capture).where(
        Capture.timestamp >= start, Capture.timestamp <= end
    )
    if order == 'asc':
        base = base.order_by(Capture.timestamp.asc(), Capture.id.asc())
    else:
        base = base.order_by(Capture.timestamp.desc(), Capture.id.desc())

    total = db.session.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    page = db.session.execute(base.offset(offset).limit(limit)).scalars().all()
    items = [c.to_dict() for c in page]
    return jsonify({
        "items": items, "total": total,
        "start": start, "end": end, "limit": limit, "offset": offset
    }), 200

#  ENDPOINT ĐỂ BẮT ĐẦU ĐĂNG KÍ VÂN TAY   
@app.route('/api/fingerprint/register', methods=['POST'])
@jwt_required()
def fingerprint_register_command():
    # 0) caller identity ----------------------------------------------------
    try:
        uid = int(get_jwt_identity() or -1)
    except ValueError:
        return jsonify(error='Invalid token identity'), 422

    created_at   = int(datetime.utcnow().timestamp())
    command_type = "fingerprint.enroll"

    # 2) create row first, flush to get ID ----------------------------------
    cmd = Command(
        created_at   = created_at,
        user_id      = uid,
        command_type = command_type,
        topic        = MQTT_TOPIC_FINGERPRINT_COMMAND,
        status       = 'pending'
    )
    db.session.add(cmd)
    db.session.flush()

    # 3) build payload & publish -------------------------------------------
    payload = json.dumps({"cmd_id": cmd.id, "action": "enroll"})
    published_ok = mqtt.publish(MQTT_TOPIC_FINGERPRINT_COMMAND, payload, qos=1) # Dùng qos=1 để đảm bảo lệnh đến

    # 4) finalise row -------------------------------------------------------
    cmd.payload = payload
    cmd.status  = 'sent' if published_ok else 'error'
    cmd.note    = None   if published_ok else 'mqtt.publish() returned False'
    db.session.commit()

    return (
        jsonify(
            id      = cmd.id,
            status  = cmd.status,
            topic   = cmd.topic,
            payload = cmd.payload
        ),
        200 if published_ok else 500
    )

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=BACK_END_PORT, debug=True)