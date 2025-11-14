// ----- Map setup -----
let map = L.map('map').setView([20.5937, 78.9629], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

let startCoord = null;
let endCoord = null;
let routeLines = [];
let startMarker = null;
let endMarker = null;

// colors for multiple routes
const ROUTE_COLORS = ['rgba(8, 72, 28, 1)', '#2ca02c', '#9467bd', '#d62728'];

// ---------------- Helpers ----------------
async function geocodeOnce(query) {
    if (!query) return null;
    const res = await fetch(`/geocode?query=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (data && data.results && data.results.length > 0) {
        return {
            coord: data.results[0].position,
            label: data.results[0].address.freeformAddress
        };
    }
    return null;
}

async function fetchSuggestions(query) {
    if (!query) return [];
    const response = await fetch(`/geocode?query=${encodeURIComponent(query)}`);
    const data = await response.json();
    return data.results || [];
}

// suggestions rendering
function showSuggestions(results, listEl, inputEl, isStart) {
    listEl.innerHTML = '';
    if (!results.length) { listEl.style.display = 'none'; return; }
    listEl.style.display = 'block';
    results.forEach(place => {
        const li = document.createElement('li');
        li.textContent = place.address.freeformAddress;
        li.addEventListener('click', () => {
            inputEl.value = place.address.freeformAddress;
            listEl.innerHTML = '';
            listEl.style.display = 'none';
            if (isStart) {
                startCoord = place.position;
                updateMarker(true, startCoord, place.address.freeformAddress);
            } else {
                endCoord = place.position;
                updateMarker(false, endCoord, place.address.freeformAddress);
            }
        });
        listEl.appendChild(li);
    });
}

function attachSearch(inputId, suggestionsId, isStart) {
    const inputEl = document.getElementById(inputId);
    const listEl = document.getElementById(suggestionsId);
    let debounceTimer = null;
    inputEl.addEventListener('input', () => {
        const q = inputEl.value.trim();
        if (isStart) startCoord = null; else endCoord = null;
        if (debounceTimer) clearTimeout(debounceTimer);
        if (q.length < 2) { listEl.innerHTML=''; listEl.style.display='none'; return; }
        debounceTimer = setTimeout(async () => {
            const results = await fetchSuggestions(q);
            inputEl.dataset.results = JSON.stringify(results);
            showSuggestions(results, listEl, inputEl, isStart);
        }, 200);
    });

    inputEl.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const q = inputEl.value.trim(); let picked = null;
            try {
                const results = JSON.parse(inputEl.dataset.results || '[]');
                if (results.length > 0) {
                    const best = results[0];
                    inputEl.value = best.address.freeformAddress;
                    picked = best.position;
                }
            } catch(_) {}
            if (!picked && q) {
                const geo = await geocodeOnce(q);
                if (geo) { inputEl.value = geo.label; picked = geo.coord; }
            }
            listEl.innerHTML=''; listEl.style.display='none';
            if (picked) {
                if (isStart) { startCoord = picked; updateMarker(true, startCoord, inputEl.value); }
                else { endCoord = picked; updateMarker(false, endCoord, inputEl.value); }
            } else {
                if (isStart) startCoord = null; else endCoord = null;
            }
        }
        if (e.key === 'Escape') { listEl.innerHTML=''; listEl.style.display='none'; }
    });

    document.addEventListener('click', (evt) => {
        if (!listEl.contains(evt.target) && evt.target !== inputEl) {
            listEl.innerHTML=''; listEl.style.display='none';
        }
    });
}

attachSearch('start', 'start-suggestions', true);
attachSearch('end', 'end-suggestions', false);

// ---------------- markers (Only visual update) ----------------
function createCustomMarkerIcon(color, emoji) {
    return L.divIcon({
        className: 'custom-marker',
        html: `<div style="
            background-color:${color};
            width:20px;height:20px;border-radius:50%;
            border:2px solid #fff;
            box-shadow:0 0 8px ${color};
            display:flex;align-items:center;justify-content:center;
            font-size:14px;color:white;
        ">${emoji}</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });
}

function updateMarker(isStart, coord, label) {
    if (!coord) return;
    const lat = coord.lat || coord.latitude || coord[0];
    const lon = coord.lon || coord.longitude || coord[1];

    if (isStart) {
        if (startMarker)
            startMarker.setLatLng([lat, lon]).bindTooltip(label, { permanent: true, direction: 'top' });
        else
            startMarker = L.marker([lat, lon], {
                icon: createCustomMarkerIcon('#00e5ff', '➤'),
                title: label,
                zIndexOffset: 300
            }).addTo(map)
              .bindTooltip(label, { permanent: true, direction: 'top' })
              .bringToFront();
    } else {
        if (endMarker)
            endMarker.setLatLng([lat, lon]).bindTooltip(label, { permanent: true, direction: 'top' });
        else
            endMarker = L.marker([lat, lon], {
                icon: createCustomMarkerIcon('#ff007f', '🏁'),
                title: label,
                zIndexOffset: 300
            }).addTo(map)
              .bindTooltip(label, { permanent: true, direction: 'top' })
              .bringToFront();
    }

    const bounds = [];
    if (startMarker) bounds.push(startMarker.getLatLng());
    if (endMarker) bounds.push(endMarker.getLatLng());
    if (bounds.length) map.fitBounds(bounds, { padding: [60, 60] });
}

async function resolveCoordsOnSubmit() {
    const startText = document.getElementById('start').value.trim();
    const endText = document.getElementById('end').value.trim();
    if ((!startCoord || !startCoord.lat || !startCoord.lon) && startText) {
        const geo = await geocodeOnce(startText);
        if (geo) { startCoord = geo.coord; updateMarker(true, startCoord, geo.label); }
    }
    if ((!endCoord || !endCoord.lat || !endCoord.lon) && endText) {
        const geo = await geocodeOnce(endText);
        if (geo) { endCoord = geo.coord; updateMarker(false, endCoord, geo.label); }
    }
}

// ---------------- routing/drawing ----------------
function clearRoutes() {
    routeLines.forEach(o => {
        if (o.polyline) map.removeLayer(o.polyline);
    });
    routeLines = [];
    document.getElementById('routes-list').innerHTML = '';
}

async function findRoute() {
    await resolveCoordsOnSubmit();
    if (!startCoord || !endCoord) { 
        alert('Please enter valid start and end locations!'); 
        return; 
    }

    const sLat = startCoord.lat || startCoord.latitude;
    const sLon = startCoord.lon || startCoord.longitude;
    const eLat = endCoord.lat || endCoord.latitude;
    const eLon = endCoord.lon || endCoord.longitude;

    const url = `/get_routes?start_lat=${sLat}&start_lon=${sLon}&end_lat=${eLat}&end_lon=${eLon}`;
    const res = await fetch(url);
    const data = await res.json();

    clearRoutes();

    if (!data.routes || data.routes.length === 0) {
        alert('No routes found.');
        return;
    }

    // 🕓 Helper: Convert seconds → "Xh Ym" format
    function formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        if (h > 0) return `${h}h ${m}m`;
        return `${m}m`;
    }

    data.routes.forEach((route, idx) => {
        const coords = route.legs[0].points.map(p => [p.lat, p.lon]);
        const color = ROUTE_COLORS[idx % ROUTE_COLORS.length];
        const weight = (idx === 0) ? 6 : 4;

        const poly = L.polyline(coords, { color, weight, opacity: 0.9 }).addTo(map);

        const distKm = (route.summary.lengthInMeters / 1000).toFixed(2);
        const timeFormatted = formatTime(route.summary.travelTimeInSeconds);
        const tooltipText = `Distance: ${distKm} km · ${timeFormatted}`;
        poly.bindTooltip(tooltipText, { sticky: true, direction: 'center' });

        poly.on('mouseover', () => poly.setStyle({ weight: weight + 2 }));
        poly.on('mouseout', () => {
            const isSelected = routeLines.some(r => r.idx === idx && r.selected);
            poly.setStyle({ weight: isSelected ? weight + 2 : weight });
        });

        routeLines.push({ polyline: poly, idx, summary: route.summary, selected: idx === 0 });

        const li = document.createElement('li');
        li.textContent = `Route ${idx + 1}: ${distKm} km · ${timeFormatted}`;
        li.addEventListener('click', () => {
            routeLines.forEach(r => {
                r.selected = false;
                r.polyline.setStyle({ color: ROUTE_COLORS[r.idx % ROUTE_COLORS.length], weight: 4 });
            });
            const found = routeLines.find(r => r.idx === idx);
            if (found) {
                found.selected = true;
                found.polyline.setStyle({ color: '#0609c5ff', weight: 7, opacity: 1 });
                map.fitBounds(found.polyline.getBounds(), { padding: [60, 60] });
            }
        });
        document.getElementById('routes-list').appendChild(li);

        if (idx === 0) poly.setStyle({ color: '#0609c5ff', weight: 7 });
    });

    if (routeLines.length) map.fitBounds(routeLines[0].polyline.getBounds(), { padding: [60, 60] });
    if (startMarker) startMarker.bringToFront();
    if (endMarker) endMarker.bringToFront();
}


document.getElementById('find-route').addEventListener('click', findRoute);
['start', 'end'].forEach(id => {
    document.getElementById(id).addEventListener('keydown', (e) => {
        if (e.key === 'Enter') findRoute();
    });
});

// ---------------- Use My Location ----------------
function setMyLocation(inputId, isStart) {
    if (!navigator.geolocation) return alert("Geolocation not supported.");
    navigator.geolocation.getCurrentPosition(async (pos) => {
        const lat = pos.coords.latitude; const lon = pos.coords.longitude;
        try {
            const res = await fetch(`/reverse_geocode?lat=${lat}&lon=${lon}`);
            const data = await res.json();
            const placeName = data.address || `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
            document.getElementById(inputId).value = placeName;
            if (isStart) { startCoord = { lat, lon }; updateMarker(true, startCoord, placeName); }
            else { endCoord = { lat, lon }; updateMarker(false, endCoord, placeName); }
        } catch (err) {
            console.error(err);
        }
    }, (err) => {
        alert("Unable to fetch location."); console.error(err);
    }, { enableHighAccuracy: true, timeout: 10000 });
}

document.getElementById("use-my-location-start").addEventListener("click", () => setMyLocation("start", true));
document.getElementById("use-my-location-end").addEventListener("click", () => setMyLocation("end", false));

// ---------------- Predicted traffic markers ----------------
let predictionMarkers = [];

function createPredictionIcon(isHeavy) {
    const color = isHeavy ? 'rgba(255,80,0,0.9)' : 'rgba(50,200,50,0.9)';
    const shadow = isHeavy ? 'rgba(255,120,0,0.7)' : 'rgba(80,255,80,0.5)';
    return L.divIcon({
        html: `<div style="
            width:16px;height:16px;border-radius:50%;
            background:${color};
            border:2px solid #fff;
            box-shadow:0 0 12px ${shadow}, inset 0 0 6px rgba(255,255,255,0.15);
            "></div>`,
        className: '',
        iconSize: [16,16],
        iconAnchor: [8,8]
    });
}

async function showPredictions() {
    predictionMarkers.forEach(m => map.removeLayer(m));
    predictionMarkers = [];

    try {
        const res = await fetch('/get_predictions?limit=50');
        const data = await res.json();
        if (!data.predictions) return;

        data.predictions.forEach(p => {
            if (!p.lat || !p.lon) return;
            const heavy = (p.prediction || '').toLowerCase().includes('heavy');

            // offset & z-index to avoid overlap
            const offsetLat = p.lat + (Math.random() - 0.5) * 0.0005;
            const offsetLon = p.lon + (Math.random() - 0.5) * 0.0005;

            const marker = L.marker([offsetLat, offsetLon], {
                icon: createPredictionIcon(heavy),
                title: p.label,
                zIndexOffset: heavy ? 200 : 150
            }).addTo(map)
              .bindTooltip(`<b>${p.label}</b><br>${p.prediction}<br><small>${p.timestamp}</small>`);
            predictionMarkers.push(marker);
        });
    } catch (err) {
        console.error('Prediction load failed', err);
    }
}

document.getElementById('refresh-predictions')?.addEventListener('click', showPredictions);
showPredictions();
