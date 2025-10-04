# FRESH Backend API PRD - Iteration 1

## Project Overview

**Product Name:** FRESH Backend API
**Version:** 1.0 (Iteration 1)
**Duration:** Months 1-2
**Technology Stack:** FastAPI, PostgreSQL (Supabase), Redis, Python 3.11+

## Repository Structure

```
fresh-backend-api/
├── README.md
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── main.py                   # FastAPI application entry
├── src/
│   ├── core/                  # Core configurations
│   │   ├── __init__.py
│   │   ├── config.py          # Settings and environment
│   │   ├── database.py        # Database connection (Supabase/PostgreSQL)
│   │   ├── security.py        # Authentication & authorization
│   │   ├── exceptions.py      # Custom exceptions
│   │   └── middleware.py      # Custom middleware
│   ├── api/                   # API routes
│   │   ├── __init__.py
│   │   ├── deps.py           # Dependencies & role-based access
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── users.py          # User management
│   │   ├── detection.py      # Object & disease detection
│   │   ├── images.py         # Image upload/management
│   │   ├── results.py        # Detection results
│   │   └── health.py         # Health checks
│   ├── models/               # Data models (aligned with Supabase schema)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── detection.py
│   │   ├── disease.py
│   │   ├── image.py
│   │   └── result.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── detection.py
│   │   ├── disease.py
│   │   ├── image.py
│   │   └── response.py
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── detection_service.py
│   │   ├── disease_service.py
│   │   ├── image_service.py
│   │   ├── notification_service.py
│   │   └── ml_integration.py
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── image_processing.py
│   │   ├── file_handler.py
│   │   ├── validation.py
│   │   └── helpers.py
│   └── tests/                # Test modules
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_detection.py
│       └── test_images.py
├── scripts/                  # Utility scripts
│   ├── init_db.py
│   ├── create_admin.py
│   └── seed_data.py
├── docs/                     # API documentation
│   ├── api_design.md
│   ├── database_schema.md
│   └── deployment.md
└── monitoring/               # Monitoring configs
    ├── prometheus.yml
    └── grafana/
```

## Iteration 1 Scope

### Module 1: Object Detection API

**Deliverable:** Complete object detection model integration with REST API

#### Core Endpoints


* `POST /api/detection/batch-fruit`
* `GET  /api/detection/fruit/{detection_id}`
* `GET  /api/detection/fruit/results`
* `POST /api/detection/quality`
* `GET  /api/detection/quality/{quality_id}`
* `GET  /api/detection/quality/history`

#### Features

* Multi-fruit Classification: Orange, guava, grapefruit, mango
* Batch Processing: Multiple images per request
* Quality Metrics: Size, color, ripeness, surface defects
* Result Caching: Redis-based caching
* Asynchronous Processing: Background tasks

### Module 2: Disease Detection API

**Deliverable:** Primary disease detection models with REST API integration

#### Core Endpoints

* `POST /api/disease/detect`
* `POST /api/disease/batch-detect`
* `GET  /api/disease/results/{disease_id}`
* `GET  /api/disease/history`
* `POST /api/alerts/create`
* `GET  /api/alerts/active`
* `PUT  /api/alerts/{alert_id}/acknowledge`
* `DELETE /api/alerts/{alert_id}`

#### Features

* Primary Disease Detection: Anthracnose (mango), Citrus canker (orange/grapefruit)
* Severity Assessment: Multi-level scoring (0–100)
* Alert Management: Automated creation and notifications
* Disease Tracking: Historical disease occurrence
* Visualization: Heat maps and affected area data

### Module 3: Image Management System

**Deliverable:** Image upload, storage, and processing system

#### Core Endpoints

* `POST /api/images/upload`
* `POST /api/images/batch-upload`
* `GET  /api/images/{image_id}`
* `DELETE /api/images/{image_id}`

#### Features

* Multi-format Support: JPEG, PNG, WebP, TIFF
* S3 Integration: AWS S3 for storage
* Image Optimization: Compression & resizing
* Metadata Extraction: EXIF data processing
* CDN Integration: CloudFront delivery

## Database Schema Design (Supabase/PostgreSQL)

### Core Tables

**Users**

* `id` (UUID, primary key)
* `email` (unique)
* `password_hash`
* `full_name`
* `role` (farmer, exporter,government, admin)
* `created_at`
* `updated_at`

**Images**

* `id` (UUID, primary key)
* `user_id` (FK → users.id)
* `file_path`
* `file_name`
* `metadata` (JSONB)
* `created_at`

**Detection Results**

* `detection_id` (UUID, primary key)
* `user_id` (FK → users.id)
* `image_id` (FK → images.id)
* `fruit_type`
* `confidence`
* `bounding_box` (JSONB)
* `created_at`

**Classification Results** 
* - classification_id (Primary Key)
* - detection_id (Foreign Key)
* - ripeness_level (VARCHAR: ripe/unripe/overripe/rotten)
* - confidence_score (DECIMAL: 0.0-1.0)
* - estimated_color (VARCHAR)
* - estimated_size (VARCHAR)

**Disease Detections**

* `id` (UUID, primary key)
* `user_id` (FK → users.id)
* `image_id` (FK → images.id)
* `fruit_detection_id` (FK → fruit\_detections.id)
* `disease_type`
* `confidence`
* `severity_score`
* `affected_area` (JSONB)
* `visualization_data` (JSONB)
* `created_at`

**Alerts**

* `id` (UUID, primary key)
* `user_id` (FK → users.id)
* `disease_detection_id` (FK → disease\_detections.id)
* `alert_type`
* `severity`
* `title`
* `description`
* `is_acknowledged`
* `acknowledged_at`
* `created_at`

## API Architecture

### FastAPI Application

* Uses **lifespan events** for resource initialization (DB, Redis, S3)
* CORS middleware for secure API access
* Organized routers under `/api/*`

### Service Layer

* Encapsulates ML integrations and business logic
* Handles detection, disease analysis, image processing, and alerting
* Uses Redis caching for performance

## Authentication & Security

### Authentication

* **JWT-based Authentication** for secure access
* **Google OAuth2 Authentication** integration for user login via Google accounts
* Access tokens issued with expiry times

### Role-Based Access Control

Roles defined:

* **Farmer**: Upload images, view results
* **Exporter**: Access quality grading reports
* **Government**: Monitor disease alerts & compliance
* **Admin**: Full system access

RBAC ensures only authorized users can perform specific actions (e.g., only Admin can delete users, only Government can view all disease reports).

---

