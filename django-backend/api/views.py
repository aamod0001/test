import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.db.models import Sum
from .models import BloodBank, Blood, BloodAndBloodBank, BloodRequest

def get_blood_banks(request, latitude, longitude, type):
    try:
        lat = float(latitude)
        lon = float(longitude)
    except ValueError:
        return JsonResponse({"error": "Invalid latitude or longitude"}, status=400)

    # Decode url encoded type if needed (e.g. "O+" / "O%2B" is handled by Django router automatically)
    blood_type = type

    query = """
        SELECT bb.blood_bank_id, bb.name, bb.latitude, bb.longitude,
               bb.image_url, bb.address, bb.contact, babb.quantity
        FROM blood_bank bb
        JOIN blood_and_blood_bank babb ON bb.blood_bank_id = babb.bloodbankid
        JOIN blood b ON babb.bloodtype = b.bloodtype
        WHERE b.bloodtype = %s
        AND babb.quantity >= 1
        ORDER BY (6371 * acos(greatest(-1.0, least(1.0,
                  cos(radians(%s)) * cos(radians(bb.latitude)) *
                  cos(radians(bb.longitude) - radians(%s)) +
                  sin(radians(%s)) * sin(radians(bb.latitude)))))) ASC
        LIMIT 20
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [blood_type, lat, lon, lat])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    results = []
    for row in rows:
        item = dict(zip(columns, row))
        results.append({
            "bloodBankId": item.get("blood_bank_id"),
            "name": item.get("name"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "imageUrl": item.get("image_url"),
            "address": item.get("address"),
            "contact": item.get("contact"),
            "type": blood_type,
            "quantity": float(item.get("quantity", 0))
        })

    return JsonResponse(results, safe=False)


@csrf_exempt
def add_bank(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    bank = BloodBank.objects.create(
        name=data.get('name'),
        latitude=data.get('latitude', 0.0),
        longitude=data.get('longitude', 0.0),
        image_url=data.get('imageUrl') or data.get('image_url'),
        address=data.get('address'),
        contact=data.get('contact')
    )

    return JsonResponse({
        "bloodBankId": bank.blood_bank_id,
        "name": bank.name,
        "latitude": bank.latitude,
        "longitude": bank.longitude,
        "imageUrl": bank.image_url,
        "address": bank.address,
        "contact": bank.contact
    }, status=200)


# Debug endpoints

def get_junction_count(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM blood_and_blood_bank")
        count = cursor.fetchone()[0]
    return JsonResponse(count, safe=False)


def get_junction_data(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM blood_and_blood_bank LIMIT 10")
        rows = cursor.fetchall()
    return JsonResponse(rows, safe=False)


def get_available_types(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT bloodtype FROM blood_and_blood_bank")
        types = [row[0] for row in cursor.fetchall()]
    return JsonResponse(types, safe=False)


def test_join(request):
    query = """
        SELECT bb.blood_bank_id, bb.name, bb.latitude, bb.longitude,
               bb.image_url, bb.address, bb.contact
        FROM blood_bank bb
        JOIN blood_and_blood_bank babb ON bb.blood_bank_id = babb.bloodbankid
        LIMIT 5
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    results = []
    for row in rows:
        item = dict(zip(columns, row))
        results.append({
            "bloodBankId": item.get("blood_bank_id"),
            "name": item.get("name"),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "imageUrl": item.get("image_url"),
            "address": item.get("address"),
            "contact": item.get("contact")
        })

    return JsonResponse(results, safe=False)


# Main Web Dashboard Serve View

def serve_dashboard(request):
    return render(request, 'index.html')


# New REST APIs for Full-Fledged App Features

def get_all_bloodbanks(request):
    banks = BloodBank.objects.all().order_by('name')
    results = []
    for bank in banks:
        results.append({
            "bloodBankId": bank.blood_bank_id,
            "name": bank.name,
            "latitude": bank.latitude,
            "longitude": bank.longitude,
            "imageUrl": bank.image_url,
            "address": bank.address,
            "contact": bank.contact
        })
    return JsonResponse(results, safe=False)


@csrf_exempt
def manage_stock(request, bank_id):
    try:
        bank = BloodBank.objects.get(pk=bank_id)
    except BloodBank.DoesNotExist:
        return JsonResponse({"error": "Blood bank not found"}, status=404)

    if request.method == 'GET':
        all_types = Blood.objects.all()
        stock_map = {bt.type: 0 for bt in all_types}
        junctions = BloodAndBloodBank.objects.filter(blood_bank=bank)
        for j in junctions:
            stock_map[j.blood.type] = j.quantity
        results = [{"type": k, "quantity": v} for k, v in stock_map.items()]
        return JsonResponse(results, safe=False)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
            
        blood_type = data.get('type')
        quantity = data.get('quantity')
        
        if not blood_type or quantity is None:
            return JsonResponse({"error": "Missing 'type' or 'quantity'"}, status=400)
            
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError()
        except ValueError:
            return JsonResponse({"error": "Quantity must be a non-negative integer"}, status=400)
            
        try:
            blood = Blood.objects.get(pk=blood_type)
        except Blood.DoesNotExist:
            blood = Blood.objects.create(type=blood_type)
            
        junction, created = BloodAndBloodBank.objects.get_or_create(
            blood_bank=bank,
            blood=blood,
            defaults={'quantity': quantity}
        )
        if not created:
            junction.quantity = quantity
            junction.save()
            
        return JsonResponse({
            "bloodBankId": bank_id,
            "type": blood_type,
            "quantity": quantity
        })
        
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def manage_requests(request):
    if request.method == 'GET':
        requests = BloodRequest.objects.filter(status='Pending').order_by('-created_at')
        results = []
        for req in requests:
            results.append({
                "requestId": req.request_id,
                "patientName": req.patient_name,
                "bloodType": req.blood_type.type,
                "quantity": req.quantity_needed,
                "hospitalName": req.hospital_name,
                "contactNumber": req.contact_number,
                "urgencyLevel": req.urgency_level,
                "status": req.status,
                "createdAt": req.created_at.isoformat()
            })
        return JsonResponse(results, safe=False)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
            
        patient_name = data.get('patientName')
        blood_type_str = data.get('bloodType')
        quantity = data.get('quantity')
        hospital_name = data.get('hospitalName')
        contact_number = data.get('contactNumber')
        urgency_level = data.get('urgencyLevel', 'Normal')
        
        if not all([patient_name, blood_type_str, quantity, hospital_name, contact_number]):
            return JsonResponse({"error": "Missing required fields"}, status=400)
            
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError()
        except ValueError:
            return JsonResponse({"error": "Quantity must be a positive integer"}, status=400)
            
        try:
            blood_type = Blood.objects.get(pk=blood_type_str)
        except Blood.DoesNotExist:
            blood_type = Blood.objects.create(type=blood_type_str)
            
        req = BloodRequest.objects.create(
            patient_name=patient_name,
            blood_type=blood_type,
            quantity_needed=quantity,
            hospital_name=hospital_name,
            contact_number=contact_number,
            urgency_level=urgency_level
        )
        
        return JsonResponse({
            "requestId": req.request_id,
            "patientName": req.patient_name,
            "bloodType": req.blood_type.type,
            "quantity": req.quantity_needed,
            "hospitalName": req.hospital_name,
            "contactNumber": req.contact_number,
            "urgencyLevel": req.urgency_level,
            "status": req.status,
            "createdAt": req.created_at.isoformat()
        }, status=201)
        
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def fulfill_request(request, request_id):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        req = BloodRequest.objects.get(pk=request_id)
    except BloodRequest.DoesNotExist:
        return JsonResponse({"error": "Blood request not found"}, status=404)
        
    req.status = 'Fulfilled'
    req.save()
    
    return JsonResponse({
        "requestId": req.request_id,
        "status": req.status
    })


def get_stats_dashboard(request):
    total_banks = BloodBank.objects.count()
    active_requests = BloodRequest.objects.filter(status='Pending').count()
    total_quantity = BloodAndBloodBank.objects.aggregate(total=Sum('quantity'))['total'] or 0
    type_quantities = BloodAndBloodBank.objects.values('blood__type').annotate(total=Sum('quantity'))
    
    breakdown = {}
    for item in type_quantities:
        b_type = item['blood__type']
        qty = item['total'] or 0
        breakdown[b_type] = {
            "quantity": qty,
            "percentage": round((qty / total_quantity * 100), 1) if total_quantity > 0 else 0
        }
        
    return JsonResponse({
        "totalBanks": total_banks,
        "activeRequests": active_requests,
        "totalBloodPints": total_quantity,
        "breakdown": breakdown
    })
