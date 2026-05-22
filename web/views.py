from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

def home(request):
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173/")
    accept = request.headers.get("Accept", "")
    if "text/html" in accept or "*/*" in accept:
        return HttpResponseRedirect(frontend_url)
    return JsonResponse({"ok": True, "message": "API server running", "frontend_url": frontend_url})
