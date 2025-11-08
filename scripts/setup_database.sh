#!/bin/bash
# Database Setup Script for LearnR
# Run this after Docker Desktop WSL2 integration is enabled

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         LearnR Database Setup - Automated Script              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is available
echo "Step 1: Checking Docker availability..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not available in WSL2${NC}"
    echo "Please enable Docker Desktop WSL2 integration first."
    echo "See DOCKER_SETUP_GUIDE.md for instructions."
    exit 1
fi
echo -e "${GREEN}✓ Docker is available${NC}"
echo ""

# Check if Docker daemon is running
echo "Step 2: Checking Docker daemon..."
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker Desktop on Windows."
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"
echo ""

# Start PostgreSQL container
echo "Step 3: Starting PostgreSQL container..."
docker-compose up -d postgres
echo -e "${GREEN}✓ PostgreSQL container started${NC}"
echo ""

# Wait for PostgreSQL to be ready
echo "Step 4: Waiting for PostgreSQL to be ready..."
sleep 5
until docker exec learnr_postgres pg_isready -U postgres &> /dev/null; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
echo ""

# Activate virtual environment
echo "Step 5: Activating virtual environment..."
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Generate migration
echo "Step 6: Generating database migration..."
alembic revision --autogenerate -m "Initial schema - 25 tables"
echo -e "${GREEN}✓ Migration generated${NC}"
echo ""

# Apply migration
echo "Step 7: Applying migration to database..."
alembic upgrade head
echo -e "${GREEN}✓ Migration applied - 25 tables created${NC}"
echo ""

# Verify tables
echo "Step 8: Verifying tables created..."
TABLE_COUNT=$(docker exec learnr_postgres psql -U postgres -d learnr_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "Tables created: $TABLE_COUNT"
if [ "$TABLE_COUNT" -ge 25 ]; then
    echo -e "${GREEN}✓ All tables created successfully${NC}"
else
    echo -e "${YELLOW}⚠ Expected 25+ tables, found $TABLE_COUNT${NC}"
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  Database Setup Complete! ✅                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "1. Run seed script:    bash scripts/seed_data.sh"
echo "2. Start API server:   uvicorn app.main:app --reload"
echo "3. Test endpoints:     http://localhost:8000/docs"
echo ""
