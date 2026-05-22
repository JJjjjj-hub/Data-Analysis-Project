from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


def _bad(message: str, *, code: str = "bad_request", status: int = 400) -> Response:
    return Response({"ok": False, "error": {"code": code, "message": message}}, status=status)


def _ok(payload: dict, *, status: int = 200) -> Response:
    return Response({"ok": True, **payload}, status=status)


@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([JSONParser])
def register(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username:
        return _bad("username 不能为空")
    if len(password) < 6:
        return _bad("password 至少 6 位")
    if User.objects.filter(username=username).exists():
        return _bad("用户名已存在", code="conflict", status=409)

    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return _ok({"token": token.key, "user": {"id": user.id, "username": user.username}}, status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([JSONParser])
def login(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user = authenticate(username=username, password=password)
    if user is None:
        return _bad("用户名或密码错误", code="unauthorized", status=401)
    token, _ = Token.objects.get_or_create(user=user)
    return _ok({"token": token.key, "user": {"id": user.id, "username": user.username}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return _ok({"message": "logged_out"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return _ok({"user": {"id": request.user.id, "username": request.user.username}})

