from django.core.management.base import BaseCommand
from api.models import Blood, BloodBank, BloodAndBloodBank, BloodRequest
import random

class Command(BaseCommand):
    help = 'Seeds the database with Nepalese blood banks, blood types, stock, and sample requests.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding blood types...')
        blood_types = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
        blood_objects = []
        for t in blood_types:
            obj, created = Blood.objects.get_or_create(type=t)
            blood_objects.append(obj)
            
        self.stdout.write('Seeding blood banks...')
        banks_data = [
            {
                "name": "Nepal Red Cross Central Blood Transfusion Service",
                "latitude": 27.698888,
                "longitude": 85.323888,
                "address": "Exhibition Road, Bhrikutimandap, Kathmandu",
                "contact": "+977-1-4225344",
                "image_url": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=400"
            },
            {
                "name": "Teaching Hospital Blood Bank",
                "latitude": 27.736000,
                "longitude": 85.330000,
                "address": "Maharajgunj, Kathmandu",
                "contact": "+977-1-4412303",
                "image_url": "https://images.unsplash.com/photo-1586773860418-d3b3da9671fd?q=80&w=400"
            },
            {
                "name": "Patan Hospital Blood Unit",
                "latitude": 27.667500,
                "longitude": 85.321000,
                "address": "Lagankhel, Lalitpur",
                "contact": "+977-1-5522295",
                "image_url": "https://images.unsplash.com/photo-1516549655169-df83a0774514?q=80&w=400"
            },
            {
                "name": "Alka Hospital Blood Bank Service",
                "latitude": 27.674000,
                "longitude": 85.313000,
                "address": "Jawalakhel, Lalitpur",
                "contact": "+977-1-5555555",
                "image_url": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?q=80&w=400"
            },
            {
                "name": "Civil Service Hospital Blood Unit",
                "latitude": 27.689000,
                "longitude": 85.342000,
                "address": "Minbhawan, Kathmandu",
                "contact": "+977-1-4763177",
                "image_url": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=400"
            },
            {
                "name": "Bhaktapur Cancer Hospital Blood Bank",
                "latitude": 27.669800,
                "longitude": 85.421000,
                "address": "Liwali, Bhaktapur",
                "contact": "+977-1-6611532",
                "image_url": "https://images.unsplash.com/photo-1538108176447-280586497d96?q=80&w=400"
            }
        ]
        
        bank_objects = []
        for data in banks_data:
            bank, created = BloodBank.objects.get_or_create(
                name=data["name"],
                defaults={
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "address": data["address"],
                    "contact": data["contact"],
                    "image_url": data["image_url"]
                }
            )
            bank_objects.append(bank)

        self.stdout.write('Seeding stock quantities...')
        for bank in bank_objects:
            # Seed stock for each blood type
            for blood in blood_objects:
                qty = random.randint(5, 45)
                junction, created = BloodAndBloodBank.objects.get_or_create(
                    blood_bank=bank,
                    blood=blood,
                    defaults={"quantity": qty}
                )
                if not created:
                    junction.quantity = qty
                    junction.save()

        self.stdout.write('Seeding sample blood requests...')
        requests_data = [
            {
                "patient_name": "Roshan Adhikari",
                "blood_type_str": "O-",
                "quantity_needed": 3,
                "hospital_name": "Bir Hospital, Kathmandu",
                "contact_number": "9841234567",
                "urgency_level": "Critical"
            },
            {
                "patient_name": "Sita Thapa",
                "blood_type_str": "AB+",
                "quantity_needed": 2,
                "hospital_name": "Patan Hospital, Lalitpur",
                "contact_number": "9801234567",
                "urgency_level": "Urgent"
            },
            {
                "patient_name": "Hari Shrestha",
                "blood_type_str": "A+",
                "quantity_needed": 4,
                "hospital_name": "Tribhuvan University Teaching Hospital",
                "contact_number": "9851122334",
                "urgency_level": "Normal"
            }
        ]
        
        for rdata in requests_data:
            blood_obj = Blood.objects.get(type=rdata["blood_type_str"])
            BloodRequest.objects.get_or_create(
                patient_name=rdata["patient_name"],
                blood_type=blood_obj,
                hospital_name=rdata["hospital_name"],
                defaults={
                    "quantity_needed": rdata["quantity_needed"],
                    "contact_number": rdata["contact_number"],
                    "urgency_level": rdata["urgency_level"],
                    "status": "Pending"
                }
            )
            
        self.stdout.write(self.style.SUCCESS('Successfully seeded dummy blood bank dataset!'))
