# Story 1.6: Deploy to AWS EC2 with Docker Compose

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to deploy GamePulse to AWS EC2 with Docker Compose and Traefik reverse proxy,
So that I have a live public URL accessible for demos and interviews.

---

## Acceptance Criteria

**Given** I have AWS infrastructure provisioned via Terraform (Story 1.1b)
**When** I configure the EC2 instance for production deployment
**Then** the instance is already configured with:
- Security group allowing ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Elastic IP attached for persistent public IP
- Docker and Docker Compose installed via Terraform user_data

**And** I create a production Docker Compose configuration (`docker-compose.prod.yml`) with:
- Traefik reverse proxy for automatic HTTPS
- PostgreSQL with persistent volume
- Backend API container
- Frontend served by Nginx

**And** I manually deploy the first time:
```bash
ssh ubuntu@<ELASTIC_IP>
git clone <repo_url> gamepulse
cd gamepulse
# Copy .env file with production secrets
docker-compose -f docker-compose.prod.yml up -d
```

**And** I can access the application at `http://<ELASTIC_IP>` (HTTPS after Traefik provisions cert)

**And** the health check endpoint responds: `curl http://<ELASTIC_IP>/api/health`

**And** subsequent deployments work via GitHub Actions (Story 1.5 workflow now succeeds)

---

## Prerequisites

- Story 1.1b (AWS infrastructure provisioned via Terraform)
- Story 1.4 (database schema exists)
- Story 1.5 (CI/CD pipeline ready)

---

## Technical Notes

**AWS EC2 Setup:**
- Instance type: t2.micro (1 vCPU, 1GB RAM)
- AMI: Ubuntu 22.04 LTS
- Free tier: 750 hours/month

**Security Group Rules:**
```
Inbound:
- Port 22 (SSH) from My IP
- Port 80 (HTTP) from 0.0.0.0/0
- Port 443 (HTTPS) from 0.0.0.0/0

Outbound:
- All traffic to 0.0.0.0/0
```

**Install Docker:**
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu
```

**docker-compose.prod.yml Template:**
```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.5
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=your-email@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./letsencrypt:/letsencrypt

  db:
    image: timescale/timescaledb:latest-pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: gamepulse
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: gamepulse

  backend:
    build: ./backend
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://gamepulse:${DB_PASSWORD}@db:5432/gamepulse
    labels:
      - "traefik.http.routers.backend.rule=Host(`${DOMAIN}`) && PathPrefix(`/api`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"

  frontend:
    build: ./frontend
    labels:
      - "traefik.http.routers.frontend.rule=Host(`${DOMAIN}`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"

volumes:
  postgres_data:
```

**Environment Variables:**
- Store in `/home/ubuntu/gamepulse/.env` (not in git)
- Required: DB_PASSWORD, DOMAIN (or use Elastic IP)

**Cost Estimate:**
- EC2 t2.micro: $0/month (within free tier)
- EBS storage (20GB): ~$2/month
- Data transfer: Negligible for portfolio project
- **Total: ~$2/month**

**Optional:** Set up domain name (point DNS A record to Elastic IP)

---

## Definition of Done

- [ ] EC2 instance provisioned with Ubuntu 22.04
- [ ] Security group configured correctly
- [ ] Elastic IP attached
- [ ] Docker and Docker Compose installed
- [ ] SSH key pair created and added to GitHub secrets
- [ ] docker-compose.prod.yml created
- [ ] .env file configured on server
- [ ] Manual deployment successful
- [ ] Application accessible via HTTP
- [ ] Health check endpoint responds
- [ ] GitHub Actions deployment works
- [ ] HTTPS certificate provisioned by Traefik
- [ ] Documentation added with deployment steps
- [ ] Changes committed to git
