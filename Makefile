# Kubernetes Certificate Health Check with Slack Notifications
# Makefile for easy project management

# Load configuration from config.yaml if available, otherwise use env vars
DOCKER_USERNAME ?= $(shell if [ -f config.yaml ]; then grep -A 1 "^docker:" config.yaml | grep username | cut -d'"' -f2 | cut -d'"' -f1 || echo ""; fi)
SLACK_TOKEN ?= $(shell if [ -f config.yaml ]; then grep -A 1 "^slack:" config.yaml | grep bot_token | cut -d'"' -f2 | cut -d'"' -f1 || echo ""; fi)
OPENAI_API_KEY ?= $(shell if [ -f config.yaml ]; then grep -A 1 "^openai:" config.yaml | grep api_key | cut -d'"' -f2 | cut -d'"' -f1 || echo ""; fi)

IMAGE_NAME = kube-certs-manager
IMAGE_TAG ?= latest
FULL_IMAGE_NAME = $(DOCKER_USERNAME)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: help build deploy deploy-cron clean test logs status helm-deploy helm-deploy-cron helm-clean helm-status setup-minikube check-minikube start-minikube stop-minikube reset-minikube docker-build docker-push docker-login config install activate secret openai-secret

# Default target
help:
	@echo "🔐 Kubernetes Certificate Health Check with Slack Notifications"
	@echo ""
	@echo "Available targets:"
	@echo "  setup-minikube - Install and setup minikube (if needed)"
	@echo "  start-minikube - Start minikube cluster"
	@echo "  stop-minikube  - Stop minikube cluster"
	@echo "  reset-minikube - Delete and recreate minikube cluster"
	@echo "  check-minikube - Check minikube status"
	@echo "  docker-login   - Login to Docker Hub"
	@echo "  docker-build   - Build and push Docker image to Docker Hub"
	@echo "  build          - Build Docker image (for local use)"
	@echo "  deploy         - Deploy one-time job using kubectl/kustomize"
	@echo "  deploy-cron    - Deploy CronJob using kubectl/kustomize"
	@echo "  helm-deploy    - Deploy one-time job using Helm (recommended)"
	@echo "  helm-deploy-cron - Deploy CronJob using Helm"
	@echo "  clean          - Clean up all resources (kubectl)"
	@echo "  helm-clean     - Clean up Helm release"
	@echo "  config         - Create config.yaml from example"
	@echo "  install        - Install Python dependencies in virtual environment"
	@echo "  test           - Test Slack connection locally [uses config.yaml]"
	@echo "  logs           - View application logs"
	@echo "  status         - Check deployment status"
	@echo "  helm-status    - Check Helm release status"
	@echo "  secret         - Create Kubernetes secret (requires SLACK_TOKEN)"
	@echo "  openai-secret  - Create OpenAI API key secret (requires OPENAI_API_KEY)"
	@echo ""
	@echo "Quick Start (Docker Hub):"
	@echo "  1. make config  # Create config.yaml from example"
	@echo "  2. Edit config.yaml with your secrets"
	@echo "  3. make docker-login DOCKER_USERNAME=your-username"
	@echo "  4. make docker-build DOCKER_USERNAME=your-username"
	@echo "  5. make setup-minikube"
	@echo "  6. make helm-deploy # Uses config.yaml values"
	@echo ""
	@echo "Note: config.yaml contains all secrets and is NOT committed to git"

# Check if minikube is installed
check-minikube:
	@echo "🔍 Checking minikube installation..."
	@if command -v minikube >/dev/null 2>&1; then \
		echo "✅ Minikube is installed"; \
		minikube version; \
	else \
		echo "❌ Minikube is not installed"; \
		echo "Run 'make setup-minikube' to install it"; \
		exit 1; \
	fi

# Install minikube
setup-minikube:
	@echo "🔧 Setting up minikube..."
	@if command -v minikube >/dev/null 2>&1; then \
		echo "✅ Minikube is already installed"; \
		minikube version; \
	else \
		echo "📦 Installing minikube..."; \
		if [ "$$(uname)" = "Darwin" ]; then \
			if command -v brew >/dev/null 2>&1; then \
				brew install minikube; \
			else \
				echo "❌ Homebrew not found"; \
				exit 1; \
			fi; \
		elif [ "$$(uname)" = "Linux" ]; then \
			curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64; \
			sudo install minikube-linux-amd64 /usr/local/bin/minikube; \
			rm minikube-linux-amd64; \
		fi; \
	fi
	@$(MAKE) start-minikube

# Start minikube cluster
start-minikube:
	@echo "🚀 Starting minikube cluster..."
	@if ! command -v minikube >/dev/null 2>&1; then \
		echo "❌ Minikube not found. Run 'make setup-minikube' first"; \
		exit 1; \
	fi
	@if minikube status 2>&1 | grep -q "host: Running"; then \
		echo "✅ Minikube is already running"; \
	else \
		minikube delete 2>/dev/null || true; \
		minikube start --driver=docker --cpus=2 --memory=3072; \
	fi

# Stop minikube cluster
stop-minikube:
	@minikube stop || true

# Reset minikube cluster
reset-minikube:
	@minikube delete 2>/dev/null || true
	@minikube start --driver=docker --cpus=2 --memory=3072

# Login to Docker Hub
docker-login:
	@if [ -z "$(DOCKER_USERNAME)" ]; then \
		echo "❌ DOCKER_USERNAME not found in config.yaml or environment"; \
		exit 1; \
	fi
	@docker login -u $(DOCKER_USERNAME)

# Build and push Docker image to Docker Hub
docker-build:
	@if [ -z "$(DOCKER_USERNAME)" ]; then \
		echo "❌ DOCKER_USERNAME not found in config.yaml or environment"; \
		exit 1; \
	fi
	@echo "🔨 Building Docker image..."
	docker build -t $(FULL_IMAGE_NAME) -f src/Dockerfile src/
	@echo "📤 Pushing image to Docker Hub..."
	docker push $(FULL_IMAGE_NAME)
	@echo "✅ Image built and pushed successfully!"

# Build Docker image for local minikube use
build: check-minikube
	@echo "🔨 Building Docker image for local use..."
	docker build -t kube-certs-manager:latest -f src/Dockerfile src/
	@echo "📦 Loading image into minikube..."
	minikube image load kube-certs-manager:latest
	@echo "✅ Build complete!"

# Deploy using kubectl/kustomize
deploy:
	@if [ -n "$(DOCKER_USERNAME)" ]; then \
		cd k8s && kustomize edit set image kube-certs-manager=$(FULL_IMAGE_NAME); \
		kubectl apply -k k8s/; \
	else \
		$(MAKE) build; \
		kubectl apply -k k8s/; \
	fi
	@echo "✅ Deployment complete!"

# Deploy CronJob using kubectl/kustomize
deploy-cron:
	@if [ -n "$(DOCKER_USERNAME)" ]; then \
		sed "s|image: kube-certs-manager:latest|image: $(FULL_IMAGE_NAME)|g; s|imagePullPolicy: Never|imagePullPolicy: Always|g" k8s/kube-certs-cronjob.yaml | kubectl apply -f -; \
	else \
		$(MAKE) build; \
		kubectl apply -f k8s/kube-certs-cronjob.yaml; \
	fi
	@echo "✅ CronJob deployment complete!"

# Deploy using Helm
helm-deploy: check-minikube
	@if [ -z "$(SLACK_TOKEN)" ]; then \
		echo "❌ SLACK_TOKEN not found in config.yaml or environment"; \
		exit 1; \
	fi
	@kubectl create namespace kube-certs --dry-run=client -o yaml | kubectl apply -f -
	@if [ -n "$(DOCKER_USERNAME)" ]; then \
		if [ -n "$(OPENAI_API_KEY)" ]; then \
			helm upgrade --install kube-certs-manager ./helm/kube-certs-manager \
				--set slack.token="$(SLACK_TOKEN)" \
				--set openai.apiKey="$(OPENAI_API_KEY)" \
				--set openai.enabled=true \
				--set image.repository="$(DOCKER_USERNAME)/$(IMAGE_NAME)" \
				--set image.tag="$(IMAGE_TAG)" \
				--set image.pullPolicy="Always" \
				--namespace kube-certs \
				--wait; \
		else \
			helm upgrade --install kube-certs-manager ./helm/kube-certs-manager \
				--set slack.token="$(SLACK_TOKEN)" \
				--set image.repository="$(DOCKER_USERNAME)/$(IMAGE_NAME)" \
				--set image.tag="$(IMAGE_TAG)" \
				--set image.pullPolicy="Always" \
				--namespace kube-certs \
				--wait; \
		fi; \
	else \
		$(MAKE) build; \
		if [ -n "$(OPENAI_API_KEY)" ]; then \
			helm upgrade --install kube-certs-manager ./helm/kube-certs-manager \
				--set slack.token="$(SLACK_TOKEN)" \
				--set openai.apiKey="$(OPENAI_API_KEY)" \
				--set openai.enabled=true \
				--namespace kube-certs \
				--wait; \
		else \
			helm upgrade --install kube-certs-manager ./helm/kube-certs-manager \
				--set slack.token="$(SLACK_TOKEN)" \
				--namespace kube-certs \
				--wait; \
		fi; \
	fi
	@echo "✅ Helm deployment complete!"

# Deploy CronJob using Helm
helm-deploy-cron: check-minikube
	@if [ -z "$(SLACK_TOKEN)" ]; then \
		echo "❌ SLACK_TOKEN not found in config.yaml or environment"; \
		exit 1; \
	fi
	@kubectl create namespace kube-certs --dry-run=client -o yaml | kubectl apply -f -
	@if [ -n "$(DOCKER_USERNAME)" ]; then \
		helm upgrade --install kube-certs-manager ./helm/kube-certs-manager \
			--set slack.token="$(SLACK_TOKEN)" \
			--set image.repository="$(DOCKER_USERNAME)/$(IMAGE_NAME)" \
			--set image.tag="$(IMAGE_TAG)" \
			--set image.pullPolicy="Always" \
			--set cronjob.enabled=true \
			--set cronjob.schedule="$(or $(CRON_SCHEDULE),0 0 * * *)" \
			--namespace kube-certs \
			--wait; \
	else \
		$(MAKE) build; \
		helm upgrade --install kube-certs-manager ./helm/kube-certs-manager \
			--set slack.token="$(SLACK_TOKEN)" \
			--set cronjob.enabled=true \
			--set cronjob.schedule="$(or $(CRON_SCHEDULE),0 0 * * *)" \
			--namespace kube-certs \
			--wait; \
	fi
	@echo "✅ Helm CronJob deployment complete!"

# Create Kubernetes secret
secret:
	@if [ -z "$(SLACK_TOKEN)" ]; then \
		echo "❌ SLACK_TOKEN not found in config.yaml or environment"; \
		exit 1; \
	fi
	@kubectl create namespace kube-certs --dry-run=client -o yaml | kubectl apply -f -
	@if [ -n "$(OPENAI_API_KEY)" ]; then \
		kubectl create secret generic slack-credentials \
			--from-literal=slack-bot-token="$(SLACK_TOKEN)" \
			--from-literal=openai-api-key="$(OPENAI_API_KEY)" \
			--namespace=kube-certs \
			--dry-run=client -o yaml | kubectl apply -f -; \
	else \
		kubectl create secret generic slack-credentials \
			--from-literal=slack-bot-token="$(SLACK_TOKEN)" \
			--namespace=kube-certs \
			--dry-run=client -o yaml | kubectl apply -f -; \
	fi
	@echo "✅ Secret created!"

# Create OpenAI secret
openai-secret:
	@if [ -z "$(OPENAI_API_KEY)" ]; then \
		echo "❌ OPENAI_API_KEY is required"; \
		exit 1; \
	fi
	@kubectl create namespace kube-certs --dry-run=client -o yaml | kubectl apply -f -
	@kubectl create secret generic openai-credentials \
		--from-literal=openai-api-key="$(OPENAI_API_KEY)" \
		--namespace=kube-certs \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "✅ OpenAI secret created!"

# Install dependencies
install:
	@echo "📦 Installing Python dependencies..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate && cd src && pip install -r requirements.txt; \
	else \
		python3 -m venv venv; \
		. venv/bin/activate && cd src && pip install -r requirements.txt; \
	fi
	@echo "✅ Dependencies installed!"

# Test Slack connection locally
test:
	@echo "🧪 Testing Slack connection..."
	@if [ -d "venv" ]; then \
		if [ -f "config.yaml" ]; then \
			echo "📝 Using config.yaml for configuration"; \
		fi; \
		. venv/bin/activate && cd src && python main.py; \
	else \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi

# View application logs
logs:
	@echo "📝 Viewing application logs..."
	@kubectl logs job/kube-certs-health-check -n kube-certs -c slack-notifier --tail=50

# Check deployment status
status:
	@echo "📊 Deployment status:"
	@kubectl get all -n kube-certs
	@echo ""
	@echo "Job details:"
	@kubectl describe job kube-certs-health-check -n kube-certs

# Check Helm release status
helm-status:
	@echo "📊 Helm release status:"
	@helm status kube-certs-manager -n kube-certs

# Clean up all resources (kubectl)
clean:
	@echo "🧹 Cleaning up resources..."
	@kubectl delete -k k8s/ --ignore-not-found=true
	@echo "✅ Cleanup complete!"

# Clean up Helm release
helm-clean:
	@echo "🧹 Cleaning up Helm release..."
	@helm uninstall kube-certs-manager -n kube-certs --ignore-not-found
	@echo "✅ Helm cleanup complete!"

# Create config.yaml from example
config:
	@echo "📝 Creating config.yaml from example..."
	@if [ -f "config.yaml" ]; then \
		echo "⚠️  config.yaml already exists!"; \
	else \
		cp config.yaml.example config.yaml; \
		echo "✅ config.yaml created from example"; \
		echo ""; \
		echo "📝 Next steps:"; \
		echo "   1. Edit config.yaml with your actual values"; \
		echo "   2. config.yaml is in .gitignore and will NOT be committed"; \
	fi

