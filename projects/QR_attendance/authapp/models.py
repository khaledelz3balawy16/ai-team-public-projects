from django.db import models
from django.utils import timezone


def current_local_time():
    return timezone.localtime().time().replace(microsecond=0)


class AttendanceQR(models.Model):
    id = models.BigAutoField(primary_key=True, db_column='row_number')
    student_id = models.BigIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    group = models.CharField(max_length=255, db_column='module')
    other_group = models.CharField(max_length=255, blank=True, default='', db_column='second_module')
    second_module_reason = models.CharField(max_length=255, blank=True, default='')
    selected_group = models.CharField(max_length=255, blank=True, default='', db_column='selected_module')
    attendance_reason = models.CharField(max_length=50, blank=True, default='', db_column='selected_module_reason')
    date = models.DateTimeField(auto_now_add=True)
    time = models.TimeField(default=current_local_time)

    class Meta:
        db_table = 'attendance_QR'

    def __str__(self):
        return f"{self.name} - {self.email}"
