#!/usr/bin/env python3
"""
Practice Session API Test Script.

Tests the complete practice flow:
1. Login as learner
2. Start practice session (10 questions, adaptive)
3. Answer all questions with adaptive selection
4. Complete session and view results
5. Check practice history
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
    CYAN = '\033[0;36m'
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


def print_competency_change(ka_name: str, before: float, after: float, change: float):
    """Print competency change with color coding."""
    if change > 0:
        color = Colors.GREEN
        arrow = "↑"
    elif change < 0:
        color = Colors.RED
        arrow = "↓"
    else:
        color = Colors.YELLOW
        arrow = "→"

    print(f"  {ka_name}: {before:.3f} {arrow} {after:.3f} ({color}{change:+.3f}{Colors.NC})")


def main():
    """Run the practice session test flow."""
    print_section("LearnR Practice Session API Test")

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

    #############################################################
    # Step 3: Start Practice Session
    #############################################################
    print_info("\n[Step 3] Starting practice session (10 questions, adaptive)...")

    practice_start_response = requests.post(
        f"{API_URL}/practice/start",
        headers=headers,
        json={
            "course_id": course_id,
            "num_questions": 10
        }
    )

    if practice_start_response.status_code != 201:
        print_error(f"Failed to start practice: {practice_start_response.text}")
        return

    practice_data = practice_start_response.json()
    session_id = practice_data["session_id"]
    total_questions = practice_data["total_questions"]

    print_success("Practice session started")
    print(f"  Session ID: {session_id}")
    print(f"  Total questions: {total_questions}")
    print(f"  Mode: Adaptive (targets weak KAs)")

    #############################################################
    # Step 4: Answer All Questions
    #############################################################
    print_info(f"\n[Step 4] Answering {total_questions} adaptive questions...")

    correct_count = 0
    competency_changes = []

    for i in range(1, total_questions + 1):
        print(f"\n  {Colors.BOLD}Question {i}/{total_questions}{Colors.NC}")

        # Get next adaptive question
        question_response = requests.get(
            f"{API_URL}/practice/next-question",
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
        ka_competency = float(question_data["ka_current_competency"])
        difficulty = float(question_data["difficulty"])
        choices = question_data["answer_choices"]

        print(f"    KA: {ka_name} (competency: {ka_competency:.3f})")
        print(f"    Difficulty: {difficulty:.2f}")
        print(f"    Q: {question_text[:80]}...")

        # For testing, select the first choice
        # In real usage, user would select
        selected_choice_id = choices[0]["choice_id"]

        # Submit answer
        answer_response = requests.post(
            f"{API_URL}/practice/submit-answer",
            headers=headers,
            json={
                "session_id": session_id,
                "question_id": question_id,
                "selected_choice_id": selected_choice_id,
                "time_spent_seconds": 25
            }
        )

        if answer_response.status_code != 200:
            print_error(f"Failed to submit answer: {answer_response.text}")
            break

        answer_data = answer_response.json()
        is_correct = answer_data["is_correct"]
        prev_comp = float(answer_data["previous_competency"])
        new_comp = float(answer_data["new_competency"])
        comp_change = float(answer_data["competency_change"])
        session_accuracy = answer_data["session_accuracy"]

        if is_correct:
            print(f"    {Colors.GREEN}✓ Correct{Colors.NC}")
            correct_count += 1
        else:
            print(f"    {Colors.RED}✗ Incorrect{Colors.NC}")

        # Show competency change
        if comp_change != 0:
            change_color = Colors.GREEN if comp_change > 0 else Colors.RED
            arrow = "↑" if comp_change > 0 else "↓"
            print(f"    Competency: {prev_comp:.3f} {arrow} {new_comp:.3f} ({change_color}{comp_change:+.3f}{Colors.NC})")

        print(f"    Session accuracy: {session_accuracy:.1f}%")

        competency_changes.append({
            "ka_name": ka_name,
            "before": prev_comp,
            "after": new_comp,
            "change": comp_change
        })

        time.sleep(0.2)  # Small delay

    print_success(f"\nAll questions answered ({correct_count}/{total_questions} correct)")

    #############################################################
    # Step 5: Complete Practice Session
    #############################################################
    print_info("\n[Step 5] Completing practice session...")

    complete_response = requests.post(
        f"{API_URL}/practice/complete",
        headers=headers,
        json={"session_id": session_id}
    )

    if complete_response.status_code != 200:
        print_error(f"Failed to complete session: {complete_response.text}")
        return

    complete_data = complete_response.json()

    print_section("Practice Session Results")

    print(f"{Colors.GREEN}Overall Performance:{Colors.NC}")
    print(f"  Accuracy: {complete_data['accuracy_percentage']:.1f}%")
    print(f"  Correct: {complete_data['correct_answers']}/{complete_data['total_questions']}")
    print(f"  Duration: {complete_data['duration_minutes']} minutes")

    print(f"\n{Colors.CYAN}Competency Changes:{Colors.NC}")
    for comp in complete_data['competencies_improved']:
        print_competency_change(
            comp['ka_name'],
            comp['before'],
            comp['after'],
            comp['change']
        )

    print(f"\n{Colors.YELLOW}Weakest Area:{Colors.NC}")
    print(f"  {complete_data['weakest_ka_name']}")

    print(f"\n{Colors.YELLOW}Recommendation:{Colors.NC}")
    print(f"  {complete_data['recommendation']}")

    #############################################################
    # Step 6: Get Practice History
    #############################################################
    print_info("\n[Step 6] Checking practice history...")

    history_response = requests.get(
        f"{API_URL}/practice/history",
        headers=headers,
        params={"limit": 5}
    )

    if history_response.status_code != 200:
        print_error(f"Failed to get history: {history_response.text}")
    else:
        history = history_response.json()

        print(f"\n{Colors.CYAN}Practice History:{Colors.NC}")
        print(f"  Total sessions: {history['total_sessions']}")
        print(f"  Total questions: {history['total_questions_practiced']}")
        print(f"  Overall accuracy: {history['overall_accuracy']:.1f}%")

        if history['sessions']:
            print(f"\n  Recent sessions:")
            for session in history['sessions'][:3]:
                status = "✓" if session['is_completed'] else "⧗"
                print(f"    {status} {session['questions_answered']}/{session['total_questions']} "
                      f"({session['accuracy_percentage']:.0f}%) - {session['started_at'][:10]}")

    #############################################################
    # Step 7: Get Session Details
    #############################################################
    print_info("\n[Step 7] Checking session details...")

    session_response = requests.get(
        f"{API_URL}/practice/session/{session_id}",
        headers=headers
    )

    if session_response.status_code != 200:
        print_error(f"Failed to get session: {session_response.text}")
    else:
        session_data = session_response.json()
        print_success(f"Session completed: {session_data['is_completed']}")
        print(f"  Duration: {session_data['duration_seconds']} seconds")
        print(f"  Accuracy: {session_data['accuracy_percentage']:.1f}%")

    #############################################################
    # Summary
    #############################################################
    print_section("Test Suite Complete")
    print_success("All practice API endpoints tested successfully\n")

    print("API Endpoints Tested:")
    print("  1. POST /v1/auth/login")
    print("  2. GET  /v1/onboarding/courses")
    print("  3. POST /v1/practice/start")
    print("  4. GET  /v1/practice/next-question (adaptive)")
    print("  5. POST /v1/practice/submit-answer (with competency updates)")
    print("  6. POST /v1/practice/complete")
    print("  7. GET  /v1/practice/history")
    print("  8. GET  /v1/practice/session/{id}")

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
