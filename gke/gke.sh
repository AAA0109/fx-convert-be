#!/bin/bash

# Set script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to display usage information
usage() {
    echo "Usage: $0 <environment> <action> [options]"
    echo "Environments: dev, staging, prod"
    echo "Actions: apply, delete, list, logs, redeploy"
    echo "Options:"
    echo "  -c, --config <config_file>    Specify config file (optional, uses all YAML files in config dir if not specified)"
    echo "  -n, --namespace <namespace>   Specify Kubernetes namespace (default: environment-specific)"
    echo "  -f, --follow                  Follow log output (only applicable for 'logs' action)"
    echo "  -d, --debug                   Enable debug mode (print commands before execution)"
    echo "  -h, --help                    Display this help message"
}

# Function to validate environment
validate_environment() {
    case $1 in
        dev|staging|prod) return 0 ;;
        *) echo "Invalid environment. Choose dev, staging, or prod."; exit 1 ;;
    esac
}

# Function to set up kubectl context
setup_kubectl_context() {
    local env=$1
    case $env in
        dev)
            namespace="pangea-development"
            env_file="$SCRIPT_DIR/env/.dev.env"
            gcloud config set project pangea-development
            gcloud container clusters get-credentials pangea-development-autopilot-cluster --region us-central1 --project pangea-development
            ;;
        staging)
            namespace="pangea-staging"
            env_file="$SCRIPT_DIR/env/.staging.env"
            gcloud config set project pangea-staging-338618
            gcloud container clusters get-credentials pangea-staging-autopilot-cluster --region us-central1 --project pangea-staging-338618
            ;;
        prod)
            namespace="pangea-production"
            env_file="$SCRIPT_DIR/env/.prod.env"
            gcloud config set project pangea-production
            gcloud container clusters get-credentials pangea-production-autopilot-cluster --region us-central1 --project pangea-production
            ;;
    esac
}

# Function to get all YAML files in config directory
get_config_files() {
    local config_dir="$SCRIPT_DIR/configs"
    if [ ! -d "$config_dir" ]; then
        echo "Error: Config directory not found: $config_dir" >&2
        return 1
    fi
    find "$config_dir" -maxdepth 1 -name "*.yaml" -o -name "*.yml"
}

# Function to get deployment names from a YAML file
get_deployment_names() {
    local config=$1
    if [ ! -f "$config" ]; then
        echo "Error: Config file not found: $config" >&2
        return 1
    fi
    grep 'name:' "$config" | awk '{print $2}' | head -n 1
}

# Function to apply configuration
apply_config() {
    local config=$1
    local ns=$2

    echo "Applying configuration from $config"

    # Load environment variables
    if [[ -f "$env_file" ]]; then
        set -a  # automatically export all variables
        source "$env_file"
        set +a
    else
        echo "Environment file $env_file not found."
        return 1
    fi

    # Create a temporary file for the processed config
    local temp_config=$(mktemp)

    # Use envsubst to replace variables in the config file
    envsubst < "$config" > "$temp_config"

    # Apply the processed configuration
    kubectl apply -f "$temp_config" --namespace "$ns"

    # Clean up the temporary file
    rm "$temp_config"
}

# Function to delete configuration
delete_config() {
    local config=$1
    local ns=$2

    echo "Deleting configuration from $config"

    # Load environment variables
    if [[ -f "$env_file" ]]; then
        export $(grep -v '^#' "$env_file" | xargs)
    else
        echo "Environment file $env_file not found."
        return 1
    fi

    # Delete the configuration
    kubectl delete -f "$config" --namespace "$ns"
}

# Function to list resources
list_resources() {
    local ns=$1
    kubectl get all,configmap,secret,ingress --namespace "$ns"
}

# Function to kill existing log streaming processes
kill_existing_log_processes() {
    pkill -f "kubectl logs -f"
}

# Function to cleanup on exit
cleanup() {
    kill_existing_log_processes
}

# Set trap to ensure cleanup on script exit
trap cleanup EXIT

# Function to fetch logs
fetch_logs() {
    local config=$1
    local ns=$2
    local follow=$3

    echo "Fetching logs for config: $config"

    # Kill existing log processes before starting new ones
    kill_existing_log_processes

    # Get deployment names from the config file
    local deployments=$(get_deployment_names "$config")

    if [[ -z "$deployments" ]]; then
        echo "No deployments found in the config file: $config"
        return
    fi

    for deployment in $deployments; do
        echo "Fetching logs for deployment: $deployment"

        # Check if pods exist for this deployment
        local pod_count=$(kubectl get pods -n "$ns" -l "app=$deployment" --no-headers | wc -l)

        if [[ "$pod_count" -eq 0 ]]; then
            echo "No pods found for deployment $deployment"
            continue
        fi

        if [[ "$follow" == "true" ]]; then
            echo "Streaming logs for all pods in deployment $deployment. Use Ctrl+C to stop."
            kubectl logs -f -n "$ns" --selector="app=$deployment" --all-containers=true --prefix=true
        else
            echo "Logs for deployment: $deployment"
            echo "----------------------------------------"
            kubectl logs -n "$ns" --selector="app=$deployment" --all-containers=true --prefix=true
            echo "----------------------------------------"
        fi
    done
}

redeploy_and_wait() {
    local config=$1
    local ns=$2

    echo "Redeploying from config file: $config"

    # Apply the configuration (this will use the updated apply_config function)
    apply_config "$config" "$ns"

    # Get the deployment name(s) from the config file
    local deployments=$(get_deployment_names "$config")

    # Restart and wait for each deployment to be ready
    for deployment in $deployments; do
        echo "Restarting deployment $deployment..."
        kubectl rollout restart deployment "$deployment" -n "$ns"

        echo "Waiting for deployment $deployment to be ready..."
        kubectl rollout status deployment "$deployment" -n "$ns" --timeout=300s
        if [ $? -ne 0 ]; then
            echo "Deployment $deployment failed to become ready within 5 minutes."
            return 1
        fi
    done

    echo "All deployments from $config have been redeployed and are ready."
}

# Main script execution
if [[ $# -lt 2 ]]; then
    usage
    exit 1
fi

ENVIRONMENT=$1
ACTION=$2
shift 2

# Validate environment
validate_environment "$ENVIRONMENT"

# Set default values
CONFIG=""
FOLLOW="false"
DEBUG="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -c|--config)
        CONFIG="$2"
        shift 2
        ;;
        -n|--namespace)
        namespace="$2"
        shift 2
        ;;
        -f|--follow)
        FOLLOW="true"
        shift
        ;;
        -d|--debug)
        DEBUG=true
        shift
        ;;
        -h|--help)
        usage
        exit 0
        ;;
        *)
        echo "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
done

# Enable debug mode if the flag is set
if [[ "$DEBUG" == true ]]; then
    set -x
fi

# Setup kubectl context and set environment-specific variables
setup_kubectl_context "$ENVIRONMENT"

# Handle config file selection
if [[ -z $CONFIG ]]; then
    echo "No specific config file provided. Using all YAML files in the configs directory."
    CONFIG_FILES=($(get_config_files))
    if [[ ${#CONFIG_FILES[@]} -eq 0 ]]; then
        echo "Error: No YAML files found in the configs directory."
        exit 1
    fi
else
    CONFIG="$SCRIPT_DIR/configs/$CONFIG"
    if [[ ! -f $CONFIG ]]; then
        echo "Error: Specified config file not found: $CONFIG"
        exit 1
    fi
    CONFIG_FILES=("$CONFIG")
fi

echo "Config files to process: ${CONFIG_FILES[@]}"

# Execute the requested action
case $ACTION in
    apply)
        for config_file in "${CONFIG_FILES[@]}"; do
            apply_config "$config_file" "$namespace"
        done
        ;;
    delete)
        for config_file in "${CONFIG_FILES[@]}"; do
            delete_config "$config_file" "$namespace"
        done
        ;;
    list)
        list_resources "$namespace"
        ;;
    logs)
        if [[ "$FOLLOW" == "true" ]]; then
            echo "Streaming logs for specified deployment(s). Use Ctrl+C to stop."
            for config_file in "${CONFIG_FILES[@]}"; do
                fetch_logs "$config_file" "$namespace" "$FOLLOW"
            done
        else
            for config_file in "${CONFIG_FILES[@]}"; do
                fetch_logs "$config_file" "$namespace" "$FOLLOW"
            done
        fi
        ;;
    redeploy)
        for config_file in "${CONFIG_FILES[@]}"; do
            redeploy_and_wait "$config_file" "$namespace"
        done
        ;;
    *)
        echo "Invalid action. Choose apply, delete, list, logs, or redeploy."
        usage
        exit 1
        ;;
esac

# Disable debug mode if it was set
if [[ "$DEBUG" == true ]]; then
    set +x
fi
