import os
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import (
    ChainsawBrand,
    CHImport,
    CHImportModelDetail,
    CHImportAttachment,
    CHApplication
)
import traceback
from django.utils import timezone
from django.db import connections
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage


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
                with connections['default'].cursor() as cursor:
                    cursor.execute("""
                        SELECT userid
                        FROM ch_access_level
                        WHERE type = %s
                        ORDER BY RAND()
                        LIMIT 1
                    """, ['fus_evaluator'])
                    result = cursor.fetchone()
                    if result:
                        evaluator_id = result[0]
        
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
                    remarks = 'fus_evaluator',
                    status = 'pending',
                    arrival_date=request.POST.get('arrival_date'),
                    is_existing_permittee=request.POST.get('is_existing_permittee') == '1',
                    warehouse_city = request.POST.get('warehouse_city'),
                    warehouse_address = request.POST.get('warehouse_address'),
                    evaluator_id = evaluator_id
                )
                
                # ✅ Generate and save reference number
                ref_no = f"{datetime.now().strftime('%Y-%m-%d')}-PIC-{application.id}"
                application.reference_no  = ref_no
                application.save()

                # ✅ Create CHApplication record
                CHApplication.objects.create(
                    date_created=timezone.now(),
                    app_id=application.id,
                    reference_no=ref_no,
                    forwarded_by_id=request.session.get('user_id'),
                    forwarded_to_id = evaluator_id,
                    action='For Evaluation',
                    notes='Created New Application',
                    status='pending',
                    days_pending=0
                )
                
                # Save model/quantity details
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
                        formatted_filename = f"{application.id}-{file.name}"
                        filename = fs.save(formatted_filename, file)
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

                return JsonResponse({'success': True, 'message': 'Application submitted successfully.'})

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"An error occurred: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Error occurred during submission.'})

    return render(request, 'import/apply.html')


@csrf_exempt
def edit_application(request, permitType, app_id):
    # Validate permit type
    if permitType == 'PIC':

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    brand_name = request.POST.get('brand')
                    
                    chimport = get_object_or_404(CHImport, id=app_id)
                    brand, _ = ChainsawBrand.objects.get_or_create(name=brand_name)
                
                    chimport.brand_id = brand.id
                    chimport.origin = request.POST.get('origin')
                    chimport.purpose = request.POST.get('purpose')
                    chimport.estab_id_dniis = request.POST.get('estab_id_dniis')
                    chimport.estab_name = request.POST.get('estab_name')
                    chimport.estab_address = request.POST.get('estab_address')
                    chimport.estab_email = request.POST.get('estab_email')
                    chimport.estab_contact = request.POST.get('estab_contact')
                    chimport.arrival_date = request.POST.get('arrival_date')
                    chimport.is_existing_permittee = request.POST.get('is_existing_permittee')
                    chimport.warehouse_city = request.POST.get('warehouse_city')
                    chimport.warehouse_address = request.POST.get('warehouse_address')
                    chimport.save()

                    # Chainsaw Details
                    CHImportModelDetail.objects.filter(application_id=app_id).delete()
                    model_list = request.POST.getlist('model[]')
                    quantity_list = request.POST.getlist('quantity[]')
                    # Save model/quantity details
                    for model, quantity in zip(model_list, quantity_list):
                        if model.strip() and quantity.isdigit():
                            CHImportModelDetail.objects.create(
                                application_id=app_id,
                                model=model.strip(),
                                quantity=int(quantity)
                            )
                            
                    # Attachments
                    # --- DELETE SELECTED ATTACHMENTS ---
                    delete_ids = request.POST.getlist('delete_attachments')
                    if delete_ids:
                        for att_id in delete_ids:
                            try:
                                att = CHImportAttachment.objects.get(id=att_id)
                                if att.file_location:
                                    if default_storage.exists(att.file_location):
                                        default_storage.delete(att.file_location)
                                att.delete()
                            except CHImportAttachment.DoesNotExist:
                                pass

                    # --- ADD NEW ATTACHMENTS IF PROVIDED ---
                    def save_files(files, type_key, subfolder):
                        if not files:
                            return
                        folder_path = os.path.join(settings.BASE_DIR, 'cps', 'media', 'attachments', subfolder)
                        os.makedirs(folder_path, exist_ok=True)
                        fs = FileSystemStorage(location=folder_path)

                        for file in files:
                            formatted_filename = f"{app_id}-{file.name}"
                            filename = fs.save(formatted_filename, file)
                            file_path = os.path.join('attachments', subfolder, filename)
                            CHImportAttachment.objects.create(
                                application_id=app_id,
                                name=file.name,
                                file_location=file_path,
                                type=type_key,
                                date_uploaded=timezone.now()
                            )

                    # === Save each attachment type (multiple files supported) ===
                    save_files(request.FILES.getlist('purchase_order'), 'purchase_order', 'purchase_orders')
                    save_files(request.FILES.getlist('affidavit'), 'affidavit', 'affidavits')
                    save_files(request.FILES.getlist('dti_sec'), 'dti_sec', 'dti')
                    
                    
                    #TRANSACTION DETAILS
                    user_id = request.session.get('user_id')
                    
                    #prev_transaction
                    ch_application = CHApplication.objects.filter(app_id=app_id).order_by('-id').first()
                    
                    reference_no = ch_application.reference_no
                    last_forwarded_by_id = ch_application.forwarded_by_id
                    action="For Re-evaluation"
                    notes="Resubmit Application"
                    remarks =  request.POST.get('remarks', '').strip()
                    status = 'pending'
                        
                        
                    # ✅ Create CHApplication record
                    CHApplication.objects.create(
                        date_created=timezone.now(),
                        app_id=app_id,
                        reference_no=reference_no,
                        forwarded_by_id = user_id,
                        forwarded_to_id = last_forwarded_by_id,
                        action=action,
                        notes=notes,
                        remarks=remarks,
                        status=status,
                        days_pending=0
                    )
                    
                    CHImport.objects.filter(id=int(app_id)).update(
                        remarks='fus_evaluator',
                        status='pending'
                    )
                    
                return JsonResponse({'success': True, 'message': 'Application resubmitted successfully.'})

            except Exception as e:
                # No need to call transaction.set_rollback(True); it happens automatically in an atomic block
                traceback.print_exc()
                return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
        else:
            
            # Get main application
            ch_import = get_object_or_404(CHImport, id=app_id)
            app_ch_details = CHImportModelDetail.objects.filter(application_id=app_id)
            app_attachments = CHImportAttachment.objects.filter(application_id=app_id)
            brands = ChainsawBrand.objects.all()
            business_list = []

            user_id = ch_import.crs_id

            with connections['dniis_db'].cursor() as cursor:
                cursor.execute("""
                    SELECT business_type, fullname, cel_no, email
                    FROM systems_clients
                    WHERE user_id = %s
                    LIMIT 1
                """, [user_id])
                client_info = cursor.fetchone()
                
                client_name = client_info[1]
                client_contact = client_info[2]
                client_email = client_info[3]
                
                if client_info:
                    code = client_info[0]
                    if code == '1':
                        business_type = 'Individual'
                    elif code == '2':
                        business_type = 'Government'
                    elif code == '3':
                        business_type = 'Corporation'
                        
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
        
            ncr_cities = [
                'Caloocan', 'Las Piñas', 'Makati', 'Malabon', 'Mandaluyong', 'Manila', 'Marikina',
                'Muntinlupa', 'Navotas', 'Parañaque', 'Pasay', 'Pasig', 'Pateros', 'Quezon City',
                'San Juan', 'Taguig', 'Valenzuela'
            ]
   
            return render(request, 'import/edit.html', {
                'application': ch_import,
                'ch_details': app_ch_details,
                'attachments': app_attachments,
                'permit_type_short': 'PIC',
                'permit_type': 'Permit to Import Chainsaw',
                'applicant_type': business_type,
                'client_name': client_name,
                'client_contact': client_contact,
                'client_email': client_email,
                'brands': brands,
                'business_list': business_list,
                'ncr_cities': ncr_cities,
            })