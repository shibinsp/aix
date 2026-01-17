#!/bin/bash
# AI CyberX Kubernetes Deployment Script
# This script deploys the complete AI CyberX stack to Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_pods() {
    local namespace=$1
    local label=$2
    local timeout=$3

    log_info "Waiting for pods with label '$label' in namespace '$namespace'..."
    kubectl wait --for=condition=ready pod -l "$label" -n "$namespace" --timeout="${timeout}s" || {
        log_error "Timeout waiting for pods"
        kubectl get pods -n "$namespace" -l "$label"
        return 1
    }
    log_success "Pods are ready"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Install dependencies
install_dependencies() {
    log_info "Installing cluster dependencies..."

    # Install Nginx Ingress Controller (if not exists)
    if ! kubectl get namespace ingress-nginx &> /dev/null; then
        log_info "Installing Nginx Ingress Controller..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/baremetal/deploy.yaml
        sleep 10
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=controller -n ingress-nginx --timeout=120s
        log_success "Nginx Ingress Controller installed"
    else
        log_info "Nginx Ingress Controller already installed"
    fi

    # Install cert-manager (if not exists)
    if ! kubectl get namespace cert-manager &> /dev/null; then
        log_info "Installing cert-manager..."
        kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
        sleep 10
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=120s
        log_success "cert-manager installed"
    else
        log_info "cert-manager already installed"
    fi

    log_success "Dependencies installed"
}

# Deploy application
deploy_app() {
    log_info "Starting AI CyberX deployment..."

    # Phase 1: Namespaces
    log_info "Phase 1: Creating namespaces..."
    kubectl apply -f "$SCRIPT_DIR/namespaces/"
    log_success "Namespaces created"

    # Phase 2: Storage
    log_info "Phase 2: Applying storage classes..."
    kubectl apply -f "$SCRIPT_DIR/storage/" || log_warning "Storage classes may already exist"
    log_success "Storage classes applied"

    # Phase 3: Secrets
    log_info "Phase 3: Creating secrets..."
    log_warning "IMPORTANT: Make sure you've updated the secrets with real values!"
    kubectl apply -f "$SCRIPT_DIR/secrets/"
    log_success "Secrets created"

    # Phase 4: ConfigMaps
    log_info "Phase 4: Creating ConfigMaps..."
    kubectl apply -f "$SCRIPT_DIR/configmaps/"
    log_success "ConfigMaps created"

    # Phase 5: RBAC
    log_info "Phase 5: Setting up RBAC..."
    kubectl apply -f "$SCRIPT_DIR/rbac/"
    log_success "RBAC configured"

    # Phase 6: Network Policies
    log_info "Phase 6: Applying network policies..."
    kubectl apply -f "$SCRIPT_DIR/network-policies/"
    log_success "Network policies applied"

    # Phase 7: Database and Cache
    log_info "Phase 7: Deploying database and cache..."
    kubectl apply -f "$SCRIPT_DIR/database/"
    kubectl apply -f "$SCRIPT_DIR/cache/"

    log_info "Waiting for PostgreSQL to be ready..."
    wait_for_pods "cyberaix-data" "app=postgres" 180

    log_info "Waiting for Redis to be ready..."
    wait_for_pods "cyberaix-data" "app=redis" 60
    log_success "Database and cache deployed"

    # Phase 8: Run migrations
    log_info "Phase 8: Running database migrations..."
    # Delete old migration job if exists
    kubectl delete job db-migration -n cyberaix-system --ignore-not-found=true
    kubectl apply -f "$SCRIPT_DIR/jobs/db-migration-job.yaml"

    log_info "Waiting for migration to complete..."
    kubectl wait --for=condition=complete job/db-migration -n cyberaix-system --timeout=300s || {
        log_error "Migration failed!"
        kubectl logs job/db-migration -n cyberaix-system
        exit 1
    }
    log_success "Database migrations completed"

    # Phase 9: Deploy applications
    log_info "Phase 9: Deploying backend and frontend..."
    kubectl apply -f "$SCRIPT_DIR/backend/"
    kubectl apply -f "$SCRIPT_DIR/frontend/"

    log_info "Waiting for backend to be ready..."
    wait_for_pods "cyberaix-system" "app=backend" 180

    log_info "Waiting for frontend to be ready..."
    wait_for_pods "cyberaix-system" "app=frontend" 120
    log_success "Applications deployed"

    # Phase 10: Ingress
    log_info "Phase 10: Configuring ingress..."
    kubectl apply -f "$SCRIPT_DIR/ingress/"
    log_success "Ingress configured"

    log_success "AI CyberX deployment completed!"
}

# Show status
show_status() {
    echo ""
    log_info "Deployment Status:"
    echo ""

    echo "=== Namespaces ==="
    kubectl get namespaces | grep cyberaix
    echo ""

    echo "=== System Pods ==="
    kubectl get pods -n cyberaix-system -o wide
    echo ""

    echo "=== Data Pods ==="
    kubectl get pods -n cyberaix-data -o wide
    echo ""

    echo "=== Labs Pods ==="
    kubectl get pods -n cyberaix-labs -o wide 2>/dev/null || echo "No lab pods running"
    echo ""

    echo "=== Services ==="
    kubectl get svc -n cyberaix-system
    kubectl get svc -n cyberaix-data
    echo ""

    echo "=== Ingress ==="
    kubectl get ingress -n cyberaix-system
    echo ""

    echo "=== Certificates ==="
    kubectl get certificate -n cyberaix-system 2>/dev/null || echo "Certificates not ready yet"
}

# Cleanup
cleanup() {
    log_warning "This will delete ALL AI CyberX resources!"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Cleanup cancelled"
        exit 0
    fi

    log_info "Cleaning up AI CyberX..."

    kubectl delete namespace cyberaix-labs --ignore-not-found=true
    kubectl delete namespace cyberaix-system --ignore-not-found=true
    kubectl delete namespace cyberaix-data --ignore-not-found=true

    log_success "Cleanup completed"
}

# Main
main() {
    case "${1:-deploy}" in
        deploy)
            check_prerequisites
            install_dependencies
            deploy_app
            show_status
            ;;
        status)
            show_status
            ;;
        cleanup)
            cleanup
            ;;
        deps)
            check_prerequisites
            install_dependencies
            ;;
        *)
            echo "Usage: $0 {deploy|status|cleanup|deps}"
            echo ""
            echo "Commands:"
            echo "  deploy  - Full deployment (default)"
            echo "  status  - Show deployment status"
            echo "  cleanup - Remove all resources"
            echo "  deps    - Install dependencies only"
            exit 1
            ;;
    esac
}

main "$@"
