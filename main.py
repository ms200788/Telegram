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

# ================= USER FUNNEL PAGE =================
@app.get("/go/{slug}", response_class=HTMLResponse)
async def ad_page(slug: str, request: Request, db=Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return HTMLResponse("Invalid link", status_code=404)

    link.clicks += 1
    db.commit()

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Special Report | Artificial Intelligence</title>

<style>
body {
    margin:0;
    background:#e9ecef;
    font-family:system-ui, -apple-system, BlinkMacSystemFont;
}

/* HEADER */
.topbar {
    background:#b30000;
    color:#fff;
    padding:12px 16px;
    font-size:20px;
    font-weight:700;
}

/* SATIRE LABEL */
.satire {
    background:#000;
    color:#fff;
    text-align:center;
    padding:8px;
    font-size:13px;
    font-weight:600;
}

/* MAIN CARD */
.article {
    max-width:860px;
    margin:16px auto;
    background:#fff;
    border-radius:16px;
    padding:20px;
}

/* HEADLINE */
h1 {
    font-size:28px;
    line-height:1.3;
    margin-bottom:10px;
    color:#111;
}

.meta {
    color:#666;
    font-size:13px;
    margin-bottom:16px;
}

/* PROFILE */
.profile {
    display:flex;
    gap:16px;
    background:#f4f6f8;
    padding:14px;
    border-radius:14px;
    margin:18px 0;
}

.profile img {
    width:96px;
    height:96px;
    border-radius:12px;
    object-fit:cover;
    border:2px solid #ddd;
}

.profile-details h3 {
    margin:0 0 6px 0;
    font-size:18px;
}

.profile-details p {
    margin:4px 0;
    font-size:14px;
    color:#333;
}

/* ARTICLE TEXT */
p {
    font-size:15px;
    line-height:1.8;
    color:#222;
    margin:14px 0;
}

/* ADS */
.ad {
    margin:24px 0;
    text-align:center;
}

/* TIMER */
.timer {
    background:#fff3cd;
    padding:12px;
    border-radius:12px;
    text-align:center;
    font-size:15px;
    margin:20px 0;
}

/* CONTINUE */
.btn {
    width:100%;
    background:#e63946;
    color:#fff;
    border:none;
    padding:14px;
    font-size:16px;
    border-radius:30px;
    cursor:pointer;
}

/* DISCLAIMER */
.disclaimer {
    background:#111;
    color:#fff;
    padding:16px;
    font-size:13px;
    border-radius:12px;
    margin-top:30px;
}
</style>

<script>
let t = 20;
let interval;

function startTimer() {
    interval = setInterval(() => {
        document.getElementById("t").innerText = t;
        if (t <= 0) {
            clearInterval(interval);
            document.getElementById("msg").innerText = "You may now continue";
            document.getElementById("continue").style.display = "block";
        }
        t--;
    }, 1000);
}

startTimer();

document.addEventListener("visibilitychange", () => {
    if (document.hidden) clearInterval(interval);
    else startTimer();
});
</script>
</head>

<body>

<div class="topbar">NEWS REPORT</div>
<div class="satire">⚠️ THIS ARTICLE IS FICTIONAL & FOR DEMONSTRATION PURPOSES ONLY</div>

<div class="article">

<h1>Artificial Intelligence: How Modern Systems Are Reshaping the Digital World</h1>

<div class="meta">
By Editorial Desk | Updated Today
</div>

<!-- PROFILE -->
<div class="profile">
    <img src="https://via.placeholder.com/300x300.png?text=Profile" alt="Profile Photo">
    <div class="profile-details">
        <h3>Rohan Verma</h3>
        <p><b>Age:</b> 24</p>
        <p><b>Location:</b> India</p>
        <p><b>Field:</b> Computer Science</p>
        <p><b>Status:</b> Fictional Profile</p>
    </div>
</div>

<!-- AD -->
<div class="ad">
<script src="https://pl28574839.effectivegatecpm.com/6f/6f/f2/6f6ff25ccc5d4bbef9cdeafa839743bb.js"></script>
</div>

<div class="timer">
<p id="msg">Please wait <b id="t">20</b> seconds to continue reading</p>
</div>

<p>
Artificial Intelligence has rapidly evolved from a theoretical concept into a core pillar of modern
technology. Today, AI systems are embedded in smartphones, recommendation engines, navigation systems,
and enterprise tools used by millions of people daily.
</p>

<p>
Experts suggest that AI’s ability to learn from data, recognize patterns, and automate decision-making
has transformed industries such as healthcare, finance, education, and cybersecurity.
</p>

<h2>How AI Systems Operate</h2>

<p>
Modern AI relies on machine learning and neural networks trained on massive datasets. These systems do
not follow rigid instructions; instead, they adapt based on outcomes and feedback.
</p>

<!-- MID AD -->
<div class="ad">
<script async data-cfasync="false" src="https://pl28575184.effectivegatecpm.com/f42c86f37946ef5ab59eb2d53980afa3/invoke.js"></script>
<div id="container-f42c86f37946ef5ab59eb2d53980afa3"></div>
</div>

<p>
As AI adoption increases, discussions around ethical use, transparency, and accountability have become
central to global policy debates.
</p>

<h2>Looking Ahead</h2>

<p>
Industry analysts believe AI will continue to redefine how humans interact with technology. Responsible
innovation and informed usage will be key to ensuring its benefits are shared broadly.
</p>

<!-- END AD -->
<div class="ad">
<script>
  atOptions = {
    'key' : '32b56ec2e176097bcb57ac54cb139aa2',
    'format' : 'iframe',
    'height' : 50,
    'width' : 320,
    'params' : {}
  };
</script>
<script src="https://www.highperformanceformat.com/32b56ec2e176097bcb57ac54cb139aa2/invoke.js"></script>
</div>

<!-- CONTINUE -->
<div id="continue" style="display:none;">
<a href="{BASE_URL}/redirect/{slug}">
<button class="btn">Continue</button>
</a>
</div>

<div class="disclaimer">
<strong>DISCLAIMER:</strong><br>
This webpage is a fictional demonstration designed for testing, UI preview, and educational purposes.
Any names, images, or profiles shown are not real and do not represent any actual individual.
</div>

</div>
</body>
</html>
"""
# ================= FINAL REDIRECT =================
@app.get("/redirect/{slug}")
async def final_redirect(slug: str, db=Depends(get_db)):
    link = db.query(Link).filter(Link.slug == slug).first()
    if not link:
        return RedirectResponse("/")
    link.completed += 1
    db.commit()
    return RedirectResponse(link.target)