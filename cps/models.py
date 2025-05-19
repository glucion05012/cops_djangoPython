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

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Returned', 'Returned'),
        ('Rejected', 'Rejected'),
    ]

    brand = models.ForeignKey(ChainsawBrand, on_delete=models.CASCADE, related_name='imports')
    origin = models.CharField(max_length=255)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    submitted_at = models.DateTimeField(auto_now_add=True)
    date_applied = models.DateField(auto_now_add=True)
    crs_id = models.CharField(max_length=100)  # Required
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    estab_id_dniis = models.CharField(max_length=100)  # Required
    estab_name = models.CharField(max_length=255, blank=True, null=True)
    estab_address = models.TextField(blank=True, null=True)
    estab_email = models.EmailField(blank=True, null=True)
    estab_contact = models.CharField(max_length=50, blank=True, null=True)
    date_approved = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    evaluator_id = models.CharField(max_length=100)  # Required
    survey = models.TextField(blank=True, null=True)

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


class CHApplication(models.Model):
    date_created = models.DateTimeField(default=timezone.now)
    app_id = models.IntegerField()  # Required (not null)
    reference_no = models.CharField(max_length=100)
    forwarded_by_id = models.IntegerField()  # Required (not null)
    forwarded_to_id = models.IntegerField(null=True, blank=True)  # Optional
    action = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=50, default='pending')
    days_pending = models.IntegerField(default=0)

    class Meta:
        db_table = 'ch_application'

    def __str__(self):
        return f"{self.reference_no} - {self.status}"