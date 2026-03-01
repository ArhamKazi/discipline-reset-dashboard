from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

from database import SessionLocal, engine
from models import Base, DailyLog, User

app = FastAPI()
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind=engine)

# =======================
# JWT CONFIG
# =======================

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretdevkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =======================
# CREATE DEFAULT ADMIN
# =======================

db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    admin_user = User(
        username="admin",
        password_hash=hash_password("admin123")
    )
    db.add(admin_user)
    db.commit()
db.close()


# =======================
# AUTH ROUTES
# =======================

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(User).filter(User.username == form_data.username).first()
    db.close()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


from fastapi import Cookie

from fastapi.responses import RedirectResponse

def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    access_token: str = Cookie(default=None)
):
    if not token and access_token:
        token = access_token

    if not token:
        return RedirectResponse("/login", status_code=303)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return RedirectResponse("/login", status_code=303)
    except JWTError:
        return RedirectResponse("/login", status_code=303)

    return username

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_form(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/login", status_code=303)

    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True
    )
    return response
# =======================
# DASHBOARD
# =======================

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, user = Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    db: Session = SessionLocal()
    logs = db.query(DailyLog).all()

    total_points = 0
    max_points = len(logs) * 6

    for log in logs:
        total_points += int(log.wake_on_time)
        total_points += int(log.sleep_on_time)
        total_points += int(log.gym)
        total_points += int(log.applications_done >= 1)
        total_points += int(log.learning_minutes >= 120)
        total_points += int(not log.gaming_violation)

    compliance = round((total_points / max_points) * 100, 2) if max_points else 0

    db.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "logs": logs,
        "compliance": compliance
    })


# =======================
# ADD LOG
# =======================

@app.post("/add")
def add_log(
    wake_on_time: str = Form(None),
    sleep_on_time: str = Form(None),
    gym: str = Form(None),
    applications_done: int = Form(0),
    learning_minutes: int = Form(0),
    gaming_violation: str = Form(None),
    salah_count: int = Form(0),
    weight: float = Form(None),
    user: str = Depends(get_current_user)
):
    db: Session = SessionLocal()

    today = date.today().isoformat()

    wake_on_time_bool = wake_on_time == "on"
    sleep_on_time_bool = sleep_on_time == "on"
    gym_bool = gym == "on"
    gaming_violation_bool = gaming_violation == "on"

    existing = db.query(DailyLog).filter(DailyLog.date == today).first()

    if existing:
        existing.wake_on_time = wake_on_time_bool
        existing.sleep_on_time = sleep_on_time_bool
        existing.gym = gym_bool
        existing.applications_done = applications_done
        existing.learning_minutes = learning_minutes
        existing.gaming_violation = gaming_violation_bool
        existing.salah_count = salah_count
        existing.weight = weight
    else:
        log = DailyLog(
            date=today,
            wake_on_time=wake_on_time_bool,
            sleep_on_time=sleep_on_time_bool,
            gym=gym_bool,
            applications_done=applications_done,
            learning_minutes=learning_minutes,
            gaming_violation=gaming_violation_bool,
            salah_count=salah_count,
            weight=weight
        )
        db.add(log)

    db.commit()
    db.close()

    return RedirectResponse("/", status_code=303)