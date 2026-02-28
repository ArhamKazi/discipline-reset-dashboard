from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from database import SessionLocal, engine
from models import Base, DailyLog

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def calculate_compliance(logs):
    total_points = 0
    max_points = len(logs) * 6

    for log in logs:
        total_points += int(log.wake_on_time)
        total_points += int(log.sleep_on_time)
        total_points += int(log.gym)
        total_points += int(log.applications_done >= 1)
        total_points += int(log.learning_minutes >= 120)
        total_points += int(not log.gaming_violation)

    if max_points == 0:
        return 0

    return round((total_points / max_points) * 100, 2)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    db: Session = next(get_db())
    logs = db.query(DailyLog).all()

    compliance = calculate_compliance(logs)

    total_gym = sum(log.gym for log in logs)
    total_apps = sum(log.applications_done for log in logs)
    gaming_violations = sum(log.gaming_violation for log in logs)

    today_str = date.today().isoformat()

    today_log = db.query(DailyLog).filter(DailyLog.date == today_str).first()
    weights = [(log.date, log.weight) for log in logs if log.weight is not None]

    weight_values = [w[1] for w in weights]

    current_weight = weight_values[-1] if weight_values else None
    start_weight = weight_values[0] if weight_values else None

    weight_change = None
    if start_weight and current_weight:
        weight_change = round(current_weight - start_weight, 2)

# 7-day average (if at least 7 entries)
    weekly_avg = None
    if len(weight_values) >= 7:
        last_7 = weight_values[-7:]
        weekly_avg = round(sum(last_7) / 7, 2)        

    today_score = 0
    # Sort logs by date
    logs_sorted = sorted(logs, key=lambda x: x.date)

    wake_streak = 0
    gaming_streak = 0
    full_streak = 0

    for log in reversed(logs_sorted):
        if log.wake_on_time:
            wake_streak += 1
        else:
            break

    for log in reversed(logs_sorted):
        if not log.gaming_violation:
            gaming_streak += 1
        else:
            break

    for log in reversed(logs_sorted):
        score = (
        int(log.wake_on_time) +
        int(log.sleep_on_time) +
        int(log.gym) +
        int(log.applications_done >= 1) +
        int(log.learning_minutes >= 120) +
        int(not log.gaming_violation)
    )
        if score == 6:
            full_streak += 1
        else:
            break
        if today_log:
            today_score += int(today_log.wake_on_time)
            today_score += int(today_log.sleep_on_time)
            today_score += int(today_log.gym)
            today_score += int(today_log.applications_done >= 1)
            today_score += int(today_log.learning_minutes >= 120)
            today_score += int(not today_log.gaming_violation)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "logs": logs,
        "compliance": compliance,
        "total_gym": total_gym,
        "total_apps": total_apps,
        "gaming_violations": gaming_violations,
        "today_score": today_score,
        "current_weight": current_weight,
        "start_weight": start_weight,
        "weight_change": weight_change,
        "weekly_avg": weekly_avg,
        "wake_streak": wake_streak,
        "gaming_streak": gaming_streak,
        "full_streak": full_streak,
    })

@app.post("/add")
def add_log(
    wake_on_time: str = Form(None),
    sleep_on_time: str = Form(None),
    gym: str = Form(None),
    applications_done: int = Form(0),
    learning_minutes: int = Form(0),
    gaming_violation: str = Form(None),
    salah_count: int = Form(0),
    weight: float = Form(None)
):
    db: Session = next(get_db())

    today = date.today().isoformat()

    # Convert checkbox values safely
    wake_on_time_bool = wake_on_time == "on"
    sleep_on_time_bool = sleep_on_time == "on"
    gym_bool = gym == "on"
    gaming_violation_bool = gaming_violation == "on"

    existing = db.query(DailyLog).filter(DailyLog.date == today).first()

    if existing:
        # UPDATE existing entry
        existing.wake_on_time = wake_on_time_bool
        existing.sleep_on_time = sleep_on_time_bool
        existing.gym = gym_bool
        existing.applications_done = applications_done
        existing.learning_minutes = learning_minutes
        existing.gaming_violation = gaming_violation_bool
        existing.salah_count = salah_count
        existing.weight = weight
    else:
        # INSERT new entry
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

    return RedirectResponse("/", status_code=303)