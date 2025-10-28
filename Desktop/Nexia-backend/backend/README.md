# Nexia Backend

Professional fitness training management system built with FastAPI.

## 🚀 Quick Start

1. **Navigate to the backend folder:**
   ```bash
   cd backend
   ```

2. **Set up the environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp env.example .env
   # Edit .env and set your DATABASE_URL, SECRET_KEY, ENVIRONMENT, DEBUG, etc.
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Visit the API docs:**
   - Swagger UI: http://127.0.0.1:8000/api/v1/docs
   - ReDoc: http://127.0.0.1:8000/api/v1/redoc

## 🧪 Testing

### Automated Testing
```bash
# Run all tests
pytest -v

# Run tests with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_main.py -v
```

### Manual Testing
Use the provided curl commands or test via Swagger UI/Postman.

## 🛠️ Development Tools

### Code Quality
```bash
# Format code with Black
black app/

# Sort imports with isort
isort app/

# Lint code with flake8
flake8 app/ --max-line-length=88

# Run all quality checks
black --check app/
isort --check-only app/
flake8 app/ --max-line-length=88
```

### Pre-commit Hooks
Pre-commit hooks are automatically installed and will run on every commit:
- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8)
- File checks (trailing whitespace, YAML validation, etc.)

## 📊 Features

### Core Functionality
- ✅ **Client Management**: Full CRUD operations with automatic BMI calculation
- ✅ **Trainer Management**: Complete trainer profile management
- ✅ **Exercise Database**: Comprehensive exercise library with 100+ exercises
- ✅ **Advanced Filtering**: Filter exercises by muscle group, equipment, level, and ID
- ✅ **Statistics**: Detailed exercise statistics and summaries
- ✅ **Pagination**: Efficient data pagination for large datasets

### Technical Features
- ✅ **Modern FastAPI**: Latest version with automatic OpenAPI documentation
- ✅ **SQLAlchemy ORM**: Professional database abstraction
- ✅ **Alembic Migrations**: Database schema version control
- ✅ **Pydantic Validation**: Robust data validation and serialization
- ✅ **Professional Logging**: Structured logging with different levels
- ✅ **Error Handling**: Comprehensive exception handling
- ✅ **CORS Support**: Cross-origin resource sharing configuration
- ✅ **Security Middleware**: Production-ready security features

### Development Environment
- ✅ **Code Quality Tools**: Black, flake8, isort for consistent code style
- ✅ **Pre-commit Hooks**: Automatic code quality checks
- ✅ **Automated Testing**: Comprehensive test suite with pytest
- ✅ **Environment Management**: Professional environment variable handling
- ✅ **Documentation**: Complete API documentation with examples

## 🗄️ Database

### Development
- **SQLite**: Used for development and testing
- **File**: `nexia.db` in the backend directory
- **Migrations**: Managed with Alembic

### Production
- **PostgreSQL/MySQL**: Recommended for production deployment
- **Configuration**: Set `DATABASE_URL` in environment variables
- **Migration**: Use Alembic to migrate schema changes

## 🔧 Environment Variables

Key environment variables (see `env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string (use `postgresql+psycopg2://` for PostgreSQL) | `sqlite:///./nexia.db` |
| `SECRET_KEY` | Secret key for security | `your-secret-key-change-in-production` |
| `ENVIRONMENT` | Environment (development/production/testing) | `development` |
| `DEBUG` | Enable debug mode | `True` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `SMTP_HOST` | SMTP server host (optional) | `None` |
| `SMTP_PORT` | SMTP server port (optional) | `587` |
| `SMTP_USERNAME` | SMTP username (optional) | `None` |
| `SMTP_PASSWORD` | SMTP password (optional) | `None` |
| `SMTP_SENDER` | SMTP sender email (optional) | `None` |
| `SMTP_USE_TLS` | Use TLS for SMTP (optional) | `True` |

### Database Configuration
- **SQLite (Development)**: `DATABASE_URL=sqlite:///./nexia.db`
- **PostgreSQL (Production)**: `DATABASE_URL=postgresql+psycopg2://user:password@localhost/nexia`
- **MySQL (Production)**: `DATABASE_URL=mysql://user:password@localhost/nexia`

## 🔐 Role-Based Access Control (RBAC)

### User Roles
- **admin**: Full system access, can manage all data
- **trainer**: Can manage their own clients and training data
- **athlete**: Can view their own data and submit feedback

### Access Matrix

| Endpoint Category | Admin | Trainer | Athlete |
|------------------|-------|---------|---------|
| Client Management | ✅ All | ✅ Own clients only | ❌ |
| Trainer Management | ✅ All | ❌ | ❌ |
| Exercise Database | ✅ All | ✅ All | ✅ All |
| Training Plans | ✅ All | ✅ Own plans only | ✅ Own plans only |
| Training Sessions | ✅ All | ✅ Own sessions only | ✅ Own sessions only |
| Client Feedback | ✅ All | ✅ Own clients only | ✅ Own feedback only |
| Progress Tracking | ✅ All | ✅ Own clients only | ✅ Own progress only |
| Fatigue Analysis | ✅ All | ✅ Own clients only | ✅ Own data only |
| Fatigue Alerts | ✅ All | ✅ Own alerts only | ❌ |
| Workload Tracking | ✅ All | ✅ Own clients only | ✅ Own data only |

## 📈 API Endpoints

### Health Check
- `GET /health` - API health and status

### Client Management
- `GET /api/v1/clients/` - List all clients
- `POST /api/v1/clients/` - Create new client
- `GET /api/v1/clients/{client_id}` - Get client by ID
- `PUT /api/v1/clients/{client_id}` - Update client
- `DELETE /api/v1/clients/{client_id}` - Delete client

### Trainer Management
- `GET /api/v1/trainers/` - List all trainers
- `POST /api/v1/trainers/` - Create new trainer
- `GET /api/v1/trainers/{trainer_id}` - Get trainer by ID
- `PUT /api/v1/trainers/{trainer_id}` - Update trainer
- `DELETE /api/v1/trainers/{trainer_id}` - Delete trainer

### Exercise Management
- `GET /api/v1/exercises/` - List all exercises (paginated)
- `POST /api/v1/exercises/` - Create new exercise
- `GET /api/v1/exercises/{exercise_id}` - Get exercise by ID
- `PUT /api/v1/exercises/{exercise_id}` - Update exercise
- `DELETE /api/v1/exercises/{exercise_id}` - Delete exercise

### Exercise Filtering
- `GET /api/v1/exercises/by-muscle-group/{muscle_group}` - Filter by muscle group
- `GET /api/v1/exercises/by-equipment/{equipment}` - Filter by equipment
- `GET /api/v1/exercises/by-level/{level}` - Filter by difficulty level
- `GET /api/v1/exercises/by-exercise-id/{exercise_id}` - Get by exercise ID

### Exercise Statistics
- `GET /api/v1/exercises/stats/summary` - Get exercise statistics

### Authentication
- `POST /api/v1/auth/register` – Register a user (admin/trainer/athlete)
- `POST /api/v1/auth/login` – Login (OAuth2 password)
- `GET /api/v1/auth/me` – Current user info
- `POST /api/v1/auth/forgot-password` – Request a password reset token (also emails if SMTP configured)
- `POST /api/v1/auth/reset-password` – Reset password using token
 - `POST /api/v1/auth/change-password` – Change password (requires current password)
 - `PUT /api/v1/auth/me` – Update current user profile (name/email)
 - `DELETE /api/v1/auth/me` – Deactivate account (GDPR-friendly)
 - `POST /api/v1/auth/refresh` – Rotate refresh token and issue new access token
 - `POST /api/v1/auth/logout` – Revoke current refresh token (server-side logout)

### Training Planning System
- `POST /api/v1/training-plans/` – Create training plan
- `GET /api/v1/training-plans/` – List training plans
- `GET /api/v1/training-plans/{plan_id}` – Get training plan
- `PUT /api/v1/training-plans/{plan_id}` – Update training plan
- `DELETE /api/v1/training-plans/{plan_id}` – Delete training plan

### Multi-stage Planning
- `POST /api/v1/training-plans/{plan_id}/macrocycles/` – Create macrocycle
- `GET /api/v1/training-plans/{plan_id}/macrocycles/` – List macrocycles
- `POST /api/v1/macrocycles/{macrocycle_id}/mesocycles/` – Create mesocycle
- `GET /api/v1/macrocycles/{macrocycle_id}/mesocycles/` – List mesocycles
- `POST /api/v1/mesocycles/{mesocycle_id}/microcycles/` – Create microcycle
- `GET /api/v1/mesocycles/{mesocycle_id}/microcycles/` – List microcycles

### Training Sessions
- `POST /api/v1/training-sessions/` – Create training session
- `GET /api/v1/training-sessions/` – List training sessions (with filters)
- `GET /api/v1/training-sessions/{session_id}` – Get training session
- `PUT /api/v1/training-sessions/{session_id}` – Update training session
- `DELETE /api/v1/training-sessions/{session_id}` – Delete training session

### Session Exercises
- `POST /api/v1/training-sessions/{session_id}/exercises` – Add exercise to session
- `GET /api/v1/training-sessions/{session_id}/exercises` – List session exercises
- `GET /api/v1/training-sessions/exercises/{exercise_id}` – Get session exercise
- `PUT /api/v1/training-sessions/exercises/{exercise_id}` – Update session exercise
- `DELETE /api/v1/training-sessions/exercises/{exercise_id}` – Delete session exercise

### Client Feedback
- `POST /api/v1/training-sessions/{session_id}/feedback` – Create session feedback
- `GET /api/v1/training-sessions/{session_id}/feedback` – Get session feedback
- `GET /api/v1/training-sessions/feedback/client/{client_id}` – Get client feedback history
- `PUT /api/v1/training-sessions/feedback/{feedback_id}` – Update feedback
- `DELETE /api/v1/training-sessions/feedback/{feedback_id}` – Delete feedback

### Progress Tracking
- `POST /api/v1/training-sessions/progress` – Create progress tracking
- `GET /api/v1/training-sessions/progress/client/{client_id}` – Get client progress
- `GET /api/v1/training-sessions/progress/client/{client_id}/exercise/{exercise_id}` – Get exercise progress
- `PUT /api/v1/training-sessions/progress/{progress_id}` – Update progress
- `DELETE /api/v1/training-sessions/progress/{progress_id}` – Delete progress

### Fatigue Analysis & Monitoring
- `POST /api/v1/fatigue/fatigue-analysis/` – Create fatigue analysis
- `GET /api/v1/fatigue/fatigue-analysis/` – List fatigue analysis (trainer-scoped)
- `GET /api/v1/fatigue/fatigue-analysis/{analysis_id}` – Get fatigue analysis
- `GET /api/v1/fatigue/clients/{client_id}/fatigue-analysis/` – Get client fatigue analysis
- `PUT /api/v1/fatigue/fatigue-analysis/{analysis_id}` – Update fatigue analysis
- `DELETE /api/v1/fatigue/fatigue-analysis/{analysis_id}` – Delete fatigue analysis

### Fatigue Alerts
- `POST /api/v1/fatigue/fatigue-alerts/` – Create fatigue alert
- `GET /api/v1/fatigue/fatigue-alerts/` – List fatigue alerts (trainer-scoped)
- `GET /api/v1/fatigue/fatigue-alerts/unread/` – List unread alerts (trainer-scoped)
- `PUT /api/v1/fatigue/fatigue-alerts/{alert_id}/read` – Mark alert as read
- `PUT /api/v1/fatigue/fatigue-alerts/{alert_id}/resolve` – Resolve alert

### Workload Tracking
- `POST /api/v1/fatigue/workload-tracking/` – Create workload tracking
- `GET /api/v1/fatigue/clients/{client_id}/workload-tracking/` – Get client workload tracking
- `GET /api/v1/fatigue/clients/{client_id}/fatigue-analytics/` – Get comprehensive fatigue analytics

#### SMTP setup (optional, for reset emails)
Add to `.env` (see `env.example`):

```
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SMTP_SENDER="Your App <no-reply@yourdomain.com>"
SMTP_USE_TLS=true
```

When configured, forgot-password will send an email containing a reset link while still returning the token in development/testing.

## 🚀 Production Deployment

### Database Migration
```bash
# For PostgreSQL (use postgresql+psycopg2:// for SQLAlchemy 2.0+)
DATABASE_URL="postgresql+psycopg2://user:password@localhost/nexia"

# For MySQL
DATABASE_URL="mysql://user:password@localhost/nexia"

# Run migrations
alembic upgrade head
```

### Environment Setup
- Set `ENVIRONMENT=production`
- Set `DEBUG=False`
- Configure secure `SECRET_KEY`
- Set up proper `BACKEND_CORS_ORIGINS`

### Deployment Steps (EC2/Production)
```bash
# 1. Pull latest code
git pull origin main

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Restart service
sudo systemctl restart nexia

# 6. Check service status
sudo systemctl status nexia

# 7. Verify health
curl https://yourdomain.com/health
```

### Security Considerations
- Use HTTPS in production
- Configure proper CORS origins
- Set up trusted hosts
- Use environment-specific secret keys
- Enable proper logging and monitoring
- Ensure database indexes are created for performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run code quality checks: `black app/ && isort app/ && flake8 app/`
5. Run tests: `pytest -v`
6. Commit your changes (pre-commit hooks will run automatically)
7. Submit a pull request

## 📝 License

This project is part of the Nexia fitness platform.
