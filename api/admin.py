from django.contrib import admin
from .models import *


@admin.register(ParkingLot)
class ParkingLotAdmin(admin.ModelAdmin):
    list_display = (
        "lot_id",
        "lot_name",
        "area",
        "car_space",
        "available_spaces_display"
    )

    search_fields = (
        "lot_name",
        "addr"
    )

    list_filter = (
        "area",
    )

    def available_spaces_display(self, obj):
        try:
            return obj.parkinglotstatus.ava_car
        except:
            return None

    available_spaces_display.short_description = "Available Spaces"


@admin.register(RoadSide)
class RoadSideAdmin(admin.ModelAdmin):
    list_display = (
        "road_id",
        "road_name",
        "area",
        "total_car"
    )

    search_fields = (
        "road_name",
    )

    list_filter = (
        "area",
    )


@admin.register(UpdateHistory)
class UpdateHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "his_id",
        "source_name",
        "status",
        "update_time"
    )

    search_fields = (
        "source_name",
    )

    list_filter = (
        "status",
    )


admin.site.register(Area)
admin.site.register(OwnerType)
admin.site.register(ParkingLotStatus)
admin.site.register(ParkingRateRule)
admin.site.register(RoadSideStatus)
admin.site.register(YellowLineReal)
admin.site.register(YellowLineTest)
admin.site.register(AdminActionLog)
