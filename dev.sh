#!/bin/bash
# ============================================================
# agentmaker - Local Development Setup Script
# ============================================================
# Usage:
#   ./dev.sh                 # Full setup (interactive)
#   ./dev.sh --skip-db       # Skip Supabase setup
#   ./dev.sh --reset-db      # Reset database and run migrations
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
APP_PORT=5011
SUPABASE_PORT=54322

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
SUPABASE_DIR="$PROJECT_ROOT/supabase"

# ============================================================
# Helper Functions
# ============================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is not installed"
        return 1
    fi
    return 0
}

kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        log_warn "Port $port is in use by PID $pid, killing..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
        log_info "Port $port freed"
    fi
}

# ============================================================
# Parse Arguments
# ============================================================

SKIP_DB=false
RESET_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --reset-db)
            RESET_DB=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================
# Pre-flight Checks
# ============================================================

section "Pre-flight Checks"

# Check Python
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_info "Python 3 found: $(python3 --version)"
else
    log_error "Python 3 is required. Install from https://www.python.org/downloads/"
    exit 1
fi

# Check pip
if ! python3 -m pip --version &> /dev/null; then
    log_error "pip is not installed"
    exit 1
fi

# ============================================================
# Kill Existing Processes on Ports
# ============================================================

section "Checking Ports"

kill_port $APP_PORT
kill_port $SUPABASE_PORT

# ============================================================
# Environment Setup
# ============================================================

section "Environment Setup"

ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.local.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        log_info "Creating .env from template..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        # Update port in .env
        sed -i '' "s/PORT=5001/PORT=$APP_PORT/g" "$ENV_FILE" 2>/dev/null || true
        sed -i '' "s/PORT=.*/PORT=$APP_PORT/g" "$ENV_FILE" 2>/dev/null || true
        log_success "Created .env file (port: $APP_PORT)"
        log_warn "Please edit .env and add your LLM_API_KEY"
    else
        log_warn ".env file not found and no template available"
    fi
else
    log_info ".env file already exists"
fi

# Ensure .env has correct port
if grep -q "PORT=" "$ENV_FILE" 2>/dev/null; then
    sed -i '' "s/PORT=.*/PORT=$APP_PORT/g" "$ENV_FILE" 2>/dev/null || true
fi

# ============================================================
# Dependencies
# ============================================================

section "Installing Dependencies"

log_info "Installing Python packages..."
cd "$PROJECT_ROOT"
python3 -m pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    log_success "Dependencies installed"
else
    log_error "Failed to install dependencies"
    exit 1
fi

# ============================================================
# Supabase Setup
# ============================================================

if [ "$SKIP_DB" = false ]; then

section "Supabase Setup"

    # Check if Supabase CLI is installed
    if check_command supabase; then
        SUPABASE_VERSION=$(supabase --version 2>/dev/null || echo "unknown")
        log_info "Supabase CLI found: $SUPABASE_VERSION"

        # Check if Supabase is already running
        if supabase status &> /dev/null; then
            log_info "Supabase is already running"
        else
            log_info "Attempting to start Supabase..."

            # Try to start Supabase, but handle version compatibility issues
            if supabase start 2>&1 | grep -q "failed to parse config"; then
                log_warn "Supabase config file has compatibility issues"
                echo ""
                echo -e "  ${YELLOW}Config file may be out of date. Options:${NC}"
                echo "  1. Run 'supabase init' to regenerate config"
                echo "  2. Use --skip-db to skip database setup"
                echo ""
                log_info "Skipping Supabase startup, continuing with in-memory storage..."
            else
                if supabase start 2>/dev/null; then
                    log_success "Supabase started"
                fi
            fi
        fi

        # Get connection info (if running)
        if supabase status &> /dev/null; then
            log_info "Supabase connection info:"
            supabase status 2>/dev/null || true
        fi

        # Run migrations
        if [ "$RESET_DB" = true ]; then
            section "Resetting Database"
            log_warn "Resetting database..."
            # Link local project
            supabase link --project-ref "$(grep 'project_id' "$SUPABASE_DIR/config.toml" | cut -d'=' -f2 | tr -d ' "')" 2>/dev/null || true
            supabase db reset --db-url "postgresql://postgres:postgres@127.0.0.1:54322/postgres" 2>/dev/null || true
            log_success "Database reset complete"
        else
            log_info "Running migrations..."
            # Apply migration directly via psql
            MIGRATION_FILE="$SUPABASE_DIR/migrations/001_initial_schema.sql"
            if [ -f "$MIGRATION_FILE" ]; then
                PGPASSWORD=postgres psql -h 127.0.0.1 -p 54322 -U postgres -d postgres -f "$MIGRATION_FILE" 2>/dev/null || {
                    log_warn "Could not apply migration via psql (may already be applied)"
                }
            fi
        fi

        # Update .env with local Supabase URL
        if grep -q "SUPABASE_URL=http://127.0.0.1:54321" "$ENV_FILE" 2>/dev/null; then
            log_info "Supabase URL already configured in .env"
        else
            log_info "Local Supabase is running at http://127.0.0.1:54321"
        fi

    else
        log_warn "Supabase CLI not found"
        echo ""
        echo -e "  ${YELLOW}To install Supabase CLI:${NC}"
        echo "  macOS: brew install supabase/tap/supabase"
        echo "  Linux: npm install -g supabase"
        echo ""
        log_info "Skipping database setup. App will use in-memory storage."
    fi

else
    log_info "Skipping Supabase setup (--skip-db)"
fi

# ============================================================
# Start Application
# ============================================================

section "Starting Application"

# Load env vars for startup check
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Check if LLM is configured
if [ -z "$LLM_API_KEY" ] || [ "$LLM_API_KEY" = "your_api_key_here" ] || [ "$LLM_API_KEY" = "sk-your-deepseek-api-key" ]; then
    log_warn "LLM_API_KEY not configured in .env"
    echo ""
    echo -e "  ${YELLOW}You can:${NC}"
    echo "  1. Edit .env and add your DeepSeek API key"
    echo "  2. Run in Mock mode (no API key needed)"
    echo ""
fi

# Check if Supabase is configured
if [ -z "$SUPABASE_URL" ] || [ "$SUPABASE_URL" = "http://127.0.0.1:54321" ]; then
    if supabase status &> /dev/null; then
        log_info "Supabase local detected at http://127.0.0.1:54321"
    fi
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}║   NextStudio - AgentScope + FastHTML                         ║${NC}"
echo -e "${GREEN}║   Local Development Server                                    ║${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}║   🌐 http://localhost:$APP_PORT                               ║${NC}"
echo -e "${GREEN}║   📚 http://localhost:54323 (Supabase Studio)                ║${NC}"
echo -e "${GREEN}║                                                               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Start the app
cd "$PROJECT_ROOT"
python3 app.py
