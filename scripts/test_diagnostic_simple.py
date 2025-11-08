#!/usr/bin/env python3
"""
Simple diagnostic assessment test script (no jq dependency).

Tests the complete diagnostic flow using Python requests.
"""
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/v1"

# Test credentials
TEST_EMAIL = "learner@test.com"
TEST_PASSWORD = "Test123Pass"

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    print(f"{Colors.BLUE}{title}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.YELLOW}{message}{Colors.NC}")


def pretty_print(data: Dict[Any, Any], indent: int = 2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def main():
    """Run the diagnostic assessment test flow."""
    print_section("LearnR Diagnostic Assessment API Test")

    #############################################################
    # Step 1: Login
    #############################################################
    print_info("[Step 1] Logging in...")

    login_response = requests.post(
        f"{API_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )

    if login_response.status_code != 200:
        print_error(f"Login failed: {login_response.text}")
        return

    login_data = login_response.json()
    access_token = login_data.get("access_token")

    if not access_token:
        print_error("No access token in response")
        return

    print_success("Login successful")
    print(f"  Token: {access_token[:20]}...")

    # Set headers for authenticated requests
    headers = {"Authorization": f"Bearer {access_token}"}

    #############################################################
    # Step 2: Get CBAP Course ID
    #############################################################
    print_info("\n[Step 2] Getting CBAP course...")

    courses_response = requests.get(f"{API_URL}/onboarding/courses")

    if courses_response.status_code != 200:
        print_error(f"Failed to get courses: {courses_response.text}")
        return

    courses = courses_response.json()
    cbap_course = next((c for c in courses if c.get("course_code") == "CBAP"), None)

    if not cbap_course:
        print_error("CBAP course not found")
        return

    course_id = cbap_course["course_id"]
    print_success(f"Found CBAP course: {course_id}")
    print(f"  Name: {cbap_course['course_name']}")

    #############################################################
    # Step 3: Start Diagnostic
    #############################################################
    print_info("\n[Step 3] Starting diagnostic assessment...")

    diagnostic_start_response = requests.post(
        f"{API_URL}/diagnostic/start",
        headers=headers,
        json={"course_id": course_id}
    )

    if diagnostic_start_response.status_code != 201:
        print_error(f"Failed to start diagnostic: {diagnostic_start_response.text}")
        return

    diagnostic_data = diagnostic_start_response.json()
    session_id = diagnostic_data["session_id"]
    total_questions = diagnostic_data["total_questions"]

    print_success("Diagnostic started")
    print(f"  Session ID: {session_id}")
    print(f"  Total questions: {total_questions}")

    #############################################################
    # Step 4: Answer All Questions
    #############################################################
    print_info(f"\n[Step 4] Answering {total_questions} questions...")

    correct_count = 0

    for i in range(1, total_questions + 1):
        print(f"\n  {Colors.BOLD}Question {i}/{total_questions}{Colors.NC}")

        # Get next question
        question_response = requests.get(
            f"{API_URL}/diagnostic/next-question",
            headers=headers,
            params={"session_id": session_id}
        )

        if question_response.status_code != 200:
            print_error(f"Failed to get question: {question_response.text}")
            break

        question_data = question_response.json()
        question_id = question_data["question_id"]
        question_text = question_data["question_text"]
        ka_name = question_data["ka_name"]
        choices = question_data["answer_choices"]

        print(f"    KA: {ka_name}")
        print(f"    Q: {question_text[:80]}...")

        # For testing, select the first choice
        # In real usage, user would select
        selected_choice_id = choices[0]["choice_id"]

        # Submit answer
        answer_response = requests.post(
            f"{API_URL}/diagnostic/submit-answer",
            headers=headers,
            json={
                "session_id": session_id,
                "question_id": question_id,
                "selected_choice_id": selected_choice_id,
                "time_spent_seconds": 30
            }
        )

        if answer_response.status_code != 200:
            print_error(f"Failed to submit answer: {answer_response.text}")
            break

        answer_data = answer_response.json()
        is_correct = answer_data["is_correct"]

        if is_correct:
            print(f"    {Colors.GREEN}✓ Correct{Colors.NC}")
            correct_count += 1
        else:
            print(f"    {Colors.RED}✗ Incorrect{Colors.NC}")

        time.sleep(0.1)  # Small delay

    print_success(f"\nAll questions answered ({correct_count}/{total_questions} correct)")

    #############################################################
    # Step 5: Get Results
    #############################################################
    print_info("\n[Step 5] Retrieving diagnostic results...")

    results_response = requests.get(
        f"{API_URL}/diagnostic/results",
        headers=headers,
        params={"session_id": session_id}
    )

    if results_response.status_code != 200:
        print_error(f"Failed to get results: {results_response.text}")
        return

    results = results_response.json()

    print_section("Diagnostic Results Summary")

    print(f"{Colors.GREEN}Overall Metrics:{Colors.NC}")
    print(f"  Accuracy: {results['overall_accuracy']:.1f}%")
    print(f"  Competency: {results['overall_competency']}")
    print(f"  Correct: {results['total_correct']}/{results['total_questions']}")
    print(f"  Duration: {results['duration_minutes']} minutes")

    print(f"\n{Colors.GREEN}Weakest Area:{Colors.NC}")
    print(f"  {results['weakest_ka_name']}")

    print(f"\n{Colors.YELLOW}Recommendation:{Colors.NC}")
    print(f"  {results['recommendation']}")

    print(f"\n{Colors.GREEN}Knowledge Area Breakdown:{Colors.NC}")
    for ka in results['ka_results']:
        status_color = Colors.GREEN if ka['status'] == 'above_target' else (
            Colors.YELLOW if ka['status'] == 'on_track' else Colors.RED
        )
        print(f"  {ka['ka_code']}: {ka['competency_score']} ({status_color}{ka['status']}{Colors.NC}) - "
              f"{ka['questions_correct']}/{ka['questions_attempted']} correct ({ka['accuracy_percentage']:.0f}%)")

    #############################################################
    # Step 6: Check Progress
    #############################################################
    print_info("\n[Step 6] Checking progress...")

    progress_response = requests.get(
        f"{API_URL}/diagnostic/progress",
        headers=headers,
        params={"session_id": session_id}
    )

    if progress_response.status_code != 200:
        print_error(f"Failed to get progress: {progress_response.text}")
    else:
        progress = progress_response.json()
        print_success(f"Progress: {progress['progress_percentage']}% complete")
        print(f"  Completed: {progress['is_completed']}")

    #############################################################
    # Summary
    #############################################################
    print_section("Test Suite Complete")
    print_success("All diagnostic API endpoints tested successfully\n")

    print("API Endpoints Tested:")
    print("  1. POST /v1/auth/login")
    print("  2. GET  /v1/onboarding/courses")
    print("  3. POST /v1/diagnostic/start")
    print("  4. GET  /v1/diagnostic/next-question")
    print("  5. POST /v1/diagnostic/submit-answer")
    print("  6. GET  /v1/diagnostic/results")
    print("  7. GET  /v1/diagnostic/progress")

    print(f"\n{Colors.YELLOW}Session ID: {session_id}{Colors.NC}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Test interrupted by user{Colors.NC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.NC}")
        import traceback
        traceback.print_exc()
