# Epic 4 Parameter Store Configuration

**Purpose:** AWS Parameter Store configuration for Reddit data pipeline environment variables (Story 4-1).

## Required Parameters for Production

Add these parameters to AWS Parameter Store under `/gamepulse/production/app/`:

```bash
# Epic 4: Reddit Data Pipeline Configuration
# All parameters are non-secret (Type: String, not SecureString)

# Enable/disable Reddit polling (toggle for legal compliance)
aws ssm put-parameter \
  --name '/gamepulse/production/app/reddit_polling_enabled' \
  --value 'true' \
  --type String \
  --description 'Epic 4: Enable/disable Reddit data polling' \
  --region us-east-1

# User-Agent header for Reddit API requests
aws ssm put-parameter \
  --name '/gamepulse/production/app/reddit_user_agent' \
  --value 'GamePulse/1.0 (Educational portfolio project; +https://gamepulse.top)' \
  --type String \
  --description 'Epic 4: Reddit API User-Agent header' \
  --region us-east-1

# Rate limit for Reddit API (queries per minute)
aws ssm put-parameter \
  --name '/gamepulse/production/app/reddit_rate_limit_qpm' \
  --value '10' \
  --type String \
  --description 'Epic 4: Reddit API rate limit (queries per minute)' \
  --region us-east-1
```

## Verification

After adding parameters, verify they're accessible:

```bash
# List all Epic 4 parameters
aws ssm get-parameters-by-path \
  --path '/gamepulse/production/app/' \
  --recursive \
  --query 'Parameters[?contains(Name, `reddit`)].Name' \
  --region us-east-1

# Test environment generation
cd /opt/gamepulse
bash backend/scripts/create-env-from-aws-parameters.sh production test.env
grep REDDIT test.env
rm test.env
```

## Deployment Integration

The `create-env-from-aws-parameters.sh` script automatically maps these parameters:

- `/gamepulse/production/app/reddit_polling_enabled` → `REDDIT_POLLING_ENABLED`
- `/gamepulse/production/app/reddit_user_agent` → `REDDIT_USER_AGENT`
- `/gamepulse/production/app/reddit_rate_limit_qpm` → `REDDIT_RATE_LIMIT_QPM`

No additional deployment script changes required beyond what's in this commit.

## Local Development

For local development, these values are already in `.env.example`. Just run:

```bash
cp .env.example .env
```

## Toggling Reddit Polling

To disable Reddit polling in production (recommended for forks):

```bash
aws ssm put-parameter \
  --name '/gamepulse/production/app/reddit_polling_enabled' \
  --value 'false' \
  --type String \
  --overwrite \
  --region us-east-1

# Redeploy or manually restart services
git push origin main
```

## Legal Disclaimer

Reddit polling violates Reddit's Terms of Service. These parameters enable toggling the feature on/off without code changes. See [README.md Legal Disclaimer](../README.md#legal-disclaimer) and [CLAUDE.md Troubleshooting](../CLAUDE.md#issue-reddit-data-pipeline-legal-concerns) for full details.
