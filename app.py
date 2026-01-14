from flask import Flask, render_template, request, redirect, session
import sqlite3
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

@app.before_request
def require_login():
    if request.endpoint is None:
        return

    allowed_routes = [
    "login",
    "signup",
    "logout",
    "redirect_url",
    "static"
]


    if request.endpoint not in allowed_routes:
        if "user_id" not in session:
            return redirect("/login")



# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short TEXT UNIQUE,
            long TEXT,
            user_id INTEGER
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- UTIL ----------------
def generate_short():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

# ---------------- AUTH ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        try:
            conn = sqlite3.connect("urls.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            return "Username already exists"

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("urls.db")
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect("/")
        return "Invalid login"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- MAIN ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    short_url = None

    if request.method == "POST":
        long_url = request.form["long_url"]
        short_code = generate_short()

        conn = sqlite3.connect("urls.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO urls (short, long, user_id) VALUES (?, ?, ?)",
            (short_code, long_url, session["user_id"])
        )
        conn.commit()
        conn.close()

        short_url = "https://url-shortener-cxvr.onrender.com/" + short_code

    return render_template("index.html", short_url=short_url)
@app.route("/go/<short_code>")
def go(short_code):
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long FROM urls WHERE short=?", (short_code,))
    result = c.fetchone()
    conn.close()

    if result:
        return render_template("redirect.html", long_url=result[0])

    return "URL not found", 404

@app.route("/get/<short_code>")
def get(short_code):
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long FROM urls WHERE short=?", (short_code,))
    result = c.fetchone()
    conn.close()

    if result:
        return render_template("continue.html", long_url=result[0])

    return "URL not found", 404


@app.route("/<short_code>")
def redirect_url(short_code):
    


    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long FROM urls WHERE short=?", (short_code,))
    result = c.fetchone()
    conn.close()

    if result:
        return redirect(f"/go1/{short_code}")
    return "URL not found", 404
@app.route("/go1/<short_code>")
def go1(short_code):
    return redirect(f"/ad1/{short_code}")
@app.route("/ad1/<short_code>")
def ad1(short_code):
    return render_template("ad1.html", short_code=short_code)
@app.route("/ad2/<short_code>")
def ad2(short_code):
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long FROM urls WHERE short=?", (short_code,))
    result = c.fetchone()
    conn.close()

    if result:
        return render_template("ad2.html", long_url=result[0])

    return "URL not found", 404

@app.route("/test")
def test():
    return "Render deployment works!"


    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, debug=False)

