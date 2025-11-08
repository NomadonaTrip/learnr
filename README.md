# LearnR - Adaptive Learning Platform

[![Tests](https://github.com/NomadonaTrip/learnr/actions/workflows/tests.yml/badge.svg)](https://github.com/NomadonaTrip/learnr/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/NomadonaTrip/learnr/branch/main/graph/badge.svg)](https://codecov.io/gh/NomadonaTrip/learnr)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI-powered adaptive learning platform for professional certification exam preparation, built with comprehensive Test-Driven Development (TDD) specifications.

## 🌟 Features

- **Adaptive Learning Algorithm** - 1PL IRT for real-time competency estimation
- **Spaced Repetition** - SM-2 algorithm for optimal retention
- **Multi-Course Support** - CBAP, PSM1, CFA with variable knowledge areas
- **Diagnostic Testing** - Comprehensive skill assessment
- **Progress Tracking** - Real-time competency dashboards
- **Secure Authentication** - JWT + Argon2id + 2FA support
- **Payment Integration** - Stripe subscriptions with full lifecycle management
- **Field-Level Encryption** - PII protection with Fernet (AES-256)

## 🏗️ Tech Stack

- **Backend:** FastAPI + Python 3.11
- **Database:** PostgreSQL 15 + pgvector
- **ORM:** SQLAlchemy 2.0
- **Validation:** Pydantic v2
- **Testing:** pytest + pytest-cov (84.73% coverage)
- **Payments:** Stripe
- **AI:** OpenAI embeddings for semantic search
- **Auth:** JWT (RS256) + Argon2id

## 📊 Project Status

```
✅ Tests:       259/267 passing (96.8%)
✅ Coverage:    84.73% (exceeds 80% threshold)
✅ Warnings:    0 (fully modernized codebase)
⚠️  Known Issues: 1 (timezone-related test hangs - documented)
```

**Current Sprint:** Database timezone migration for 100% test pass rate

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker (optional, for containerized setup)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/NomadonaTrip/learnr.git
cd learnr

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Generate encryption key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Set up database
docker-compose up -d postgres
alembic upgrade head

# Run the application
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for API documentation.

### Docker Setup

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e          # End-to-end tests only

# Run excluding hanging tests (until timezone migration)
pytest tests/ \
  --deselect=tests/integration/test_reviews_endpoints.py::TestGetDueReviews \
  --deselect=tests/integration/test_dashboard_endpoints.py::TestGetRecentActivity \
  --deselect=tests/integration/test_diagnostic_endpoints.py::TestGetDiagnosticResults \
  --deselect=tests/integration/test_practice_endpoints.py::TestGetPracticeSession \
  --deselect=tests/integration/test_practice_endpoints.py::TestCompletePracticeSession \
  --deselect=tests/e2e/test_user_journey.py::TestDiagnosticToReviewJourney \
  --deselect=tests/e2e/test_user_journey.py::TestMultiSessionProgressJourney
```

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Fast setup guide
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development instructions
- **[GITHUB_SETUP.md](GITHUB_SETUP.md)** - GitHub repository configuration
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing best practices
- **[DOCKER_SETUP_GUIDE.md](DOCKER_SETUP_GUIDE.md)** - Docker configuration
- **[docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)** - Known issues and solutions
- **[docs/TDDoc_DatabaseSchema.md](docs/TDDoc_DatabaseSchema.md)** - Complete database schema
- **[docs/TDDoc_API_Endpoints.md](docs/TDDoc_API_Endpoints.md)** - API endpoint specifications
- **[docs/TDDoc_Algorithms.md](docs/TDDoc_Algorithms.md)** - IRT, SM-2, adaptive selection

## 🗄️ Database Schema

23 tables across 5 categories:
- **Core** (5 tables): users, user_profiles, courses, knowledge_areas, domains
- **Content** (3 tables): questions, answer_choices, content_chunks
- **Learning** (5 tables): sessions, question_attempts, user_competency, spaced_repetition_cards, reading_consumed
- **Financial** (8 tables): subscriptions, payments, refunds, chargebacks, invoices, revenue_events
- **Security** (2 tables): security_logs, rate_limit_entries

See [docs/TDDoc_DatabaseSchema.md](docs/TDDoc_DatabaseSchema.md) for complete schema.

## 🔐 Security Features

- **Password Hashing:** Argon2id (cost factor 12)
- **Authentication:** JWT with RS256 signing (1-hour expiry)
- **2FA Support:** TOTP-based two-factor authentication
- **PII Encryption:** Field-level encryption (AES-256 via Fernet)
- **Rate Limiting:** 100 requests/minute (authenticated users)
- **Audit Trail:** Immutable security logs
- **PCI Compliance:** Stripe tokenized payment storage

## 🧬 Adaptive Learning Algorithm

**1PL IRT (Item Response Theory)** for competency estimation:
- Real-time competency updates after each question attempt
- Question selection based on difficulty matching (±0.1 of competency)
- Weakest knowledge area prioritization
- 2PL IRT upgrade path reserved (discrimination field)

**SM-2 Spaced Repetition** for retention:
- Easiness factor, interval days, repetition count tracking
- Quality ratings (0-5) drive review scheduling
- Optimal review timing for long-term memory

See [docs/TDDoc_Algorithms.md](docs/TDDoc_Algorithms.md) for detailed algorithms.

## 🎯 API Endpoints

**45+ RESTful endpoints** organized by functionality:
- `/v1/auth/*` - Registration, login, 2FA
- `/v1/onboarding/*` - Profile setup, course selection
- `/v1/sessions/*` - Diagnostic, practice, mock exams
- `/v1/reviews/*` - Spaced repetition due cards
- `/v1/dashboard` - Progress tracking, competency scores
- `/v1/admin/*` - Course management, metrics, user management
- `/v1/webhooks/stripe` - Payment event processing

Full API documentation: http://localhost:8000/docs (when running locally)

## 📈 CI/CD Pipeline

GitHub Actions workflows automatically:
- ✅ Run 259 passing tests on every push/PR
- ✅ Generate coverage reports (target: 80%+)
- ✅ Check code formatting (Black, isort)
- ✅ Lint code (flake8)
- ✅ Type check (mypy)
- ✅ Security scan (Bandit, Safety)

See [.github/workflows/tests.yml](.github/workflows/tests.yml) for configuration.

## ⚠️ Known Issues

**Timezone-Aware DateTime Comparison (8 tests hanging)**
- **Status:** Deferred to database migration sprint
- **Impact:** 8 integration/e2e tests hang due to timezone mismatch
- **Root Cause:** PostgreSQL `TIMESTAMP` (naive) vs Python `datetime.now(timezone.utc)` (aware)
- **Solution:** Alembic migration to convert columns to `TIMESTAMPTZ`
- **Tracking:** [See GitHub Issues](https://github.com/NomadonaTrip/learnr/issues)

Full details: [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit changes: `git commit -m "feat: add your feature"`
6. Push to branch: `git push origin feature/your-feature`
7. Open a Pull Request

## 📝 Development Workflow

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Format code
black app/ tests/
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type check
mypy app/

# Run security checks
bandit -r app/
safety check
```

## 🛣️ Roadmap

### Current Sprint
- [ ] Fix timezone issue (database migration to TIMESTAMPTZ)
- [ ] Achieve 100% test pass rate (267/267 tests)
- [ ] Increase coverage to 90%+

### Next Sprint
- [ ] Frontend development (Next.js 14 + React)
- [ ] Mobile responsive design
- [ ] Admin dashboard implementation
- [ ] Content management system

### Future
- [ ] Machine learning model for question difficulty prediction
- [ ] Gamification features (badges, leaderboards)
- [ ] Social learning (study groups, forums)
- [ ] Mobile app (React Native)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [PostgreSQL](https://www.postgresql.org/)
- Developed using Test-Driven Development (TDD)
- AI-assisted with [Claude Code](https://claude.com/claude-code)

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/NomadonaTrip/learnr/issues)
- **Discussions:** [GitHub Discussions](https://github.com/NomadonaTrip/learnr/discussions)
- **Documentation:** See `/docs` directory

---

**Built with ❤️ using Test-Driven Development**
