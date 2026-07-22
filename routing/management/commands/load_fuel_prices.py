import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from routing.models import FuelStation

DEFAULT_CSV = Path("data/fuel-prices.csv")


class Command(BaseCommand):
    help = "Load truckstop fuel prices from the OPIS CSV export into the database."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", nargs="?", default=str(DEFAULT_CSV))

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        with path.open(newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))

        stations = []
        skipped = 0
        for row in rows:
            try:
                stations.append(
                    FuelStation(
                        opis_id=int(row["OPIS Truckstop ID"]),
                        name=row["Truckstop Name"].strip(),
                        address=row["Address"].strip(),
                        city=row["City"].strip(),
                        state=row["State"].strip().upper(),
                        rack_id=int(row["Rack ID"]) if row["Rack ID"].strip() else None,
                        retail_price=row["Retail Price"].strip(),
                    )
                )
            except (KeyError, ValueError):
                skipped += 1

        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create(stations, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {len(stations)} stations"
                + (f" ({skipped} rows skipped)" if skipped else "")
            )
        )
