#!/bin/bash

# Get absolute path to repository root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
PIDS_DIR="$DIR/.pids"
LOGS_DIR="$DIR/logs/system"

# Ensure directories exist
mkdir -p "$PIDS_DIR"
mkdir -p "$LOGS_DIR"

# Helper function to start a service
start_service() {
    local name=$1
    local dir=$2
    local venv_name=$3
    local cmd=$4
    local logfile="$LOGS_DIR/${name// /_}.log"
    local pidfile="$PIDS_DIR/${name// /_}.pid"

    echo "Starting $name..."
    cd "$DIR/$dir" || return
    if [ "$venv_name" != "none" ]; then
        source "$venv_name/bin/activate"
    fi
    
    # Run command in background and redirect output
    nohup $cmd > "$logfile" 2>&1 &
    local pid=$!
    echo $pid > "$pidfile"
    echo "$name started with PID $pid"
}

start_all() {
    echo "Starting Cammina AI Ecosystem..."
    
    start_service "Local Agent" "services/local_agent" "venv" "python3 main.py"
    start_service "LLM Manager" "services/llm_manager" ".venv" "python3 main.py"
    start_service "Memory" "services/memory" ".venv" "python3 main.py"
    start_service "Orchestrator" "services/orchestrator" ".venv" "python3 main.py"
    start_service "Web UI" "apps/web" "none" "npm run dev -- --port 3000"

    echo "Waiting for services to spin up..."
    sleep 3
    
    echo "Cammina AI is running at http://localhost:3000"
    open "http://localhost:3000" || xdg-open "http://localhost:3000" 2>/dev/null
}

stop_all() {
    echo "Stopping Cammina AI..."
    for pidfile in "$PIDS_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            local pid=$(cat "$pidfile")
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid
                echo "Stopped process $pid"
            fi
            rm "$pidfile"
        fi
    done
    echo "Cammina AI stopped"
}

status_all() {
    echo "Cammina AI Status:"
    
    check_port() {
        local name=$1
        local port=$2
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
            echo "$name ($port): running"
        else
            echo "$name ($port): stopped"
        fi
    }

    check_port "Local Agent" "8765"
    check_port "LLM Manager" "8001"
    check_port "Memory" "8002"
    check_port "Orchestrator" "8000"
    check_port "Web UI" "3000"
}

logs_all() {
    echo "=== Last 50 lines from all services ==="
    for logfile in "$LOGS_DIR"/*.log; do
        if [ -f "$logfile" ]; then
            local name=$(basename "$logfile" .log)
            echo "--- ${name//_/ } ---"
            tail -n 50 "$logfile"
            echo ""
        fi
    done
}

case "$1" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_all
        ;;
    status)
        status_all
        ;;
    logs)
        logs_all
        ;;
    *)
        echo "Usage: cammina {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
