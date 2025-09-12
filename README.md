# FRESH Backend API 🍊🥭

**Fruit Recognition and Evaluation System for Health**

A FastAPI-based backend system for fruit detection, disease identification, and quality assessment using machine learning models.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Development](#development)
- [Contributing](#contributing)

## 🎯 Overview

FRESH Backend API is a comprehensive system designed to:
- Detect and classify fruits (Orange, Guava, Grapefruit, Mango)
- Identify diseases in fruits (Anthracnose in mango, Citrus canker in citrus fruits)
- Assess fruit quality metrics (size, color, ripeness, surface defects)
- Provide role-based access for farmers, exporters, government officials, and administrators
- Manage alerts and notifications for disease outbreaks

## ✨ Features

### Current Implementation (Iteration 1)
- ✅ **FastAPI Framework** - High-performance async API
- ✅ **Supabase Integration** - PostgreSQL database connection
- ✅ **Environment Configuration** - Secure configuration management
- ✅ **Health Monitoring** - Database connectivity checks
- ✅ **CORS Support** - Cross-origin resource sharing
- ✅ **Auto Documentation** - Interactive API docs with Swagger UI

### Planned Features
- 🔄 **Object Detection API** - Multi-fruit classification
- 🔄 **Disease Detection API** - AI-powered disease identification
- 🔄 **Image Management** - Upload, storage, and processing
- 🔄 **Authentication System** - JWT and OAuth2 integration
- 🔄 **Role-based Access Control** - Farmer, Exporter, Government, Admin roles
- 🔄 **Alert System** - Disease outbreak notifications
- 🔄 **Caching Layer** - Redis integration for performance

## 🛠 Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy 2.0.23
- **Authentication**: JWT with python-jose
- **Caching**: Redis
- **Environment**: Python 3.11+
- **Documentation**: Automatic OpenAPI/Swagger
- **Deployment**: Docker, Uvicorn

## 📋 Prerequisites

- Python 3.11 or higher
- Git
- Supabase account (for database)
- Redis (optional, for caching)

## 🚀 Installation

### Step 1: Clone the Repository

```powershell
git clone <repository-url>
cd FRESH_backend
```

### Step 2: Create Virtual Environment

#### Using Python venv (Recommended)

```powershell
# Create virtual environment
python -m venv fresh_env

# Activate virtual environment (Windows)
fresh_env\Scripts\activate

# For Linux/Mac:
source fresh_env/bin/activate
```

#### Using conda (Alternative)

```powershell
# Create conda environment
conda create -n fresh_env python=3.11

# Activate conda environment
conda activate fresh_env
```

### Step 3: Install Dependencies

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

### Step 4: Verify Installation

```powershell
# Check Python version
python --version

# Check installed packages
pip list
```

## ⚙️ Configuration

### Step 1: Environment Variables

1. Copy the example environment file:
   ```powershell
   copy .env.example .env
   ```

2. Edit `.env` file with your configuration:
   ```env
   # Database Configuration
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.zyirkbzespzqrhgudofq.supabase.co:5432/postgres
   SUPABASE_URL=https://zyirkbzespzqrhgudofq.supabase.co
   SUPABASE_ANON_KEY=your_supabase_anon_key_here
   
   # Application Configuration
   DEBUG=True
   SECRET_KEY=your_secret_key_here_change_this_in_production
   
   # CORS Configuration
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
   ```

### Step 2: Database Setup

The application will automatically connect to your Supabase PostgreSQL database using the provided credentials.

## 🏃‍♂️ Running the Application

### Development Mode

```powershell
# Run with Python
python main.py

# Or run with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```powershell
# Run without reload
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **Application**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📚 API Documentation

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint with API information |
| GET | `/health` | Health check with database status |
| GET | `/api` | API information and future endpoints |
| GET | `/docs` | Interactive API documentation (Swagger UI) |
| GET | `/redoc` | Alternative API documentation |

### Health Check Response

```json
{
  "status": "healthy",
  "service": "FRESH Backend API",
  "version": "1.0.0",
  "database": "connected"
}
```

## 📁 Project Structure

```
FRESH_backend/
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── main.py                   # FastAPI application entry
├── .env                     # Environment variables (not in git)
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
├── PRD.md                   # Product Requirements Document
├── src/                     # Source code
│   ├── __init__.py
│   └── core/                # Core configurations
│       ├── __init__.py
│       ├── config.py        # Settings and environment
│       └── database.py      # Database connection
```

### Future Structure (As per PRD)

```
src/
├── api/                     # API routes
├── models/                  # Data models
├── schemas/                 # Pydantic schemas
├── services/                # Business logic
├── utils/                   # Utility functions
└── tests/                   # Test modules
```

## 🔧 Development

### Code Style

The project follows Python best practices:
- PEP 8 style guide
- Type hints
- Async/await patterns
- Pydantic for data validation

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Add your changes following the project structure
3. Test your changes
4. Submit a pull request

### Environment Management

```powershell
# Deactivate virtual environment
deactivate

# Reactivate virtual environment
fresh_env\Scripts\activate

# Update requirements.txt after installing new packages
pip freeze > requirements.txt
```

### Database Migrations

```powershell
# Future: Generate migration
alembic revision --autogenerate -m "Description"

# Future: Apply migration
alembic upgrade head
```

## 🧪 Testing

```powershell
# Run tests (when test suite is added)
pytest

# Run with coverage
pytest --cov=src
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure virtual environment is activated
2. **Database Connection**: Verify DATABASE_URL in .env file
3. **Port Already in Use**: Change port in main.py or kill existing process
4. **Environment Variables**: Ensure .env file exists and is properly formatted

### Debug Mode

Set `DEBUG=True` in `.env` file to enable:
- Detailed error messages
- SQL query logging
- Auto-reload on code changes

## 📄 License

This project is part of an academic Final Year Project (FYP).

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

**Built with ❤️ for FRESH - Fruit Recognition and Evaluation System for Health**