from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
import json
from django.views.decorators.csrf import csrf_exempt
from .decorators import admin_required
from django.shortcuts import render
from django.http import JsonResponse
from .models import ParkingLot, Area, OwnerType, UpdateHistory, AdminActionLog
from django.forms.models import model_to_dict


@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Only POST allowed"
        }, status=405)

    data = json.loads(request.body)

    username = data.get("username")
    password = data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return JsonResponse({
            "status": "error",
            "message": "Invalid username or password"
        }, status=401)

    token, created = Token.objects.get_or_create(user=user)

    return JsonResponse({
        "status": "success",
        "token": token.key
    })

@admin_required
def test_admin_api(request):
    return JsonResponse({
        "status": "success",
        "message": "You are admin",
        "username": request.user.username
    })

def dashboard_page(request):
    return render(request, "api/dashboard.html")

def search_parking_lots(request):

    area = request.GET.get("area", "")
    keyword = request.GET.get("keyword", "")

    parking_lots = ParkingLot.objects.filter(
        area__area_name__icontains=area,
        lot_name__icontains=keyword
    )

    data = []

    for lot in parking_lots:

        data.append({
            "lot_id": lot.lot_id,
            "lot_name": lot.lot_name,
            "area": lot.area.area_name,
            "addr": lot.addr,
            "car_space": lot.car_space,
            "charge": lot.charge,
            "service_time": lot.service_time
        })

    return JsonResponse(data, safe=False)

@csrf_exempt
@admin_required
def delete_parking_lot(request, lot_id):
    if request.method != "DELETE":
        return JsonResponse({
            "status": "error",
            "message": "Only DELETE allowed"
        }, status=405)

    try:
        lot = ParkingLot.objects.get(lot_id=lot_id)
    except ParkingLot.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Parking lot not found"
        }, status=404)

    lot_name = lot.lot_name
    lot_id = lot.lot_id

    lot.delete()

    AdminActionLog.objects.create(
        admin_username=request.user.username,
        action_type="DELETE",
        target_table="parking_lot",
        target_id=lot_id,
        description=f"刪除停車場：{lot_name}"
    )

    return JsonResponse({
        "status": "success",
        "message": "Parking lot deleted"
    })

def login_page(request):
    return render(request, "api/login.html")

@csrf_exempt
@admin_required
def update_parking_lot(request, lot_id):
    if request.method != "PUT":
        return JsonResponse({
            "status": "error",
            "message": "Only PUT allowed"
        }, status=405)

    try:
        lot = ParkingLot.objects.get(lot_id=lot_id)
    except ParkingLot.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "Parking lot not found"
        }, status=404)

    data = json.loads(request.body)

    lot.lot_name = data.get("lot_name", lot.lot_name)
    lot.addr = data.get("addr", lot.addr)
    lot.car_space = data.get("car_space", lot.car_space)
    lot.charge = data.get("charge", lot.charge)
    lot.service_time = data.get("service_time", lot.service_time)

    lot.save()

    AdminActionLog.objects.create(
        admin_username=request.user.username,
        action_type="UPDATE",
        target_table="parking_lot",
        target_id=lot.lot_id,
        description=f"修改停車場：{lot.lot_name}"
    )

    return JsonResponse({
        "status": "success",
        "message": "Parking lot updated"
    })

@csrf_exempt
@admin_required
def create_parking_lot(request):

    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Only POST allowed"
        }, status=405)

    data = json.loads(request.body)

    required_fields = [
        "lot_id",
        "lot_name",
        "area",
        "addr",
        "car_space",
        "latitude",
        "longitude"
    ]

    for field in required_fields:
        if not data.get(field):
            return JsonResponse({
                "status": "error",
                "message": f"{field} 不可為空"
            }, status=400)

    if ParkingLot.objects.filter(lot_id=data["lot_id"]).exists():
        return JsonResponse({
            "status": "error",
            "message": "此停車場 ID 已存在"
        }, status=400)

    try:
        car_space = int(data["car_space"])
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])

        if car_space < 1:
            return JsonResponse({
                "status": "error",
                "message": "總車位必須大於 0"
            }, status=400)

    except ValueError:
        return JsonResponse({
            "status": "error",
            "message": "總車位、經緯度格式錯誤"
        }, status=400)

    try:
        area = Area.objects.get(
            area_name=data["area"]
        )

        owner_type = OwnerType.objects.first()

        if owner_type is None:
            return JsonResponse({
                "status": "error",
                "message": "請先在 OwnerType 新增至少一筆資料"
            }, status=400)

        lot = ParkingLot.objects.create(
            lot_id=data["lot_id"],
            area=area,
            lot_name=data["lot_name"],
            data_type=1,
            owner_type=owner_type,
            addr=data["addr"],
            car_space=car_space,
            pregnancy_space=0,
            handicap_space=0,
            service_time=data.get("service_time", ""),
            latitude=latitude,
            longitude=longitude,
            charge=data.get("charge", "")
        )

        AdminActionLog.objects.create(
            admin_username=request.user.username,
            action_type="CREATE",
            target_table="parking_lot",
            target_id=lot.lot_id,
            description=f"新增停車場：{lot.lot_name}"
        )

        return JsonResponse({
            "status": "success",
            "message": "Parking lot created"
        })

    except Exception as e:

        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=400)

@admin_required
def update_history_api(request):
    histories = UpdateHistory.objects.all().order_by("-update_time")[:100]

    data = []

    for h in histories:
        data.append({
            "his_id": h.his_id,
            "data_type": h.data_type,
            "status": h.status,
            "note": h.note,
            "update_time": h.update_time.strftime("%Y-%m-%d %H:%M:%S") if h.update_time else ""
        })

    return JsonResponse(data, safe=False)

@admin_required
def admin_action_logs_api(request):
    logs = AdminActionLog.objects.all().order_by("-created_at")[:100]

    data = []

    for log in logs:
        data.append({
            "action_id": log.action_id,
            "admin_username": log.admin_username,
            "action_type": log.action_type,
            "target_table": log.target_table,
            "target_id": log.target_id,
            "description": log.description,
            "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse(data, safe=False)

def area_list_api(request):

    areas = Area.objects.all().order_by("area_name")

    data = []

    for area in areas:
        data.append({
            "area_id": area.area_id,
            "area_name": area.area_name
        })

    return JsonResponse(data, safe=False)

def logs_page(request):
    return render(request, "api/logs.html")
