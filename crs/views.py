from django.shortcuts import render, get_object_or_404
from django.db import connections
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.contrib.auth.hashers import make_password
import os
import random
import string
from PIL import Image
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse
import bcrypt
import secrets
import time
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from operator import itemgetter
from django.db import transaction
import traceback
from datetime import datetime

from cps.models import (
    CHImport,
    CHApplication,
    ProofOfPayment,
    ChPayment,
    InspectionReport,
    InspectionAttachment,
    Survey
)

from datetime import date, timedelta

from .utils.encryption import encrypt_id, decrypt_id

def test(request):
    password = 'your_password'

    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=10)
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return HttpResponse(hashed_password.decode('utf-8'))
    
def index(request):
    with connections['dniis_db'].cursor() as cursor:
        cursor.execute('SELECT * FROM systems_users_nationality')
        rows_nationality = cursor.fetchall()

    with connections['dniis_db'].cursor() as cursor:
        cursor.execute('SELECT * FROM systems_users_id_type')
        rows_id_type = cursor.fetchall()

    # Clear all session data
    request.session.flush()
    
    return render(request, 'login.html', {
        'rows_nationality': rows_nationality,
        'rows_id_type': rows_id_type,
    })

def check_existing(request):
    if request.method == 'POST':
        # Extract the POST data
        username = request.POST.get('usernameCreate')
        contact_no = request.POST.get('contactNo')
        email = request.POST.get('email')
        
        # Initialize response dictionary
        response = {
            'usernameExists': False,
            'contactNoExists': False,
            'emailExists': False
        }

        # Using raw SQL with the custom database connection (dniis_db)
        with connections['dniis_db'].cursor() as cursor:
            # Check if the username exists in the 'core_users' table
            cursor.execute("SELECT COUNT(*) FROM core_users WHERE username = %s", [username])
            username_exists = cursor.fetchone()[0] > 0
            if username_exists:
                response['usernameExists'] = True

            # Check if the contact number exists in the 'core_users' table
            cursor.execute("SELECT COUNT(*) FROM systems_clients WHERE cel_no = %s", [contact_no])
            contact_no_exists = cursor.fetchone()[0] > 0
            if contact_no_exists:
                response['contactNoExists'] = True

            # Check if the email exists in the 'core_users' table
            cursor.execute("SELECT COUNT(*) FROM core_users WHERE email = %s", [email])
            email_exists = cursor.fetchone()[0] > 0
            if email_exists:
                response['emailExists'] = True

        # Return the response as a JSON object
        return JsonResponse(response)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

def generate_random_digits(length=4):
    """Generate a random string of digits of a specific length."""
    return ''.join(random.choices(string.digits, k=length))

def create_account(request):
    applicantType = request.POST.get('applicantType')
    firstName = request.POST.get('firstName')
    middleName = request.POST.get('middleName')
    lastName = request.POST.get('lastName')
    birthdate = request.POST.get('birthdate')
    gender = request.POST.get('gender')
    nationality = request.POST.get('nationality')
    email = request.POST.get('email')
    contactNo = request.POST.get('contactNo')
    address = request.POST.get('address')
    usernameCreate = request.POST.get('usernameCreate')
    passwordCreate = request.POST.get('passwordCreate')
    idType = request.POST.get('idType')
    idNumber = request.POST.get('idNumber')
    idFront = request.POST.get('idFront')
    idBack = request.POST.get('idBack')
    params = '{}'


    timezone.activate('Asia/Manila')
    currentDateTime = timezone.now()

    first_name = request.POST.get('firstName')
    middle_name = request.POST.get('middleName')
    last_name = request.POST.get('lastName')

    full_name = f"{last_name}, {first_name} {middle_name}"

    #hash the password
    password = request.POST.get('passwordCreate')
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=10)
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    hashed_password = hashed_password.decode('utf-8')

    #attachment
    # Process 'idFront' file
    id_front = request.FILES.get('idFront')
    if id_front:
        random_digits = generate_random_digits()
        new_file_name = timezone.now().strftime('%Y%m%d_%H%M%S') + random_digits + '.' + id_front.name.split('.')[-1]
        upload_dir = os.path.join(settings.BASE_DIR, 'media', 'attachments')
        os.makedirs(upload_dir, exist_ok=True)
        target_file_path_front = os.path.join(upload_dir, new_file_name)
        
        # Save the 'idFront' file
        with open(target_file_path_front, 'wb+') as destination:
            for chunk in id_front.chunks():
                destination.write(chunk)
        
        # Create thumbnail for 'idFront'
        thumbnail_file_name = 'thumb_pic_' + new_file_name
        thumbnail_path = os.path.join(upload_dir, thumbnail_file_name)
        create_thumbnail(target_file_path_front, thumbnail_path)
    
        target_file_path_front_label = "/uploads/systems_clients/client_photos/" + new_file_name
    
    # Process 'idBack' file (if exists)
    id_back = request.FILES.get('idBack')
    if id_back:
        random_digits = generate_random_digits()
        new_file_name = timezone.now().strftime('%Y%m%d_%H%M%S') + random_digits + '.' + id_back.name.split('.')[-1]
        upload_dir = os.path.join(settings.BASE_DIR, 'media', 'attachments')
        os.makedirs(upload_dir, exist_ok=True)
        target_file_path_back = os.path.join(upload_dir, new_file_name)
        
        # Save the 'idBack' file
        with open(target_file_path_back, 'wb+') as destination:
            for chunk in id_back.chunks():
                destination.write(chunk)
        
        # Create thumbnail for 'idBack'
        thumbnail_file_name = 'thumb_pic_' + new_file_name
        thumbnail_path = os.path.join(upload_dir, thumbnail_file_name)
        create_thumbnail(target_file_path_back, thumbnail_path)
        
        target_file_path_back_label = "/uploads/systems_clients/client_photos/" + new_file_name
        
    #insert to core_users
    with connections['dniis_db'].cursor() as cursor:
    # Execute the INSERT query
        last_reset_time = "1970-01-01 00:00:00"
        
        cursor.execute('''
            INSERT INTO core_users (name, email, residential_address,
                    username, password, registerDate, lastvisitDate, lastResetTime, block,
                    activation, params, employee_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', [full_name, email, address,
                usernameCreate, hashed_password, currentDateTime, currentDateTime, last_reset_time,
                1, 0, params, 10])

        # Get the last inserted ID using lastrowid after the insert
        last_inserted_id = cursor.lastrowid

        # Perform the UPDATE query with the last inserted ID
        cursor.execute('''
            UPDATE core_users
            SET crs_ = %s
            WHERE id = %s
        ''', ['CRS-' + str(last_inserted_id), last_inserted_id])

        #insert to systems_clients
        cursor.execute('''
            INSERT INTO systems_clients (business_type, user_id, username, password,
            email, fullname, cel_no, birthdate, nationality, gender, block,
            user_group, photo, photo2, terms_and_condition, address, spacer, first_name,
            middle_name, last_name, valid_id, valid_id_, registration_date, spacer2,
            spacer3, spacer4, spacer5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', [applicantType, last_inserted_id, usernameCreate, hashed_password, email, full_name,
              contactNo, birthdate, nationality, gender, 1, 74, target_file_path_front_label, target_file_path_back_label,
              '["1"]', address, '[]', first_name, middle_name, last_name, idType, idNumber,
              currentDateTime, '[]', '[]', '[]', '[]'])


        # Perform the UPDATE query with the last inserted ID
        cursor.execute('''
            UPDATE systems_clients
            SET crs_ = %s
            WHERE user_id = %s
        ''', ['CRS-' + str(last_inserted_id), last_inserted_id])
        
    return JsonResponse({'success': True, 
                         'message': 'User created successfully',
                         'file_path': f'/media/uploads/systems_clients/client_photos/{new_file_name}',
                         'thumbnail_path': f'/media/uploads/systems_clients/client_photos/{thumbnail_file_name}'})

def create_thumbnail(image_path, thumbnail_path):
    """Create a thumbnail for the given image."""
    with Image.open(image_path) as img:
        # Set the width of the thumbnail
        thumbnail_width = 150
        # Calculate the height maintaining aspect ratio
        aspect_ratio = img.height / img.width
        thumbnail_height = int(thumbnail_width * aspect_ratio)

        # Convert the image to RGB if it's in RGBA mode (which includes transparency)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Create the thumbnail
        img.thumbnail((thumbnail_width, thumbnail_height))
        img.save(thumbnail_path, "JPEG")
        
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Using raw SQL with the custom database connection (dniis_db)
        with connections['dniis_db'].cursor() as cursor:
            # Check if the username exists in the 'core_users' table
            cursor.execute("SELECT COUNT(*) FROM core_users WHERE username = %s", [username])
            username_exists = cursor.fetchone()[0] > 0

            if username_exists:
                # Check if the password is correct
                cursor.execute("SELECT password FROM core_users WHERE username = %s", [username])
                hashed_password = cursor.fetchone()[0]

                # Verify the password using bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                    
                    
                    cursor.execute("SELECT * FROM core_users WHERE username = %s AND employee_type = %s", [username, 10])
                    user = cursor.fetchone()
                    
                    # set session for approvers
                    request.session['fus_sc_id'] = 497
                    request.session['lpdd_dc_id'] = 550
                    request.session['ts_id'] = 1400
                    request.session['red_id'] = 1465
                    
                
                    if not user:
                        # DENR NCR Employee Account
                        cursor.execute("SELECT * FROM core_users WHERE username = %s", [username])
                        user = cursor.fetchone()
                        request.session['user_id'] = user[0] #id
                        request.session['user_type'] = 'Employee' #user_type
                        request.session['fullname'] = user[1] #name 
                    else:
                        # Client Account
                        cursor.execute("SELECT * FROM systems_clients WHERE username = %s", [username])
                        client = cursor.fetchone()
                        
                        #Check if user is blocked
                        print("User verification status:", user[5])
                        if user[5] == "1":
                            return JsonResponse({'success': False, 'message': 'User is not yet verified.'})
                
                        # Store the user_id and fullname in the session
                        request.session['user_id'] = user[0] #id
                        request.session['user_type'] = 'Client' #user_type
                        request.session['fullname'] = user[1] #name
                        request.session['app_type'] = client[51] #business_type
                        
                        # <option value="1">Individual</option>
                        # <option value="2">Government</option>
                        # <option value="3">Corporation</option>
                    
                    
                    user_id = request.session['user_id']
                    
                    session_id = secrets.token_hex(18)
                    timestamp = int(time.time())
                    
                    # insert session
                    cursor.execute("""
                        INSERT INTO core_session (session_id, client_id, guest, time, userid, username)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [session_id, 0, 0, timestamp, user_id, username])
                    
                    request.session['authenticated'] = True
                    
                    
                    # return response to view
                    return JsonResponse({
                        'success': True, 
                        'message': 'Login successful', 
                        'redirect_url': '/dashboard/',
                    })
                else:
                    request.session['authenticated'] = False
                    return JsonResponse({'success': False, 'message': 'Invalid password'})
            else:
                return JsonResponse({'success': False, 'message': 'Username does not exist'})

    return JsonResponse({'error': 'Invalid request method.'}, status=400)

def dashboard(request):
    # Check if the user is authenticated (you can implement your own authentication logic here)
    if request.session.get('authenticated'):
        return render(request, 'dashboard.html')
    else:
        return render(request, 'login.html', {'error': 'You need to log in first.'})
    
def myApplications(request):
    # Check if the user is authenticated (you can implement your own authentication logic here)
    if request.session.get('authenticated'):
        return render(request, 'myApplications.html')
    else:
        return render(request, 'login.html', {'error': 'You need to log in first.'})
    
    
def get_session(request):
    if request.session.get('authenticated') and request.session.get('user_id'):
        with connections['dniis_db'].cursor() as cursor:
            cursor.execute("SELECT session_id FROM core_session WHERE userid = %s", [request.session['user_id']])
            result = cursor.fetchone()
            if result:
                session_id = result[0]

                # If session_id is in bytes, decode it
                if isinstance(session_id, bytes):
                    session_id = session_id.decode('utf-8')

                return JsonResponse({
                    'status': 'success',  # Match JS
                    'session_id': session_id  # Provide decoded session_id
                })

    return JsonResponse({'status': 'fail', 'message': 'Please login again.'})

@csrf_exempt
def application_list_json(request):
    user_id = request.session.get('user_id')

    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))
    search_value = request.POST.get('search[value]', '').strip().lower()
    order_column = int(request.POST.get('order[0][column]', 0))
    order_dir = request.POST.get('order[0][dir]', 'asc')

    column_names = [
        'permit_type',
        'estab_name',
        'reference_no',
        'date_applied',
        'status',
        'client_remarks',
    ]
    sort_column = column_names[order_column] if order_column < len(column_names) else 'date_applied'
    reverse = order_dir == 'desc'

    data = []

    # TCP Count Queries
    with connections['tcp_db'].cursor() as cursor:
        # Total
        cursor.execute("SELECT COUNT(*) FROM app_tcp WHERE crs_id = %s", [user_id])
        tcp_total = cursor.fetchone()[0]

        # Filtered
        if search_value:
            like_term = f'%{search_value}%'
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM app_tcp a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id
                    FROM app_application
                    WHERE id IN (SELECT MAX(id) FROM app_application GROUP BY app_id)
                ) c ON a.id = c.app_id
                WHERE a.crs_id = %s AND (
                    LOWER(a.estab_name) LIKE %s OR
                    LOWER(COALESCE(a.reference_no_new, a.reference_no)) LIKE %s OR
                    LOWER(a.status) LIKE %s
                )
            """, [user_id, like_term, like_term, like_term])
        else:
            cursor.execute("SELECT COUNT(*) FROM app_tcp WHERE crs_id = %s", [user_id])
        tcp_filtered = cursor.fetchone()[0]

    # CHIMPORT Count Queries
    with connections['default'].cursor() as cursor:
        # Total
        cursor.execute("SELECT COUNT(*) FROM cps_chimport WHERE crs_id = %s", [user_id])
        ch_total = cursor.fetchone()[0]

        # Filtered
        if search_value:
            like_term = f'%{search_value}%'
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id
                    FROM ch_application
                    WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                ) c ON a.id = c.app_id
                WHERE a.crs_id = %s AND (
                    LOWER(a.estab_name) LIKE %s OR
                    LOWER(a.reference_no) LIKE %s OR
                    LOWER(a.status) LIKE %s
                )
            """, [user_id, like_term, like_term, like_term])
        else:
            cursor.execute("SELECT COUNT(*) FROM cps_chimport WHERE crs_id = %s", [user_id])
        ch_filtered = cursor.fetchone()[0]

    # TCP Data
    with connections['tcp_db'].cursor() as cursor:
        sql_filter = ""
        params = [user_id, user_id, user_id]
        if search_value:
            sql_filter = """
                AND (
                    LOWER(a.estab_name) LIKE %s OR
                    LOWER(COALESCE(a.reference_no_new, a.reference_no)) LIKE %s OR
                    LOWER(a.status) LIKE %s
                )
            """
            like_term = f"%{search_value}%"
            params.extend([like_term, like_term, like_term])

        cursor.execute(f"""
            SELECT 
                a.id AS app_id,
                'TCP' AS permit_type_short,
                a.estab_name,
                COALESCE(a.reference_no_new, a.reference_no) AS reference_no,
                a.date_applied,
                CASE 
                    WHEN c.forwarded_to_id = %s THEN 'Returned to Client'
                    ELSE a.status
                END AS status,
                CASE 
                    WHEN c.forwarded_to_id = %s THEN c.remarks
                    ELSE 'Pending'
                END AS client_remarks,
                c.client_notes,
                a.permit_type,
                p.status AS paid_status
            FROM app_tcp a
            LEFT JOIN (
                SELECT app_id, remarks, forwarded_to_id, notes AS client_notes
                FROM app_application
                WHERE id IN (
                    SELECT MAX(id) FROM app_application GROUP BY app_id
                )
            ) c ON a.id = c.app_id
            LEFT JOIN payment p ON a.id = p.app_id
            WHERE a.crs_id = %s
            {sql_filter}
            LIMIT %s OFFSET %s
        """, params + [length, start])

        for row in cursor.fetchall():
            app_id, permit_type_short, estab_name, reference_no, date_applied, status, client_remarks, client_notes, permit_type, paid_status = row
            data.append({
                'app_id' : app_id,
                'permit_type_short': permit_type_short,
                'permit_type': {
                    'tcp': 'Tree Cutting Permit',
                    'stcp': 'Special Tree Cutting Permit',
                    'tebp': 'Tree-Earth-Balling Permit',
                    'stebp': 'Special Tree-Earth-Balling Permit',
                    'tpp': 'Tree-Pruning Permit',
                }.get(permit_type, permit_type.upper()),
                'estab_name': estab_name,
                'reference_no': reference_no,
                'date_applied': date_applied,
                'status': status,
                'client_remarks': client_remarks,
                'client_notes': client_notes,
                'paid_status': paid_status
            })

    # CHIMPORT Data
    with connections['default'].cursor() as cursor:
        sql_filter = ""
        params = [user_id, user_id, user_id]
        if search_value:
            sql_filter = """
                AND (
                    LOWER(a.estab_name) LIKE %s OR
                    LOWER(a.reference_no) LIKE %s OR
                    LOWER(a.status) LIKE %s
                )
            """
            like_term = f"%{search_value}%"
            params.extend([like_term, like_term, like_term])

        cursor.execute(f"""
            SELECT 
                a.id AS app_id,
                'PIC' AS permit_type_short,
                'Permit to Import Chainsaw' AS permit_type,
                a.estab_name,
                a.reference_no,
                a.date_applied,
                CASE 
                    WHEN c.forwarded_to_id = %s THEN 
                        CASE 
                            WHEN a.status = 'pending' AND a.remarks='client' THEN 'Returned to Client'
                            WHEN p.status = 0 THEN 'Returned to Client'
                            WHEN p.status = 1 THEN 'For Validation of Payment'
                            ELSE a.status
                        END
                    ELSE a.status
                END AS status,
                CASE 
                    WHEN c.forwarded_to_id = %s THEN c.remarks
                    ELSE 'Pending'
                END AS client_remarks,
                c.client_notes,
                p.status AS paid_status,
                a.survey
            FROM cps_chimport a
            LEFT JOIN (
                SELECT app_id, remarks, forwarded_to_id, notes AS client_notes
                FROM ch_application
                WHERE id IN (
                    SELECT MAX(id) FROM ch_application GROUP BY app_id
                )
            ) c ON a.id = c.app_id
            LEFT JOIN ch_payment p ON a.id = p.app_id
            WHERE a.crs_id = %s
            {sql_filter}
            LIMIT %s OFFSET %s
        """, params + [length, start])

        for row in cursor.fetchall():
            app_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, client_notes, paid_status, survey = row
            data.append({
                'app_id': encrypt_id(app_id),  # Encrypt here
                'permit_type_short': permit_type_short,
                'permit_type': permit_type,
                'estab_name': estab_name,
                'reference_no': reference_no,
                'date_applied': date_applied,
                'status': status,
                'client_remarks': client_remarks,
                'client_notes': client_notes,
                'paid_status': paid_status,
                'survey': survey
            })

    # Sort in Python
    def safe_key(item):
        value = item.get(sort_column)
        if isinstance(value, (str, int, float)):
            return value
        elif hasattr(value, 'isoformat'):  # datetime or date
            return value.isoformat()
        elif value is None:
            return ''
        return str(value)

    data.sort(key=safe_key, reverse=reverse)

    return JsonResponse({
        'draw': draw,
        'recordsTotal': tcp_total + ch_total,
        'recordsFiltered': tcp_filtered + ch_filtered,
        'data': data,
    })
    
    
def get_application_details(request):
    reference_no = request.GET.get('reference_no')
    permit_type_short = request.GET.get('permit_type_short', '').lower()  # Normalize

    app_id = request.GET.get('appid')
    try:
        decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")
        
    data = {}

    if permit_type_short == 'pic':
        # Query CHIMPORT table (default DB)
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    'PIC' AS permit_type_short,
                    'PIC' AS permit_type,
                    a.*,
                    b.name as brand_name,
                    a.remarks AS client_remarks,
                    c.op_id,
                    c.id AS payment_id,
                    c.amount,
                    c.date_created AS op_date
                FROM cps_chimport a
                LEFT JOIN cps_chainsawbrand b ON a.brand_id = b.id
                LEFT JOIN ch_payment c ON a.id = c.app_id
                WHERE a.reference_no = %s
            """, [reference_no])
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                data = dict(zip(columns, row))
                data['permit_type'] = 'Permit to Import Chainsaw'
                
                # 🔽 ADD: fetch model details
                cursor.execute("""
                    SELECT model, quantity 
                    FROM cps_chimportmodeldetail 
                    WHERE application_id = %s
                """, [data['id']])
                model_rows = cursor.fetchall()
                data['models'] = [{'model': r[0], 'quantity': r[1]} for r in model_rows]
                
        # Attachments
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT a.*
                FROM cps_chimportattachment a
                LEFT JOIN cps_chimport b ON a.application_id = b.id
                WHERE reference_no = %s
            """, [reference_no])
            attachments = cursor.fetchall()

        file_type_map = {
            'dti_sec': 'Business Name Registration (DTI/SEC with GIS)',
            'purchase_order': 'Purchase Order',
            'affidavit': 'Affidavit for Legal Purpose',
            'geotag_photo': 'Geotagged Photo',
            # Add other mappings as needed
        }
        
        data['attachments'] = [
            {
                'file_type': file_type_map.get(att[4], att[4]),
                'file_name': att[1],
                'file_url': settings.MEDIA_URL + att[2] + att[1],
            } for att in attachments
        ]
        
    elif permit_type_short == 'tcp':
        # Default to TCP
        with connections['tcp_db'].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    'TCP' AS permit_type_short,
                    a.*,
                    COALESCE(a.reference_no_new, a.reference_no) AS reference_no,
                    c.remarks AS client_remarks,
                    t.address AS tree_location
                FROM app_tcp a
                LEFT JOIN (
                    SELECT app_id, remarks
                    FROM app_application
                    WHERE id IN (
                        SELECT MAX(id) FROM app_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                LEFT JOIN tree_location t ON a.tree_location_id = t.id
                WHERE COALESCE(a.reference_no_new, a.reference_no) = %s
            """, [reference_no])

            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                data = dict(zip(columns, row))
                permit_map = {
                    'tcp': 'Tree Cutting Permit',
                    'stcp': 'Special Tree Cutting Permit',
                    'tebp': 'Tree-Earth-Balling Permit',
                    'stebp': 'Special Tree-Earth-Balling Permit',
                    'tpp': 'Tree-Pruning Permit',
                }
                data['permit_type'] = permit_map.get(data.get('permit_type'), data.get('permit_type', '').upper())

        # Attachments
        with connections['tcp_db'].cursor() as cursor:
            cursor.execute("""
                SELECT a.*
                FROM app_attachment a
                LEFT JOIN app_tcp b ON a.app_id = b.id
                WHERE reference_no = %s
            """, [reference_no])
            attachments = cursor.fetchall()

        file_type_map = {
            'SPA': 'SPA / Authorization Letter',
            'LT': 'Land title (OCT/TCT)',
            'LA': 'If property is leased (Lease Agreement)',
            'DS': 'If property is sold (Deed of Sale)',
            'GI': 'If property is owned by Corporation (General Information Sheet)',
            'BC': 'Barangay Certificate of No Objection',
            'SM': 'Sketch map or site development plan',
            'PT': 'Photograph of trees',
            'EC': 'ECC/CNC',
            'CO': 'If within private property (Certificate of No Objection)',
            'HB': 'If within public space (HOA Board Resolution)',
            'PR': 'PTA Resolution (if within school)',
            'UP': 'Utilization Plan (if area covers 10 ha or larger)',
            'EA': 'Endorsement by local Agrarian reform (If covered by CLOA)',
            # Add other mappings as needed
        }

        data['attachments'] = [
            {
                'file_type': file_type_map.get(att[5], att[5]),
                'file_name': att[2],
                'file_url': settings.MEDIA_URL + att[3] + att[2],
            } for att in attachments
        ]
        

    if data is not None:
        data['app_id'] = decrypted_id
        
        if permit_type_short == 'pic':
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    SELECT crs_id FROM cps_chimport WHERE id = %s LIMIT 1
                """, [decrypted_id])
                result = cursor.fetchone()
                if result:
                    user_id = result[0]
                else:
                    return JsonResponse({'error': 'Application not found (no user_id)'}, status=404)
        elif permit_type_short == 'tcp':
            with connections['tcp_db'].cursor() as cursor:
                cursor.execute("""
                    SELECT crs_id FROM app_tcp WHERE id = %s LIMIT 1
                """, [decrypted_id])
                result = cursor.fetchone()
                if result:
                    user_id = result[0]
                else:
                    return JsonResponse({'error': 'Application not found (no user_id)'}, status=404)
            
        with connections['dniis_db'].cursor() as cursor:
            cursor.execute("""
                SELECT cel_no, email, fullname, business_type
                FROM systems_clients
                WHERE user_id = %s
                LIMIT 1
            """, [user_id])
            client_row = cursor.fetchone()
            if client_row:
                data['client_cel_no'] = client_row[0]
                data['client_email'] = client_row[1]
                data['client_name'] = client_row[2]
                data['app_type'] = client_row[3]  # business_type
            else:
                data['client_cel_no'] = ''
                data['client_email'] = ''
                data['client_name'] = ''
                data['app_type'] = ''
                    
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'Application not found'}, status=404)
    
    
    
    
# DENR EMPLOYEE
def process_application(request):
    # Check if the user is authenticated (you can implement your own authentication logic here)
    if request.session.get('authenticated'):
        return render(request, 'processApplications.html')
    else:
        return render(request, 'login.html', {'error': 'You need to log in first.'})
    
@csrf_exempt
def application_list_json_emp(request):
    user_id = request.session.get('user_id')

    ch_user_type = None
    tcp_user_type = None
    tcp_total = 0
    ch_total = 0
    tcp_filtered  = 0
    ch_filtered = 0

    # Check ch_access_level
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            SELECT type
            FROM ch_access_level
            WHERE userid = %s
            LIMIT 1
        """, [user_id])
        result = cursor.fetchone()
        if result:
            ch_user_type = result[0]

    # Check tcp_db user_access
    with connections['tcp_db'].cursor() as cursor:
        cursor.execute("""
            SELECT type
            FROM user_access
            WHERE userid = %s
            LIMIT 1
        """, [user_id])
        result = cursor.fetchone()
        if result:
            tcp_user_type = result[0]

    # If no access found in both databases
    if ch_user_type is None and tcp_user_type is None:
        return JsonResponse({
            'draw': 1,
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': 'You do not have an access to this system.'
        }, status=403)


    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))
    search_value = request.POST.get('search[value]', '').strip().lower()
    order_column = int(request.POST.get('order[0][column]', 0))
    order_dir = request.POST.get('order[0][dir]', 'asc')

    column_names = [
        'permit_type',
        'estab_name',
        'reference_no',
        'date_applied',
        'status',
        'client_remarks',
    ]
    sort_column = column_names[order_column] if order_column < len(column_names) else 'date_applied'
    reverse = order_dir == 'desc'

    data = []

    if(tcp_user_type == 'admin'):
        # --- TCP COUNT ---
        with connections['tcp_db'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM app_tcp a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM app_application
                        WHERE id IN (SELECT MAX(id) FROM app_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(COALESCE(a.reference_no_new, a.reference_no)) LIKE %s OR
                        LOWER(a.status) LIKE %s
                """, [like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM app_tcp")
            tcp_filtered = cursor.fetchone()[0]
            tcp_total = tcp_filtered
            
            
        # --- TCP DATA ---
        with connections['tcp_db'].cursor() as cursor:
            tcp_filter = ""
            tcp_params = []

            if search_value:
                tcp_filter = """
                    WHERE
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(COALESCE(a.reference_no_new, a.reference_no)) LIKE %s OR
                        LOWER(a.status) LIKE %s
                """
                like_term = f"%{search_value}%"
                tcp_params = [like_term, like_term, like_term]

            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'TCP' AS permit_type_short,
                    a.estab_name,
                    COALESCE(a.reference_no_new, a.reference_no) AS reference_no,
                    a.date_applied,
                    CONCAT(
                        UPPER(SUBSTRING(a.status FROM 1 FOR 1)),
                        LOWER(SUBSTRING(a.status FROM 2)),
                        ' - ',
                        c.notes
                    ) AS status,
                    c.remarks AS client_remarks,
                    a.permit_type,
                    a.remarks AS curr_assign
                FROM app_tcp a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id, notes
                    FROM app_application
                    WHERE id IN (
                        SELECT MAX(id) FROM app_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {tcp_filter}
            """, tcp_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, estab_name, reference_no, date_applied, status, client_remarks, permit_type, curr_assign = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly used
                    'permit_type': {
                        'tcp': 'Tree Cutting Permit',
                        'stcp': 'Special Tree Cutting Permit',
                        'tebp': 'Tree-Earth-Balling Permit',
                        'stebp': 'Special Tree-Earth-Balling Permit',
                        'tpp': 'Tree-Pruning Permit',
                    }.get(permit_type, (permit_type or 'UNKNOWN').upper()),
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                })

    if(ch_user_type == 'admin'):
        # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                """, [like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM cps_chimport")
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                """
                like_term = f"%{search_value}%"
                ch_params = [like_term, like_term, like_term]

            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                })

    if(tcp_user_type == 'fus_evaluator'):
        # --- TCP COUNT ---
        with connections['tcp_db'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM app_tcp a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM app_application
                        WHERE id IN (SELECT MAX(id) FROM app_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        a.evaluator_id = %s AND a.remarks = %s AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(COALESCE(a.reference_no_new, a.reference_no)) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """, [user_id, 'fus_evaluator', like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM app_tcp where evaluator_id = %s AND remarks = %s", [user_id, 'fus_evaluator'])
            tcp_filtered = cursor.fetchone()[0]
            tcp_total = tcp_filtered
            
        # --- TCP DATA ---
        with connections['tcp_db'].cursor() as cursor:
            tcp_filter = ""
            tcp_params = []

            if search_value:
                tcp_filter = """
                    WHERE
                        evaluator_id = %s AND a.remarks = %s  AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(COALESCE(a.reference_no_new, a.reference_no)) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                tcp_params = [user_id, 'fus_evaluator', like_term, like_term, like_term]
            else:
                tcp_filter = """
                    WHERE
                        a.evaluator_id = %s
                        AND a.remarks = %s 
                """
                tcp_params = [user_id, 'fus_evaluator']
                
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'TCP' AS permit_type_short,
                    a.estab_name,
                    COALESCE(a.reference_no_new, a.reference_no) AS reference_no,
                    a.date_applied,
                    CONCAT(
                        UPPER(SUBSTRING(a.status FROM 1 FOR 1)),
                        LOWER(SUBSTRING(a.status FROM 2)),
                        ' - ',
                        c.notes
                    ) AS status,
                    c.remarks AS client_remarks,
                    a.permit_type,
                    a.remarks AS curr_assign
                FROM app_tcp a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id, notes
                    FROM app_application
                    WHERE id IN (
                        SELECT MAX(id) FROM app_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {tcp_filter}
            """, tcp_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, estab_name, reference_no, date_applied, status, client_remarks, permit_type, curr_assign = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly used
                    'permit_type': {
                        'tcp': 'Tree Cutting Permit',
                        'stcp': 'Special Tree Cutting Permit',
                        'tebp': 'Tree-Earth-Balling Permit',
                        'stebp': 'Special Tree-Earth-Balling Permit',
                        'tpp': 'Tree-Pruning Permit',
                    }.get(permit_type, (permit_type or 'UNKNOWN').upper()),
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                })
             
    if(ch_user_type == 'fus_evaluator'):
         # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        c.forwarded_to_id = %s AND a.remarks = %s AND (
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                        )
                """, [user_id, 'fus_evaluator', like_term, like_term, like_term])
            else:
                cursor.execute("""SELECT COUNT(*) FROM cps_chimport a LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application a
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id WHERE c.forwarded_to_id = %s AND a.remarks = %s""", [user_id, 'fus_evaluator'])
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        c.forwarded_to_id = %s AND a.remarks = %s AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(a.reference_no) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                ch_params = [user_id, 'fus_evaluator', like_term, like_term, like_term]
            else:
                ch_filter = """
                    WHERE
                        c.forwarded_to_id = %s
                        AND a.remarks = %s 
                """
                ch_params = [user_id, 'fus_evaluator']
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign,
                    CASE 
                        WHEN ir.id IS NOT NULL THEN 1
                        ELSE 0
                    END AS inspection_exists
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                LEFT JOIN cps_inspectionreport ir ON a.id = ir.application_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign, inspection_exists = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                    'inspection_exists': inspection_exists,
                })
                
    if(ch_user_type == 'cashier'):
         # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    LEFT JOIN ch_payment p ON a.id = p.app_id
                    WHERE
                        p.status = '1' AND (
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                        )
                """, [like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM cps_chimport a LEFT JOIN ch_payment p ON a.id = p.app_id WHERE p.status = '1'")
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        p.status = '1' AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(a.reference_no) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                ch_params = [like_term, like_term, like_term]
            else:
                ch_filter = """
                    WHERE
                        p.status = '1'
                """
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign,
                    p.id AS payment_id
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                LEFT JOIN ch_payment p ON a.id = p.app_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign, payment_id = row
                data.append({
                    'user_type': ch_user_type,
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                    'payment_id': payment_id,
                })            

    if(ch_user_type == 'fus_sc'):
         # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        a.remarks = %s AND (
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                        )
                """, ['fus_sc', like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM cps_chimport WHERE remarks = %s", ['fus_sc'])
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        a.remarks = %s AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(a.reference_no) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                ch_params = ['fus_sc', like_term, like_term, like_term]
            else:
                ch_filter = """
                    WHERE
                        a.remarks = %s 
                """
                ch_params = ['fus_sc']
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign,
                    c.action AS curr_action
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id, action
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign, curr_action = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                    'curr_action': curr_action,
                })
                
    if(ch_user_type == 'lpdd_dc'):
         # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        a.remarks = %s AND (
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                        )
                """, ['lpdd_dc', like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM cps_chimport WHERE remarks = %s", ['lpdd_dc'])
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        a.remarks = %s AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(a.reference_no) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                ch_params = ['lpdd_dc', like_term, like_term, like_term]
            else:
                ch_filter = """
                    WHERE
                        a.remarks = %s 
                """
                ch_params = ['lpdd_dc']
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign,
                    c.action AS curr_action
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id, action
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign, curr_action = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                    'curr_action': curr_action,
                })
                
    if(ch_user_type == 'ard_ts'):
        # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        a.remarks = %s AND (
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                        )
                """, ['ard_ts', like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM cps_chimport WHERE remarks = %s", ['ard_ts'])
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        a.remarks = %s AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(a.reference_no) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                ch_params = ['ard_ts', like_term, like_term, like_term]
            else:
                ch_filter = """
                    WHERE
                        a.remarks = %s 
                """
                ch_params = ['ard_ts']
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign,
                    c.action AS curr_action
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id, action
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign, curr_action = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                    'curr_action': curr_action,
                }) 
       
    if(ch_user_type == 'red'):
        # --- CHIMPORT COUNT ---
        with connections['default'].cursor() as cursor:
            if search_value:
                like_term = f'%{search_value}%'
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM cps_chimport a
                    LEFT JOIN (
                        SELECT app_id, remarks, forwarded_to_id
                        FROM ch_application
                        WHERE id IN (SELECT MAX(id) FROM ch_application GROUP BY app_id)
                    ) c ON a.id = c.app_id
                    WHERE
                        a.remarks = %s AND (
                        LOWER(a.estab_name) LIKE %s OR
                        LOWER(a.reference_no) LIKE %s OR
                        LOWER(a.status) LIKE %s
                        )
                """, ['red', like_term, like_term, like_term])
            else:
                cursor.execute("SELECT COUNT(*) FROM cps_chimport WHERE remarks = %s", ['red'])
            ch_filtered = cursor.fetchone()[0]
            ch_total = ch_filtered
            
        # --- CHIMPORT DATA ---
        with connections['default'].cursor() as cursor:
            ch_filter = ""
            ch_params = []

            if search_value:
                ch_filter = """
                    WHERE
                        a.remarks = %s AND (
                            LOWER(a.estab_name) LIKE %s OR
                            LOWER(a.reference_no) LIKE %s OR
                            LOWER(a.status) LIKE %s
                        )
                """
                like_term = f"%{search_value}%"
                ch_params = ['red', like_term, like_term, like_term]
            else:
                ch_filter = """
                    WHERE
                        a.remarks = %s 
                """
                ch_params = ['red']
                
            cursor.execute(f"""
                SELECT 
                    a.id as app_id,
                    a.crs_id,
                    'PIC' AS permit_type_short,
                    'Permit to Import Chainsaw' AS permit_type,
                    a.estab_name,
                    a.reference_no,
                    a.date_applied,
                    a.status,
                    c.remarks AS client_remarks,
                    a.remarks AS curr_assign,
                    c.action AS curr_action
                FROM cps_chimport a
                LEFT JOIN (
                    SELECT app_id, remarks, forwarded_to_id, action
                    FROM ch_application
                    WHERE id IN (
                        SELECT MAX(id) FROM ch_application GROUP BY app_id
                    )
                ) c ON a.id = c.app_id
                {ch_filter}
            """, ch_params)

            for row in cursor.fetchall():
                app_id, crs_id, permit_type_short, permit_type, estab_name, reference_no, date_applied, status, client_remarks, curr_assign, curr_action = row
                data.append({
                    'app_id': encrypt_id(app_id),
                    'crs_id': crs_id,
                    'permit_type_short': permit_type_short,  # Now correctly taken from SELECT
                    'permit_type': permit_type,
                    'estab_name': estab_name,
                    'reference_no': reference_no,
                    'date_applied': date_applied,
                    'status': status,
                    'client_remarks': client_remarks,
                    'curr_assign': curr_assign,
                    'curr_action': curr_action,
                }) 
                                   
    # --- SORT + PAGINATE ---
    def safe_key(item):
        value = item.get(sort_column)
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value or '').lower()

    data.sort(key=safe_key, reverse=reverse)
    paginated_data = data[start:start + length]
    

    return JsonResponse({
        'draw': draw,
        'recordsTotal': tcp_total + ch_total,
        'recordsFiltered': tcp_filtered + ch_filtered,
        'data': paginated_data,
    })
    
@csrf_exempt
def process_application_action(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                
                app_id = request.POST.get('app_id')
                try:
                    decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
                except Exception:
                    return HttpResponseBadRequest("Invalid or tampered ID")
                
                crs_id = request.POST.get('crsid')
                reference_no = request.POST.get('reference_no')
                remarks = request.POST.get('remarks', '').strip()
                action = request.POST.get('action')
                notes = request.POST.get('notes')
                status = request.POST.get('status')
                permit_type_short = request.POST.get('permit_type_short')
                chi_remarks = request.POST.get('chi_remarks')
                chi_status = request.POST.get('chi_status')

                if not all([decrypted_id, reference_no, remarks, permit_type_short]):
                    return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

                user_id = request.session.get('user_id')
                
                # ✅ Create CHApplication record
                CHApplication.objects.create(
                    date_created=timezone.now(),
                    app_id=decrypted_id,
                    reference_no=reference_no,
                    forwarded_by_id=request.session.get('user_id'),
                    forwarded_to_id = crs_id,
                    action=action,
                    notes=notes,
                    remarks=remarks,
                    status=status,
                    days_pending=0
                )
                
                CHImport.objects.filter(id=int(decrypted_id)).update(
                    remarks=chi_remarks,
                    status=chi_status
                )
                
                if permit_type_short == 'PIC' and notes == 'For Payment':
                    # Generate OP number
                    today = datetime.now().strftime('%Y-%m-%d')
                    op_number = f"{today}-OP-{permit_type_short}-{decrypted_id}"
                
                    # Create Order of Payment
                    ChPayment.objects.create(
                        app_id=decrypted_id,
                        op_id=op_number,
                        date_paid=None,  # Set to None initially
                        or_no=None,  # Set to None initially
                        amount=500,  # Default amount, can be updated later
                        fund_cluster='01101101',
                        type=permit_type_short,
                        status=0
                    )

            return JsonResponse({'success': True, 'message': 'Application returned to client successfully.'})

        except Exception as e:
            # No need to call transaction.set_rollback(True); it happens automatically in an atomic block
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def upload_proof(request):
    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        payment_id = request.POST.get('payment_id')
        uploaded_files = request.FILES.getlist('proof_file')
        or_no = request.POST.get('or_no')

        if not uploaded_files:
            return JsonResponse({'success': False, 'message': 'No files received'})

        upload_dir = os.path.join(settings.MEDIA_ROOT, 'proof_of_payment')
        os.makedirs(upload_dir, exist_ok=True)

        try:
            with transaction.atomic():
                for file in uploaded_files:
                    original_name = file.name
                    extension = os.path.splitext(original_name)[1]
                    timestamp = int(time.time() * 1000)

                    new_file_name = f"{payment_id}_proof_{timestamp}{extension}"
                    file_path = os.path.join(upload_dir, new_file_name)

                    while os.path.exists(file_path):
                        timestamp += 1
                        new_file_name = f"{payment_id}_proof_{timestamp}{extension}"
                        file_path = os.path.join(upload_dir, new_file_name)

                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    # Save proof record
                    ProofOfPayment.objects.create(
                        app_id=app_id,
                        payment_id=payment_id,
                        file_name=new_file_name,
                        file_location=os.path.join('proof_of_payment', new_file_name),
                        date_uploaded=timezone.now()
                    )

                # ✅ Update ChPayment after all files are processed
                try:
                    payment = ChPayment.objects.get(id=payment_id)
                    payment.or_no = or_no
                    payment.date_paid = timezone.now().date()
                    payment.status = 1  # Paid
                    payment.save()
                except ChPayment.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Payment record not found'})
                
                

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
def confirm_payment_action(request):
    
    app_id = request.POST.get('app_id')
    try:
        decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")

    if request.method == 'POST':
        
        try:
            with transaction.atomic():
                payment_id = request.POST.get('payment_id')

                # Update ChPayment status
                ChPayment.objects.filter(id=int(payment_id)).update(
                    lbp_ref_no=request.POST.get('chi_lbp_ref_no'),
                    status=2,
                    date_confirmed=timezone.now().date()
                )
                
                #ch_application
                reference_no = request.POST.get('reference_no')
                forwarded_to = request.POST.get('forwarded_to')
                action = request.POST.get('action')
                notes = request.POST.get('notes')
                remarks = request.POST.get('remarks', '').strip()
                status = request.POST.get('status')
                
                chi_remarks = request.POST.get('chi_remarks')
                chi_status = request.POST.get('chi_status')

                # ✅ Create CHApplication record
                CHApplication.objects.create(
                    date_created=timezone.now(),
                    app_id=decrypted_id,
                    reference_no=reference_no,
                    forwarded_by_id=request.session.get('user_id'),
                    forwarded_to_id = forwarded_to,
                    action=action,
                    notes=notes,
                    remarks=remarks,
                    status=status,
                    days_pending=0
                )
                
                #chimport
                CHImport.objects.filter(id=int(decrypted_id)).update(
                    remarks=chi_remarks,
                    status=chi_status
                )

            return JsonResponse({'success': True, 'message': 'Payment action processed successfully.'})
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@csrf_exempt
def process_application_action_emp(request):
    app_id = request.POST.get('app_id')
    try:
        decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                
                #ch_application
                reference_no = request.POST.get('reference_no')
                forwarded_to = request.POST.get('forwarded_to')
                action = request.POST.get('action')
                notes = request.POST.get('notes')
                remarks = request.POST.get('remarks', '').strip()
                status = request.POST.get('status')
                
                chi_remarks = request.POST.get('chi_remarks')
                chi_status = request.POST.get('chi_status')

                # ✅ Create CHApplication record
                CHApplication.objects.create(
                    date_created=timezone.now(),
                    app_id=decrypted_id,
                    reference_no=reference_no,
                    forwarded_by_id=request.session.get('user_id'),
                    forwarded_to_id = forwarded_to,
                    action=action,
                    notes=notes,
                    remarks=remarks,
                    status=status,
                    days_pending=0
                )
                
                #chimport
                update_fields = {
                    'remarks': chi_remarks,
                    'status': chi_status
                }

                # If status is 'approved', also update date_approved
                if chi_status.lower() == 'approved':
                    update_fields['date_approved'] = timezone.now()

                # Perform update
                CHImport.objects.filter(id=int(decrypted_id)).update(**update_fields)

            return JsonResponse({'success': True, 'message': 'Transaction processed successfully.'})
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


def get_action_officer(request):
    try:
        # Step 1: Get access records from default DB (ch_access_level)
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT id, userid, type
                FROM ch_access_level
                WHERE type = %s
            """, ['fus_evaluator'])
            access_rows = cursor.fetchall()

        officers = []

        # Step 2: Get user details from dniis_db (core_users)
        for row in access_rows:
            ch_id, userid, user_type = row

            with connections['dniis_db'].cursor() as cursor:
                cursor.execute("""
                    SELECT name FROM core_users WHERE id = %s
                """, [userid])
                user = cursor.fetchone()

            fullname = user[0] if user else ''

            officers.append({
                'id': ch_id,
                'userid': userid,
                'fullname': fullname,
                'user_type': user_type
            })

        # Step 3: Determine current handler (from cps or chimport)
        evaluator_id = None
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT evaluator_id FROM cps_chimport WHERE evaluator_id IS NOT NULL LIMIT 1")
            result = cursor.fetchone()
            if result and result[0]:
                evaluator_id = result[0]
            else:
                cursor.execute("SELECT evaluator_id FROM cps_chimport WHERE evaluator_id IS NOT NULL LIMIT 1")
                result = cursor.fetchone()
                if result and result[0]:
                    evaluator_id = result[0]

        current_handler_name = ''
        if evaluator_id:
            with connections['dniis_db'].cursor() as cursor:
                cursor.execute("SELECT name FROM core_users WHERE id = %s", [evaluator_id])
                user = cursor.fetchone()
                current_handler_name = user[0] if user else ''
                
        return JsonResponse({'success': True, 
                             'officers': officers,
                             'current_handler': current_handler_name})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    
def assign_action_officer(request):
    app_id = request.POST.get('app_id')
    try:
        decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                
                reference_no = request.POST.get('reference_no')
                action_officer_id = request.POST.get('officer_id')
                action = request.POST.get('action')
                notes = request.POST.get('notes')
                status = request.POST.get('status')
                chi_remarks = request.POST.get('chi_remarks')
                chi_status = request.POST.get('chi_status')
                
                # ✅ Create CHApplication record
                CHApplication.objects.create(
                    date_created=timezone.now(),
                    app_id=decrypted_id,
                    reference_no=reference_no,
                    forwarded_by_id=request.session.get('user_id'),
                    forwarded_to_id = action_officer_id,
                    action=action,
                    notes=notes,
                    remarks=action,
                    status=status,
                    days_pending=0
                )
                
                CHImport.objects.filter(id=int(decrypted_id)).update(
                    remarks=chi_remarks,
                    status=chi_status,
                    action_officer_id=action_officer_id
                )
                

            return JsonResponse({'success': True, 'message': 'Application assigned to Action Officer successfully.'})

        except Exception as e:
            # No need to call transaction.set_rollback(True); it happens automatically in an atomic block
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


def submit_inspection_report(request):
    if request.method == 'POST':
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'inspection_attachments')
        os.makedirs(upload_dir, exist_ok=True)
        
        print("FILES IN REQUEST:", request.FILES)
        print("FILES RECEIVED:", len(request.FILES.getlist('ir_attachments')))
        
        app_id = request.POST.get('app_id_ir')
        
        try:
            decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
        except Exception:
            return HttpResponseBadRequest("Invalid or tampered ID")
        
        try:
            with transaction.atomic():
                reference_no = request.POST.get('reference_no_ir')
                inspection_report_text = request.POST.get('inspection_report_text', '').strip()
                ir_attachments = request.FILES.getlist('ir_attachments')

                print("FILES RECEIVED:", len(ir_attachments))

                if not all([decrypted_id, reference_no, inspection_report_text]):
                    return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

                application = CHImport.objects.get(id=int(decrypted_id))

                report = InspectionReport.objects.create(
                    application_id=application.id,
                    inspector=request.session.get('user_id'),
                    report_content=inspection_report_text
                )

                for file in ir_attachments:
                    original_name = file.name
                    extension = os.path.splitext(original_name)[1]
                    timestamp = int(time.time() * 1000)

                    new_file_name = f"{decrypted_id}_IR_{timestamp}{extension}"
                    file_path = os.path.join(upload_dir, new_file_name)

                    while os.path.exists(file_path):
                        timestamp += 1
                        new_file_name = f"{decrypted_id}_IR_{timestamp}{extension}"
                        file_path = os.path.join(upload_dir, new_file_name)

                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    relative_path = os.path.join('inspection_attachments', new_file_name)
                    print("Saving attachment:", relative_path)

                    InspectionAttachment.objects.create(
                        report=report,
                        file_path=relative_path
                    )

            return JsonResponse({'success': True, 'message': 'Inspection report submitted successfully.'})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


def get_ir_details(request):
    appid = request.GET.get('appid')
    permit_type_short = request.GET.get('permit_type_short', '').lower()

    try:
        decrypted_id = decrypt_id(appid)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")
        
    if not appid or permit_type_short != 'pic':
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    data = {'app_id': decrypted_id}

    # Step 1: Fetch inspection report
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            SELECT id, inspector, report_content, created_at, updated_at
            FROM cps_inspectionreport
            WHERE application_id = %s
            LIMIT 1
        """, [decrypted_id])
        report = cursor.fetchone()

    if not report:
        return JsonResponse({'error': 'Inspection report not found'}, status=404)

    report_id, inspector_id, report_content, created_at, updated_at = report
    data.update({
        'report_id': report_id,
        'inspector_id': inspector_id,
        'report_content': report_content,
        'created_at': created_at,
        'updated_at': updated_at
    })

    # Step 2: Fetch inspector name from core_users (in dniis_db)
    with connections['dniis_db'].cursor() as cursor:
        cursor.execute("""
            SELECT name
            FROM core_users
            WHERE id = %s
            LIMIT 1
        """, [inspector_id])
        user_row = cursor.fetchone()
        data['inspector_name'] = user_row[0] if user_row else ''

    # Step 3: Fetch attachments
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            SELECT file_path
            FROM cps_inspectionattachment
            WHERE report_id = %s
        """, [report_id])
        attachments = cursor.fetchall()
        data['attachments'] = [row[0] for row in attachments] if attachments else []

    return JsonResponse(data)

@csrf_exempt
def save_ir(request):
    app_id = request.POST.get('app_id')
    try:
        decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")
        
    if request.method == 'POST':
        try:
            with transaction.atomic():
                report_content = request.POST.get('report_content', '').strip()
                removed_attachments = request.POST.getlist('removed_attachments[]')
                ir_attachments = request.FILES.getlist('new_attachments[]')

                if not decrypted_id or not report_content:
                    return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

                # Ensure upload directory exists
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'inspection_attachments')
                os.makedirs(upload_dir, exist_ok=True)

                # Get or create the InspectionReport instance
                report, created = InspectionReport.objects.get_or_create(application_id=decrypted_id)

                # Optional: Update inspector if not yet assigned
                if created and request.session.get('user_id'):
                    report.inspector_id = request.session.get('user_id')

                # Update report content
                report.report_content = report_content
                report.save()

                # Delete removed attachments (from DB and disk)
                for rel_path in removed_attachments:
                    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                    if os.path.exists(abs_path):
                        os.remove(abs_path)
                    InspectionAttachment.objects.filter(report=report, file_path=rel_path).delete()

                # Save new uploaded files
                for file in ir_attachments:
                    original_name = file.name
                    extension = os.path.splitext(original_name)[1]
                    timestamp = int(time.time() * 1000)

                    new_file_name = f"{decrypted_id}_IR_{timestamp}{extension}"
                    file_path = os.path.join(upload_dir, new_file_name)

                    while os.path.exists(file_path):
                        timestamp += 1
                        new_file_name = f"{decrypted_id}_IR_{timestamp}{extension}"
                        file_path = os.path.join(upload_dir, new_file_name)

                    with open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    relative_path = os.path.join('inspection_attachments', new_file_name)

                    InspectionAttachment.objects.create(
                        report=report,
                        file_path=relative_path
                    )

                return JsonResponse({'status': 'success'})

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def weekdays_between(start_date, end_date):
    """
    Count business days between two dates.
    - Excludes start_date
    - Includes end_date
    - Skips Saturday/Sunday
    Automatically handles reversed dates.
    """
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    day_count = 0
    current_date = start_date + timedelta(days=1)  # start counting *after* start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # 0=Mon ... 4=Fri
            day_count += 1
        current_date += timedelta(days=1)
    return day_count


def transaction_history(request):
    reference_no = request.GET.get("reference_no")
    if not reference_no:
        return JsonResponse({"data": []})

    # 1. Get all rows from ch_application
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            SELECT date_created, forwarded_by_id, forwarded_to_id, notes, remarks, status
            FROM ch_application
            WHERE reference_no = %s
            ORDER BY date_created DESC
        """, [reference_no])
        rows = cursor.fetchall()

    # 2. Collect user IDs
    user_ids = {f_by for _, f_by, f_to, _, _, _ in rows if f_by} | \
               {f_to for _, f_by, f_to, _, _, _ in rows if f_to}

    # 3. Get user names in one query
    user_map = {}
    if user_ids:
        with connections['dniis_db'].cursor() as cursor:
            sql = "SELECT id, name FROM core_users WHERE id IN (%s)" % \
                  ",".join(["%s"] * len(user_ids))
            cursor.execute(sql, list(user_ids))
            user_map = {u: n for u, n in cursor.fetchall()}

    # 4. Prepare data
    data = []
    prev_date = None
    for date_created, f_by, f_to, notes, remarks, status in rows:
        days_processed = weekdays_between(date_created.date(), prev_date.date()) if prev_date and date_created else 0
        prev_date = date_created or prev_date
        data.append({
            "days_processed": days_processed,
            "date_received": date_created.strftime("%Y-%m-%d") if date_created else "",
            "created_by": user_map.get(f_by, f_by or ""),
            "forwarded_to": user_map.get(f_to, f_to or ""),
            "notes": notes or "",
            "remarks": remarks or "",
            "status": status.capitalize() if status else "",
        })

    return JsonResponse({"data": data})

def css(request, permitType, app_id):
    try:
        decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
    except Exception:
        return HttpResponseBadRequest("Invalid or tampered ID")

    if permitType.lower() != 'pic':
        return HttpResponseBadRequest("Invalid permit type for CSS")

    # Fetch application details
    try:
        application = CHImport.objects.get(id=decrypted_id)
    except CHImport.DoesNotExist:
        return HttpResponseBadRequest("Application not found")

    # Fetch user name from core_users using crs_id
    user_name = ""
    with connections['dniis_db'].cursor() as cursor:
        cursor.execute("SELECT fullname, business_type FROM systems_clients WHERE user_id = %s", [application.crs_id])
        row = cursor.fetchone()
        if row:
            user_name = row[0]
            if row[1]:
                code = row[1]
                if code == '1':
                    app_type = 'Individual'
                elif code == '2':
                    app_type = 'Government'
                elif code == '3':
                    app_type = 'Corporation'

    context = {
        'reference_no': application.reference_no,
        'date_now': datetime.now().strftime('%B %d, %Y'),
        'app_id': app_id,
        'crs_name': user_name,
        'crs_id': application.crs_id,
        'date_applied': application.date_applied.strftime('%B %d, %Y'),
        'app_type': app_type if 'app_type' in locals() else 'Unknown',
        'date_approved': application.date_approved.strftime('%B %d, %Y'),
    }

    return render(request, 'css.html', context)


def save_survey(request, app_id):
    try:
        with transaction.atomic():
                
            try:
                decrypted_id = decrypt_id(app_id)  # Decrypt the encrypted ID
            except Exception:
                return HttpResponseBadRequest("Invalid or tampered ID")
            
            if request.method == "POST":
                application = get_object_or_404(CHImport, id=decrypted_id)

                # Create a new survey entry
                survey = Survey.objects.create(
                    application=application,
                    client_id=request.POST.get('crs_id'),
                    cc1=request.POST.get('cc1'),
                    cc2=request.POST.get('cc2'),
                    cc3=request.POST.get('cc3'),
                    cc41=request.POST.get('cc41'),
                    cc42=request.POST.get('cc42'),
                    cc43=request.POST.get('cc43'),
                    cc44=request.POST.get('cc44'),
                    cc45=request.POST.get('cc45'),
                    cc46=request.POST.get('cc46'),
                    cc47=request.POST.get('cc47'),
                    cc48=request.POST.get('cc48'),
                    cc49=request.POST.get('cc49'),
                    suggestions=request.POST.get('suggestions'),
                )
                
                CHImport.objects.filter(id=int(decrypted_id)).update(
                    survey = 1
                )

                # You can return a success response
                return JsonResponse({"status": "success", "survey_id": survey.id})

            return JsonResponse({"status": "error", "message": "Invalid request"})
        
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)