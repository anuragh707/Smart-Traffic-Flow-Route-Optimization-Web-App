# app.py
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
import sqlite3
import pandas as pd
import string
import nltk
from nltk.corpus import stopwords
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
from datetime import datetime
import pytz
import requests
import os

# ---------------------------
# App initialization
# ---------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Anuragh707@'  # change to a strong secret in prod

# ---------------------------
# MySQL config (traffic app)
# ---------------------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Anuragh707@'  # replace with your MySQL root password
app.config['MYSQL_DB'] = 'cityflow'
mysql = MySQL(app)

# ---------------------------
# TomTom API Key (routing)
# ---------------------------
TOMTOM_API_KEY = "6gb8ttf2CPnkPyzWcok0jF0bv87WBb0y"  # replace with your valid key

# ---------------------------
# NLTK setup / model training
# ---------------------------
try:
    _ = stopwords.words('english')
except Exception:
    try:
        nltk.download('stopwords', quiet=True)
    except Exception as e:
        print("Warning: nltk.download failed:", e)

# Load dataset (adjust path if needed)
DATASET_PATH = r"D:\cityflow\merged_dataset.csv"
if not os.path.exists(DATASET_PATH):
    if os.path.exists("merged_dataset.csv"):
        DATASET_PATH = "merged_dataset.csv"
    else:
        print("Warning: merged_dataset.csv not found at provided path. Text model training will be skipped.")
        DATASET_PATH = None

df = None
text_grid_search = None

if DATASET_PATH:
    try:
        df = pd.read_csv(DATASET_PATH)
        df = df.drop_duplicates()

        def preprocess_text(text):
            stop_words = set(stopwords.words('english'))
            if not isinstance(text, str):
                text = str(text)
            text = text.lower()
            text = text.translate(str.maketrans('', '', string.punctuation))
            tokens = text.split()
            tokens = [word for word in tokens if word not in stop_words]
            return ' '.join(tokens)

        df['text'] = df['text'].apply(preprocess_text)

        X = df['text']
        y = df['trafficflow']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        text_pipeline = make_pipeline(
            TfidfVectorizer(),
            RandomForestClassifier(random_state=42)
        )

        param_grid = {
            'randomforestclassifier__n_estimators': [100],
            'randomforestclassifier__max_depth': [10]
        }

        text_grid_search = GridSearchCV(text_pipeline, param_grid, cv=3)
        text_grid_search.fit(X_train, y_train)
        print("Text model trained.")
    except Exception as e:
        print("Error training text model:", e)
        text_grid_search = None
else:
    text_grid_search = None

# ---------------------------
# SQLite initialization (history)
# ---------------------------
DATABASE = 'traffic_flow.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            street_name TEXT,
            description TEXT,
            traffic_flow_prediction TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

from functools import wraps

# ---------------------------
# Auth / traffic app routes (register, login, entry, show ...)
# (unchanged from your merged version)
# ---------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        hashed_password = generate_password_hash(password)

        # Additional fields for traffic_info
        police_name = request.form['police_name'].strip()
        station_id = request.form['station_id'].strip()
        station_name = request.form['station_name'].strip()
        position = request.form['position'].strip()
        mobile = request.form['mobile'].strip()
        police_id=request.form['police_id'].strip()

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                flash('Username already exists. Please login.', 'danger')
                cur.close()
                return redirect(url_for('login'))

            # Insert into users table
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            user_id = cur.lastrowid  # Get the newly inserted user's ID

            # Insert into traffic_info table
            cur.execute("""
                INSERT INTO traffic_info (user_id, police_id, station_id, station_name, police_name, position, mobile, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, police_id, station_id, station_name, police_name, position, mobile, hashed_password))

            mysql.connection.commit()
            cur.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')

    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password_input = request.form['password'].strip()
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if not user:
            flash("Please register before logging in.", "warning")
            return redirect(url_for('register'))
        if check_password_hash(user[1], password_input):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('entry'))
        else:
            flash("Invalid password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/entry', methods=['GET', 'POST'])
def entry():
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('login'))
    error_message = None
    if request.method == 'POST':
        location = request.form['location'].strip().lower()
        street_name = request.form.get('street_name', '').strip().lower()
        description = request.form['description'].strip().lower()
        try:
            text_processed = description
            if text_grid_search:
                stop_words = set(stopwords.words('english'))
                text_processed = description.lower().translate(str.maketrans('', '', string.punctuation))
                text_processed = ' '.join([w for w in text_processed.split() if w not in stop_words])
                text_prediction = text_grid_search.predict([text_processed])[0]
            else:
                text_prediction = 0
            final_prediction = text_prediction
            if df is not None:
                similar_cases = df[df['text'] == text_processed]
                if not similar_cases.empty:
                    historical_flow = similar_cases['trafficflow'].mean()
                    final_prediction = (text_prediction + historical_flow) / 2
            traffic_status = "Smooth Traffic" if final_prediction < 0.5 else "Heavy Traffic"
            timestamp_ist = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO traffic_data (location, street_name, description, traffic_flow_prediction, timestamp) VALUES (?, ?, ?, ?, ?)",
                (location, street_name, description, traffic_status, timestamp_ist)
            )
            conn.commit()
            conn.close()
            return render_template('result.html',
                                   location=f"{location}, {street_name}",
                                   description=description,
                                   text_prediction=text_prediction,
                                   final_prediction=final_prediction,
                                   traffic_status=traffic_status,
                                   username=session.get('username'))
        except Exception as e:
            print("DEBUG: Error in entry:", e)
            error_message = "An unexpected error occurred. Please try again later."
    return render_template('entry.html', error_message=error_message, username=session.get('username'))

@app.route('/show', methods=['GET', 'POST'])
def show():
    data = None
    error_message = None
    if request.method == 'POST':
        location = request.form['location'].strip().lower()
        street_name = request.form.get('street_name', '').strip().lower()
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:
            if street_name:
                cursor.execute("SELECT * FROM traffic_data WHERE location=? AND street_name=? ORDER BY timestamp DESC LIMIT 5", (location, street_name))
            else:
                cursor.execute("SELECT * FROM traffic_data WHERE location=? ORDER BY timestamp DESC LIMIT 5", (location,))
            data = cursor.fetchall()
            if not data:
                error_message = "No data found for the specified location."
        except Exception as e:
            error_message = "An unexpected error occurred while retrieving data."
            print("SHOW ERROR:", e)
        finally:
            conn.close()
    return render_template('show.html', data=data, error_message=error_message)

# ---------------------------
# Routing app routes
# ---------------------------
@app.route('/routing')
def routing_page():
    return render_template('routing.html')

@app.route("/geocode", methods=["GET"])
def geocode():
    query = request.args.get("query")
    if not query:
        return jsonify({"results": []})
    url = f"https://api.tomtom.com/search/2/search/{requests.utils.requote_uri(query)}.json?typeahead=true&limit=5&key={TOMTOM_API_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({"results": []})
    data = resp.json()
    results = []
    for item in data.get("results", []):
        results.append({
            "address": {"freeformAddress": item["address"].get("freeformAddress")},
            "position": item.get("position")
        })
    return jsonify({"results": results})

@app.route('/get_routes', methods=['GET'])
def get_routes():
    start_lat = request.args.get('start_lat')
    start_lon = request.args.get('start_lon')
    end_lat = request.args.get('end_lat')
    end_lon = request.args.get('end_lon')
    if not all([start_lat, start_lon, end_lat, end_lon]):
        return jsonify({"routes": []})
    try:
        start_lat, start_lon, end_lat, end_lon = map(float, [start_lat, start_lon, end_lat, end_lon])
    except ValueError:
        return jsonify({"routes": []})
    url = (
        f"https://api.tomtom.com/routing/1/calculateRoute/"
        f"{start_lat},{start_lon}:{end_lat},{end_lon}/json"
        f"?key={TOMTOM_API_KEY}"
        f"&routeType=fastest"
        f"&traffic=true"
        f"&avoid=unpavedRoads"
        f"&travelMode=car"
        f"&maxAlternatives=3"
        f"&alternativeType=anyRoute"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({"routes": []})
    data = resp.json()
    routes = []
    if 'routes' in data:
        for route in data['routes']:
            points_list = []
            leg = route['legs'][0]
            if 'points' in leg:
                points_list = [{"lat": p['latitude'], "lon": p['longitude']} for p in leg['points']]
            elif 'shape' in leg:
                for s in leg['shape']:
                    lat, lon = map(float, s.split(','))
                    points_list.append({"lat": lat, "lon": lon})
            routes.append({
                "summary": {
                    "lengthInMeters": route['summary'].get('lengthInMeters'),
                    "travelTimeInSeconds": route['summary'].get('travelTimeInSeconds')
                },
                "legs": [{"points": points_list}]
            })
    return jsonify({"routes": routes})

@app.route('/reverse_geocode')
def reverse_geocode():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"address": None})
    url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json?key={TOMTOM_API_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({"address": f"{lat}, {lon}"})
    data = resp.json()
    address = None
    try:
        address = data['addresses'][0]['address'].get('freeformAddress')
    except Exception:
        address = f"{lat}, {lon}"
    return jsonify({"address": address})


# ---------------------------
# NEW: endpoint to return recent traffic prediction rows with lat/lon (geocoded on-the-fly)
# - Does NOT change DB schema
# - Returns a small set (default limit 50) of latest rows, with lat/lon obtained by calling TomTom search once per unique address.
# ---------------------------
@app.route('/get_predictions')
def get_predictions():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location, street_name, traffic_flow_prediction, timestamp
        FROM traffic_data
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()

    predictions = []
    seen = set()  # avoid duplicate locations

    for r in rows:
        location_name = f"{r[0]} {r[1]}".strip()
        if not location_name or location_name.lower() in seen:
            continue
        seen.add(location_name.lower())

        try:
            # Geocode using TomTom API (with fallback)
            geo_url = f"https://api.tomtom.com/search/2/geocode/{requests.utils.requote_uri(location_name + ', India')}.json?limit=1&countrySet=IN&key={TOMTOM_API_KEY}"
            resp = requests.get(geo_url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    pos = data["results"][0]["position"]
                    predictions.append({
                        "label": location_name.title(),
                        "prediction": r[2],
                        "timestamp": r[3],
                        "lat": pos.get("lat"),
                        "lon": pos.get("lon")
                    })
                else:
                    print(f"⚠️ No coordinates found for {location_name}")
            else:
                print(f"❌ Geocode failed for {location_name}")
        except Exception as e:
            print(f"Geocode error for {location_name}:", e)
            continue

    return jsonify({"predictions": predictions})


# ---------------------------
# Run app
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
