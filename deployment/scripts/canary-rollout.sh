#!/bin/bash
set -euo pipefail

# Canary Deployment Script
# Gradually increases traffic to canary deployment
#
# Services in the full stack:
#   ai-orchestrator   (port 5001) - Blue/Green deployable
#   agentic-team      (port 5002) - Blue/Green deployable
#   mcp-server        (port 8000) - Single replica, rolling update
#   context-dashboard (port 5003) - Single replica, rolling update

NAMESPACE="${NAMESPACE:-ai-orchestrator}"
APP_NAME="${APP_NAME:-ai-orchestrator}"
APP_PORT="${APP_PORT:-5001}"
CONTAINER_NAME="${CONTAINER_NAME:-$APP_NAME}"
STABLE_DEPLOYMENT="${APP_NAME}-stable"
CANARY_DEPLOYMENT="${APP_NAME}-canary"
STABLE_REPLICAS=5
CANARY_REPLICAS=1

echo "================================================"
echo "Canary Deployment Rollout"
echo "================================================"
echo "Namespace: $NAMESPACE"
echo "Application: $APP_NAME"
echo "Stable Deployment: $STABLE_DEPLOYMENT"
echo "Canary Deployment: $CANARY_DEPLOYMENT"
echo "App Port: $APP_PORT"
echo "================================================"

# Traffic distribution stages: 10% -> 25% -> 50% -> 100%
STAGES=(
    "10:5:1"   # 10% canary: 5 stable, 1 canary
    "25:3:1"   # 25% canary: 3 stable, 1 canary
    "50:1:1"   # 50% canary: 1 stable, 1 canary
    "100:0:3"  # 100% canary: 0 stable, 3 canary
)

# Function to check metrics
check_metrics() {
    local deployment=$1
    local threshold=${2:-95}  # Success rate threshold

    echo "Checking metrics for $deployment..."

    # Get error rate from Prometheus (example query)
    local success_rate=$(kubectl exec -n monitoring prometheus-0 -- \
        promtool query instant 'sum(rate(http_requests_total{deployment="'$deployment'",status=~"2.."}[5m])) / sum(rate(http_requests_total{deployment="'$deployment'"}[5m])) * 100' \
        2>/dev/null | grep -oP '\d+\.\d+' || echo "100")

    echo "Success rate: ${success_rate}%"

    # Compare with threshold
    if (( $(echo "$success_rate < $threshold" | bc -l) )); then
        echo "❌ Success rate below threshold ($threshold%)"
        return 1
    fi

    echo "✅ Metrics look good"
    return 0
}

# Function to scale deployments
scale_deployments() {
    local stable_replicas=$1
    local canary_replicas=$2
    local percentage=$3

    echo ""
    echo "Scaling to $percentage% canary traffic..."
    echo "  Stable replicas: $stable_replicas"
    echo "  Canary replicas: $canary_replicas"

    # Scale stable deployment
    kubectl scale deployment "$STABLE_DEPLOYMENT" \
        --replicas="$stable_replicas" \
        -n "$NAMESPACE"

    # Scale canary deployment
    kubectl scale deployment "$CANARY_DEPLOYMENT" \
        --replicas="$canary_replicas" \
        -n "$NAMESPACE"

    echo "Waiting for deployments to be ready..."
    kubectl rollout status deployment "$STABLE_DEPLOYMENT" -n "$NAMESPACE" --timeout=5m
    kubectl rollout status deployment "$CANARY_DEPLOYMENT" -n "$NAMESPACE" --timeout=5m

    echo "✅ Scaling completed"
}

# Function to monitor stage
monitor_stage() {
    local duration=${1:-300}  # Default 5 minutes
    local percentage=$2

    echo ""
    echo "Monitoring stage for ${duration}s ($percentage% canary)..."

    local interval=30
    local iterations=$((duration / interval))

    for i in $(seq 1 $iterations); do
        echo "  Check $i/$iterations..."

        if ! check_metrics "$CANARY_DEPLOYMENT"; then
            echo "❌ Canary metrics degraded!"
            return 1
        fi

        if [ $i -lt $iterations ]; then
            sleep $interval
        fi
    done

    echo "✅ Stage monitoring completed successfully"
    return 0
}

# Function to rollback
rollback() {
    echo ""
    echo "🔄 Rolling back canary deployment..."

    # Scale canary to 0
    kubectl scale deployment "$CANARY_DEPLOYMENT" --replicas=0 -n "$NAMESPACE"

    # Restore stable to full capacity
    kubectl scale deployment "$STABLE_DEPLOYMENT" --replicas=5 -n "$NAMESPACE"

    echo "✅ Rollback completed"
    exit 1
}

# Function to promote canary
promote_canary() {
    echo ""
    echo "🎉 Promoting canary to stable..."

    # Update stable deployment with canary image
    local canary_image=$(kubectl get deployment "$CANARY_DEPLOYMENT" -n "$NAMESPACE" \
        -o jsonpath='{.spec.template.spec.containers[0].image}')

    kubectl set image deployment/"$STABLE_DEPLOYMENT" \
        "$CONTAINER_NAME"="$canary_image" \
        -n "$NAMESPACE"

    # Scale stable back to normal
    kubectl scale deployment "$STABLE_DEPLOYMENT" --replicas=5 -n "$NAMESPACE"

    # Scale down canary
    kubectl scale deployment "$CANARY_DEPLOYMENT" --replicas=0 -n "$NAMESPACE"

    echo "✅ Canary promoted to stable"
}

# Main execution
main() {
    echo ""
    echo "Starting canary rollout..."
    echo ""

    # Verify canary deployment exists and is healthy
    if ! kubectl get deployment "$CANARY_DEPLOYMENT" -n "$NAMESPACE" &> /dev/null; then
        echo "❌ Canary deployment not found"
        exit 1
    fi

    # Process each stage
    for stage in "${STAGES[@]}"; do
        IFS=':' read -r percentage stable_replicas canary_replicas <<< "$stage"

        echo ""
        echo "================================================"
        echo "Stage: ${percentage}% Canary Traffic"
        echo "================================================"

        # Scale deployments
        scale_deployments "$stable_replicas" "$canary_replicas" "$percentage"

        # Determine monitoring duration based on stage
        case $percentage in
            10)  monitor_duration=300 ;;  # 5 minutes
            25)  monitor_duration=600 ;;  # 10 minutes
            50)  monitor_duration=900 ;;  # 15 minutes
            100) monitor_duration=600 ;;  # 10 minutes
            *)   monitor_duration=300 ;;
        esac

        # Monitor this stage
        if ! monitor_stage "$monitor_duration" "$percentage"; then
            echo "❌ Stage $percentage% failed"
            rollback
        fi

        echo "✅ Stage $percentage% completed successfully"

        # Prompt for next stage (except for last stage)
        if [ "$percentage" != "100" ]; then
            echo ""
            read -p "Proceed to next stage? (yes/no/rollback) " -r
            case $REPLY in
                [Yy][Ee][Ss])
                    continue
                    ;;
                [Rr][Oo][Ll][Ll][Bb][Aa][Cc][Kk])
                    rollback
                    ;;
                *)
                    echo "Paused. Keeping current stage."
                    echo "Run script again to continue or rollback manually."
                    exit 0
                    ;;
            esac
        fi
    done

    echo ""
    echo "================================================"
    echo "✅ Canary rollout completed successfully!"
    echo "================================================"
    echo ""

    # Promote canary to stable
    read -p "Promote canary to stable? (yes/no) " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        promote_canary
    else
        echo "Canary not promoted. Manual action required."
    fi
}

# Trap errors and rollback
trap 'rollback' ERR

# Run main function
main
