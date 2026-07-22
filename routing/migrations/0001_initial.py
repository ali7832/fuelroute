from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FuelStation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opis_id", models.IntegerField()),
                ("name", models.CharField(max_length=255)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(max_length=120)),
                ("state", models.CharField(max_length=8)),
                ("rack_id", models.IntegerField(blank=True, null=True)),
                ("retail_price", models.DecimalField(decimal_places=4, max_digits=7)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="fuelstation",
            index=models.Index(fields=["latitude", "longitude"], name="routing_fue_latitud_ffb9f2_idx"),
        ),
        migrations.AddIndex(
            model_name="fuelstation",
            index=models.Index(fields=["state", "city"], name="routing_fue_state_1d3a7e_idx"),
        ),
    ]
