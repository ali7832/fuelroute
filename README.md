# Fuel Route

A small Django API that plans the cheapest way to fuel a road trip across the US.
Give it a start and a finish; it returns the driving route, the fuel stops to make
along the way, and what the fuel will cost — assuming a 500-mile range and 10 MPG.

## How it works

A single request flows through four steps:

1. **Geocode** the start and finish with Nominatim (OpenStreetMap).
2. **Route** them with OSRM — one call returns the full geometry *and* the driving
   distance, so the routing service is hit exactly once per trip.
3. **Match** truckstops from the dataset against the route. Stations are pulled by
   a bounding box, then a vectorised nearest-vertex pass keeps the ones within a
   few miles of the road and places each one at its mile-marker along the route.
4. **Optimize** which stations to buy at. With prices known up front and a fixed
   tank, this is the classic gas-station problem; a look-ahead greedy finds the
   provably cheapest plan (see `routing/services/optimizer.py`).

Both upstreams are keyless, so a reviewer can run this without signing up for
anything. Point `OSRM_BASE_URL` / `NOMINATIM_BASE_URL` at other providers if you'd
rather use your own.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py load_fuel_prices          # loads data/fuel-prices.csv
python manage.py geocode_stations          # one-time; see note below
python manage.py runserver
```

### The geocoding step

The dataset identifies each truckstop only down to its city — there are no
coordinates in the file — so stations are geocoded to their city centre once and
cached. `geocode_stations` walks the ~3,900 unique cities, respects Nominatim's
one-request-per-second policy, and writes results to `data/geocode-cache.json`. It
is **resumable**: stop it any time and re-run to pick up where it left off. A full
first pass takes a while but only happens once.

For a quick look before committing to the full run:

```bash
python manage.py geocode_stations --limit 300   # geocode a first slice
```

Because stations sit at city granularity, the route-matching buffer is generous
(25 miles, configurable) so a station still counts even though its city centre is
some distance from the actual highway exit.

## API

### `POST /api/route/` (also accepts `GET` with query params)

```bash
curl -X POST http://localhost:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start": "Dallas, TX", "finish": "Denver, CO"}'
```

Response:

```json
{
  "start":  {"query": "Dallas, TX", "lat": 32.78, "lon": -96.80},
  "finish": {"query": "Denver, CO", "lat": 39.74, "lon": -104.99},
  "total_distance_miles": 781.4,
  "total_gallons": 78.14,
  "total_fuel_cost": 243.11,
  "fuel_stops": [
    {"mile_marker": 0.0, "name": "Departure fill-up (nearest station price)",
     "price_per_gallon": 3.11, "gallons": 50.0, "cost": 155.5},
    {"mile_marker": 470.2, "name": "PILOT TRAVEL CENTER #...", "city": "...",
     "state": "...", "price_per_gallon": 2.98, "gallons": 28.14, "cost": 83.86,
     "lat": 37.9, "lon": -103.1, "off_route_miles": 4.2}
  ],
  "map_url": "http://localhost:8000/api/route/map/?start=Dallas, TX&finish=Denver, CO"
}
```

### `GET /api/route/map/?start=...&finish=...`

An interactive Leaflet map (OpenStreetMap tiles) showing the route line, the start
and finish, and a marker for every fuel stop with its price and cost. The JSON
response's `map_url` links straight to it. Repeated calls for the same trip reuse a
cached plan, so opening the map right after the JSON call adds no extra routing
request.

## Assumptions

- **10 MPG, 500-mile range** per the brief (both overridable via env vars).
- The tank starts empty and you fill up before leaving, so the whole trip's fuel is
  purchased. The departure fill-up is priced at the first station on the route.
- Total gallons for a trip is therefore `distance / 10`, bought as cheaply as the
  range constraint allows.
- If any stretch of the route has no reachable station within 500 miles, the trip is
  reported as infeasible (HTTP 422) rather than guessed at.

## Design notes

- **One routing call per trip.** OSRM returns geometry and distance together, and
  planned results are cached by (start, finish), so the JSON and map endpoints share
  a single call.
- **Fast matching.** Candidate stations are narrowed by an indexed bounding-box
  query, then matched to the route in one vectorised numpy pass — no per-station API
  calls at request time.
- **Optimizer correctness.** The greedy is verified in the test suite against an
  independent fine-grained reference cost, and the API/planner paths are covered with
  the upstreams mocked.

## Tests

```bash
python manage.py test
```

## Layout

```
fuelroute/            project settings & urls
routing/
  services/
    geocoding.py      Nominatim client (cached)
    directions.py     OSRM client (one call -> geometry + distance)
    geometry.py       haversine, cumulative distance, route matching
    optimizer.py      gas-station problem solver
    planner.py        orchestration + result caching
  management/commands/
    load_fuel_prices.py
    geocode_stations.py
  views.py            JSON + map endpoints
  tests/
data/fuel-prices.csv  the provided dataset
```
