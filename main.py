import os
import time
import random
import string
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# ================= CONFIG =================
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_URL = "https://telegram-93bm.onrender.com"

# ================= DB SETUP =================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True)
    target = Column(String)
    clicks = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    created_at = Column(Integer)

Base.metadata.create_all(bind=engine)

# ================= APP =================
app = FastAPI()
REQUEST_LOG = {}
ADMIN_COOKIE = "admin_session"

# ================= HELPERS =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_admin_cookie(request: Request):
    cookie = request.cookies.get(ADMIN_COOKIE)
    if cookie != "true":
        raise HTTPException(status_code=403, detail="Forbidden: Admin only")

def generate_slug(length=6):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

# ================= HEALTH =================
@app.get("/health")
async def health():
    return {"status": "alive"}

# ================= HOME =================
@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h2 style='text-align:center'>Fast Link Gateway</h2>"

# ================= ADMIN LOGIN =================
@app.get("/admin", response_class=HTMLResponse)
async def admin_login():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f2027;color:#fff;font-family:system-ui}
.card{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}
input,button{width:100%;padding:14px;margin-top:10px;border-radius:12px}
button{background:#ff4b2b;color:#fff;border:none}
</style>
</head>
<body>

<div class="card">
<h3>Admin Login</h3>
<form method="post" action="/admin/login">
<input type="password" name="password" placeholder="Admin password">
<button>Login</button>
</form>
</div>

</body>
</html>
"""

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_do_login(password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Forbidden: Wrong password")
    # Set cookie and redirect to admin panel
    response = RedirectResponse("/admin/panel", status_code=302)
    response.set_cookie(key=ADMIN_COOKIE, value="true", max_age=86400, httponly=False)
    return response

# ================= ADMIN PANEL =================
@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel(request: Request, db=Depends(get_db)):
    check_admin_cookie(request)
    links = db.query(Link).all()
    links_html = ""
    for link in links:
        links_html += f"<tr><td>{link.slug}</td><td>{link.target}</td><td>{link.clicks}</td><td>{link.completed}</td></tr>"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0f2027;color:#fff;font-family:system-ui}}
.card{{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}}
input,button{{width:100%;padding:12px;margin-top:8px;border-radius:12px}}
button{{background:#4caf50;color:#fff;border:none;padding:12px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;border:1px solid #000;text-align:center}}
</style>
</head>
<body>

<div class="card">
<h3>Create Funnel Link</h3>
<form method="post" action="/admin/create">
<input type="url" name="target" placeholder="Target URL" required>
<button>Create Funnel Link</button>
</form>
</div>

<div class="card">
<h3>All Links Stats</h3>
<table>
<tr><th>Slug</th><th>Target</th><th>Clicks</th><th>Completed</th></tr>
{links_html}
</table>
</div>

</body>
</html>
"""

@app.post("/admin/create", response_class=HTMLResponse)
async def admin_create(request: Request, target: str = Form(...), db=Depends(get_db)):
    check_admin_cookie(request)

    slug = generate_slug()
    while db.query(Link).filter(Link.slug == slug).first():
        slug = generate_slug()

    link = Link(
        slug=slug,
        target=target,
        clicks=0,
        completed=0,
        created_at=int(time.time())
    )
    db.add(link)
    db.commit()

    full_url = f"{BASE_URL}/go/{slug}"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{{background:#0f2027;color:#fff;font-family:system-ui}}
.card{{background:#fff;color:#000;border-radius:16px;padding:16px;margin:16px}}
input{{width:100%;padding:12px}}
button{{background:#4caf50;color:#fff;border:none;padding:14px;width:100%;border-radius:30px}}
</style>
<script>
function copyLink(){{
  let i=document.getElementById("l");
  i.select();
  document.execCommand("copy");
  alert("Copied");
}}
</script>
</head>
<body>

<div class="card">
<h3>Link Created</h3>
<input id="l" value="{full_url}" readonly>
<button onclick="copyLink()">Copy Link</button>
</div>

<a href="/admin/panel" style="display:block;text-align:center;margin-top:16px;color:#fff">Back to Admin Panel</a>

</body>
</html>
"""

# ================= IMPORTS =================
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

app = FastAPI()

# ================= DB DEPENDENCY (example) =================
def get_db():
    db = SessionLocal()   # <-- your existing SessionLocal
    try:
        yield db
    finally:
        db.close()


# ================= USER FUNNEL PAGE =================
@app.get("/go/{slug}", response_class=HTMLResponse)
async def ad_page(slug: str, request: Request, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return HTMLResponse("Invalid link", status_code=404)

    link.clicks += 1
    db.commit()

    base = str(request.base_url).rstrip("/")

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Special Report</title>

<style>
body {{
    margin:0;
    background:#e9ecef;
    font-family:system-ui, -apple-system, BlinkMacSystemFont;
}}
.topbar {{
    background:#b30000;
    color:#fff;
    padding:12px 16px;
    font-size:20px;
    font-weight:700;
}}
.satire {{
    background:#000;
    color:#fff;
    text-align:center;
    padding:8px;
    font-size:13px;
    font-weight:600;
}}
.article {{
    max-width:860px;
    margin:16px auto;
    background:#fff;
    border-radius:16px;
    padding:20px;
}}
h1 {{
    font-size:28px;
    margin-bottom:10px;
}}
.meta {{
    color:#666;
    font-size:13px;
    margin-bottom:16px;
}}
.profile {{
    display:flex;
    gap:16px;
    background:#f4f6f8;
    padding:14px;
    border-radius:14px;
    margin:18px 0;
}}
.profile img {{
    width:96px;
    height:96px;
    border-radius:12px;
    object-fit:cover;
    border:2px solid #ddd;
}}
.profile-details h3 {{
    margin:0 0 6px 0;
    font-size:18px;
}}
.profile-details p {{
    margin:4px 0;
    font-size:14px;
}}
.timer {{
    background:#fff3cd;
    padding:12px;
    border-radius:12px;
    text-align:center;
    margin:20px 0;
}}
.btn {{
    width:100%;
    background:#e63946;
    color:#fff;
    border:none;
    padding:14px;
    font-size:16px;
    border-radius:30px;
    cursor:pointer;
}}
.disclaimer {{
    background:#111;
    color:#fff;
    padding:16px;
    font-size:13px;
    border-radius:12px;
    margin-top:30px;
}}
</style>

<script>
let t = 20;
function startTimer() {{
    let interval = setInterval(() => {{
        document.getElementById("t").innerText = t;
        if (t <= 0) {{
            clearInterval(interval);
            document.getElementById("msg").innerText = "You may now continue";
            document.getElementById("continue").style.display = "block";
        }}
        t--;
    }}, 1000);
}}
window.onload = startTimer;
</script>
</head>

<body>

<div class="topbar">NEWS REPORT</div>
<div class="satire">⚠️ THIS ARTICLE IS FICTIONAL & FOR DEMONSTRATION PURPOSES ONLY</div>

<div class="article">

<h1>Power - Chainsaw Man</h1>
<div class="meta">By Editorial Desk | Updated Today</div>

<div class="profile">
    <img src="https://ibb.co/TqxdNhwD/Power.jpg" alt="Power">
    <div class="profile-details">
        <h3>Power</h3>
        <p><b>Age:</b> 20</p>
        <p><b>Location:</b> Japan</p>
        <p><b>Field:</b> Devil</p>
        <p><b>Status:</b> Fictional Profile</p>
    </div>
</div>

<h2>Character Analysis</h2>

<ul>
    <li><b>Identity:</b> Power is the Blood Fiend from <i>Chainsaw Man</i>.</li>
    <li><b>Personality:</b> Loud, arrogant, selfish, and dishonest.</li>
    <li><b>Abilities:</b> Can manipulate blood into weapons.</li>
    <li><b>Combat:</b> Fights aggressively with little strategy.</li>
    <li><b>Humans:</b> Initially views humans as inferior.</li>
    <li><b>Meowy:</b> Deeply loves her pet cat.</li>
    <li><b>Denji & Aki:</b> Slowly forms emotional bonds.</li>
    <li><b>Growth:</b> Learns fear, trust, and sacrifice.</li>
    <li><b>Symbolism:</b> Represents chaos and selfish freedom.</li>
    <li><b>Impact:</b> One of the most emotionally powerful characters.</li>
</ul>

<div class="timer">
<p id="msg">Please wait <b id="t">20</b> seconds to continue</p>
</div>

<div id="continue" style="display:none;">
<a href="{base}/redirect/{slug}">
<button class="btn">Continue</button>
</a>
</div>

<div class="disclaimer">
<b>DISCLAIMER:</b> This page is fictional and for testing purposes only.
</div>

</div>
</body>
</html>
"""

    return HTMLResponse(html)


# ================= FINAL REDIRECT =================
@app.get("/redirect/{slug}")
async def final_redirect(slug: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return RedirectResponse("/")

    link.completed += 1
    db.commit()

    return RedirectResponse(link.target)