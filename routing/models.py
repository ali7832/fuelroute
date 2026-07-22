from django.db import models


class FuelStation(models.Model):
    """A truckstop and its retail diesel price, loaded from the OPIS export.

    The source data only identifies a station down to its city, so geocoding
    happens at the city level and every station in the same city shares those
    coordinates. Latitude/longitude stay null until `geocode_stations` runs.
    """

    opis_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=8)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.DecimalField(max_digits=7, decimal_places=4)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["state", "city"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) ${self.retail_price}"
