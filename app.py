import os, sqlite3, secrets, hmac
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", DATA_DIR / "uploads"))
DB_PATH = Path(os.environ.get("DB_PATH", DATA_DIR / "mi_tuchi.sqlite3"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

DEFAULT_STORY = """Nos conocimos un 19 de mayo del 2026. Fue algo repentino, un poquito imprudente y, aun así, maravilloso; como si en ese instante el mundo hubiera decidido darnos un momento solo para nosotros.

Alejandra, eres una niña espectacular, hermosa, preciosa, amigable y cortés. No creo que exista alguien igual a ti en este mundo. Te amo, te quise muchísimo desde aquel momento y hoy te sigo queriendo con todo mi corazón.

Quiero cuidarte y amarte, acompañarte y hacerte sentir especial. Incluso cuando las cosas se compliquen, deseo que recuerdes lo importante que eres para mí. No sabes cuánto te adoro ni cuánto te amo. En las mañanas, las horas, los minutos y los segundos, siempre encuentro una razón para pensar en ti.

Por eso, en este día tan especial, quiero decirte: feliz aniversario, mi tuchi. Gracias por aparecer en mi vida y convertir aquel momento inesperado en un recuerdo que guardo con muchísimo cariño. 💗"""

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        defaults = {
            "partner_name": os.environ.get("PARTNER_NAME", "Alejandra"),
            "owner_name": os.environ.get("OWNER_NAME", "mi renegón"),
            "story": os.environ.get("INITIAL_STORY", DEFAULT_STORY),
            "love_note": "Feliz aniversario, mi tuchi. Eres mi lugar bonito. 💗"
        }
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, value))

def get_setting(key, default=""):
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(key, value):
    with db() as conn:
        conn.execute("""INSERT INTO settings(key,value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (key, value))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def current_role():
    return session.get("role")

def login_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if current_role() != role:
                return redirect(url_for("login", role=role))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    return response

@app.route("/")
def index():
    if current_role() == "admin":
        return redirect(url_for("admin"))
    if current_role() == "partner":
        return redirect(url_for("love"))
    return render_template("landing.html", partner=get_setting("partner_name", "Alejandra"))

@app.route("/login/<role>", methods=["GET", "POST"])
def login(role):
    if role not in {"admin", "partner"}:
        abort(404)
    if request.method == "POST":
        password = request.form.get("password", "")
        env_name = "ADMIN_PASSWORD" if role == "admin" else "PARTNER_PASSWORD"
        expected = os.environ.get(env_name, "")
        if not expected:
            flash("El acceso aún no está configurado en el servidor. Revisa las variables de entorno.", "error")
        elif hmac.compare_digest(password.encode(), expected.encode()):
            session.clear()
            session["role"] = role
            session.permanent = True
            return redirect(url_for("admin" if role == "admin" else "love"))
        else:
            flash("La contraseña no coincide. Inténtalo de nuevo 💗", "error")
    return render_template("login.html", role=role, partner=get_setting("partner_name", "Alejandra"))

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/love")
@login_required("partner")
def love():
    with db() as conn:
        photos = conn.execute("SELECT * FROM photos ORDER BY id DESC").fetchall()
    return render_template("love.html", partner=get_setting("partner_name", "Alejandra"),
        owner=get_setting("owner_name", "mi renegón"), story=get_setting("story", DEFAULT_STORY),
        note=get_setting("love_note", ""), photos=photos)

@app.route("/uploads/<path:filename>")
@login_required("partner")
def uploaded_photo(filename):
    # Serve only files referenced in the photo database, preventing arbitrary path reads.
    with db() as conn:
        row = conn.execute("SELECT filename FROM photos WHERE filename=?", (filename,)).fetchone()
    if not row:
        abort(404)
    from flask import send_from_directory
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/admin")
@login_required("admin")
def admin():
    with db() as conn:
        photos = conn.execute("SELECT * FROM photos ORDER BY id DESC").fetchall()
    return render_template("admin.html", partner=get_setting("partner_name", "Alejandra"),
        owner=get_setting("owner_name", "mi renegón"), story=get_setting("story", DEFAULT_STORY),
        note=get_setting("love_note", ""), photos=photos)

@app.route("/admin/save", methods=["POST"])
@login_required("admin")
def save():
    set_setting("partner_name", request.form.get("partner_name", "Alejandra")[:80])
    set_setting("owner_name", request.form.get("owner_name", "mi renegón")[:80])
    set_setting("story", request.form.get("story", "")[:30000])
    set_setting("love_note", request.form.get("love_note", "")[:5000])
    flash("Tus cambios quedaron guardados 💗", "success")
    return redirect(url_for("admin"))

@app.route("/admin/upload", methods=["POST"])
@login_required("admin")
def upload():
    files = request.files.getlist("photos")
    caption = request.form.get("caption", "")[:180]
    saved = 0
    for file in files:
        if not file or not file.filename:
            continue
        if not allowed_file(file.filename):
            flash("Se omitió un archivo: usa JPG, PNG, WEBP o GIF.", "error")
            continue
        safe = secure_filename(file.filename)
        unique_name = secrets.token_hex(8) + "_" + safe
        file.save(UPLOAD_DIR / unique_name)
        with db() as conn:
            conn.execute("INSERT INTO photos(filename,caption) VALUES(?,?)", (unique_name, caption))
        saved += 1
    if saved:
        flash(f"Se guardaron {saved} foto(s). Recuerda que el servidor debe tener almacenamiento persistente.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/delete-photo/<int:photo_id>", methods=["POST"])
@login_required("admin")
def delete_photo(photo_id):
    with db() as conn:
        row = conn.execute("SELECT filename FROM photos WHERE id=?", (photo_id,)).fetchone()
        if row:
            try:
                (UPLOAD_DIR / row["filename"]).unlink(missing_ok=True)
            except OSError:
                pass
            conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    flash("Foto eliminada.", "success")
    return redirect(url_for("admin"))

@app.errorhandler(413)
def too_large(_):
    return "La carga supera el límite de 12 MB. Reduce el tamaño de las fotos e inténtalo otra vez.", 413

init_db()

if __name__ == "__main__":
    # Desarrollo local. En producción usa gunicorn y HTTPS.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
