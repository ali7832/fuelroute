# Fuel Route API

A Django REST API that plans the cheapest way to fuel a road trip across the US.
Give it a start and finish location; it returns the optimal fuel stops along the
driving route and the total cost — no guesswork, just the cheapest plan the data
supports.

---

## Live API

**Base URL:** `https://fuelroute-718272209757.us-central1.run.app`

Deployed on Google Cloud Run. No setup, no API key, no sign-up — just call it.

### Try it right now

**Plan a route:**
```bash
curl -X POST https://fuelroute-718272209757.us-central1.run.app/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "Chicago, IL", "finish": "Denver, CO"}'
```

**View the interactive map:**
```
https://fuelroute-718272209757.us-central1.run.app/api/route/map/?start=Chicago%2C+IL&finish=Denver%2C+CO
```

Or open any map URL returned in the `map_url` field of the JSON response.

---

## Endpoints

### `POST /api/route/`

Plan a fuel-optimal route between two US locations.

**Request body:**
```json
{
  "start": "Chicago, IL",
  "finish": "Denver, CO"
}
```

Also accepts `GET` with the same fields as query parameters.

**Response:**
```json
{
  "start":  { "query": "Chicago, IL", "lat": 41.875, "lon": -87.624 },
  "finish": { "query": "Denver, CO",  "lat": 39.739, "lon": -104.984 },
  "total_distance_miles": 1004.3,
  "total_gallons": 100.43,
  "total_fuel_cost": 292.06,
  "fuel_stops": [
    {
      "mile_marker": 0.0,
      "name": "Departure fill-up (nearest station price)",
      "price_per_gallon": 3.569,
      "gallons": 0.01,
      "cost": 0.03
    },
    {
      "mile_marker": 559.9,
      "name": "AKAL TRAVEL CENTER",
      "city": "Waco", "state": "NE",
      "price_per_gallon": 2.799,
      "gallons": 44.45,
      "cost": 124.41,
      "lat": 40.896, "lon": -97.463,
      "off_route_miles": 5.2
    }
  ],
  "map_url": "https://fuelroute-718272209757.us-central1.run.app/api/route/map/?start=Chicago%2C+IL&finish=Denver%2C+CO"
}
```

### `GET /api/route/map/`

Returns an interactive Leaflet map showing the driving route, start/finish markers,
and a clickable marker for every fuel stop with its price and cost breakdown.

```
/api/route/map/?start=Chicago%2C+IL&finish=Denver%2C+CO
```

---

## How it works

### The data problem
The provided CSV has ~8,150 US truckstops with city/state but **no coordinates**.
Addresses are highway-exit descriptions ("I-80, EXIT 143") — not geocodable cleanly.
The solution: geocode once at city level (~3,900 unique cities via Nominatim) and
store the results. At request time, zero station geocoding happens.

### Request flow — one routing API call per trip
1. **Geocode** the start and finish with Nominatim (OpenStreetMap, keyless).
2. **Route** with OSRM — one call returns the full driving geometry *and* distance.
3. **Match** stations to the route: indexed bounding-box DB query narrows candidates,
   then a vectorised numpy pass finds each station's nearest point on the route and
   filters by a 25-mile buffer (generous because stations sit at city centroids).
4. **Optimize** fuel stops: classic gas-station greedy with full price look-ahead —
   provably optimal when prices are known upfront.

Results are cached by `(start, finish)` so the JSON and map endpoints share one
OSRM call. Both external services are keyless — no API keys needed anywhere.

### Optimizer
With prices known and a fixed 500-mile tank, the look-ahead greedy is the optimal
strategy: coast to the next cheaper station if reachable, otherwise fill up and push
to the cheapest station within range. Verified against an independent fine-grained
reference cost model across 400 random routes — max error $0.03.

### Vehicle assumptions (per the brief)
- 500-mile range, 10 MPG
- Tank starts empty; the whole trip's fuel is purchased along the way
- Departure fill-up priced at the nearest station to the start point
- Trip is reported infeasible (HTTP 422) if any 500-mile stretch has no station

---

## Running locally

```bash
git clone https://github.com/ali7832/fuelroute.git
cd fuelroute
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata data/stations_fixture.json  # loads all 8,151 stations with coordinates
python manage.py runserver
```

The `stations_fixture.json` file includes the pre-geocoded coordinates so you don't
need to run the geocoding step (which takes ~65 minutes against Nominatim's
rate limit). The server is ready immediately after `loaddata`.

---

## Running with Docker

```bash
docker build -t fuelroute .
docker run -p 8080:8080 fuelroute
```

The image builds the database and loads all stations at build time, so the container
starts serving requests immediately with no further setup.

---

## Tests

```bash
python manage.py test
```

The test suite covers the optimizer, route geometry matching, the planner
orchestration layer, and the API endpoints. All external services (OSRM, Nominatim)
are mocked so tests run offline with no network dependency.

---

## Project layout

```
fuelroute/              Django project (settings, urls, wsgi)
routing/
  services/
    geocoding.py        Nominatim client with Django cache layer
    directions.py       OSRM client — one call returns geometry + distance
    geometry.py         Haversine, cumulative distance, vectorised route matching
    optimizer.py        Gas-station problem solver (look-ahead greedy)
    planner.py          Orchestration: geocode → route → match → optimize → cache
  management/commands/
    load_fuel_prices.py  Imports the provided CSV into SQLite
    geocode_stations.py  One-time city-level geocoding (resumable, rate-limited)
  views.py              JSON and Leaflet map endpoints
  tests/                Full test suite (optimizer, geometry, planner, API)
data/
  fuel-prices.csv       The provided dataset (8,151 OPIS truckstops)
  stations_fixture.json Pre-geocoded station data for instant local setup
Dockerfile              Production image (gunicorn, builds DB at image build time)
docker-compose.yml      Local Docker setup
```

---

## Deployment

The API is containerised with Docker and deployed on **Google Cloud Run** — fully
managed, scales to zero when idle, HTTPS out of the box.

Build and deploy from source (requires `gcloud` CLI):
```bash
gcloud run deploy fuelroute \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --timeout 300 \
  --memory 1Gi
```
