# app.py
import streamlit as st
import sqlite3
import requests
from typing import Tuple, Optional

# ==============================
# CONFIG
# ==============================
API_KEY = "sk-c826210b86bb4cc48fea02988643d484"
DB_FILE = "app.db"

ADMIN_EMAIL = "Admin@AIHUMANIZER.COM"
ADMIN_PASS = "@Master123##₦"

# ==============================
# DATABASE HELPERS
# ==============================
def init_db():
    """Create DB and default rows if they don't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password TEXT,
                tokens INTEGER DEFAULT 2
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                tokens_per_ad INTEGER,
                tokens_per_use INTEGER
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                ads_watched INTEGER,
                texts_humanized INTEGER
            )
            """
        )
        # Insert default settings/stats if missing
        c.execute("INSERT OR IGNORE INTO settings (id, tokens_per_ad, tokens_per_use) VALUES (1, 1, 1)")
        c.execute("INSERT OR IGNORE INTO stats (id, ads_watched, texts_humanized) VALUES (1, 0, 0)")
        conn.commit()

def get_settings() -> Tuple[int, int]:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT tokens_per_ad, tokens_per_use FROM settings WHERE id=1")
        row = c.fetchone()
        if row:
            return int(row[0]), int(row[1])
        return 1, 1

def update_settings(tokens_per_ad: int, tokens_per_use: int) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE settings SET tokens_per_ad=?, tokens_per_use=? WHERE id=1", (tokens_per_ad, tokens_per_use))
        conn.commit()

def get_stats() -> Tuple[int, int]:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT ads_watched, texts_humanized FROM stats WHERE id=1")
        row = c.fetchone()
        if row:
            return int(row[0]), int(row[1])
        return 0, 0

def increment_stat(field: str) -> None:
    assert field in ("ads_watched", "texts_humanized")
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(f"UPDATE stats SET {field} = {field} + 1 WHERE id=1")
        conn.commit()

def get_user(email: str) -> Optional[tuple]:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, password, tokens FROM users WHERE email=?", (email,))
        return c.fetchone()

def add_user(email: str, password: str, tokens: int = 2) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password, tokens) VALUES (?, ?, ?)", (email, password, tokens))
        conn.commit()

def update_tokens(email: str, tokens: int) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET tokens=? WHERE email=?", (tokens, email))
        conn.commit()

def count_users() -> Tuple[int, int]:
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(tokens) FROM users")
        row = c.fetchone()
        if row:
            user_count = int(row[0])
            total_tokens = int(row[1]) if row[1] is not None else 0
            return user_count, total_tokens
        return 0, 0

# ==============================
# AI CALL
# ==============================
def humanize_text(input_text: str) -> str:
    """Call DeepSeek (or return an error message)."""
    if not input_text or not input_text.strip():
        return "⚠️ No text provided."

    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "prompt": "Humanize this text: " + input_text,
                "max_tokens": 500
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        # safe navigation
        choices = data.get("choices") or []
        if len(choices) > 0:
            return choices[0].get("text") or choices[0].get("message", {}).get("content", "⚠️ No text returned.")
        # fallback for other shapes:
        return data.get("text") or "⚠️ Unexpected response shape from API."
    except requests.RequestException as e:
        return f"⚠️ Network/API error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"

# ==============================
# STREAMLIT UI
# ==============================
def user_app(email: str):
    st.header("📝 AI Text Humanizer")
    user = get_user(email)
    if not user:
        st.error("User not found. Please log out and log in again.")
        return

    user_id, user_email, _, user_tokens = user
    user_tokens = int(user_tokens)

    tokens_per_ad, tokens_per_use = get_settings()

    col_top_left, col_top_right = st.columns([3, 1])
    with col_top_left:
        st.write(f"**Logged in as:** {user_email}")
    with col_top_right:
        st.metric("Tokens", user_tokens)

    st.write("---")
    text_input = st.text_area("Paste your text here:", height=220)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Humanize"):
            if user_tokens < tokens_per_use:
                st.warning("Not enough tokens. Please watch an ad to earn more!")
            elif not text_input.strip():
                st.warning("Please enter some text first.")
            else:
                # Deduct tokens first
                new_tokens = user_tokens - tokens_per_use
                update_tokens(email, new_tokens)
                increment_stat("texts_humanized")
                # Get result and display
                with st.spinner("Humanizing..."):
                    result = humanize_text(text_input)
                st.subheader("✅ Humanized Text")
                st.write(result)
                # refresh the page so token metric updates
                st.experimental_rerun()

    with col2:
        if st.button("🎬 Watch Ad (Simulated)"):
            # Add tokens_per_ad to user's tokens
            new_tokens = user_tokens + tokens_per_ad
            update_tokens(email, new_tokens)
            increment_stat("ads_watched")
            st.success(f"Ad watched! You earned {tokens_per_ad} token(s).")
            st.experimental_rerun()

    st.write("---")
    st.markdown(
        "⚠️ Ads are simulated on web. To integrate AdMob/Start.io you will need platform SDKs (mobile)."
    )

def admin_app():
    st.header("⚙️ Admin Panel")
    tokens_per_ad, tokens_per_use = get_settings()
    ads_watched, texts_humanized = get_stats()
    user_count, total_tokens = count_users()

    st.subheader("🔧 Settings")
    with st.form("settings_form", clear_on_submit=False):
        new_tokens_per_ad = st.number_input("Tokens per Ad", min_value=1, value=int(tokens_per_ad))
        new_tokens_per_use = st.number_input("Tokens per Use (tokens consumed per humanize)", min_value=1, value=int(tokens_per_use))
        submitted = st.form_submit_button("Update Settings")
        if submitted:
            update_settings(int(new_tokens_per_ad), int(new_tokens_per_use))
            st.success("Settings updated.")
            st.experimental_rerun()

    st.subheader("📊 Stats")
    st.write(f"👥 Total Users: **{user_count}**")
    st.write(f"💰 Total Tokens across users: **{total_tokens}**")
    st.write(f"🎬 Ads Watched: **{ads_watched}**")
    st.write(f"📝 Texts Humanized: **{texts_humanized}**")

    st.subheader("🔎 Users")
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, email, tokens FROM users ORDER BY id DESC LIMIT 200")
        rows = c.fetchall()
        if rows:
            for r in rows:
                st.write(f"- {r[1]} — {r[2]} tokens")
        else:
            st.write("No users yet.")

# ==============================
# MAIN
# ==============================
def main():
    st.set_page_config(page_title="AI Text Humanizer", page_icon="✨", layout="centered")
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.email = None
        st.session_state.admin = False

    # Top-level layout: login or app
    if not st.session_state.logged_in:
        st.title("🔑 Login / Sign Up")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login / Sign Up")

            if submitted:
                if not email or not password:
                    st.error("Please provide both email and password.")
                else:
                    # Admin login check
                    if email == ADMIN_EMAIL and password == ADMIN_PASS:
                        st.session_state.logged_in = True
                        st.session_state.admin = True
                        st.session_state.email = ADMIN_EMAIL
                        st.success("Admin logged in.")
                        st.experimental_rerun()
                    else:
                        user = get_user(email)
                        if user:
                            # existing user: check password
                            _, _, stored_password, _ = user
                            if stored_password == password:
                                st.session_state.logged_in = True
                                st.session_state.email = email
                                st.session_state.admin = False
                                st.success("Logged in.")
                                st.experimental_rerun()
                            else:
                                st.error("Wrong password.")
                        else:
                            # register user
                            try:
                                add_user(email, password, tokens=2)
                                st.session_state.logged_in = True
                                st.session_state.email = email
                                st.session_state.admin = False
                                st.success("Account created and logged in.")
                                st.experimental_rerun()
                            except sqlite3.IntegrityError:
                                st.error("This email is already registered.")
    else:
        # Logged in view
        if st.session_state.admin:
            admin_app()
        else:
            user_app(st.session_state.email)

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.email = None
            st.session_state.admin = False
            st.experimental_rerun()

if __name__ == "__main__":
    main()def add_user(email, password):
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
