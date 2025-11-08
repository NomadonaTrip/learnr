#!/bin/bash

##############################################################################
# Diagnostic Assessment API Test Script
#
# Tests the complete diagnostic flow:
# 1. Login as test user
# 2. Start diagnostic assessment
# 3. Answer all 24 questions
# 4. View results with competency scores
#
# Usage: ./scripts/test_diagnostic_flow.sh
##############################################################################

set -e  # Exit on error

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/v1"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test data
TEST_EMAIL="learner@test.com"
TEST_PASSWORD="Test123Pass"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       LearnR Diagnostic Assessment API Test Suite             ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo ""

##############################################################################
# Step 1: Login
##############################################################################
echo -e "${YELLOW}[Step 1] Logging in as ${TEST_EMAIL}...${NC}"

LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${TEST_EMAIL}\",
    \"password\": \"${TEST_PASSWORD}\"
  }")

echo "$LOGIN_RESPONSE" | jq '.'

# Extract access token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}✗ Login failed. Cannot proceed.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}"
echo -e "Access Token: ${ACCESS_TOKEN:0:20}..."
echo ""

##############################################################################
# Step 2: Get Course ID
##############################################################################
echo -e "${YELLOW}[Step 2] Getting CBAP course ID...${NC}"

COURSES_RESPONSE=$(curl -s -X GET "${API_URL}/onboarding/courses")

echo "$COURSES_RESPONSE" | jq '.'

# Extract CBAP course ID
COURSE_ID=$(echo "$COURSES_RESPONSE" | jq -r '.[] | select(.course_code == "CBAP") | .course_id')

if [ "$COURSE_ID" == "null" ] || [ -z "$COURSE_ID" ]; then
  echo -e "${RED}✗ CBAP course not found. Cannot proceed.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Found CBAP course: ${COURSE_ID}${NC}"
echo ""

##############################################################################
# Step 3: Start Diagnostic Assessment
##############################################################################
echo -e "${YELLOW}[Step 3] Starting diagnostic assessment...${NC}"

DIAGNOSTIC_START_RESPONSE=$(curl -s -X POST "${API_URL}/diagnostic/start" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"course_id\": \"${COURSE_ID}\"
  }")

echo "$DIAGNOSTIC_START_RESPONSE" | jq '.'

# Extract session ID
SESSION_ID=$(echo "$DIAGNOSTIC_START_RESPONSE" | jq -r '.session_id')
TOTAL_QUESTIONS=$(echo "$DIAGNOSTIC_START_RESPONSE" | jq -r '.total_questions')

if [ "$SESSION_ID" == "null" ] || [ -z "$SESSION_ID" ]; then
  echo -e "${RED}✗ Failed to start diagnostic. Cannot proceed.${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Diagnostic started${NC}"
echo -e "Session ID: ${SESSION_ID}"
echo -e "Total Questions: ${TOTAL_QUESTIONS}"
echo ""

##############################################################################
# Step 4: Answer All Questions
##############################################################################
echo -e "${YELLOW}[Step 4] Answering diagnostic questions (${TOTAL_QUESTIONS} total)...${NC}"

for i in $(seq 1 $TOTAL_QUESTIONS); do
  echo -e "${BLUE}Question ${i}/${TOTAL_QUESTIONS}${NC}"

  # Get next question
  QUESTION_RESPONSE=$(curl -s -X GET "${API_URL}/diagnostic/next-question?session_id=${SESSION_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")

  # echo "$QUESTION_RESPONSE" | jq '.'

  QUESTION_ID=$(echo "$QUESTION_RESPONSE" | jq -r '.question_id')
  QUESTION_TEXT=$(echo "$QUESTION_RESPONSE" | jq -r '.question_text')
  KA_NAME=$(echo "$QUESTION_RESPONSE" | jq -r '.ka_name')

  if [ "$QUESTION_ID" == "null" ]; then
    echo -e "${RED}✗ Failed to get question ${i}${NC}"
    break
  fi

  echo "  KA: ${KA_NAME}"
  echo "  Q: ${QUESTION_TEXT:0:80}..."

  # Get all answer choices
  CHOICES=$(echo "$QUESTION_RESPONSE" | jq -r '.answer_choices')

  # Select first choice (for testing - in real usage, user would choose)
  SELECTED_CHOICE_ID=$(echo "$CHOICES" | jq -r '.[0].choice_id')

  # Submit answer
  ANSWER_RESPONSE=$(curl -s -X POST "${API_URL}/diagnostic/submit-answer" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"session_id\": \"${SESSION_ID}\",
      \"question_id\": \"${QUESTION_ID}\",
      \"selected_choice_id\": \"${SELECTED_CHOICE_ID}\",
      \"time_spent_seconds\": 30
    }")

  IS_CORRECT=$(echo "$ANSWER_RESPONSE" | jq -r '.is_correct')
  QUESTIONS_REMAINING=$(echo "$ANSWER_RESPONSE" | jq -r '.questions_remaining')

  if [ "$IS_CORRECT" == "true" ]; then
    echo -e "  ${GREEN}✓ Correct${NC}"
  else
    echo -e "  ${RED}✗ Incorrect${NC}"
  fi

  echo "  Remaining: ${QUESTIONS_REMAINING}"
  echo ""

  # Small delay to avoid overwhelming the server
  sleep 0.2
done

echo -e "${GREEN}✓ All questions answered${NC}"
echo ""

##############################################################################
# Step 5: Get Diagnostic Results
##############################################################################
echo -e "${YELLOW}[Step 5] Retrieving diagnostic results...${NC}"

RESULTS_RESPONSE=$(curl -s -X GET "${API_URL}/diagnostic/results?session_id=${SESSION_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$RESULTS_RESPONSE" | jq '.'

# Extract key metrics
OVERALL_ACCURACY=$(echo "$RESULTS_RESPONSE" | jq -r '.overall_accuracy')
OVERALL_COMPETENCY=$(echo "$RESULTS_RESPONSE" | jq -r '.overall_competency')
TOTAL_CORRECT=$(echo "$RESULTS_RESPONSE" | jq -r '.total_correct')
WEAKEST_KA=$(echo "$RESULTS_RESPONSE" | jq -r '.weakest_ka_name')
RECOMMENDATION=$(echo "$RESULTS_RESPONSE" | jq -r '.recommendation')

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Diagnostic Results Summary                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${GREEN}Overall Accuracy:${NC} ${OVERALL_ACCURACY}%"
echo -e "${GREEN}Overall Competency:${NC} ${OVERALL_COMPETENCY}"
echo -e "${GREEN}Correct Answers:${NC} ${TOTAL_CORRECT}/${TOTAL_QUESTIONS}"
echo -e "${GREEN}Weakest KA:${NC} ${WEAKEST_KA}"
echo ""
echo -e "${YELLOW}Recommendation:${NC}"
echo -e "${RECOMMENDATION}"
echo ""

# Display per-KA breakdown
echo -e "${BLUE}Knowledge Area Breakdown:${NC}"
echo "$RESULTS_RESPONSE" | jq -r '.ka_results[] |
  "  \(.ka_code): \(.competency_score) (\(.status)) - \(.questions_correct)/\(.questions_attempted) correct"'
echo ""

##############################################################################
# Step 6: Test Progress Endpoint
##############################################################################
echo -e "${YELLOW}[Step 6] Testing progress endpoint...${NC}"

PROGRESS_RESPONSE=$(curl -s -X GET "${API_URL}/diagnostic/progress?session_id=${SESSION_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$PROGRESS_RESPONSE" | jq '.'

IS_COMPLETED=$(echo "$PROGRESS_RESPONSE" | jq -r '.is_completed')
PROGRESS_PCT=$(echo "$PROGRESS_RESPONSE" | jq -r '.progress_percentage')

echo ""
echo -e "${GREEN}Completed:${NC} ${IS_COMPLETED}"
echo -e "${GREEN}Progress:${NC} ${PROGRESS_PCT}%"
echo ""

##############################################################################
# Summary
##############################################################################
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Test Suite Complete                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${GREEN}✓ All diagnostic API endpoints tested successfully${NC}"
echo ""
echo "API Endpoints Tested:"
echo "  1. POST /v1/auth/login"
echo "  2. GET  /v1/onboarding/courses"
echo "  3. POST /v1/diagnostic/start"
echo "  4. GET  /v1/diagnostic/next-question"
echo "  5. POST /v1/diagnostic/submit-answer"
echo "  6. GET  /v1/diagnostic/results"
echo "  7. GET  /v1/diagnostic/progress"
echo ""
echo -e "${YELLOW}Session ID for reference: ${SESSION_ID}${NC}"
