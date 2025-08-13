import os
import re
import json
import time
import secrets
import requests
import traceback
from flask_cors import CORS
from flask_mqtt import Mqtt
from datetime import timedelta, datetime
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, func, CheckConstraint, ForeignKey, Index
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from flask import Flask, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies, set_access_cookies, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from utils.email import send_registration_email, send_fingerprint_action_email
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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MQTT_TOPIC_CAPTURE              = topic("camera-captures")
MQTT_TOPIC_FINGERPRINT_LOG      = topic("fingerprint", "log")
MQTT_TOPIC_SERVO_LOG            = topic("servo", "log")
MQTT_TOPIC_LCD_LOG              = topic("lcd", "log")
MQTT_TOPIC_FINGERPRINT_COMMAND  = topic("fingerprint", "command")
MQTT_TOPIC_SERVO_COMMAND        = topic("servo", "command")
MQTT_TOPIC_LCD_COMMAND          = topic("lcd", "command")

FINGERPRINT_MAX_CAPACITY = int(os.getenv('FINGERPRINT_MAX_CAPACITY', '5'))

# Initialize extensions
db  = SQLAlchemy(app)
jwt = JWTManager(app)
mqtt = Mqtt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    fingerprints = relationship("Fingerprint", back_populates="user", cascade="all, delete-orphan")


    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

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
    
class Fingerprint(db.Model):
    __tablename__ = 'fingerprint'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True) 
    created_at = db.Column(db.BigInteger, nullable=False)

    user = relationship("User", back_populates="fingerprints")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "N/A",
            "name": self.name,
            "created_at": self.created_at
        }

class Webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.Integer, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "user_id": self.user_id, "url": self.url, "created_at": self.created_at}
    
    def notify(self, content: str, timeout: float = 6.0, **extra) -> tuple[bool, int, str]:
        
        if not content:
            content = "\u200b"
        if len(content) > 2000:
            content = content[:1990] + "…"

        payload = {"content": content}

        # đưa metadata vào embeds để tránh Invalid Form Body
        if extra:
            fields = []
            title = str(extra.get("event", "Notification"))
            for k, v in extra.items():
                if v is None:
                    continue
                fields.append({"name": str(k), "value": str(v), "inline": False})
            if fields:
                payload["embeds"] = [{"title": title, "fields": fields[:25]}]

        for attempt in (1, 2):
            try:
                r = requests.post(self.url, json=payload, timeout=(3, timeout))
                if r.status_code == 429 and attempt == 1:
                    try:
                        delay = float(r.headers.get("Retry-After", "1"))
                    except Exception:
                        delay = 1.0
                    time.sleep(min(delay, 2.0))
                    continue
                return (r.ok, r.status_code, r.text)
            except requests.exceptions.Timeout as e:
                if attempt == 1:
                    continue
                return (False, 0, f"timeout: {e}")
            except Exception as e:
                return (False, 0, str(e))
# Create tables on startup
def init_db():
    with app.app_context():
        # db.drop_all()  # REMEMBER TO DELETE THIS
        db.create_all()

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

    if "timestamp" not in obj or "url" not in obj  or "thumb_url" not in obj:
        app.logger.warning("Missing required keys (timestamp, url, thumb_url): %r", obj)
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
        
        if cmd_id:
            original_command = db.session.get(Command, cmd_id)
            if original_command:
                wh = Webhook.query.filter_by(user_id=original_command.user_id).first()
                if wh:
                    user = User.query.filter_by(id=original_command.user_id).first()
                    username = user.username if user else "Unknown"
                    tmp = "mở" if obj.get('payload') == "open" else "đóng"
                                        
                    ok, code, body = wh.notify(
                        content=f"🔔 Cửa được {tmp} bởi {username}",
                        event="servo.log",
                        log_type=obj.get("log_type"),
                        description=obj.get("description"),
                        payload=obj.get("payload"),
                        log_id=log.id,
                        command_id=cmd_id,
                    )
                    if ok:
                        app.logger.info(f"Sent webhook to {wh.url} for log #{log.id}")
                    else:
                        app.logger.error(f"Webhook failed ({code}): {body}")
            else:
                app.logger.error(f"Can not found user id for command id {original_command}")
        else:
            app.logger.error(f"No cmd_id field in log")

@mqtt.on_topic(MQTT_TOPIC_FINGERPRINT_LOG)
def handle_fingerprint_log(client, userdata, message):
    # 1) Parse JSON
    try:
        obj = json.loads(message.payload.decode("utf-8"))
    except json.JSONDecodeError:
        app.logger.warning("Bad JSON on fingerprint/log")
        return

    if "created_at" not in obj or "log_type" not in obj:
        app.logger.warning("Missing keys in fingerprint/log: %r", obj)
        return

    cmd_id   = obj.get("command_id")
    log_type = obj.get("log_type", "")

    # Normalize payload -> dict
    payload_raw = obj.get("payload")
    payload_data = {}
    if isinstance(payload_raw, dict):
        payload_data = payload_raw
    elif isinstance(payload_raw, str):
        try:
            payload_data = json.loads(payload_raw) if payload_raw else {}
        except json.JSONDecodeError:
            payload_data = {}
    # else: leave as {}

    with app.app_context():
        
        if log_type == "match.success":
            fingerprint_id = payload_data.get("id")
            if fingerprint_id is not None:
                fp = Fingerprint.query.get(int(fingerprint_id))
                if fp:
                    user = User.query.get(fp.user_id)
                    wh = Webhook.query.filter_by(user_id=fp.user_id).first()
                    if wh:
                        app.logger.info(f"Webhook retrieved for user {user.username}")
                        ok, code, body = wh.notify(
                            content=f"✅ Người dùng {user.username} quét vân tay thành công",
                            event="fingerprint.match.success",
                            fingerprint_id=fingerprint_id
                        )
                        if ok:
                            app.logger.info(f"Sent webhook (match.success) to {wh.url}")
                        else:
                            app.logger.error(f"Webhook failed ({code}): {body}")
            else:
                app.logger.warning("match.success missing fingerprint id")

        elif log_type == "match.fail":
            # Nếu fail thì gửi cho TẤT CẢ webhook, tại vì quét fail thì trong log không có cmmd_id và id vân tay 
            fingerprint_id = payload_data.get("id")

            webhooks = Webhook.query.order_by(Webhook.id.asc()).all()
            if not webhooks:
                app.logger.info("No webhooks configured; skipping match.fail notification")
            else:
                for wh in webhooks:
                    ok, code, body = wh.notify(
                        content="❌ Có người quét vân tay nhưng thất bại",
                        event="fingerprint.match.fail",
                        fingerprint_id=fingerprint_id
                    )
                    if ok:
                        app.logger.info(f"Sent webhook (match.fail) to {wh.url}")
                    else:
                        app.logger.error(f"Webhook failed ({code}) to {wh.url}: {body}")
 
        elif log_type == "enroll.success" and cmd_id:
            original_command = db.session.get(Command, cmd_id)
            user = User.query.filter_by(id=original_command.user_id).first()
            
            send_fingerprint_action_email(user.email, user.username, "enroll") # send email when user enroll a fingerprint successfully
            try:
                fingerprint_id = payload_data.get("id")
                if fingerprint_id is None:
                    raise ValueError("payload.id missing for enroll.success")
                fingerprint_id = int(fingerprint_id)

                original_command = db.session.get(Command, cmd_id)
                if original_command:
                    fp = db.session.get(Fingerprint, fingerprint_id)
                    if fp is None:
                        fp = Fingerprint(
                            id=fingerprint_id,
                            user_id=original_command.user_id,
                            name=f"Vân tay #{fingerprint_id}",
                            created_at=int(obj["created_at"]),
                        )
                        db.session.add(fp)
                    else:
                        fp.user_id    = original_command.user_id
                        fp.name       = fp.name or f"Vân tay #{fingerprint_id}"
                        fp.created_at = int(obj["created_at"])
                    db.session.commit()
                    app.logger.info(
                        "Linked fingerprint ID %s to user ID %s",
                        fingerprint_id, original_command.user_id
                    )
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Failed to create/update Fingerprint link: {e}")

        elif log_type == "delete.success" and cmd_id:
            
            original_command = db.session.get(Command, cmd_id)
            user = User.query.filter_by(id=original_command.user_id).first()
            send_fingerprint_action_email(user.email, user.username, "delete") # send email when user delete a fingerprint successfully
            try:
                original_command = db.session.get(Command, cmd_id)
                user = User.query.filter_by(id=original_command.user_id).first()
                fingerprint_id_to_delete = payload_data.get("id")
                if fingerprint_id_to_delete is None:
                    raise ValueError("payload.id missing for delete.success")
                fingerprint_id_to_delete = int(fingerprint_id_to_delete)

                Fingerprint.query.filter_by(id=fingerprint_id_to_delete).delete()
                db.session.commit()
                app.logger.info(
                    "Deleted fingerprint record ID %s from database.",
                    fingerprint_id_to_delete
                )
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Failed to delete Fingerprint record: {e}")

        # 4) Always store the log row
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

from sqlalchemy import or_, and_
import json

@app.route('/api/servo/last-open', methods=['GET'])
@jwt_required()
def api_servo_last_open():
    # Lấy một tập ứng viên mới nhất gồm:
    # - servo.status + payload == "open"  (mở bằng giao diện web)
    # - match.success                    (mở bằng vân tay)
    candidates = db.session.execute(
        select(Log)
        .where(
            or_(
                and_(Log.log_type == 'servo.status', Log.payload.in_(['open', '"open"'])),
                Log.log_type == 'match.success'
            )
        )
        .order_by(Log.created_at.desc(), Log.id.desc())
        .limit(200)
    ).scalars().all()

    for log in candidates:
        # Trường hợp mở bằng web: servo.status + payload=open
        if log.log_type == 'servo.status':
            payload_val = (str(log.payload) or '').strip('"').lower()
            if payload_val != 'open':
                continue
            if not log.command_id:
                continue

            cmd = db.session.get(Command, int(log.command_id))
            if not cmd or not cmd.user_id:
                continue

            user = cmd.user or db.session.get(User, int(cmd.user_id))
            if not user:
                continue

            return jsonify({
                "id": user.id,
                "username": user.username,
                "source": "web",
                "log_id": log.id,
                "created_at": log.created_at
            }), 200

        # Trường hợp mở bằng vân tay: match.success + payload chứa {"id": <fingerprint_id>, ...}
        elif log.log_type == 'match.success':
            fp_id = None
            raw = log.payload

            if isinstance(raw, dict):
                fp_id = raw.get('id')
            else:
                data = {}
                try:
                    data = json.loads(raw) if raw else {}
                except Exception:
                    try:
                        import ast
                        data = ast.literal_eval(raw) if raw else {}
                    except Exception:
                        data = {}
                if isinstance(data, dict):
                    fp_id = data.get('id')

            try:
                fp_id = int(fp_id) if fp_id is not None else None
            except Exception:
                fp_id = None

            if not fp_id:
                continue

            fp = db.session.get(Fingerprint, fp_id)
            if not fp or not fp.user_id:
                continue

            user = db.session.get(User, int(fp.user_id))
            if not user:
                continue

            return jsonify({
                "id": user.id,
                "username": user.username,
                "source": "fingerprint",
                "fingerprint_id": fp_id,
                "log_id": log.id,
                "created_at": log.created_at
            }), 200

    return jsonify(error="No open event found"), 404

@app.route('/api/lcd', methods=['POST'])
@jwt_required()
def lcd_command():
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    user_id = get_jwt_identity()
    cmd = Command(
        created_at=int(datetime.utcnow().timestamp()),
        user_id=user_id,
        command_type='lcd.set',
        topic=MQTT_TOPIC_LCD_COMMAND,
        payload=message,
        status='sent'
    )
    db.session.add(cmd)
    db.session.commit()

    # Publish to MQTT
    mqtt.publish(MQTT_TOPIC_LCD_COMMAND, message)
    return jsonify({"status": "ok", "message": message})

@app.route('/api/fingerprints', methods=['GET'])
@jwt_required()
def get_all_fingerprints():
    fingerprints = Fingerprint.query.order_by(Fingerprint.id).all()
    count = len(fingerprints)

    # Gói dữ liệu vào một object
    response_data = {
        "items": [fp.to_dict() for fp in fingerprints],
        "count": count,
        "capacity": FINGERPRINT_MAX_CAPACITY
    }
    return jsonify(response_data), 200

@app.route('/api/fingerprint/register', methods=['POST'])
@jwt_required()
def fingerprint_register_command():
    current_fingerprint_count = Fingerprint.query.count()
    if current_fingerprint_count >= FINGERPRINT_MAX_CAPACITY:
        return jsonify(error="Fingerprint capacity is full. Cannot add more."), 409
    
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
    published_ok = mqtt.publish(MQTT_TOPIC_FINGERPRINT_COMMAND, payload, qos=1)

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

@app.route('/api/fingerprints/<int:fingerprint_id>', methods=['DELETE'])
@jwt_required()
def fingerprint_delete_command(fingerprint_id):
    uid = int(get_jwt_identity())
    
    # Tạo command để theo dõi
    cmd = Command(
        created_at=int(datetime.utcnow().timestamp()),
        user_id=uid,
        command_type="fingerprint.delete",
        topic=MQTT_TOPIC_FINGERPRINT_COMMAND,
        status='pending'
    )
    db.session.add(cmd)
    db.session.flush()

    # Tạo payload và gửi MQTT
    payload = json.dumps({"cmd_id": cmd.id, "action": "delete", "id": fingerprint_id})
    published_ok = mqtt.publish(MQTT_TOPIC_FINGERPRINT_COMMAND, payload, qos=1)

    cmd.payload = payload
    cmd.status = 'sent' if published_ok else 'error'
    db.session.commit()

    return jsonify(message="Delete command sent."), 200 if published_ok else 500

@app.route('/api/chat', methods=['POST'])
def chat_with_gemini():
    data = request.get_json()
    user_message = data.get('message', '').lower()

    prompt_intro = (
        "Bạn là trợ lý ảo thông minh và thân thiện của trang web điều khiển cửa thông minh vân tay từ xa. "
        "Bạn sẽ trả lời các message theo yêu cầu nhưng kèm theo tính tình cảm.\n"
    )
    prompt_open_door = (
        "Nếu message của người dùng là một câu ra lệnh mở cửa chẳng hạn như: 'Mở/Đóng cửa', 'Mở/Đóng cửa đi', "
        "'Bạn hãy mở/đóng cửa đi', 'Vui lòng mở/đóng cửa', 'Vừng ơi mở cửa ra', 'Vừng ơi đóng cửa lại' thì bạn chỉ cần trả lời lại rằng "
        "'Tôi sẽ mở/đóng cửa! Vui lòng đợi trong giây lát!'\n"
    )
    prompt_lcd = (
        "Nếu message của người dùng là một câu yêu cầu hiển thị tin nhắn hay viết tin nhắn lên LCD chẳng hạn như: 'Viết tin nhắn: ...', 'Hiển thị tin nhắn: ...', "
        "'Viết: ....', 'Hiển thị: ....', thì bạn chỉ cần trả lời lại rằng "
        "'Hiển thị thành công!'\n"
    )
    prompt_capture = (
        "Nếu message của người dùng là yêu cầu lấy ảnh mới nhất: 'Lấy ảnh mới nhất ...', 'Lấy ảnh gần đây nhất ...', "
        "'Lấy ảnh ....', 'Xin ảnh ....', thì bạn chỉ cần trả lời lại rằng "
        "'Ảnh chụp nè: '\n"
    )
    prompt_last_open = (
        "Nếu message của người dùng hỏi ai mở cửa gần nhất như: 'Ai mở cửa gần nhất', "
        "'Ai mở cửa gần đây nhất', 'Người cuối cùng mở cửa', 'User cuối cùng mở cửa' "
        "thì bạn chỉ cần trả lời lại rằng 'Người mở cửa gần nhất:'.\n"
    )
    prompt_general = (
        "Nếu message người dùng không là một câu ra lệnh mở cửa thì bạn cần trả lời message đó theo điều kiện sau:\n"
        "Điều kiện 1: Câu trả lời không được format theo định dạng như Latex, Markdown,... Chỉ là text thông thường ;\n"
        "Điều kiện 2: Trả lời ngắn gọn xúc tích không quá 200 từ ;\n"
    )

    full_prompt = (
        f"{prompt_intro}{prompt_open_door}{prompt_lcd}{prompt_capture}"
        f"{prompt_last_open}{prompt_general}Câu hỏi người dùng: \"{user_message}\""
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        reply = res.json()['candidates'][0]['content']['parts'][0]['text']

        action = None
        lcd_message = None
        capture_requested = False
        last_open_requested = False

        # Nhận diện mở/đóng cửa
        if reply.lower().startswith("tôi sẽ mở cửa"):
            action = "open"
        elif reply.lower().startswith("tôi sẽ đóng cửa"):
            action = "close"

        # Nhận diện hiển thị LCD
        elif reply.lower().startswith("hiển thị"):
            match = re.search(r'["“](.+?)["”]', user_message)
            if match:
                lcd_message = match.group(1).strip()
            else:
                parts = user_message.split(':', 1)
                if len(parts) > 1:
                    lcd_message = parts[1].strip()

        # Nhận diện yêu cầu ảnh
        elif reply.lower().startswith("ảnh chụp nè"):
            capture_requested = True

        # Nhận diện yêu cầu người mở cửa gần nhất
        elif reply.lower().startswith("người mở cửa gần nhất"):
            last_open_requested = True

        # Thực thi mở/đóng cửa
        if action:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({'error': 'Missing or invalid JWT token'}), 401

            servo_url = request.host_url.rstrip('/') + '/api/servo'
            servo_resp = requests.post(
                servo_url,
                json={"action": action},
                cookies=request.cookies
            )
            if servo_resp.status_code != 200:
                return jsonify({'reply': reply, 'servo_error': servo_resp.json()}), 500

        # Thực thi hiển thị LCD
        if lcd_message:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({'error': 'Missing or invalid JWT token'}), 401

            lcd_url = request.host_url.rstrip('/') + '/api/lcd'
            lcd_resp = requests.post(
                lcd_url,
                json={"message": lcd_message},
                cookies=request.cookies
            )
            if lcd_resp.status_code != 200:
                return jsonify({'reply': reply, 'lcd_error': lcd_resp.json()}), 500

        # Thực thi lấy ảnh mới nhất
        if capture_requested:
            cap_url = request.host_url.rstrip('/') + '/api/captures/latest'
            cap_resp = requests.get(cap_url, cookies=request.cookies)
            if cap_resp.status_code == 200:
                cap_data = cap_resp.json()
                image_url = cap_data.get('url')
                if image_url:
                    return jsonify({'reply': reply, 'image_url': image_url}), 200
                else:
                    return jsonify({'reply': reply, 'error': 'No image URL in capture'}), 500
            else:
                return jsonify({'reply': reply, 'capture_error': cap_resp.json()}), 500

        # Thực thi lấy người mở cửa gần nhất
        if last_open_requested:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({'error': 'Missing or invalid JWT token'}), 401

            last_url = request.host_url.rstrip('/') + '/api/servo/last-open'
            last_resp = requests.get(last_url, cookies=request.cookies)

            if last_resp.status_code == 200:
                info = last_resp.json()

                username = info.get('username') or 'N/A'
                uid = info.get('id')
                source = info.get('source')
                fp_id = info.get('fingerprint_id')
                log_id = info.get('log_id')
                created_at = info.get('created_at')

                source_text = {'web': 'qua web', 'fingerprint': 'qua vân tay'}.get(source, None)

                when_text = None
                try:
                    # created_at là epoch seconds (UTC)
                    when_text = datetime.fromtimestamp(int(created_at)).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

                # Ghép câu tự nhiên
                parts = [f"Người mở cửa gần nhất: {username}"]
                if uid: parts.append(f"(ID {uid})")
                if source_text: parts.append(f"{'(' + source_text + ')'}")
                if fp_id: parts.append(f", vân tay #{fp_id}")
                if when_text: parts.append(f", lúc {when_text}")
                if log_id: parts.append(f", log #{log_id}")
                msg = " ".join(parts).replace(") ,", "),").strip()
                if not msg.endswith("."):
                    msg += "."

                return jsonify({'reply': msg}), 200

            elif last_resp.status_code == 404:
                return jsonify({'reply': "Chưa tìm thấy bản ghi mở cửa nào."}), 200
            else:
                try:
                    err = last_resp.json()
                except Exception:
                    err = last_resp.text
                return jsonify({
                    'reply': "Không truy xuất được thông tin người mở cửa gần nhất.",
                    'last_open_error': err
                }), 500



        return jsonify({'reply': reply})

    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/webhook', methods=['POST'])
@jwt_required()
def update_webhook():
    try:
        uid = int(get_jwt_identity() or -1)
    except ValueError:
        return jsonify(error='Invalid token identity'), 422

    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify(error='Missing webhook URL'), 400

    wh = Webhook.query.filter_by(user_id=uid).first()
    if wh:
        wh.url = url
    else:
        wh = Webhook(user_id=uid, url=url, created_at=int(datetime.utcnow().timestamp()))
        db.session.add(wh)

    db.session.commit()
    return jsonify(message='Webhook saved successfully')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=BACK_END_PORT, debug=True)