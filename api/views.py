from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
import json
import re
from django.views.decorators.csrf import csrf_exempt
from .decorators import admin_required
from django.shortcuts import render
from django.db import connection, transaction # 🚀 引入原生資料庫連線與事務核心
import datetime
from .models import ParkingLot, Area, OwnerType, UpdateHistory, AdminActionLog, ParkingRateRule

@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON format"}, status=400)

    username = data.get("username")
    password = data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return JsonResponse({"status": "error", "message": "Invalid username or password"}, status=401)

    token, created = Token.objects.get_or_create(user=user)
    return JsonResponse({"status": "success", "token": token.key})


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
        rules_qs = ParkingRateRule.objects.filter(lot=lot)
        rules_list = []
        for rule in rules_qs:
            rules_list.append({
                "rule_id": rule.rule_id,
                "day_mask": rule.day_mask,
                "start_time": rule.start_time.strftime("%H:%M") if rule.start_time else "00:00",
                "end_time": rule.end_time.strftime("%H:%M") if rule.end_time else "23:59",
                "hourly_rate": rule.hourly_rate,
                "per_time_rate": rule.per_time_rate,
                "rate_text": rule.rate_text
            })
        data.append({
            "lot_id": lot.lot_id,
            "lot_name": lot.lot_name,
            "area": lot.area.area_name,
            "addr": lot.addr,
            "car_space": lot.car_space,
            "charge": lot.charge,
            "service_time": lot.service_time,
            "rate_rules": rules_list
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
@admin_required
def delete_parking_lot(request, lot_id):
    if request.method != "DELETE":
        return JsonResponse({"status": "error", "message": "Only DELETE allowed"}, status=405)

    try:
        lot = ParkingLot.objects.get(lot_id=lot_id)
    except ParkingLot.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Parking lot not found"}, status=404)

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
    return JsonResponse({"status": "success", "message": "Parking lot deleted"})


def login_page(request):
    return render(request, "api/login.html")


@csrf_exempt
@admin_required
def update_parking_lot(request, lot_id):
    if request.method != "PUT":
        return JsonResponse({"status": "error", "message": "Only PUT allowed"}, status=405)

    try:
        lot = ParkingLot.objects.get(lot_id=lot_id)
    except ParkingLot.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Parking lot not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "非法的 JSON 格式"}, status=400)

    # 🚀【修改防線：防空值與格式驗證】
    new_name = data.get("lot_name", lot.lot_name).strip()
    new_addr = data.get("addr", lot.addr).strip()
    new_charge = data.get("charge", lot.charge).strip()
    new_service_time = data.get("service_time", lot.service_time).strip()

    if not new_name or not new_addr:
        return JsonResponse({"status": "error", "message": "停車場名稱或地址不可修改為空"}, status=400)
        
    if len(new_name) > 100 or len(new_addr) > 200:
        return JsonResponse({"status": "error", "message": "修改的文字內容長度超出極限"}, status=400)

    # 費率規則驗證
    rate_rules = data.get("rate_rules")
    validated_rules = []
    if rate_rules is not None:
        if not rate_rules:
            return JsonResponse({"status": "error", "message": "必須填寫至少一個費率規則"}, status=400)

        for index, rule in enumerate(rate_rules):
            day_mask = rule.get("day_mask")
            start_time_str = rule.get("start_time")
            end_time_str = rule.get("end_time")
            hourly_rate_val = rule.get("hourly_rate")
            per_time_rate_val = rule.get("per_time_rate")
            rate_text_val = rule.get("rate_text", "")

            # 1. 驗證 day_mask
            try:
                day_mask = int(day_mask)
                if not (1 <= day_mask <= 127):
                    raise ValueError()
            except (TypeError, ValueError):
                return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的適用星期格式錯誤"}, status=400)

            # 2. 驗證開始與結束時間
            try:
                if len(start_time_str.split(':')) == 2:
                    start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
                else:
                    start_time = datetime.datetime.strptime(start_time_str, "%H:%M:%S").time()
                    
                if len(end_time_str.split(':')) == 2:
                    end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
                else:
                    end_time = datetime.datetime.strptime(end_time_str, "%H:%M:%S").time()
            except (TypeError, ValueError, AttributeError):
                return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的開始或結束時間格式錯誤，必須為 HH:MM 或 HH:MM:SS"}, status=400)

            # 3. 驗證費率
            try:
                if hourly_rate_val is not None and str(hourly_rate_val).strip() != "":
                    hourly_rate = int(hourly_rate_val)
                    if hourly_rate < 0:
                        return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的每小時費率不能為負數"}, status=400)
                else:
                    hourly_rate = 0
            except ValueError:
                return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的每小時費率格式錯誤"}, status=400)

            try:
                if per_time_rate_val is not None and str(per_time_rate_val).strip() != "":
                    per_time_rate = int(per_time_rate_val)
                    if per_time_rate < 0:
                        return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的計次費率不能為負數"}, status=400)
                else:
                    per_time_rate = 0
            except ValueError:
                return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的計次費率格式錯誤"}, status=400)

            if rate_text_val and len(rate_text_val) > 255:
                rate_text_val = rate_text_val[:255]

            validated_rules.append({
                "day_mask": day_mask,
                "start_time": start_time,
                "end_time": end_time,
                "hourly_rate": hourly_rate,
                "per_time_rate": per_time_rate,
                "rate_text": rate_text_val
            })

    try:
        with transaction.atomic():
            lot.lot_name = new_name
            lot.addr = new_addr
            lot.charge = new_charge
            lot.service_time = new_service_time
            
            if "car_space" in data:
                new_space = int(data["car_space"])
                if new_space < 1:
                    return JsonResponse({"status": "error", "message": "總車位必須大於 0"}, status=400)
                lot.car_space = new_space

            lot.save()

            if rate_rules is not None:
                with connection.cursor() as cursor:
                    # 1. 刪除原有費率規則
                    cursor.execute("DELETE FROM parking_rate_rule WHERE lot_id = %s", [lot.lot_id])
                    
                    # 2. 插入新費率規則
                    insert_rule_sql = """
                        INSERT INTO parking_rate_rule (
                            lot_id, day_mask, start_time, end_time, hourly_rate, per_time_rate, rate_text
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    for rule in validated_rules:
                        cursor.execute(insert_rule_sql, [
                            lot.lot_id,
                            rule["day_mask"],
                            rule["start_time"].strftime("%H:%M:%S"),
                            rule["end_time"].strftime("%H:%M:%S"),
                            rule["hourly_rate"],
                            rule["per_time_rate"],
                            rule["rate_text"]
                        ])

        desc = f"修改停車場：{lot.lot_name}"
        if rate_rules is not None:
            desc += f"，並更新為 {len(validated_rules)} 筆費率規則"

        AdminActionLog.objects.create(
            admin_username=request.user.username,
            action_type="UPDATE",
            target_table="parking_lot",
            target_id=lot.lot_id,
            description=desc
        )
        return JsonResponse({"status": "success", "message": "Parking lot updated successfully"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@csrf_exempt
@admin_required
def create_parking_lot(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "非法的 JSON 格式"}, status=400)

    required_fields = ["lot_id", "lot_name", "area", "addr", "car_space", "latitude", "longitude", "owner_type"]
    for field in required_fields:
        if not data.get(field) or str(data.get(field)).strip() == "":
            return JsonResponse({"status": "error", "message": f"{field} 不可為空或純空白"}, status=400)

    if not re.match(r"^TPE\d+$", data["lot_id"]):
        return JsonResponse({
            "status": "error", 
            "message": "❌ 停車場 ID 格式錯誤！必須以大寫 'TPE' 開頭並緊跟數字（例如：TPE0001）"
        }, status=400)

    if ParkingLot.objects.filter(lot_id=data["lot_id"]).exists():
        return JsonResponse({"status": "error", "message": "此停車場 ID 已存在"}, status=400)

    try:
        car_space = int(data["car_space"])
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])

        owner_type_val = int(data["owner_type"])
        if not (1 <= owner_type_val <= 7):
            return JsonResponse({"status": "error", "message": "營業單位類型必須在 1 至 7 之間"}, status=400)

        # 🛡️ 台灣地理物理邊界防禦機制
        if not (21.0 <= latitude <= 26.0) or not (119.0 <= longitude <= 123.0):
            return JsonResponse({"status": "error", "message": "經緯度超出台灣合理邊界範圍！"}, status=400)
            
        if car_space < 1:
            return JsonResponse({"status": "error", "message": "總車位必須大於 0"}, status=400)

    except ValueError:
        return JsonResponse({"status": "error", "message": "總車位或經緯度格式錯誤"}, status=400)

    if len(data["lot_name"]) > 100 or len(data["addr"]) > 200 or len(data["lot_id"]) > 20:
        return JsonResponse({"status": "error", "message": "字串長度過長，已超出欄位極限！"}, status=400)

    # 費率規則驗證
    rate_rules = data.get("rate_rules", [])
    if not rate_rules:
        return JsonResponse({"status": "error", "message": "必須填寫至少一個費率規則"}, status=400)

    validated_rules = []
    for index, rule in enumerate(rate_rules):
        day_mask = rule.get("day_mask")
        start_time_str = rule.get("start_time")
        end_time_str = rule.get("end_time")
        hourly_rate_val = rule.get("hourly_rate")
        per_time_rate_val = rule.get("per_time_rate")
        rate_text_val = rule.get("rate_text", "")

        # 1. 驗證 day_mask
        try:
            day_mask = int(day_mask)
            if not (1 <= day_mask <= 127):
                raise ValueError()
        except (TypeError, ValueError):
            return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的適用星期格式錯誤"}, status=400)

        # 2. 驗證開始與結束時間
        try:
            if len(start_time_str.split(':')) == 2:
                start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
            else:
                start_time = datetime.datetime.strptime(start_time_str, "%H:%M:%S").time()
                
            if len(end_time_str.split(':')) == 2:
                end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
            else:
                end_time = datetime.datetime.strptime(end_time_str, "%H:%M:%S").time()
        except (TypeError, ValueError, AttributeError):
            return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的開始或結束時間格式錯誤，必須為 HH:MM 或 HH:MM:SS"}, status=400)

        # 3. 驗證費率
        try:
            if hourly_rate_val is not None and str(hourly_rate_val).strip() != "":
                hourly_rate = int(hourly_rate_val)
                if hourly_rate < 0:
                    return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的每小時費率不能為負數"}, status=400)
            else:
                hourly_rate = 0
        except ValueError:
            return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的每小時費率格式錯誤"}, status=400)

        try:
            if per_time_rate_val is not None and str(per_time_rate_val).strip() != "":
                per_time_rate = int(per_time_rate_val)
                if per_time_rate < 0:
                    return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的計次費率不能為負數"}, status=400)
            else:
                per_time_rate = 0
        except ValueError:
            return JsonResponse({"status": "error", "message": f"第 {index+1} 個費率規則的計次費率格式錯誤"}, status=400)

        if rate_text_val and len(rate_text_val) > 255:
            rate_text_val = rate_text_val[:255]

        validated_rules.append({
            "day_mask": day_mask,
            "start_time": start_time,
            "end_time": end_time,
            "hourly_rate": hourly_rate,
            "per_time_rate": per_time_rate,
            "rate_text": rate_text_val
        })

    try:
        area = Area.objects.get(area_name=data["area"])
        owner_type = OwnerType.objects.first()

        if owner_type is None:
            return JsonResponse({"status": "error", "message": "請先在 OwnerType 新增至少一筆資料"}, status=400)

        # 使用 transaction.atomic 確保停車場與費率規則的資料完整性
        with transaction.atomic():
            # 🚀【黃金優化突破點：免 GDAL 原生 SQL 幾何寫入】
            with connection.cursor() as cursor:
                insert_sql = """
                    INSERT INTO parking_lot (
                        lot_id, area_id, lot_name, data_type, owner_type, addr, 
                        car_space, pregnancy_space, handicap_space, service_time, 
                        latitude, longitude, charge
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, %s, %s
                    )
                """
                cursor.execute(insert_sql, [
                    data["lot_id"], area.area_id, data["lot_name"].strip(), 1, owner_type_val, data["addr"].strip(),
                    car_space, 0, 0, data.get("service_time", "").strip(),
                    latitude, longitude, data.get("charge", "").strip(),
                ])

                # 插入費率規則
                insert_rule_sql = """
                    INSERT INTO parking_rate_rule (
                        lot_id, day_mask, start_time, end_time, hourly_rate, per_time_rate, rate_text
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                """
                for rule in validated_rules:
                    cursor.execute(insert_rule_sql, [
                        data["lot_id"],
                        rule["day_mask"],
                        rule["start_time"].strftime("%H:%M:%S"),
                        rule["end_time"].strftime("%H:%M:%S"),
                        rule["hourly_rate"],
                        rule["per_time_rate"],
                        rule["rate_text"]
                    ])

        AdminActionLog.objects.create(
            admin_username=request.user.username,
            action_type="CREATE",
            target_table="parking_lot",
            target_id=data["lot_id"],
            description=f"新增停車場：{data['lot_name']}，並登記 {len(validated_rules)} 筆費率規則"
        )
        return JsonResponse({"status": "success", "message": "Parking lot created successfully"})

    except Area.DoesNotExist:
        return JsonResponse({"status": "error", "message": f"找不到行政區：{data['area']}"}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


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
