from rest_framework import serializers


class TripRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=255)
    finish = serializers.CharField(max_length=255)

    def validate_start(self, value):
        return value.strip()

    def validate_finish(self, value):
        return value.strip()
