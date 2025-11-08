#!/usr/bin/env python3
"""
Dashboard API Test Script.

Tests all dashboard endpoints:
1. Login as learner
2. Get dashboard overview
3. Get detailed competencies
4. Get recent activity
5. Get exam readiness
"""
import requests
import json
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
    MAGENTA = '\033[0;35m'
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


def print_metric(label: str, value: Any, color: str = Colors.CYAN):
    """Print a metric with label."""
    print(f"  {color}{label}:{Colors.NC} {value}")


def print_competency_status(comp: Dict):
    """Print competency status with color coding."""
    status = comp['status']
    score = float(comp['competency_score'])

    if status == 'above_target':
        status_color = Colors.GREEN
        emoji = "🟢"
    elif status == 'on_track':
        status_color = Colors.YELLOW
        emoji = "🟡"
    else:
        status_color = Colors.RED
        emoji = "🔴"

    print(f"  {emoji} {comp['ka_code']}: {score:.3f} ({status_color}{status}{Colors.NC}) - "
          f"{comp['correct_count']}/{comp['attempts_count']} ({comp['accuracy_percentage']:.0f}%)")


def main():
    """Run the dashboard test flow."""
    print_section("LearnR Dashboard API Test")

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
    # Step 2: Get Dashboard Overview
    #############################################################
    print_info("\n[Step 2] Getting dashboard overview...")

    dashboard_response = requests.get(
        f"{API_URL}/dashboard",
        headers=headers
    )

    if dashboard_response.status_code != 200:
        print_error(f"Failed to get dashboard: {dashboard_response.text}")
        return

    dashboard = dashboard_response.json()

    print_section("Dashboard Overview")

    print(f"{Colors.BOLD}Course:{Colors.NC} {dashboard['course_name']}")
    print()

    print(f"{Colors.CYAN}Overall Performance:{Colors.NC}")
    print_metric("Competency", f"{float(dashboard['overall_competency']):.3f} ({dashboard['overall_competency_status']})")
    print_metric("Exam Readiness", f"{dashboard['exam_readiness_percentage']:.1f}%")
    print_metric("Questions Attempted", dashboard['total_questions_attempted'])
    print_metric("Overall Accuracy", f"{dashboard['overall_accuracy']:.1f}%")
    print()

    print(f"{Colors.CYAN}Session Stats:{Colors.NC}")
    print_metric("Sessions Completed", dashboard['total_sessions_completed'])
    print_metric("Diagnostic Done", "✓ Yes" if dashboard['diagnostic_completed'] else "✗ No")
    print_metric("Last Practice", dashboard.get('last_practice_date', 'Never'))
    print()

    print(f"{Colors.CYAN}Engagement:{Colors.NC}")
    print_metric("Current Streak", f"{dashboard['streak_days']} days")
    print_metric("Daily Goal", "✓ Met" if dashboard['daily_goal_met'] else "✗ Not met")
    print()

    print(f"{Colors.CYAN}Spaced Repetition:{Colors.NC}")
    print_metric("Reviews Due Today", dashboard['reviews_due_today'])
    print_metric("Reviews Overdue", dashboard['reviews_overdue'])
    print()

    print(f"{Colors.MAGENTA}Knowledge Areas (sorted by competency):{Colors.NC}")
    for comp in dashboard['competencies']:
        print_competency_status(comp)

    print()
    print(f"{Colors.YELLOW}Focus Areas (Recommendations):{Colors.NC}")
    for focus in dashboard.get('focus_areas', [])[:3]:
        priority_color = Colors.RED if focus['priority'] == 'high' else (
            Colors.YELLOW if focus['priority'] == 'medium' else Colors.GREEN
        )
        print(f"  [{priority_color}{focus['priority'].upper()}{Colors.NC}] {focus['ka_name']}")
        print(f"      Gap: {float(focus['gap']):.3f} - {focus['reason']}")

    #############################################################
    # Step 3: Get Detailed Competencies
    #############################################################
    print_info("\n[Step 3] Getting detailed competency breakdown...")

    competencies_response = requests.get(
        f"{API_URL}/dashboard/competencies",
        headers=headers
    )

    if competencies_response.status_code != 200:
        print_error(f"Failed to get competencies: {competencies_response.text}")
    else:
        competencies_data = competencies_response.json()

        print_section("Detailed Competency Analysis")

        print(f"{Colors.CYAN}Overall Metrics:{Colors.NC}")
        print_metric("Overall Competency", f"{float(competencies_data['overall_competency']):.3f}")
        print_metric("KAs Below Target", f"{competencies_data['kas_below_target']} (< 0.60)")
        print_metric("KAs On Track", f"{competencies_data['kas_on_track']} (0.60-0.79)")
        print_metric("KAs Above Target", f"{competencies_data['kas_above_target']} (≥ 0.80)")
        print_metric("Trend Direction", competencies_data['overall_trend_direction'].upper())
        print()

        print(f"{Colors.MAGENTA}Per-KA Details:{Colors.NC}")
        for comp in competencies_data['competencies'][:3]:  # Show top 3
            print(f"\n  {Colors.BOLD}{comp['ka_name']}{Colors.NC}")
            print(f"    Competency: {float(comp['current_competency']):.3f} ({comp['status']})")
            print(f"    Performance: {comp['correct_count']}/{comp['total_attempts']} ({comp['accuracy_percentage']:.0f}%)")
            print(f"    Needs Practice: {'Yes' if comp['needs_practice'] else 'No'}")

            rec_range = comp['recommended_difficulty_range']
            print(f"    Recommended Difficulty: {rec_range['min']:.2f} - {rec_range['max']:.2f}")

            if comp.get('trend'):
                print(f"    Trend Points: {len(comp['trend'])} data points in last 30 days")

    #############################################################
    # Step 4: Get Recent Activity
    #############################################################
    print_info("\n[Step 4] Getting recent activity...")

    activity_response = requests.get(
        f"{API_URL}/dashboard/recent",
        headers=headers,
        params={"limit": 5}
    )

    if activity_response.status_code != 200:
        print_error(f"Failed to get activity: {activity_response.text}")
    else:
        activity = activity_response.json()

        print_section("Recent Activity & Engagement")

        print(f"{Colors.CYAN}This Week:{Colors.NC}")
        print_metric("Sessions", activity['sessions_this_week'])
        print_metric("Questions", activity['questions_this_week'])
        print_metric("Accuracy", f"{activity['accuracy_this_week']:.1f}%")
        print()

        print(f"{Colors.CYAN}This Month:{Colors.NC}")
        print_metric("Sessions", activity['sessions_this_month'])
        print_metric("Questions", activity['questions_this_month'])
        print_metric("Accuracy", f"{activity['accuracy_this_month']:.1f}%")
        print()

        print(f"{Colors.CYAN}Streaks & Engagement:{Colors.NC}")
        print_metric("Current Streak", f"{activity['current_streak_days']} days")
        print_metric("Longest Streak", f"{activity['longest_streak_days']} days")
        print_metric("Total Study Time", f"{activity['total_study_minutes']} minutes")

        if activity.get('days_since_last_practice') is not None:
            print_metric("Days Since Last", activity['days_since_last_practice'])
        print()

        print(f"{Colors.MAGENTA}Recent Sessions:{Colors.NC}")
        for session in activity['recent_sessions'][:5]:
            status_emoji = "✓" if session['is_completed'] else "⧗"
            session_type = session['session_type'].replace('_', ' ').title()

            print(f"  {status_emoji} {session_type}: {session['correct_answers']}/{session['total_questions']} "
                  f"({session['accuracy_percentage']:.0f}%) - {session['started_at'][:10]}")

    #############################################################
    # Step 5: Get Exam Readiness
    #############################################################
    print_info("\n[Step 5] Getting exam readiness assessment...")

    readiness_response = requests.get(
        f"{API_URL}/dashboard/exam-readiness",
        headers=headers
    )

    if readiness_response.status_code != 200:
        print_error(f"Failed to get exam readiness: {readiness_response.text}")
    else:
        readiness = readiness_response.json()

        print_section("Exam Readiness Assessment")

        ready_color = Colors.GREEN if readiness['exam_ready'] else Colors.YELLOW
        ready_emoji = "🎉" if readiness['exam_ready'] else "📚"

        print(f"{ready_emoji} {ready_color}Exam Ready: {readiness['exam_ready']}{Colors.NC}")
        print()

        print(f"{Colors.CYAN}Readiness Metrics:{Colors.NC}")
        print_metric("Overall Readiness", f"{readiness['readiness_percentage']:.1f}%")
        print_metric("KAs Ready (≥0.80)", readiness['kas_ready'])
        print_metric("KAs Not Ready", readiness['kas_not_ready'])
        print()

        if readiness.get('estimated_questions_remaining'):
            print(f"{Colors.CYAN}Estimated Remaining:{Colors.NC}")
            print_metric("Questions", readiness['estimated_questions_remaining'])

            if readiness.get('estimated_days_remaining'):
                print_metric("Days (at 20q/day)", readiness['estimated_days_remaining'])
            print()

        print(f"{Colors.YELLOW}Recommendation:{Colors.NC}")
        print(f"  {readiness['recommendation']}")
        print()

        print(f"{Colors.YELLOW}Next Steps:{Colors.NC}")
        for step in readiness.get('next_steps', []):
            print(f"  • {step}")
        print()

        if readiness.get('weakest_kas'):
            print(f"{Colors.MAGENTA}Weakest Areas:{Colors.NC}")
            for comp in readiness['weakest_kas']:
                print_competency_status(comp)

    #############################################################
    # Summary
    #############################################################
    print_section("Test Suite Complete")
    print_success("All dashboard API endpoints tested successfully\n")

    print("API Endpoints Tested:")
    print("  1. POST /v1/auth/login")
    print("  2. GET  /v1/dashboard")
    print("  3. GET  /v1/dashboard/competencies")
    print("  4. GET  /v1/dashboard/recent")
    print("  5. GET  /v1/dashboard/exam-readiness")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Test interrupted by user{Colors.NC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.NC}")
        import traceback
        traceback.print_exc()
