from flask import Flask, render_template, request, redirect, session
import sqlite3
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# ---------------- GLOBAL VARIABLES ----------------
clicks = 0
impressions = 0
cpc_rate = 0.5   # $ per click
cpm_rate = 5.0   # $ per 1000 impressions

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # URLs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short TEXT UNIQUE,
            long TEXT,
            user_id INTEGER,
            clicks INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- UTILITIES ----------------
def generate_short():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

# ---------------- AUTH ROUTES ----------------
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

# ---------------- LOGIN PROTECTION ----------------
@app.before_request
def require_login():
    allowed_routes = ["login", "signup", "static"]
    if request.endpoint not in allowed_routes and "user_id" not in session:
        return redirect("/login")

# ---------------- MAIN URL SHORTENER ----------------
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

        short_url = request.host_url + short_code

    return render_template("index.html", short_url=short_url)

# ---------------- REDIRECT SHORT URL ----------------
@app.route("/<short_code>")
def redirect_url(short_code):
    global clicks, impressions

    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long, clicks FROM urls WHERE short=?", (short_code,))
    result = c.fetchone()

    if result:
        long_url, current_clicks = result

        # Update URL clicks
        c.execute("UPDATE urls SET clicks = clicks + 1 WHERE short=?", (short_code,))
        conn.commit()
        conn.close()

        # Update global ad revenue clicks
        clicks += 1
        impressions += 1

        return redirect(long_url)
    else:
        conn.close()
        return "Invalid URL", 404

# ---------------- DASHBOARD WITH AD REVENUE ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    global clicks, impressions

    if "user_id" not in session:
        return redirect("/login")

    # Handle ad revenue buttons
    if request.method == "POST":
        if 'add_click' in request.form:
            clicks += 1
        elif 'add_impression' in request.form:
            impressions += 1
        elif 'reset' in request.form:
            clicks = 0
            impressions = 0

    revenue = clicks * cpc_rate + (impressions / 1000) * cpm_rate

    # Fetch all links for this user
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("""
        SELECT short, long, clicks
        FROM urls
        WHERE user_id=?
    """, (session["user_id"],))
    links = c.fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        links=links,
        clicks=clicks,
        impressions=impressions,
        revenue=revenue
    )

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
