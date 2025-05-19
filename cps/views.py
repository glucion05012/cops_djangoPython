import os
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import (
    ChainsawBrand,
    CHImport,
    CHImportModelDetail,
    CHImportAttachment,
)
import traceback
from django.utils import timezone
from django.db import connections
from datetime import datetime


def index(request):
    brands = ChainsawBrand.objects.all()
    business_list = []
    
    with connections['dniis_db'].cursor() as cursor:
        cursor.execute('''
            SELECT a.*, 
                   l.name AS lgu, 
                   sl.name AS sub_lgu, 
                   br.name AS barangay
            FROM systems_clients_27_repeat a
            LEFT JOIN systems_lgu l ON a.biz_lgu = l.psgc 
            LEFT JOIN systems_sub_lgu sl ON a.biz_sub_lgu = sl.psgc 
            LEFT JOIN systems_barangays br ON a.biz_barangay = br.psgc
            WHERE a.parent_id = %s AND a.business_name != ""
        ''', [request.session.get('user_id')])
        
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            business_list.append(dict(zip(columns, row)))
            
    return render(request, 'import/apply.html', {
        'brands': brands,
        'business_list': business_list,
    })


def submit_import(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract form data
                model_list = request.POST.getlist('model[]')
                quantity_list = request.POST.getlist('quantity[]')
                brand_name = request.POST.get('brand')

                # Create or get brand
                brand, _ = ChainsawBrand.objects.get_or_create(name=brand_name)

                # Create CHImport record
                application = CHImport.objects.create(
                    brand=brand,
                    origin=request.POST.get('origin'),
                    purpose=request.POST.get('purpose'),
                    crs_id=request.session.get('user_id'),
                    estab_address = request.POST.get('estab_address'),
                    estab_contact = request.POST.get('estab_contact'),
                    estab_email = request.POST.get('estab_email'),
                    estab_id_dniis = request.POST.get('estab_id_dniis'),
                    estab_name = request.POST.get('estab_name'),
                    remarks = 'New Application'
                )
                
                # ✅ Generate and save reference number
                ref_no = f"{datetime.now().strftime('%Y-%m-%d')}-PIC-{application.id}"
                application.reference_no  = ref_no
                application.save()

                # Create model/quantity details
                for model, quantity in zip(model_list, quantity_list):
                    if model.strip() and quantity.isdigit():
                        CHImportModelDetail.objects.create(
                            application=application,
                            model=model.strip(),
                            quantity=int(quantity)
                        )

                # === File saving helper for multiple files ===
                def save_files(files, type_key, subfolder):
                    if not files:
                        return
                    folder_path = os.path.join(settings.BASE_DIR, 'cps', 'media', 'attachments', subfolder)
                    os.makedirs(folder_path, exist_ok=True)
                    fs = FileSystemStorage(location=folder_path)

                    for file in files:
                        filename = fs.save(file.name, file)
                        file_path = os.path.join('attachments', subfolder, filename)
                        CHImportAttachment.objects.create(
                            application=application,
                            name=file.name,
                            file_location=file_path,
                            type=type_key,
                            date_uploaded=timezone.now()
                        )

                # Save each attachment type (multiple files)
                save_files(request.FILES.getlist('dti_sec'), 'dti_sec', 'dti')
                save_files(request.FILES.getlist('purchase_order'), 'purchase_order', 'purchase_orders')
                save_files(request.FILES.getlist('affidavit'), 'affidavit', 'affidavits')
                save_files(request.FILES.getlist('geotag_photos'), 'geotag_photo', 'geotag_photos')

                return JsonResponse({'success': True, 'message': 'Application submitted successfully.'})

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"An error occurred: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Error occurred during submission.'})

    return render(request, 'import/apply.html')