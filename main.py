from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import (
    init_db,
    save_wait_record,
    get_best_time,
    get_history,
    predict_future_wait,
    get_prediction_series,
)
from live_crowd import get_live_crowd_level

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize DB
init_db()

PLACES = [
    {
        "id": 1,
        "name": "City Hospital OPD",
        "category": "Hospital",
        "base_wait": 30,
    },
    {
        "id": 2,
        "name": "National Bank Main Branch",
        "category": "Bank",
        "base_wait": 25,
    },
    {
        "id": 3,
        "name": "Govt. ID Service Center",
        "category": "Government Office",
        "base_wait": 40,
    },
]


def calculate_wait_time(base: int, crowd: int) -> int:
    """
    Better realistic scaling:
    1 → very low
    5 → extreme rush
    """
    multipliers = {
        1: 0.3,   # very low crowd
        2: 0.5,   # low
        3: 0.75,  # normal
        4: 1.0,   # high
        5: 1.4,   # insane
    }
    return int(base * multipliers.get(crowd, 1.0))


def get_place(place_id: int):
    for p in PLACES:
        if p["id"] == place_id:
            return p
    return None


def get_leave_now_advice(place_id: int, travel_time: int = 10, target_total: int = 20):
    """
    Use ML prediction (linear regression) to decide:
    - Leave now
    - Leave soon
    """
    predicted_wait = predict_future_wait(place_id)

    if predicted_wait is None:
        return {
            "advice": "Collecting data…",
            "detail": "Need more updates to predict accurately",
            "leave_in": None,
        }

    total_time = predicted_wait + travel_time

    if total_time <= target_total:
        return {
            "advice": "✅ Leave now",
            "detail": f"Predicted wait ≈ {predicted_wait} min",
            "leave_in": 0,
        }
    else:
        delay = total_time - target_total
        return {
            "advice": "⏳ Leave soon",
            "detail": f"Likely best in ~{delay} min",
            "leave_in": delay,
        }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page:
    - Auto-estimates crowd level for each place
    - Calculates wait time
    - Logs it to DB for ML
    - Shows best time chip
    """
    enriched_places = []

    for p in PLACES:
        live_crowd = get_live_crowd_level(place)
        est_wait = calculate_wait_time(p["base_wait"], live_crowd)

        # Save auto sample to history (so ML has data)
        save_wait_record(
            place_id=p["id"],
            crowd_level=live_crowd,
            estimated_wait=est_wait,
        )

        best_time = get_best_time(p["id"])

        enriched_places.append({
            **p,
            "crowd_level": live_crowd,
            "estimated_wait": est_wait,
            "best_time": best_time,
        })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "places": enriched_places,
        },
    )


@app.get("/place/{place_id}", response_class=HTMLResponse)
async def place_detail(place_id: int, request: Request):
    place = get_place(place_id)
    if not place:
        return HTMLResponse("Place not found", status_code=404)

    history_rows = get_history(place_id)

    labels = []
    values = []
    for ts, wait in history_rows:
        time_part = ts[11:16]  # "HH:MM"
        labels.append(time_part)
        values.append(wait)

    # Use live crowd estimate here too
    live_crowd = get_live_crowd_level(place)
    wait_now = calculate_wait_time(place["base_wait"], live_crowd)
    best_time = get_best_time(place_id)

    advice = get_leave_now_advice(place_id)

    prediction_data = get_prediction_series(place_id)
    if prediction_data:
        pred_labels, actual_waits, predicted_waits = prediction_data
    else:
        pred_labels, actual_waits, predicted_waits = [], [], []

    return templates.TemplateResponse(
        "place.html",
        {
            "request": request,
            "place": place,
            "labels": labels,
            "values": values,
            "current_wait": wait_now,
            "best_time": best_time,
            "advice": advice,
            "pred_labels": pred_labels,
            "actual_waits": actual_waits,
            "predicted_waits": predicted_waits,
        },
    )
