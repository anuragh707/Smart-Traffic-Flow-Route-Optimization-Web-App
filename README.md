# 🚦 Smart Traffic Flow & Route Optimization Web App

An intelligent web application that predicts real-time traffic conditions, visualizes traffic severity, and finds the best route using live geolocation data and machine learning models.  
It integrates the **TomTom Maps API**, **Random Forest ML models**, and a **FastAPI + Flask hybrid backend** to deliver accurate and interactive traffic insights.

---

## 🌟 Features

✅ **Real-Time Traffic Prediction**
- Predicts traffic severity (e.g., Heavy, Moderate, Light) using trained ML models.  
- Displays color-coded prediction markers on the map.

✅ **Smart Route Finder**
- Finds optimal routes between any two locations.
- Displays **multiple alternative routes**.
- Each route shows **📏 distance** and **⏱️ time (hours/mins)** in a tooltip.
- Users can click a route to highlight it visually.

✅ **Interactive Map Interface**
- Start and Destination markers have unique colors and icons:
  - 🟦 **Start:** `#00e5ff` (symbol: ➤)
  - 🩷 **Destination:** `#ff007f` (symbol: 🏁)
- Traffic prediction markers (orange/green glow) for live prediction view.
- Automatic map zoom and centering.

✅ **Geolocation Support**
- Users can set **current location** as start or destination.
- Uses **TomTom Geocoding & Routing APIs** for real-world data.

✅ **Legend Panel**
- Displays icons and color meaning for easy understanding.

---

## 🏗️ Project Structure

smart-traffic-app/
│
├── app.py # FastAPI + Flask unified backend
├── traffic_flow.db # SQLite database storing routes & predictions
├── requirements.txt # Python dependencies
│
├── static/
│ ├── script.js # Main frontend logic (Leaflet, TomTom integration)
│ └── style.css # UI and map styling
│
├── templates/
│ └── index.html # Main web interface
│
└── README.md # You are here


---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/smart-traffic-flow.git
cd smart-traffic-flow

2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Set Environment Variables

Create a .env file in the project root:

TOMTOM_API_KEY=your_tomtom_api_key_here

4️⃣ Run the Backend Server
python app.py


Server runs by default on:

http://127.0.0.1:8000

🗺️ Using the Application

Open your browser and navigate to http://127.0.0.1:8000.

Enter Start and Destination addresses.

Click Find Route — routes will appear on the map with live traffic visualization.

Optionally, click Refresh Predictions to see updated traffic data.

🧠 Technologies Used
Category	Technology
Frontend	Leaflet.js, OpenStreetMap, TomTom Maps API
Backend	FastAPI, Flask
Database	SQLite
Machine Learning	RandomForest (scikit-learn)
APIs	TomTom Routing, Geocoding, Reverse Geocoding
Language	Python, JavaScript
🧩 Future Enhancements

 Integrate weather-based traffic prediction

 Add user login & saved route history

 Add traffic incident reporting by users

 Display live ETA comparison between routes

👨‍💻 Developer

🚗 Passionate about smart mobility, data-driven solutions, and AI-powered traffic systems.

🪪 License

This project is licensed under the MIT License — free for educational and research use.

🧭 Demo Preview

🗺️ Multiple routes with color coding
🔹 Traffic severity markers
💡 Clean modern interface with real-time prediction refresh