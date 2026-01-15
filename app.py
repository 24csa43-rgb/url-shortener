from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
import os

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# ---------------- AD RATES ----------------
CPC = 0.5   # $ per click
CPM = 5.0   # $ per 1000 impressions

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
            clicks INTEGER DEFAULT 0,
            impressions INTEGER DEFAULT 0
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
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
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
    # Added 'get_stats' to allow checking logic inside the function or letting session handle it
    allowed_routes = ["login", "signup", "static", "ad1", "ad2", "redirect_url"]
    
    # We check if the endpoint exists to avoid 404 errors causing issues here
    if request.endpoint and request.endpoint not in allowed_routes and "user_id" not in session:
        return redirect("/login")

# ---------------- MAIN PAGE ----------------
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

# ---------------- SHORT URL ENTRY ----------------
@app.route("/<short_code>")
def redirect_url(short_code):
    return redirect(f"/ad1/{short_code}")

# ---------------- AD 1 (IMPRESSION) ----------------
@app.route("/ad1/<short_code>")
def ad1(short_code):
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()

    # Count impression
    c.execute(
        "UPDATE urls SET impressions = impressions + 1 WHERE short=?",
        (short_code,)
    )

    conn.commit()
    conn.close()

    return render_template("ad1.html", short_code=short_code)

# ---------------- AD 2 (CLICK) ----------------
@app.route("/ad2/<short_code>")
def ad2(short_code):
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()

    # Count click
    c.execute(
        "UPDATE urls SET clicks = clicks + 1 WHERE short=?",
        (short_code,)
    )

    c.execute("SELECT long FROM urls WHERE short=?", (short_code,))
    result = c.fetchone()

    conn.commit()
    conn.close()

    if result:
        return redirect(result[0])

    return "Invalid URL", 404

# ---------------- DASHBOARD (PAGE LOAD) ----------------
@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()

    # Get all links for user
    c.execute("""
        SELECT short, long, clicks, impressions
        FROM urls
        WHERE user_id=?
    """, (session["user_id"],))

    links = c.fetchall()
    conn.close()

    # Calculate Totals
    # Row index: 0=short, 1=long, 2=clicks, 3=impressions
    total_clicks = sum(l[2] for l in links)
    total_impressions = sum(l[3] for l in links)

    # Calculate Revenue based on your rates
    revenue = (total_clicks * CPC) + ((total_impressions / 1000) * CPM)

    # Pass everything to the template
    return render_template(
        "dashboard.html",
        urls=[{"short_code": l[0], "original_url": l[1], "clicks": l[2], "impressions": l[3]} for l in links], 
        total_clicks=total_clicks,
        total_impressions=total_impressions,
        total_revenue=revenue
    )

# ---------------- NEW: REAL-TIME API STATS ----------------
@app.route("/api/stats")
def get_stats():
    # Security check: Ensure user is logged in
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect("urls.db")
    c = conn.cursor()

    # Get only clicks and impressions for math
    c.execute("SELECT clicks, impressions FROM urls WHERE user_id=?", (session["user_id"],))
    rows = c.fetchall()
    conn.close()

    # Calculate Totals
    total_clicks = sum(row[0] for row in rows)
    total_impressions = sum(row[1] for row in rows)

    # Calculate Revenue (Must match dashboard logic)
    revenue = (total_clicks * CPC) + ((total_impressions / 1000) * CPM)

    # Return JSON for JavaScript to read
    return jsonify({
        "clicks": total_clicks,
        "impressions": total_impressions,
        "revenue": "{:.2f}".format(revenue)
    })

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)