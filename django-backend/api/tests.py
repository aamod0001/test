import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from .models import BloodBank, Blood, BloodAndBloodBank, BloodRequest

class ApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('api.views.connection.cursor')
    def test_get_blood_banks(self, mock_cursor):
        # Setup mock cursor description and fetchall output
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        
        mock_cursor_instance.description = [
            ('blood_bank_id',), ('name',), ('latitude',), ('longitude',),
            ('image_url',), ('address',), ('contact',), ('quantity',)
        ]
        mock_cursor_instance.fetchall.return_value = [
            (1, 'Central Blood Bank', 27.7007, 85.3001, 'http://image.url/1', 'Kathmandu', '9876543210', 10)
        ]

        # Call endpoint
        response = self.client.get(reverse('get_blood_banks', kwargs={
            'latitude': '27.7',
            'longitude': '85.3',
            'type': 'O+'
        }))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['bloodBankId'], 1)
        self.assertEqual(data[0]['name'], 'Central Blood Bank')
        self.assertEqual(data[0]['quantity'], 10.0)
        self.assertEqual(data[0]['type'], 'O+')

    def test_get_blood_banks_invalid_coordinates(self):
        response = self.client.get(reverse('get_blood_banks', kwargs={
            'latitude': 'invalid',
            'longitude': '85.3',
            'type': 'O+'
        }))
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    @patch('api.views.BloodBank.objects.create')
    def test_add_bank(self, mock_create):
        # Setup mock BloodBank object returned from create
        mock_bank = MagicMock()
        mock_bank.blood_bank_id = 42
        mock_bank.name = 'New Bank'
        mock_bank.latitude = 27.8
        mock_bank.longitude = 85.4
        mock_bank.image_url = 'http://image.url/new'
        mock_bank.address = 'Lalitpur'
        mock_bank.contact = '0123456789'
        mock_create.return_value = mock_bank

        payload = {
            "name": "New Bank",
            "latitude": 27.8,
            "longitude": 85.4,
            "imageUrl": "http://image.url/new",
            "address": "Lalitpur",
            "contact": "0123456789"
        }

        response = self.client.post(
            reverse('add_bank'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['bloodBankId'], 42)
        self.assertEqual(data['name'], 'New Bank')
        self.assertEqual(data['imageUrl'], 'http://image.url/new')

    def test_add_bank_method_not_allowed(self):
        response = self.client.get(reverse('add_bank'))
        self.assertEqual(response.status_code, 405)

    @patch('api.views.connection.cursor')
    def test_get_junction_count(self, mock_cursor):
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        mock_cursor_instance.fetchone.return_value = (15,)

        response = self.client.get(reverse('get_junction_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), 15)

    @patch('api.views.connection.cursor')
    def test_get_junction_data(self, mock_cursor):
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        mock_cursor_instance.fetchall.return_value = [
            (1, 'O+', 5),
            (2, 'A-', 12)
        ]

        response = self.client.get(reverse('get_junction_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [[1, 'O+', 5], [2, 'A-', 12]])

    @patch('api.views.connection.cursor')
    def test_get_available_types(self, mock_cursor):
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        mock_cursor_instance.fetchall.return_value = [
            ('O+',), ('A-',), ('B+',)
        ]

        response = self.client.get(reverse('get_available_types'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), ['O+', 'A-', 'B+'])

    @patch('api.views.connection.cursor')
    def test_test_join(self, mock_cursor):
        mock_cursor_instance = MagicMock()
        mock_cursor.return_value.__enter__.return_value = mock_cursor_instance
        mock_cursor_instance.description = [
            ('blood_bank_id',), ('name',), ('latitude',), ('longitude',),
            ('image_url',), ('address',), ('contact',)
        ]
        mock_cursor_instance.fetchall.return_value = [
            (1, 'Bank 1', 10.0, 20.0, 'img1', 'addr1', 'cont1')
        ]

        response = self.client.get(reverse('test_join'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['bloodBankId'], 1)
        self.assertEqual(data[0]['name'], 'Bank 1')

    def test_get_all_bloodbanks_orm(self):
        bank = BloodBank.objects.create(name="Test Bank", latitude=12.3, longitude=45.6)
        response = self.client.get(reverse('api_bloodbanks'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(b['name'] == 'Test Bank' for b in data))

    def test_manage_stock_get_post(self):
        bank = BloodBank.objects.create(name="Stock Bank", latitude=12.3, longitude=45.6)
        blood = Blood.objects.create(type="AB-")
        
        # Test GET stock
        response = self.client.get(reverse('api_manage_stock', kwargs={'bank_id': bank.blood_bank_id}))
        self.assertEqual(response.status_code, 200)
        
        # Test POST stock
        payload = {"type": "AB-", "quantity": 12}
        response = self.client.post(
            reverse('api_manage_stock', kwargs={'bank_id': bank.blood_bank_id}),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['quantity'], 12)
        
        # Verify DB updated
        from .models import BloodAndBloodBank
        junction = BloodAndBloodBank.objects.get(blood_bank=bank, blood=blood)
        self.assertEqual(junction.quantity, 12)

    def test_manage_requests_get_post(self):
        blood = Blood.objects.create(type="O-")
        
        # Test POST request
        payload = {
            "patientName": "John Doe",
            "bloodType": "O-",
            "quantity": 3,
            "hospitalName": "City Hospital",
            "contactNumber": "9800000000",
            "urgencyLevel": "Critical"
        }
        response = self.client.post(
            reverse('api_manage_requests'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        req_id = response.json()['requestId']
        
        # Test GET requests
        response = self.client.get(reverse('api_manage_requests'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(r['patientName'] == 'John Doe' for r in data))

    def test_fulfill_request(self):
        blood = Blood.objects.create(type="O-")
        from .models import BloodRequest
        req = BloodRequest.objects.create(
            patient_name="Jane Doe",
            blood_type=blood,
            quantity_needed=2,
            hospital_name="Red Cross",
            contact_number="12345",
            urgency_level="Normal"
        )
        
        response = self.client.post(reverse('api_fulfill_request', kwargs={'request_id': req.request_id}))
        self.assertEqual(response.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, 'Fulfilled')

    def test_get_stats_dashboard(self):
        BloodBank.objects.create(name="Stats Bank", latitude=12.3, longitude=45.6)
        response = self.client.get(reverse('api_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('totalBanks', data)
        self.assertIn('activeRequests', data)

