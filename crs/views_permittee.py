# myapp/views_permittee.py
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connections

def index(request):
    # Check if the user is authenticated (you can implement your own authentication logic here)
    if request.session.get('authenticated'):
        return render(request, 'permittee/dashboard.html')
    else:
        return render(request, 'login.html', {'error': 'You need to log in first.'})
    
def permittee_list_json(request):
    
    draw = int(request.POST.get('draw', 1))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))
    search_value = request.POST.get('search[value]', '').strip()
    column_index = int(request.POST.get('order[0][column]', 0))
    order_direction = request.POST.get('order[0][dir]', 'asc')
        
    column_names = ['business_name', 'biz_address', 'email_biz', 'cel_no_biz']
    sort_column = column_names[column_index]
    
    with connections['dniis_db'].cursor() as cursor:

            cursor.execute("""SELECT COUNT(*) from systems_clients_27_repeat
                                        WHERE parent_id = %s AND business_name != '';""", [request.session['user_id']])
            total_records = cursor.fetchone()[0]
            
            
            if search_value:
                search_query = f"%{search_value}%"
                cursor.execute("""SELECT COUNT(*) from systems_clients_27_repeat
                                            WHERE parent_id = %s 
                                            AND business_name != ''
                                            AND (business_name LIKE %s OR biz_address LIKE %s)
                """, [request.session['user_id'], search_query, search_query])
                total_filtered = cursor.fetchone()[0]
            
                cursor.execute(f"""SELECT * FROM systems_clients_27_repeat
                               WHERE parent_id = %s 
                               AND business_name != ''
                               AND (business_name LIKE %s OR biz_address LIKE %s)
                               ORDER BY {sort_column} {order_direction}
                               LIMIT %s OFFSET %s""", 
                           [request.session['user_id'], search_query, search_query, length, start])
            else:
                total_filtered = total_records
                # Fetch all data with sorting
                cursor.execute(f"""SELECT * FROM systems_clients_27_repeat
                                WHERE parent_id = %s 
                                AND business_name != ''
                                ORDER BY {sort_column} {order_direction}
                                LIMIT %s OFFSET %s""", 
                            [request.session['user_id'], length, start])
            rows = cursor.fetchall()
        
    data = [{
        'permittee_name': row[2],
        'address': row[8],
        'email': row[10],
        'contact_no': f"{row[11]} / {row[12]}",
    } for row in rows]
    
    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_filtered,
        'data': data
    })
    
def add_permittee(request):
    if request.method == 'POST':
        client_id = request.session['user_id']
        businessName = request.POST.get('businessName')
        businessAddress = request.POST.get('businessAddress')
        businessEmail = request.POST.get('businessEmail')
        businessCel = request.POST.get('businessCel')
        businessTel = request.POST.get('businessTel')
        
        with connections['dniis_db'].cursor() as cursor:
            cursor.execute("""INSERT INTO systems_clients_27_repeat (parent_id, business_name, biz_address, email_biz, cel_no_biz, tel_no_biz)
                            VALUES (%s, %s, %s, %s, %s, %s)""", [client_id, businessName, businessAddress, businessEmail, businessCel, businessTel])
        
        return JsonResponse({'status': 'success', 'message': 'Permittee added successfully.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})