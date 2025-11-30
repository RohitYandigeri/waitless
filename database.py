import sqlite3
from datetime import datetime

DB_NAME = "waitless.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wait_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        place_id INTEGER,
        crowd_level INTEGER,
        estimated_wait INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_wait_record(place_id, crowd_level, estimated_wait):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO wait_history (place_id, crowd_level, estimated_wait, timestamp)
    VALUES (?, ?, ?, ?)
    """, (
        place_id,
        crowd_level,
        estimated_wait,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_best_time(place_id):
    """
    Find hour with lowest average wait for this place
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT substr(timestamp, 12, 2) as hour,
           AVG(estimated_wait) as avg_wait
    FROM wait_history
    WHERE place_id = ?
    GROUP BY hour
    ORDER BY avg_wait ASC
    LIMIT 1
    """, (place_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return f"{row[0]}:00 – {row[0]}:59"
    return "Collecting data..."


def get_history(place_id, limit=100):
    """
    Return list of (timestamp, estimated_wait) for this place.
    Ordered by time ascending.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp, estimated_wait
    FROM wait_history
    WHERE place_id = ?
    ORDER BY timestamp ASC
    LIMIT ?
    """, (place_id, limit))

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_recent_avg_wait(place_id, n=5):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT estimated_wait
    FROM wait_history
    WHERE place_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """, (place_id, n))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    waits = [r[0] for r in rows]
    return sum(waits) / len(waits)


import numpy as np
from sklearn.linear_model import LinearRegression


def predict_future_wait(place_id, minutes_ahead=10):
    """
    Predict future wait using simple linear regression
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp, estimated_wait
    FROM wait_history
    WHERE place_id = ?
    ORDER BY timestamp ASC
    """, (place_id,))

    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return None

    # Convert timestamps to minutes since start
    times = []
    waits = []

    start_time = rows[0][0]

    for ts, wait in rows:
        # extract minutes (rough)
        minute = int(ts[11:13]) * 60 + int(ts[14:16])
        times.append(minute)
        waits.append(wait)

    X = np.array(times).reshape(-1, 1)
    y = np.array(waits)

    model = LinearRegression()
    model.fit(X, y)

    future_time = X[-1][0] + minutes_ahead
    prediction = model.predict([[future_time]])

    return max(0, int(prediction[0]))
def get_prediction_series(place_id):
    """
    Returns timestamps, actual waits, and predicted waits
    """
    import numpy as np
    from sklearn.linear_model import LinearRegression

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT timestamp, estimated_wait
    FROM wait_history
    WHERE place_id = ?
    ORDER BY timestamp ASC
    """, (place_id,))

    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 3:
        return None

    times = []
    actual = []

    for ts, wait in rows:
        minute = int(ts[11:13]) * 60 + int(ts[14:16])
        times.append(minute)
        actual.append(wait)

    X = np.array(times).reshape(-1, 1)
    y = np.array(actual)

    model = LinearRegression()
    model.fit(X, y)

    predicted = model.predict(X)

    labels = [ts[11:16] for ts, _ in rows]

    return labels, actual, predicted.astype(int).tolist()
