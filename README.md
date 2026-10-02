# hogwarts.uz-backend

Hogwarts.uz platformasining Django asosidagi backend qismi.

## O'rnatish va Ishga tushirish

1. Virtual muhit yaratish va faollashtirish:
```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# yoki venv\Scripts\activate  # Windows
```

2. Kerakli kutubxonalarni o'rnatish:
```bash
pip install -r requirements.txt
```

3. Ma'lumotlar bazasini yangilash:
```bash
python manage.py migrate
```

4. Serverni ishga tushirish:
```bash
python manage.py runserver
```
