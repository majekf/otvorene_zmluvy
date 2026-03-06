#!/usr/bin/env bash
# Start GovLens development servers (backend + frontend).
# Usage: ./scripts/start_dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== GovLens Development Server ==="
echo ""
echo "  Backend API:  http://localhost:8000"
echo "  Frontend Dev: http://localhost:5173"
echo "  API Docs:     http://localhost:8000/docs"
echo ""

# Start backend in background
cd "$ROOT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
fi

echo "[1/2] Starting backend (FastAPI + Uvicorn)..."
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "[2/2] Starting frontend (Vite dev server)..."
cd "$ROOT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Trap Ctrl+C to kill both processes
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# Wait for both
wait
