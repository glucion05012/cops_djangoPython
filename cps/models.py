from django.db import models
from django.utils import timezone

class ChainsawBrand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ChainsawModel(models.Model):
    brand = models.ForeignKey(ChainsawBrand, on_delete=models.CASCADE, related_name='models')
    model_name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)

    class Meta:
        unique_together = ('brand', 'model_name')  # optional: to prevent duplicate model names for the same brand

    def __str__(self):
        return f"{self.brand.name} - {self.model_name}"

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
    supplier = models.CharField(max_length=255, blank=True, null=True)      # Supplier
    address = models.CharField(max_length=255, blank=True, null=True)       # Address
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
    evaluator_id = models.TextField(blank=True, null=True)
    action_officer_id = models.TextField(blank=True, null=True)
    survey = models.TextField(blank=True, null=True)
    arrival_date = models.DateField(blank=True, null=True)
    is_existing_permittee = models.BooleanField(default=False)

    def __str__(self):
        return f"Import #{self.id} - {self.brand.name}"

class CHImportWarehouse(models.Model):
    application = models.ForeignKey(CHImport, on_delete=models.CASCADE, related_name='warehouses')
    city = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return f"{self.city} - {self.address}"

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
    is_old = models.BooleanField(default=False)
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
    
    
class CHUserAccess(models.Model):

    userid = models.IntegerField()
    type = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'ch_access_level'
        
    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()}"


class ChPayment(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    app_id = models.IntegerField()
    op_id = models.CharField(max_length=100)
    date_paid = models.DateField(null=True, blank=True)
    date_confirmed = models.DateField(null=True, blank=True)
    or_no = models.CharField(max_length=100, null=True, blank=True)
    lbp_ref_no = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fund_cluster = models.CharField(max_length=100)
    type = models.CharField(max_length=50)
    remarks = models.TextField(blank=True, null=True)
    is_old = models.BooleanField(default=False)
    status = models.CharField(max_length=50, help_text="0 = Unpaid, 1 = Paid, 2 = Validated")

    class Meta:
        db_table = 'ch_payment'

    def __str__(self):
        return f"Payment {self.id} - App {self.app_id}"


class ProofOfPayment(models.Model):
    app_id = models.IntegerField()
    payment = models.ForeignKey(ChPayment, on_delete=models.CASCADE, related_name='proofs')
    file_name = models.CharField(max_length=255)
    file_location = models.CharField(max_length=500)
    is_old = models.BooleanField(default=False)
    date_uploaded = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ch_proof_of_payment'

    def __str__(self):
        return self.file_name


class InspectionReport(models.Model):
    application = models.ForeignKey(CHImport, on_delete=models.CASCADE, related_name='inspection_reports')
    inspector =  models.IntegerField()
    report_content = models.TextField()  # HTML from CKEditor
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Inspection Report for CPS Import #{self.application.id}"


class InspectionAttachment(models.Model):
    report = models.ForeignKey(InspectionReport, on_delete=models.CASCADE, related_name='attachments')
    file_path = models.CharField(max_length=255, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_path
    
    
class Survey(models.Model):
    id = models.BigAutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    application = models.ForeignKey(CHImport, on_delete=models.CASCADE, related_name='surveys')
    client_id = models.IntegerField()

    cc1 = models.SmallIntegerField(blank=True, null=True)
    cc2 = models.SmallIntegerField(blank=True, null=True)
    cc3 = models.SmallIntegerField(blank=True, null=True)
    cc41 = models.SmallIntegerField(blank=True, null=True)
    cc42 = models.SmallIntegerField(blank=True, null=True)
    cc43 = models.SmallIntegerField(blank=True, null=True)
    cc44 = models.SmallIntegerField(blank=True, null=True)
    cc45 = models.SmallIntegerField(blank=True, null=True)
    cc46 = models.SmallIntegerField(blank=True, null=True)
    cc47 = models.SmallIntegerField(blank=True, null=True)
    cc48 = models.SmallIntegerField(blank=True, null=True)
    cc49 = models.SmallIntegerField(blank=True, null=True)
    suggestions = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"Survey #{self.application.id}"