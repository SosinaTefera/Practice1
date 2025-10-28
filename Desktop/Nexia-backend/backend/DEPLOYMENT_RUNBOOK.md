# Nexia Backend Deployment Runbook

## Pre-deployment Checklist

- [ ] Code is tested and ready for production
- [ ] Database migrations are ready
- [ ] Environment variables are configured
- [ ] Dependencies are updated in requirements.txt
- [ ] Health check endpoint is working

## Deployment Steps

### 1. Connect to Production Server
```bash
ssh ubuntu@your-server-ip
cd /opt/nexia/backend
```

### 2. Pull Latest Code
```bash
git pull origin main
```

### 3. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 4. Install/Update Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Restart Application Service
```bash
sudo systemctl restart nexia
```

### 7. Verify Deployment
```bash
# Check service status
sudo systemctl status nexia

# Check service logs
journalctl -u nexia -n 50

# Test health endpoint
curl https://nexiaapp.com/health

# Test API endpoints (with authentication)
curl -H "Authorization: Bearer YOUR_TOKEN" https://nexiaapp.com/api/v1/clients/
```

## Rollback Procedure

If deployment fails:

### 1. Stop Service
```bash
sudo systemctl stop nexia
```

### 2. Rollback Code
```bash
git reset --hard HEAD~1
```

### 3. Rollback Database (if needed)
```bash
alembic downgrade -1
```

### 4. Restart Service
```bash
sudo systemctl start nexia
```

## Monitoring Commands

### Service Status
```bash
sudo systemctl status nexia
```

### Service Logs
```bash
# Recent logs
journalctl -u nexia -n 100

# Follow logs in real-time
journalctl -u nexia -f

# Logs from specific time
journalctl -u nexia --since "2024-01-01 10:00:00"
```

### Health Checks
```bash
# Basic health check
curl https://nexiaapp.com/health

# API health check
curl https://nexiaapp.com/api/v1/docs
```

### Database Health
```bash
# Check database connection (if PostgreSQL)
psql $DATABASE_URL -c "SELECT 1;"

# Check migration status
alembic current
alembic history
```

## Common Issues & Solutions

### Service Won't Start
1. Check logs: `journalctl -u nexia -n 50`
2. Verify environment variables: `cat .env`
3. Check database connection
4. Verify Python dependencies: `pip list`

### Database Migration Issues
1. Check current migration: `alembic current`
2. Check migration history: `alembic history`
3. Manual migration: `alembic upgrade head`
4. If stuck, check database connection and permissions

### Performance Issues
1. Check system resources: `htop`, `df -h`
2. Check database performance
3. Review application logs for errors
4. Consider scaling resources

### Authentication Issues
1. Verify JWT secret key is set
2. Check token expiration settings
3. Verify CORS configuration
4. Check user roles and permissions

## Environment-Specific Notes

### Development
- Uses SQLite database
- Debug mode enabled
- Detailed logging
- CORS allows localhost

### Production
- Uses PostgreSQL database
- Debug mode disabled
- Production logging level
- CORS restricted to production domains
- HTTPS required
- Secure secret keys

## Security Checklist

- [ ] HTTPS is enabled
- [ ] CORS origins are restricted
- [ ] Secret keys are secure and unique
- [ ] Database credentials are secure
- [ ] SMTP credentials are secure (if used)
- [ ] File uploads are restricted
- [ ] Rate limiting is configured
- [ ] Logs don't contain sensitive data

## Backup Procedures

### Database Backup
```bash
# PostgreSQL backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql $DATABASE_URL < backup_file.sql
```

### Application Backup
```bash
# Backup application files
tar -czf nexia_backup_$(date +%Y%m%d_%H%M%S).tar.gz /opt/nexia/backend
```

## Emergency Contacts

- **System Administrator**: [Contact Info]
- **Database Administrator**: [Contact Info]
- **Development Team**: [Contact Info]

## Post-Deployment Verification

After successful deployment:

1. **Health Check**: Verify `/health` endpoint returns 200
2. **API Documentation**: Check `/api/v1/docs` is accessible
3. **Authentication**: Test login with valid credentials
4. **Core Features**: Test key endpoints (clients, exercises, training plans)
5. **Fatigue System**: Test fatigue analysis and alerts
6. **RBAC**: Verify role-based access control is working
7. **Performance**: Check response times are acceptable
8. **Logs**: Monitor logs for any errors or warnings

## Maintenance Windows

- **Scheduled Maintenance**: [Schedule]
- **Emergency Maintenance**: As needed
- **Database Maintenance**: [Schedule]
- **Security Updates**: [Schedule]
