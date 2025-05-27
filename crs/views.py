from django.shortcuts import render
from django.db import connections
from django.http import JsonResponse
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

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from operator import itemgetter


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
                    
                   
                    if not user:
                        # DENR NCR Employee Account
                        cursor.execute("SELECT * FROM core_users WHERE username = %s", [username])
                        user = cursor.fetchone()
                        request.session['user_id'] = user[0] #id
                        request.session['user_type'] = 'DENR Employee' #user_type
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

    data = []

    # TCP APP DATA
    with connections['tcp_db'].cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                'TCP' AS permit_type_short,
                a.*,
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
                END AS client_remarks
            FROM app_tcp a
            LEFT JOIN (
                SELECT app_id, remarks, forwarded_to_id
                FROM app_application
                WHERE id IN (
                    SELECT MAX(id) FROM app_application GROUP BY app_id
                )
            ) c ON a.id = c.app_id
            WHERE a.crs_id = %s
        """, [user_id, user_id, user_id])
        tcp_results = cursor.fetchall()
        tcp_columns = [col[0] for col in cursor.description]
        
        for row in tcp_results:
            item = dict(zip(tcp_columns, row))
            if item.get('permit_type') == 'tcp':
                item['permit_type'] = 'Tree Cutting Permit'
            elif item.get('permit_type') == 'stcp':
                item['permit_type'] = 'Special Tree Cutting Permit'
            elif item.get('permit_type') == 'tebp':
                item['permit_type'] = 'Tree-Earth-Balling Permit'
            elif item.get('permit_type') == 'stebp':
                item['permit_type'] = 'Special Tree-Earth-Balling Permit'
            elif item.get('permit_type') == 'tpp':
                item['permit_type'] = 'Tree-Pruning Permit'
            else:
                item['permit_type'] = item.get('permit_type', '').upper()
            data.append(item)

    # CHIMPORT DATA (DEFAULT DB)
    with connections['default'].cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                'PIC' AS permit_type_short,
                'PIC' AS permit_type,
                a.estab_name,
                a.estab_address,
                a.estab_contact,
                a.estab_email,
                a.reference_no,
                a.date_applied,
                CASE 
                    WHEN c.forwarded_to_id = %s THEN 'Returned to Client'
                    ELSE a.status
                END AS status,
                CASE 
                    WHEN c.forwarded_to_id = %s THEN c.remarks
                    ELSE 'Pending'
                END AS client_remarks
            FROM cps_chimport a
            LEFT JOIN (
                SELECT app_id, remarks, forwarded_to_id
                FROM ch_application
                WHERE id IN (
                    SELECT MAX(id) FROM ch_application GROUP BY app_id
                )
            ) c ON a.id = c.app_id
            WHERE a.crs_id = %s
        """, [user_id, user_id, user_id])
        chimport_results = cursor.fetchall()
        chimport_columns = [col[0] for col in cursor.description]
        
        for row in chimport_results:
            item = dict(zip(chimport_columns, row))
            if item.get('permit_type') == 'PIC':
                item['permit_type'] = 'Permit to Import Chainsaw'
            else:
                item['permit_type'] = item.get('permit_type', '').upper()
            data.append(item)

    # Filter
    if search_value:
        data = [
            row for row in data if any(
                search_value in str(row.get(col, '')).lower()
                for col in column_names
            )
        ]

    # Total counts
    total_filtered = len(data)
    total_records = total_filtered  # Since we merged both sources

    # Sort
    reverse = order_dir == 'desc'
    data.sort(key=itemgetter(sort_column), reverse=reverse)

    # Paginate
    paginated_data = data[start:start + length]

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_filtered,
        'data': paginated_data,
    })
    
    
def get_application_details(request):
    reference_no = request.GET.get('reference_no')
    permit_type_short = request.GET.get('permit_type_short', '').lower()  # Normalize

    data = None

    if permit_type_short == 'pic':
        # Query CHIMPORT table (default DB)
        with connections['default'].cursor() as cursor:
            cursor.execute("""
                SELECT 
                    'PIC' AS permit_type_short,
                    'PIC' AS permit_type,
                    a.*,
                    b.name as brand_name,
                    a.remarks AS client_remarks
                FROM cps_chimport a
                LEFT JOIN cps_chainsawbrand b ON a.brand_id = b.id
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
        
    # ✅ Add session data if found
    if data is not None:
        data['app_type'] = request.session.get('app_type', 'N/A')
            
        user_id = request.session['user_id']
        with connections['dniis_db'].cursor() as cursor:
            cursor.execute("""
                SELECT cel_no, email
                FROM systems_clients
                WHERE user_id = %s
                LIMIT 1
            """, [user_id])
            client_row = cursor.fetchone()
            if client_row:
                data['client_cel_no'] = client_row[0]
                data['client_email'] = client_row[1]
            else:
                data['client_cel_no'] = ''
                data['client_email'] = ''
                    
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'Application not found'}, status=404)