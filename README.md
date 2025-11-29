# Kubernetes Certificate Health Check with Slack Notifications

A complete Kubernetes solution that scans cluster certificates and automatically sends formatted health reports to Slack.

![Status](https://img.shields.io/badge/status-ready-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Architecture](#-architecture)
- [Deployment Options](#-deployment-options)
- [Slack Setup](#-slack-app-setup)
- [What You'll Get](#-what-youll-get-in-slack)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Cleanup](#-cleanup)

---

## 🚀 Quick Start

### Prerequisites

- Docker installed
- Minikube running (for Kubernetes)
- Slack app configured with bot token
- Docker Hub account (for public deployment)
- **OpenAI API key** (optional - for AI-powered analysis)

### Configuration Setup

The application uses a `config.yaml` file for configuration.

1. **Copy the example config:**
```bash
cp config.yaml.example config.yaml
```

2. **Edit `config.yaml` with your values:**
```yaml
slack:
  bot_token: "xoxb-your-actual-token"
  channel: "#kube-certs"

docker:
  username: "your-dockerhub-username"

openai:
  api_key: "sk-your-openai-key"  # Optional
  enabled: true
```

3. **Note:** `config.yaml` is in `.gitignore` and will NOT be committed

### Fastest Deployment

**1. Setup Configuration:**
```bash
# Create config file from example
make config

# Edit config.yaml with your secrets
# - slack.bot_token
# - docker.username  
# - openai.api_key (optional)
```

**2. Deploy:**
```bash
# Build and push to Docker Hub
make docker-login
make docker-build  # Uses docker.username from config.yaml

# Setup Kubernetes
make setup-minikube

# Deploy (uses secrets from config.yaml)
make helm-deploy
```

**3. Check Results:**
```bash
make logs
```

---

## ✨ Features

### 🔐 Certificate Scanning
- Comprehensive certificate health checks
- Scans all Kubernetes certificates (API server, CA, etcd, etc.)
- Detects expired and expiring certificates
- Validates certificate configuration against Kubernetes requirements
- JSON output for detailed analysis

### 📱 Slack Integration
- **Rich formatted messages** with real-time status
- **Interactive HTML reports** with complete certificate details
- **Critical issue highlighting** for expired certificates
- **Certificate-by-certificate breakdown** with expiry dates
- **Color-coded status indicators** (Valid/Expiring/Expired)

### 🤖 AI-Powered Analysis (Optional)
- **OpenAI integration** for intelligent certificate insights
- **Risk prioritization** of findings
- **Actionable remediation roadmaps**
- **Business impact assessment**
- **Estimated fix time estimates**

### ☸️ Kubernetes Native
- Runs as Kubernetes Job or CronJob
- Sidecar container design for flexibility
- Secure secret management
- RBAC for safe execution
- Resource limits and health checks

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│      kube-certs-health-check                  │
│                                              │
│  ┌──────────────┐     ┌───────────────────┐  │
│  │ cert-scanner │     │  slack-notifier   │  │
│  │  Container   │◄────┤  Container        │  │
│  │  Scans Certs │     │  Reads Results    │  │
│  └──────┬───────┘     └────────┬──────────┘  │
│         │                      │             │
│         ▼                      ▼             │
│      Shared Volume        Slack Channel      │
└──────────────────────────────────────────────┘
```

---

## 📋 Deployment Options

### 🐍 Local Testing

**Perfect for development and quick tests:**

```bash
# Install dependencies
make install

# Set Slack token
export SLACK_BOT_TOKEN=xoxb-your-token-here

# Test with dummy data
make test
```

**What you'll see:**
- ✅ Test messages in Slack
- ✅ Formatted reports with sample data
- ✅ HTML report generation

---

### ☸️ Kubernetes Job (One-Time Scan)

**For running a single scan:**

```bash
# 1. Setup minikube
make setup-minikube

# 2. Create secret
make secret SLACK_TOKEN=xoxb-your-token

# 3. Build and deploy (local image)
make build
make deploy

# OR use Docker Hub image
make docker-login DOCKER_USERNAME=your-username
make docker-build DOCKER_USERNAME=your-username
make deploy DOCKER_USERNAME=your-username

# 4. Monitor
make status
make logs
```

---

### 🎛️ Helm Chart (Recommended)

**Production-ready with easy configuration:**

```bash
# 1. Setup
make setup-minikube

# 2. Deploy with local image
make helm-deploy SLACK_TOKEN=xoxb-your-token

# OR with Docker Hub image
make docker-login DOCKER_USERNAME=your-username
make docker-build DOCKER_USERNAME=your-username
make helm-deploy SLACK_TOKEN=xoxb-your-token DOCKER_USERNAME=your-username

# 3. Monitor
make helm-status
make logs
```

**Custom configuration:**

Edit `helm/kube-certs-manager/values.yaml` or override values:

```bash
helm install kube-certs-manager helm/kube-certs-manager \
  --namespace kube-certs \
  --create-namespace \
  --set slack.channel="#security-alerts" \
  --set certscanner.certBasePath="/etc/kubernetes/pki"
```

---

### ⏰ Scheduled CronJob

**Automated recurring scans:**

```bash
# Default: daily at midnight GMT
make helm-deploy-cron SLACK_TOKEN=xoxb-your-token DOCKER_USERNAME=your-username

# Custom schedule: every 6 hours
make helm-deploy-cron SLACK_TOKEN=xoxb-your-token DOCKER_USERNAME=your-username CRON_SCHEDULE="0 */6 * * *"

# Custom schedule: every Monday at 9 AM
make helm-deploy-cron SLACK_TOKEN=xoxb-your-token DOCKER_USERNAME=your-username CRON_SCHEDULE="0 9 * * 1"
```

**Cron Schedule Examples:**
- `"0 0 * * *"` - Daily at midnight GMT
- `"0 */6 * * *"` - Every 6 hours
- `"0 9 * * 1"` - Every Monday at 9 AM
- `"0 0 * * 0"` - Every Sunday at midnight

---

## 🔧 Slack App Setup

### Step 1: Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create an App"** → **"From scratch"**
3. Name: `kube-certs-health-checker`
4. Choose your workspace
5. Click **"Create App"**

### Step 2: Configure Bot Permissions

1. Go to **Features → OAuth & Permissions**
2. Scroll to **"Bot Token Scopes"** and add:
   ```
   - app_mentions:read
   - channels:join
   - channels:read       ← Required for file uploads!
   - chat:write
   - files:write
   ```

3. Click **"Install to Workspace"**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)

### Step 3: Add Bot to Channel

```bash
# In your Slack channel (e.g., #kube-certs)
/invite @kube-certs-health-checker
```

### Step 4: Test

```bash
export SLACK_BOT_TOKEN=xoxb-your-token-here
make test
```

✅ **You should see test messages in your Slack channel!**

---

## 📊 What You'll Get in Slack

### 1. 📱 Formatted Slack Message

A rich message with:
- **Overall Status**: ✅ HEALTHY / ⚠️ WARNING / 🔴 CRITICAL
- **Summary Statistics**: Total certificates, valid, expired, expiring soon
- **Critical Issues**: Expired certificates highlighted
- **Certificate Breakdown**: Status for each certificate
- **Timestamp**: When the scan was completed

### 2. 🎨 Interactive HTML Report

A beautiful, downloadable HTML file with:
- **Executive Summary**: Visual dashboard with color-coded stats
- **Certificate Details**: Every certificate with full information
- **Expandable Sections**: Click to expand/collapse certificate details
- **Complete Certificate Info**: Subject, issuer, validity, SANs, issues
- **Color Coding**: ✅ Valid (green), ⚠️ Expiring (yellow), 🔴 Expired (red)
- **Mobile Responsive**: Works on any device
- **Print Friendly**: Ready for PDF export

**How to use:**
1. Download the HTML file from Slack
2. Open in any web browser
3. Click certificates to expand/collapse details
4. Use "Expand/Collapse All" button
5. Print or save as PDF for compliance

---

## ⚙️ Configuration

The application supports configuration via **YAML file** or **environment variables**.

### Primary Method: config.yaml (Recommended)

1. **Create config file:**
```bash
make config  # Creates config.yaml from config.yaml.example
```

2. **Edit config.yaml:**
```yaml
slack:
  bot_token: "xoxb-your-token-here"
  channel: "#kube-certs"

docker:
  username: "your-dockerhub-username"

openai:
  api_key: "sk-your-key"  # Optional
  enabled: true
```

3. **Benefits:**
- All secrets in one file
- Version control excluded (`.gitignore`)
- Easy to manage

### Alternative: Environment Variables

You can still use environment variables (they work as fallback):
| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | Required | Bot OAuth token |
| `SLACK_CHANNEL` | `#kube-certs` | Target channel |
| `OPENAI_API_KEY` | Optional | For AI-powered security analysis |

### Helm Values

Key configuration in `helm/kube-certs-manager/values.yaml`:

```yaml
# Slack configuration
slack:
  channel: "#kube-certs"
  
# Certificate scanner
certscanner:
  certBasePath: "/etc/kubernetes/pki"
  
# Resource limits
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "channel_not_found" error**
```bash
# Invite bot to channel
/invite @kube-certs-health-checker

# Verify token
curl -H "Authorization: Bearer xoxb-your-token" \
  https://slack.com/api/auth.test
```

**2. "missing_scope" error**
- Add required scopes in OAuth & Permissions
- Reinstall the app after adding scopes

**3. Job fails to start**
```bash
# Check minikube
minikube status
minikube start

# Verify image
minikube image ls | grep kube-certs-manager

# Load image if missing
make build
```

**4. No notifications in Slack**
```bash
# Check notifier logs
kubectl logs job/kube-certs-health-check -n kube-certs -c slack-notifier

# Verify secret
kubectl get secret slack-credentials -n kube-certs -o yaml

# Test token
make test
```

**5. Certificates not found**
```bash
# Verify certificate path
kubectl exec -it job/kube-certs-health-check -n kube-certs -c cert-scanner -- ls -la /etc/kubernetes/pki

# Check if cluster is kubeadm-based
kubectl exec -it job/kube-certs-health-check -n kube-certs -c cert-scanner -- cat /etc/kubernetes/manifests/kube-apiserver.yaml
```

### Debug Commands

```bash
# View all resources
kubectl get all -n kube-certs

# Describe job
kubectl describe job kube-certs-health-check -n kube-certs

# Check secret
kubectl get secret slack-credentials -n kube-certs

# Test Slack locally
export SLACK_BOT_TOKEN=xoxb-your-token
make test
```

---

## 🧹 Cleanup

### Remove Resources

```bash
# Kubernetes deployment
make clean

# Helm deployment
make helm-clean

# Both
make clean && make helm-clean
```

### Complete Cleanup

```bash
# Remove all resources
make clean
make helm-clean

# Remove Docker images
docker rmi kube-certs-manager:latest

# Remove namespace
kubectl delete namespace kube-certs
```

---

## 📚 Project Structure

```
├── src/                          # Source code
│   ├── slack_app/                # Slack integration
│   │   ├── client.py            # Slack API client
│   │   ├── formatter.py         # Message formatting
│   │   └── notifier.py          # Notification logic
│   ├── certs_analyzer/          # Certificate analysis
│   │   ├── scanner.py           # Certificate scanning
│   │   └── analyzer.py          # Result analysis
│   ├── utils/                    # Utilities
│   │   ├── html_report.py       # HTML report generation
│   │   ├── config.py             # Configuration
│   │   └── logger.py            # Logging setup
│   ├── app.py                   # Main application
│   ├── main.py                  # Entry point
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Container image
├── k8s/                          # Kubernetes manifests
│   ├── namespace.yaml            # Namespace definition
│   ├── rbac.yaml                # RBAC configuration
│   ├── kube-certs-job.yaml      # Job definition
│   ├── kube-certs-cronjob.yaml  # CronJob definition
│   └── kustomization.yaml       # Kustomize config
├── helm/                         # Helm chart
│   └── kube-certs-manager/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── scripts/                      # Deployment scripts
├── Makefile                      # Project commands
└── README.md                     # This file
```

---

## 🛠️ Available Commands

```bash
make help              # Show all available commands

# Setup
make install           # Install Python dependencies
make setup-minikube    # Install and start minikube

# Testing
make test              # Test Slack connection locally

# Docker Hub
make docker-login DOCKER_USERNAME=your-username
make docker-build DOCKER_USERNAME=your-username

# Kubernetes (kubectl)
make build             # Build Docker image
make secret SLACK_TOKEN=xoxb-your-token
make deploy            # Deploy Job
make deploy-cron       # Deploy CronJob
make status            # Check status
make logs              # View logs
make clean             # Clean up

# Helm
make helm-deploy SLACK_TOKEN=xoxb-your-token
make helm-deploy-cron SLACK_TOKEN=xoxb-your-token
make helm-status       # Check Helm release
make helm-clean        # Clean up Helm
```

---

## 📖 Quick Reference

### One-Time Scan (Docker Hub)
```bash
make docker-login DOCKER_USERNAME=your-username
make docker-build DOCKER_USERNAME=your-username
make setup-minikube
make helm-deploy SLACK_TOKEN=xoxb-your-token DOCKER_USERNAME=your-username
make logs
```

### Scheduled Scans
```bash
make helm-deploy-cron SLACK_TOKEN=xoxb-your-token DOCKER_USERNAME=your-username
```

### Local Testing
```bash
make install
export SLACK_BOT_TOKEN=xoxb-your-token
make test
```

---

## 🔐 Security Notes

- ✅ **Never commit tokens** - Use Kubernetes secrets or env vars
- ✅ **Use Docker Hub access tokens** instead of passwords
- ✅ **Enable 2FA** on Docker Hub
- ✅ **Use private repos** for sensitive workloads
- ✅ **Rotate tokens regularly** in production
- ✅ **Certificates are read-only** - No modifications are made

---

## 🤝 Contributing

Contributions welcome! Feel free to submit issues and enhancement requests.

---

## 📄 License

MIT License - See LICENSE file for details.

---

**Need help?** Check the [Troubleshooting](#-troubleshooting) section or open an issue on GitHub.

