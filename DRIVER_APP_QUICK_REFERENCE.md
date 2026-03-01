# Driver App API - Quick Reference Card

## 🚀 Setup (One-time)
```bash
pip install -r requirements.txt
alembic upgrade head
python setup_driver_test_data.py
```

## ▶️ Start Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```

## 🧪 Test
```bash
python test_driver_app_api.py
```

## 🔑 Test Credentials
```
Employee ID: PMPML-4521
Password: test123
```

## 📡 API Endpoints

### 1. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employeeId":"PMPML-4521","password":"test123"}'
```

### 2. Get Profile
```bash
curl -X GET http://localhost:8000/api/driver/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Get Today's Duty
```bash
curl -X GET http://localhost:8000/api/duty/today \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refreshToken":"YOUR_REFRESH_TOKEN"}'
```

### 5. Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📚 Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Check database connection
psql -U postgres -d pmpml_optimization
```

### Migration issues
```bash
# Check current version
alembic current

# Downgrade and upgrade
alembic downgrade -1
alembic upgrade head
```

### No test driver
```bash
# Re-run setup
python setup_driver_test_data.py
```

### 404 on /api/duty/today
- Normal if no active plan
- Run optimization and deploy plan first

## 📝 Response Format

### Success (200)
```json
{
  "token": "eyJhbGc...",
  "driver": {...}
}
```

### Error (401/404/500)
```json
{
  "error": "ERROR_CODE",
  "message": "English message",
  "messageMarathi": "मराठी संदेश"
}
```

## 🔒 Security

- Access Token: 24 hours
- Refresh Token: 30 days
- Algorithm: HS256
- Password: Bcrypt hashed

## 📊 Database

### Check driver data
```sql
SELECT driver_id, employee_id, driver_name, is_active 
FROM drivers 
WHERE employee_id = 'PMPML-4521';
```

### Check assignments
```sql
SELECT * FROM current_driver_assignments 
WHERE driver_id = 'DRV_001';
```

## 🎯 Quick Test Flow

1. Start server
2. Login → Get token
3. Use token for profile/duty
4. Refresh token when needed
5. Logout when done

---

**Docs**: `DRIVER_APP_README.md`  
**Help**: http://localhost:8000/docs
