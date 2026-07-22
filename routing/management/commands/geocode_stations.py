import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from routing.models import FuelStation
from routing.services import geocoding

CACHE_PATH = Path("data/geocode-cache.json")

# Province codes that live north of the border; everything else geocodes as US.
CANADIAN = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}


class Command(BaseCommand):
    help = (
        "Geocode fuel stations to their city centre. Runs once; results are cached "
        "to disk so re-runs only pick up whatever is still missing. Nominatim asks "
        "for ~1 request/second, so a full pass takes a while but only happens once."
    )

    def add_arguments(self, parser):
        parser.add_argument("--sleep", type=float, default=1.0,
                            help="Delay between geocode calls (Nominatim policy: >=1s).")
        parser.add_argument("--limit", type=int, default=None,
                            help="Stop after N cities (handy for a quick smoke test).")

    def handle(self, *args, **options):
        cache = self._load_cache()

        cities = (
            FuelStation.objects.filter(latitude__isnull=True)
            .values_list("city", "state")
            .distinct()
            .order_by("state", "city")
        )
        pending = [c for c in cities if self._key(*c) not in cache]

        self.stdout.write(f"{len(pending)} cities to geocode "
                          f"({len(cache)} already cached)")

        done = 0
        for city, state in pending:
            if options["limit"] and done >= options["limit"]:
                break
            key = self._key(city, state)
            country = "ca" if state in CANADIAN else "us"
            try:
                lat, lon = geocoding.geocode(f"{city}, {state}", country=country)
                cache[key] = [lat, lon]
            except Exception as exc:  # noqa: BLE001 - log and move on, don't abort the batch
                cache[key] = None
                self.stderr.write(f"  {city}, {state}: {exc}")
            done += 1
            if done % 25 == 0:
                self._save_cache(cache)
                self.stdout.write(f"  ...{done} geocoded")
            time.sleep(options["sleep"])

        self._save_cache(cache)
        updated = self._apply(cache)
        self.stdout.write(self.style.SUCCESS(
            f"Geocoded {done} cities; updated coordinates on {updated} stations."
        ))

    def _apply(self, cache):
        updated = 0
        for (city, state), coords in [((k.split("|")[0], k.split("|")[1]), v)
                                      for k, v in cache.items()]:
            if not coords:
                continue
            updated += FuelStation.objects.filter(
                city__iexact=city, state__iexact=state, latitude__isnull=True
            ).update(latitude=coords[0], longitude=coords[1])
        return updated

    @staticmethod
    def _key(city, state):
        return f"{city.strip()}|{state.strip().upper()}"

    def _load_cache(self):
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text())
        return {}

    def _save_cache(self, cache):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=0))
