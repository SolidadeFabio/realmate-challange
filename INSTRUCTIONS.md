# Instructions - RealMate Challenge

## Quick Start

### 1. Setup Environment Variables
```bash
cp .env.example .env
```

### 2. Start Application
```bash
docker compose up --build -d
```

**Services running:**
- **Frontend**: http://localhost:8000
- **Backend API**: http://localhost/api
- **Django Admin**: http://localhost/admin
- **Flower (Celery Monitor)**: http://localhost:5555

### 3. Initial Setup (Automatic)

The application automatically creates:
- **Admin User**: `admin` / `admin123`
- **User 1**: `usuario1` / `senha123`
- **User 2**: `usuario2` / `senha123`

These users are created during the first startup via the `init.sh` script.

---

## Recommended Demo Flow

### See WebSocket in Real-Time

**Experience the real-time WebSocket functionality:**

1. **Open two browser windows side-by-side:**
   - Window 1: http://localhost:8000 (login as `usuario1`)
   - Window 2: http://localhost:8000 (login as `usuario2`)

2. **In a terminal, run:**
   ```bash
   docker compose exec web python manage.py populate_db
   ```


---

## Authentication & Users

### Default Credentials

| User | Username | Password | Role |
|------|----------|----------|------|
| Admin | `admin` | `admin123` | Superuser |
| User 1 | `usuario1` | `password123` | Staff Member |
| User 2 | `usuario2` | `password123` | Staff Member |


---

## Running Automated Tests

### All Tests (66 tests)
```bash
docker compose exec web python manage.py test
```
