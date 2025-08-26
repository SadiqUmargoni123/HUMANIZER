from flask import Flask, render_template_string, request, redirect, session, url_for
import sqlite3, requests, os

app = Flask(__name__)
app.secret_key = "supersecret"  # change in production

# DeepSeek API Key
API_KEY = "sk-c826210b86bb4cc48fea02988643d484"

# ==============================
# DATABASE SETUP
# ==============================
def init_db():
    with sqlite3.connect("app.db") as conn:
        c = conn.cursor()
        # Users table
        c.execute("""CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE,
                        password TEXT,
                        tokens INTEGER DEFAULT 2
                    )""")
        # Settings table
        c.execute("""CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY,
                        tokens_per_ad INTEGER,
                        tokens_per_use INTEGER
                    )""")
        # Stats table
        c.execute("""CREATE TABLE IF NOT EXISTS stats (
                        id INTEGER PRIMARY KEY,
                        ads_watched INTEGER,
                        texts_humanized INTEGER
                    )""")
        # Default settings
        c.execute("INSERT OR IGNORE INTO settings (id, tokens_per_ad, tokens_per_use) VALUES (1, 1, 1)")
        # Default stats
        c.execute("INSERT OR IGNORE INTO stats (id, ads_watched, texts_humanized) VALUES (1, 0, 0)")
        conn.commit()

init_db()

# ==============================
# USER ROUTES
# ==============================
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    email = session["user"]

    # Get user tokens
    with sqlite3.connect("app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT tokens FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if not user:
            return redirect(url_for("logout"))
        tokens = user[0]

        # Get settings
        c.execute("SELECT tokens_per_ad, tokens_per_use FROM settings WHERE id=1")
        tokens_per_ad, tokens_per_use = c.fetchone()

    text = ""
    result = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "humanize":
            if tokens < tokens_per_use:
                result = "Not enough tokens. Watch ads to earn more!"
            else:
                text = request.form["text"]

                # Deduct tokens
                tokens -= tokens_per_use
                with sqlite3.connect("app.db") as conn:
                    c = conn.cursor()
                    c.execute("UPDATE users SET tokens=? WHERE email=?", (tokens, email))
                    c.execute("UPDATE stats SET texts_humanized = texts_humanized + 1 WHERE id=1")
                    conn.commit()

                # Call DeepSeek API
                try:
                    response = requests.post(
                        "https://api.deepseek.com/v1/completions",
                        headers={
                            "Authorization": f"Bearer {API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "prompt": "Humanize this text: " + text,
                            "max_tokens": 500
                        }
                    )
                    data = response.json()
                    result = data.get("choices", [{}])[0].get("text", "Error: No response from AI")
                except Exception as e:
                    result = f"Error: {str(e)}"

        elif action == "watch_ad":
            tokens += tokens_per_ad
            with sqlite3.connect("app.db") as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET tokens=? WHERE email=?", (tokens, email))
                c.execute("UPDATE stats SET ads_watched = ads_watched + 1 WHERE id=1")
                conn.commit()
            result = f"Ad watched! You earned {tokens_per_ad} tokens."

    # HTML Template
    html = """
    <h2>AI Text Humanizer</h2>
    <p>Logged in as {{email}} | Tokens: {{tokens}} | <a href="/logout">Logout</a></p>
    <form method="POST">
      <textarea name="text" placeholder="Paste your text here..." style="width:100%;height:150px;">{{text}}</textarea><br><br>
      <button type="submit" name="action" value="humanize">Humanize</button>
      <button type="submit" name="action" value="watch_ad">Watch Ad (Simulated)</button>
    </form>
    <div style="margin-top:20px;padding:10px;background:#f9f9f9;">{{result}}</div>
    """
    return render_template_string(html, email=email, tokens=tokens, text=text, result=result)

# ==============================
# AUTH ROUTES
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Check admin login
        if email == "Admin@AIHUMANIZER.COM" and password == "@Master123##₦":
            session["admin"] = True
            return redirect(url_for("admin"))

        with sqlite3.connect("app.db") as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=?", (email,))
            user = c.fetchone()
            if user:
                if user[2] == password:
                    session["user"] = email
                    return redirect(url_for("index"))
                else:
                    return "Wrong password"
            else:
                # Register new user
                c.execute("INSERT INTO users (email, password, tokens) VALUES (?, ?, ?)", (email, password, 2))
                conn.commit()
                session["user"] = email
                return redirect(url_for("index"))

    return """
    <h2>Login / Sign Up</h2>
    <form method="POST">
      <input type="email" name="email" placeholder="Email" required><br><br>
      <input type="password" name="password" placeholder="Password" required><br><br>
      <button type="submit">Login / Sign Up</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ==============================
# ADMIN ROUTES
# ==============================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin"):
        return redirect(url_for("login"))

    with sqlite3.connect("app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT tokens_per_ad, tokens_per_use FROM settings WHERE id=1")
        tokens_per_ad, tokens_per_use = c.fetchone()

        c.execute("SELECT COUNT(*), SUM(tokens) FROM users")
        user_count, total_tokens = c.fetchone()

        c.execute("SELECT ads_watched, texts_humanized FROM stats WHERE id=1")
        ads_watched, texts_humanized = c.fetchone()

    if request.method == "POST":
        tokens_per_ad = int(request.form["tokens_per_ad"])
        tokens_per_use = int(request.form["tokens_per_use"])
        with sqlite3.connect("app.db") as conn:
            c = conn.cursor()
            c.execute("UPDATE settings SET tokens_per_ad=?, tokens_per_use=? WHERE id=1",
                      (tokens_per_ad, tokens_per_use))
            conn.commit()
        return redirect(url_for("admin"))

    html = """
    <h2>Admin Panel</h2>
    <p><a href="/logout">Logout</a></p>
    <h3>Settings</h3>
    <form method="POST">
      Tokens per Ad: <input type="number" name="tokens_per_ad" value="{{tokens_per_ad}}"><br><br>
      Tokens per Use: <input type="number" name="tokens_per_use" value="{{tokens_per_use}}"><br><br>
      <button type="submit">Update</button>
    </form>
    <h3>Stats</h3>
    <p>Total Users: {{user_count}}</p>
    <p>Total Tokens across users: {{total_tokens}}</p>
    <p>Ads Watched: {{ads_watched}}</p>
    <p>Texts Humanized: {{texts_humanized}}</p>
    """
    return render_template_string(html, tokens_per_ad=tokens_per_ad, tokens_per_use=tokens_per_use,
                                  user_count=user_count, total_tokens=total_tokens,
                                  ads_watched=ads_watched, texts_humanized=texts_humanized)

# ==============================
if __name__ == "__main__":
    app.run(debug=True)
