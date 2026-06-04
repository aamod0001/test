from django.db import models

class Blood(models.Model):
    type = models.CharField(max_length=50, primary_key=True, db_column='bloodtype')

    class Meta:
        db_table = 'blood'
        verbose_name_plural = 'Blood'

    def __str__(self):
        return self.type


class BloodBank(models.Model):
    blood_bank_id = models.AutoField(primary_key=True, db_column='blood_bank_id')
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    image_url = models.CharField(max_length=255, null=True, blank=True, db_column='image_url')
    address = models.CharField(max_length=255, null=True, blank=True)
    contact = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'blood_bank'

    def __str__(self):
        return self.name


class BloodAndBloodBank(models.Model):
    # Standard composite unique constraint in Django.
    # We define ForeignKey relations using target columns matching Spring Boot configurations.
    blood_bank = models.ForeignKey(BloodBank, on_delete=models.CASCADE, db_column='bloodbankid')
    blood = models.ForeignKey(Blood, on_delete=models.CASCADE, db_column='bloodtype')
    quantity = models.IntegerField()

    class Meta:
        db_table = 'blood_and_blood_bank'
        unique_together = (('blood_bank', 'blood'),)

    def __str__(self):
        return f"{self.blood_bank} - {self.blood} ({self.quantity})"


class BloodRequest(models.Model):
    URGENCY_CHOICES = [
        ('Normal', 'Normal'),
        ('Urgent', 'Urgent'),
        ('Critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Fulfilled', 'Fulfilled'),
    ]

    request_id = models.AutoField(primary_key=True, db_column='request_id')
    patient_name = models.CharField(max_length=100)
    blood_type = models.ForeignKey(Blood, on_delete=models.CASCADE, db_column='bloodtype')
    quantity_needed = models.IntegerField()
    hospital_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=50)
    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='Normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blood_request'

    def __str__(self):
        return f"{self.patient_name} - {self.blood_type} ({self.status})"

