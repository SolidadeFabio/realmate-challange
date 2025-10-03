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

---

## Populate Database

### Interactive Command
```bash
docker compose exec web python manage.py populate_db
```

This command provides an interactive CLI with 3 modes:

#### **1. Batch Mode** (Recommended for large datasets)
- Creates conversations in organized batches
- Efficient for 100+ conversations
- Uses Celery task distribution

**Example:**
```
How many conversations to create? 500
Conversations per batch? 50
→ Creates 10 batches of 50 conversations each
```

#### **2. Concurrent Mode** (Maximum parallelism)
- Creates all conversations simultaneously
- Best for testing Celery worker performance
- Uses Celery groups

**Example:**
```
How many conversations to create? 100
→ Dispatches 100 tasks in parallel
```

#### **3. Peak Hour Simulation** (Stress testing)
- Simulates real-world traffic patterns
- Creates conversations over time
- Useful for testing WebSocket scaling

**Example:**
```
Peak duration in minutes? 30
Conversations per minute? 10
→ Creates ~300 conversations over 30 minutes
```

---