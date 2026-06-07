from django.db import models


class Area(models.Model):
    area_id = models.IntegerField(primary_key=True)
    area_name = models.CharField(max_length=10)

    class Meta:
        db_table = "area"

    def __str__(self):
        return self.area_name


class OwnerType(models.Model):
    owner_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=10)

    class Meta:
        db_table = "owner_type"

    def __str__(self):
        return self.type


class ParkingLot(models.Model):
    lot_id = models.CharField(max_length=11, primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column="area_id")
    lot_name = models.CharField(max_length=50)
    data_type = models.IntegerField()
    owner_type = models.ForeignKey(
        OwnerType,
        on_delete=models.CASCADE,
        db_column="owner_type",
        default=8
    )
    addr = models.CharField(max_length=300)
    car_space = models.IntegerField()
    pregnancy_space = models.IntegerField(null=True, blank=True)
    handicap_space = models.IntegerField(null=True, blank=True)
    service_time = models.CharField(max_length=500, null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    charge = models.CharField(max_length=500)

    class Meta:
        db_table = "parking_lot"

    def __str__(self):
        return self.lot_name


class ParkingLotStatus(models.Model):
    lot = models.OneToOneField(
        ParkingLot,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="lot_id"
    )
    ava_car = models.IntegerField(null=True, blank=True)
    ava_handicap = models.IntegerField(null=True, blank=True)
    ava_pregnancy = models.IntegerField(null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "parking_lot_status"

    def __str__(self):
        return f"{self.lot_id} status"


class ParkingRateRule(models.Model):
    rule_id = models.AutoField(primary_key=True)
    lot = models.ForeignKey(
        ParkingLot,
        on_delete=models.CASCADE,
        db_column="lot_id"
    )
    day_mask = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    hourly_rate = models.IntegerField(null=True, blank=True)
    per_time_rate = models.IntegerField(null=True, blank=True)
    rate_text = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "parking_rate_rule"

    def __str__(self):
        return f"{self.lot_id} rule {self.rule_id}"


class RoadSide(models.Model):
    road_id = models.CharField(max_length=10, primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column="area_id")
    road_name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    geometry_wkt = models.TextField(null=True, blank=True)
    total_car = models.IntegerField()
    total_pregnancy = models.IntegerField()
    total_handicap = models.IntegerField()
    charge = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "road_side"

    def __str__(self):
        return self.road_name


class RoadSideStatus(models.Model):
    road = models.OneToOneField(
        RoadSide,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column="road_id"
    )
    ava_car = models.IntegerField(null=True, blank=True)
    ava_pregnancy = models.IntegerField(null=True, blank=True)
    ava_handicap = models.IntegerField(null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "road_side_status"

    def __str__(self):
        return f"{self.road_id} status"


class UpdateHistory(models.Model):
    his_id = models.AutoField(primary_key=True)
    data_type = models.CharField(max_length=11)
    source_name = models.CharField(max_length=50)
    status = models.CharField(max_length=11)
    note = models.CharField(max_length=50)
    update_time = models.DateTimeField()

    class Meta:
        db_table = "update_history"

    def __str__(self):
        return f"{self.source_name} - {self.status}"


class YellowLineReal(models.Model):
    yl_id = models.AutoField(primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column="area_id")
    road_name = models.CharField(max_length=500)
    direction = models.CharField(max_length=5)
    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)
    geometry_wkt = models.TextField(null=True, blank=True)
    standard_period = models.IntegerField(default=0)
    control_time = models.TextField(null=True, blank=True)
    holiday_time = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "yellow_line_real"

    def __str__(self):
        return self.road_name


class YellowLineTest(models.Model):
    yl_id = models.AutoField(primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, db_column="area_id")
    road_name = models.CharField(max_length=500)
    geometry_wkt = models.TextField(null=True, blank=True)
    control_time = models.TextField(null=True, blank=True)
    holiday_time = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "yellow_line_test"

    def __str__(self):
        return self.road_name
    
class AdminActionLog(models.Model):
    action_id = models.AutoField(primary_key=True)
    admin_username = models.CharField(max_length=150)
    action_type = models.CharField(max_length=20)
    target_table = models.CharField(max_length=50)
    target_id = models.CharField(max_length=50)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_action_log"

    def __str__(self):
        return f"{self.admin_username} {self.action_type} {self.target_id}"
