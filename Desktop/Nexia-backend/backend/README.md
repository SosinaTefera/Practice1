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
| `DATABASE_URL` | Database connection string | `sqlite:///./nexia.db` |
| `SECRET_KEY` | Secret key for security | `your-secret-key-change-in-production` |
| `ENVIRONMENT` | Environment (development/production/testing) | `development` |
| `DEBUG` | Enable debug mode | `True` |
| `LOG_LEVEL` | Logging level | `INFO` |

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

## 🔌 Frontend Integration Samples (Form → API → Response)

Open these minimal HTML examples in a local static server and point them to your running API (production by default is set to `https://nexiaapp.com`).

- Register: `backend/examples/forms/register.html`
- Login: `backend/examples/forms/login.html`
- Create Client Profile: `backend/examples/forms/client_profile.html`
- Exercises Search/List: `backend/examples/forms/exercises.html`

Run a quick local server to avoid browser CORS/security restrictions on file URLs:

```bash
cd backend
python3 -m http.server 5500
```

Then visit:

- http://localhost:5500/examples/forms/register.html
- http://localhost:5500/examples/forms/login.html
- http://localhost:5500/examples/forms/client_profile.html
- http://localhost:5500/examples/forms/exercises.html

If your backend enforces CORS, ensure `BACKEND_CORS_ORIGINS` includes `http://localhost:5500`.

## 🚀 Production Deployment

### Database Migration
```bash
# For PostgreSQL
DATABASE_URL="postgresql://user:password@localhost/nexia"

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

### Security Considerations
- Use HTTPS in production
- Configure proper CORS origins
- Set up trusted hosts
- Use environment-specific secret keys
- Enable proper logging and monitoring

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
