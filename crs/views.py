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
                    
                    #Check if user is blocked
                    print("User verification status:", user[5])
                    if user[5] == "1":
                        return JsonResponse({'success': False, 'message': 'User is not yet verified.'})
             
                    # Store the user_id and fullname in the session
                    request.session['user_id'] = user[0] #id
                    request.session['fullname'] = user[1] #name
                    
                    
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
    search_value = request.POST.get('search[value]', '').strip()
    order_column = int(request.POST.get('order[0][column]', 0))
    order_dir = request.POST.get('order[0][dir]', 'asc')

    # You can change the column ordering if needed
    column_names = [
        'permit_type',
        'estab_name',
        'reference_no',
        'date_applied',
        'status',
        'client_remarks',
    ]
    sort_column = column_names[order_column] if order_column < len(column_names) else 'a.id'

    with connections['tcp_db'].cursor() as cursor:
        # Total records
        cursor.execute("""
            SELECT COUNT(*) FROM app_tcp a
            LEFT JOIN (
                SELECT id AS client_id, app_id, forwarded_to_id, remarks AS client_remarks, notes AS client_notes
                FROM app_application 
                WHERE id IN (
                    SELECT MAX(id) FROM app_application GROUP BY app_id
                )
            ) AS c ON c.app_id = a.id
            WHERE c.forwarded_to_id = %s
        """, [user_id])
        total_records = cursor.fetchone()[0]

        # Main query with filtering
        filter_sql = ""
        filter_params = []

        if search_value:
            filter_sql = """
                AND (
                    b.address LIKE %s OR
                    c.client_remarks LIKE %s OR
                    c.client_notes LIKE %s
                )
            """
            like_search = f"%{search_value}%"
            filter_params.extend([like_search] * 3)

        base_query = f"""
            SELECT 
                a.*,
                b.address AS tree_address, 
                b.longitude, 
                b.latitude,
                c.client_remarks,
                c.client_notes,
                c.client_id,
                c.forwarded_to_id,
                d.action_officer_id,
                y.date_paid
            FROM app_tcp a 
            LEFT JOIN tree_location b ON a.tree_location_id = b.id
            LEFT JOIN (
                SELECT 
                    id AS client_id, 
                    app_id, 
                    forwarded_to_id, 
                    remarks AS client_remarks, 
                    notes AS client_notes
                FROM app_application 
                WHERE id IN (
                    SELECT MAX(id) FROM app_application GROUP BY app_id
                )
            ) AS c ON c.app_id = a.id
            LEFT JOIN (
                SELECT 
                    id AS nr_id, 
                    app_id, 
                    action_officer_id
                FROM tcp_narrative_report 
                WHERE id IN (
                    SELECT MAX(id) FROM tcp_narrative_report GROUP BY app_id
                )
            ) AS d ON d.app_id = a.id
            LEFT JOIN (
                SELECT 
                    app_id, 
                    date_paid
                FROM payment 
                WHERE id IN (
                    SELECT MAX(id) FROM payment GROUP BY app_id
                )
            ) AS y ON y.app_id = a.id
            WHERE c.forwarded_to_id = %s {filter_sql}
            ORDER BY {sort_column} {order_dir}
            LIMIT %s OFFSET %s
        """

        params = [user_id] + filter_params + [length, start]
        cursor.execute(base_query, params)

        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        
        data = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            
            # Ensure permit_type is uppercase
            if 'permit_type' in row_dict and row_dict['permit_type']:
                row_dict['permit_type'] = row_dict['permit_type'].upper()

            # Show reference_no_new if available, otherwise reference_no
            if 'reference_no_new' in row_dict and row_dict['reference_no_new']:
                row_dict['reference_no'] = row_dict['reference_no_new']
                
            data.append(row_dict)

        # Total filtered count
        if search_value:
            cursor.execute(f"""
                SELECT COUNT(*) FROM app_tcp a 
                LEFT JOIN tree_location b ON a.tree_location_id = b.id
                LEFT JOIN (
                    SELECT id AS client_id, app_id, forwarded_to_id, remarks AS client_remarks, notes AS client_notes
                    FROM app_application WHERE id IN (
                        SELECT MAX(id) FROM app_application GROUP BY app_id
                    )
                ) AS c ON c.app_id = a.id
                WHERE c.forwarded_to_id = %s {filter_sql}
            """, [user_id] + filter_params)
            total_filtered = cursor.fetchone()[0]
        else:
            total_filtered = total_records

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_filtered,
        'data': data
    })