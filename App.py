import streamlit as st
import sqlite3
import requests

# ==============================
# CONFIG
# ==============================
API_KEY = "sk-c826210b86bb4cc48fea02988643d484"
DB_FILE = "app.db"

ADMIN_EMAIL = "Admin@AIHUMANIZER.COM"
ADMIN_PASS = "@Master123##₦"

# ==============================
# DATABASE
# ==============================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
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
        # Defaults
        c.execute("INSERT OR IGNORE INTO settings (id, tokens_per_ad, tokens_per_use) VALUES (1, 1, 1)")
        c.execute("INSERT OR IGNORE INTO stats (id, ads_watched, texts_humanized) VALUES (1, 0, 0)")
        conn.commit()

def get_settings():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT tokens_per_ad, tokens_per_use FROM settings WHERE id=1")
        return c.fetchone()

def update_settings(tokens_per_ad, tokens_per_use):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE settings SET tokens_per_ad=?, tokens_per_use=? WHERE id=1",
                  (tokens_per_ad, tokens_per_use))
        conn.commit()

def get_stats():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT ads_watched, texts_humanized FROM stats WHERE id=1")
        return c.fetchone()

def increment_stat(field):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(f"UPDATE stats SET {field} = {field} + 1 WHERE id=1")
        conn.commit()

def get_user(email):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        return c.fetchone()

def add_user(email, password):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password, tokens) VALUES (?, ?, ?)", (email, password, 2))
        conn.commit()

def update_tokens(email, tokens):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET tokens=? WHERE email=?", (tokens, email))
        conn.commit()

def count_users():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(tokens) FROM users")
        return c.fetchone()

# ==============================
# APP LOGIC
# ==============================
def humanize_text(input_text):
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "prompt": "Humanize this text: " + input_text,
                "max_tokens": 500
            }
        )
        data = response.json()
        return data.get("choices", [{}])[0].get("text", "⚠️ Error: No response from AI")
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ==============================
# STREAMLIT UI
# ==============================
def user_app(email):
    st.title("📝 AI Text Humanizer")

    # Get user tokens
    user = get_user(email)
    tokens = user[3]

    tokens_per_ad, tokens_per_use = get_settings()

    st.info(f"Logged in as: **{email}** | Tokens: **{tokens}**")

    text = st.text_area("Paste your text here:")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Humanize"):
            if tokens < tokens_per_use:
                st.warning("Not enough tokens. Please watch an ad to earn more!")
            elif not text.strip():
                st.warning("Please enter some text first.")
            else:
                update_tokens(email, tokens - tokens_per_use)
                increment_stat("texts_humanized")
                st.subheader("✅ Humanized Text")
                st.write(humanize_text(text))
    with col2:
        if st.button("🎬 Watch Ad (Simulated)"):
            update_tokens(email, tokens + tokens_per_ad)
            increment_stat("ads_watched")
            st.success(f"Ad watched! You earned {tokens_per_ad} token(s). Refresh to see updated tokens.")

def admin_app():
    st.title("⚙️ Admin Panel")

    tokens_per_ad, tokens_per_use = get_settings()
    ads_watched, texts_humanized = get_stats()
    user_count, total_tokens = count_users()

    st.subheader("🔧 Settings")
    with st.form("settings_form"):
        new_tokens_per_ad = st.number_input("Tokens per Ad", min_value=1, value=tokens_per_ad)
        new_tokens_per_use = st.number_input("Tokens per Use", min_value=1, value=tokens_per_use)
        submitted = st.form_submit_button("Update Settings")
        if submitted:
            update_settings(new_tokens_per_ad, new_tokens_per_use)
            st.success("Settings updated!")

    st.subheader("📊 Stats")
    st.write(f"👥 Total Users: {user_count}")
    st.write(f"💰 Total Tokens Across Users: {total_tokens if total_tokens else 0}")
    st.write(f"🎬 Ads Watched: {ads_watched}")
    st.write(f"📝 Texts Humanized: {texts_humanized}")

def main():
    st.set_page_config(page_title="AI Humanizer", page_icon="✨")

    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.email = None
        st.session_state.admin = False

    if not st.session_state.logged_in:
        st.title("🔑 Login / Sign Up")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login / Sign Up"):
            if email == ADMIN_EMAIL and password == ADMIN_PASS:
                st.session_state.logged_in = True
                st.session_state.admin = True
                st.success("Admin login successful!")
            else:
                user = get_user(email)
                if user:
                    if user[2] == password:
                        st.session_state.logged_in = True
                        st.session_state.email = email
                        st.success("Login successful!")
                    else:
                        st.error("Wrong password.")
                else:
                    add_user(email, password)
                    st.session_state.logged_in = True
                    st.session_state.email = email
                    st.success("Account created and logged in!")

    else:
        if st.session_state.admin:
            admin_app()
        else:
            user_app(st.session_state.email)

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.email = None
            st.session_state.admin = False
            st.success("Logged out successfully.")

if __name__ == "__main__":
    main()            else:
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
