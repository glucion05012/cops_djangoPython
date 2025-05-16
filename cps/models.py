from django.db import models
from django.utils import timezone

class ChainsawBrand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CHImport(models.Model):
    PURPOSE_CHOICES = [
        ('Distribution/Sale', 'Distribution / Sale'),
        ('Personal/Legal Use', 'Personal / Legal Use'),
    ]

    brand = models.ForeignKey(ChainsawBrand, on_delete=models.CASCADE, related_name='imports')
    origin = models.CharField(max_length=255)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Import #{self.id} - {self.brand.name}"


class CHImportModelDetail(models.Model):
    application = models.ForeignKey(CHImport, on_delete=models.CASCADE, related_name='model_details')
    model = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.model} - Qty: {self.quantity}"


class CHImportAttachment(models.Model):
    ATTACHMENT_TYPES = [
        ('dti_sec', 'DTI/SEC'),
        ('purchase_order', 'Purchase Order'),
        ('affidavit', 'Affidavit'),
        ('geotag_photo', 'Geotag Photo'),
    ]

    application = models.ForeignKey('CHImport', on_delete=models.CASCADE, related_name='attachments')
    name = models.CharField(max_length=255)
    file_location = models.CharField(max_length=500)
    date_uploaded = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES)

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"
