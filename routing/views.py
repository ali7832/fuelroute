import json
from urllib.parse import urlencode

import requests
from django.shortcuts import render
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TripRequestSerializer
from .services import directions, geocoding, planner
from .services.optimizer import RouteInfeasible


def _read_params(request):
    """Accept the trip on either a POST body or GET query string."""
    data = request.data if request.method == "POST" else request.query_params
    serializer = TripRequestSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _plan_or_error(start, finish):
    """Run the planner, translating service failures into HTTP responses."""
    try:
        return planner.plan_trip(start, finish), None
    except (geocoding.GeocodingError, RouteInfeasible) as exc:
        return None, Response(
            {"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    except directions.DirectionsError as exc:
        return None, Response(
            {"error": f"routing failed: {exc}"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except requests.RequestException as exc:
        return None, Response(
            {"error": f"upstream service unavailable: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


class RoutePlanView(APIView):
    """Plan the cheapest fuelling strategy between two US locations."""

    def get(self, request):
        return self._respond(request)

    def post(self, request):
        return self._respond(request)

    def _respond(self, request):
        params = _read_params(request)
        result, error = _plan_or_error(params["start"], params["finish"])
        if error is not None:
            return error

        payload = {k: v for k, v in result.items() if k != "route"}
        query = urlencode({"start": params["start"], "finish": params["finish"]})
        payload["map_url"] = request.build_absolute_uri(f"{reverse('route-map')}?{query}")
        return Response(payload)


def route_map(request):
    """Render the route and its fuel stops on an interactive Leaflet map."""
    serializer = TripRequestSerializer(data=request.GET)
    if not serializer.is_valid():
        return render(request, "routing/map.html", {"error": "start and finish are required"})

    data = serializer.validated_data
    result, error = _plan_or_error(data["start"], data["finish"])
    if error is not None:
        return render(request, "routing/map.html", {"error": error.data["error"]})

    return render(request, "routing/map.html", {"plan_json": json.dumps(result)})
