from flask import Flask, request, jsonify, render_template_string, redirect
import json
import math
import os

app = Flask(__name__)

CONFIG_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "latitude": 10.939019,
    "longitude": 76.958774,
    "radius": 500,
    "form_url": "https://forms.gle/xxMA8dKmayf6HP3A8"
}


def load_settings():
    if not os.path.exists(CONFIG_FILE):
        save_settings(DEFAULT_SETTINGS)

    with open(CONFIG_FILE, "r") as file:
        return json.load(file)


def save_settings(data):
    with open(CONFIG_FILE, "w") as file:
        json.dump(data, file, indent=4)


def calculate_distance(lat1, lon1, lat2, lon2):
    earth_radius = 6371000

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


ADMIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>GPS Admin Panel</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font-family: Arial; background:#edf2f7; padding:20px; }
.box { max-width:500px; margin:auto; background:white;
padding:25px; border-radius:12px; }
input { width:100%; padding:12px; margin:8px 0;
box-sizing:border-box; }
button { background:#2563eb; color:white; padding:12px;
border:0; width:100%; border-radius:6px; }
a { display:block; margin-top:20px; }
</style>
</head>
<body>
<div class="box">
<h2>Location Access Admin</h2>

<form method="POST" action="/save">
<label>Centre Latitude</label>
<input name="latitude" type="number" step="any"
value="{{ settings.latitude }}" required>

<label>Centre Longitude</label>
<input name="longitude" type="number" step="any"
value="{{ settings.longitude }}" required>

<label>Radius (metres)</label>
<input name="radius" type="number" min="1"
value="{{ settings.radius }}" required>

<label>Google Form URL</label>
<input name="form_url" type="url"
value="{{ settings.form_url }}" required>

<button type="submit">Save Settings</button>
</form>

<a href="/access">Open User Access Page</a>
</div>
</body>
</html>
"""


USER_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Google Form Location Access</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {
    font-family: Arial;
    background:#edf2f7;
    text-align:center;
    padding:30px 15px;
}
.box {
    background:white;
    padding:25px;
    max-width:420px;
    margin:auto;
    border-radius:12px;
}
button {
    background:#2563eb;
    color:white;
    padding:14px 22px;
    border:0;
    border-radius:7px;
    cursor:pointer;
}
#popup {
    display:none;
    position:fixed;
    inset:0;
    background:rgba(0,0,0,.6);
    justify-content:center;
    align-items:center;
}
.modal {
    background:white;
    padding:25px;
    border-radius:12px;
    width:80%;
    max-width:350px;
}
a {
    display:inline-block;
    padding:12px;
    background:#16a34a;
    color:white;
    text-decoration:none;
    border-radius:6px;
}
</style>
</head>

<body>
<div class="box">
<h2>Google Form Access</h2>
<p>Your location will be checked before access is granted.</p>
<button onclick="checkLocation()">Check My Location</button>
<p id="status"></p>
</div>

<div id="popup">
<div class="modal">
<h3 id="message"></h3>
<p id="details"></p>
<div id="action"></div>
<br>
<button onclick="closePopup()">Close</button>
</div>
</div>

<script>
function showPopup(message, details, action="") {
    document.getElementById("message").innerText = message;
    document.getElementById("details").innerText = details;
    document.getElementById("action").innerHTML = action;
    document.getElementById("popup").style.display = "flex";
}

function closePopup() {
    document.getElementById("popup").style.display = "none";
}

function checkLocation() {
    const status = document.getElementById("status");

    if (!navigator.geolocation) {
        showPopup("Not supported", "Your browser does not support GPS.");
        return;
    }

    status.innerText = "Checking your location...";

    navigator.geolocation.getCurrentPosition(
        async function(position) {
            try {
                const response = await fetch("/verify", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    })
                });

                const result = await response.json();
                status.innerText = "";

                if (result.allowed) {
                    showPopup(
                        "Access Granted!",
                        "You are within the permitted location.",
                        '<a href="/open-form">Open Google Form</a>'
                    );
                } else {
                    showPopup(
                        "Access Denied!",
                        "You are outside the permitted location."
                    );
                }
            } catch(error) {
                status.innerText = "Unable to verify location.";
            }
        },

        function(error) {
            showPopup(
                "Location Error",
                "Please allow location permission and try again."
            );
            status.innerText = "";
        },

        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return redirect("/access")


@app.route("/admin")
def admin():
    return render_template_string(
        ADMIN_PAGE,
        settings=load_settings()
    )


@app.route("/save", methods=["POST"])
def save():
    try:
        data = {
            "latitude": float(request.form["latitude"]),
            "longitude": float(request.form["longitude"]),
            "radius": float(request.form["radius"]),
            "form_url": request.form["form_url"].strip()
        }

        if not (-90 <= data["latitude"] <= 90):
            return "Invalid latitude", 400

        if not (-180 <= data["longitude"] <= 180):
            return "Invalid longitude", 400

        if data["radius"] <= 0:
            return "Radius must be positive", 400

        if not data["form_url"].startswith(
            "https://docs.google.com/forms/"
        ):
            return "Enter a valid Google Forms URL", 400

        save_settings(data)
        return redirect("/admin")

    except (ValueError, KeyError):
        return "Invalid settings", 400


@app.route("/access")
def access():
    return render_template_string(USER_PAGE)


@app.route("/verify", methods=["POST"])
def verify():
    try:
        user = request.get_json()
        settings = load_settings()

        user_lat = float(user["latitude"])
        user_lon = float(user["longitude"])

        if not (-90 <= user_lat <= 90):
            return jsonify({"allowed": False}), 400

        if not (-180 <= user_lon <= 180):
            return jsonify({"allowed": False}), 400

        distance = calculate_distance(
            settings["latitude"],
            settings["longitude"],
            user_lat,
            user_lon
        )

        allowed = distance <= settings["radius"]

        return jsonify({
            "allowed": allowed,
            "distance": round(distance)
        })

    except (TypeError, ValueError, KeyError):
        return jsonify({"allowed": False}), 400


@app.route("/open-form")
def open_form():
    # This route is a convenience redirect, not a secure
    # authorization boundary.
    return redirect(load_settings()["form_url"])


if __name__ == "__main__":
    load_settings()
    app.run(host="127.0.0.1", port=5000, debug=False)
