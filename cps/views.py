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


def index(request):
    brands = ChainsawBrand.objects.all()
    return render(request, 'import/apply.html', {
        'brands': brands,
    })


def submit_import(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract form data
                brand_name = request.POST.get('brand')
                origin = request.POST.get('origin')
                purpose = request.POST.get('purpose')
                model_list = request.POST.getlist('model[]')
                quantity_list = request.POST.getlist('quantity[]')

                # Create or get brand
                brand, _ = ChainsawBrand.objects.get_or_create(name=brand_name)

                # Create CHImport record
                application = CHImport.objects.create(
                    brand=brand,
                    origin=origin,
                    purpose=purpose,
                )

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