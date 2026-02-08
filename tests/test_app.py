"""Tests for the Mergington High School API."""

import pytest
from fastapi import HTTPException


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_redirects_to_index(self, client):
        """Test that root endpoint redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint."""

    def test_get_activities_returns_all_activities(self, client):
        """Test that get_activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify structure of activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert data["Chess Club"]["description"]
        assert data["Chess Club"]["schedule"]
        assert data["Chess Club"]["max_participants"]
        assert isinstance(data["Chess Club"]["participants"], list)

    def test_get_activities_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_details in data.items():
            for field in required_fields:
                assert field in activity_details, f"Missing {field} in {activity_name}"

    def test_activities_have_valid_participant_counts(self, client):
        """Test that participant counts don't exceed max_participants"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert len(activity_details["participants"]) <= activity_details["max_participants"], \
                f"{activity_name} has too many participants"


class TestSignupEndpoint:
    """Tests for the signup endpoint."""

    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the activity"""
        # Get initial count
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Chess Club"]["participants"])
        
        # Sign up new participant
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "testuser1@mergington.edu"}
        )
        
        # Check that participant was added
        response2 = client.get("/activities")
        final_count = len(response2.json()["Chess Club"]["participants"])
        
        assert final_count == initial_count + 1
        assert "testuser1@mergington.edu" in response2.json()["Chess Club"]["participants"]

    def test_signup_duplicate_student_fails(self, client):
        """Test that signing up a student twice fails"""
        email = "michael@mergington.edu"
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/Fake Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_multiple_students_different_activities(self, client):
        """Test that different students can sign up for different activities"""
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student1@mergington.edu"}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming Class/signup",
            params={"email": "student2@mergington.edu"}
        )
        assert response2.status_code == 200
        
        # Verify both signups
        activities = client.get("/activities").json()
        assert "student1@mergington.edu" in activities["Chess Club"]["participants"]
        assert "student2@mergington.edu" in activities["Programming Class"]["participants"]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint."""

    def test_unregister_student_success(self, client):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"
        
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "daniel@mergington.edu"
        
        # Verify participant exists
        response1 = client.get("/activities")
        assert email in response1.json()["Chess Club"]["participants"]
        
        # Unregister
        client.post(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        
        # Verify participant was removed
        response2 = client.get("/activities")
        assert email not in response2.json()["Chess Club"]["participants"]

    def test_unregister_nonexistent_student_fails(self, client):
        """Test that unregistering a student not in the activity fails"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from non-existent activity fails"""
        response = client.post(
            "/activities/Fake Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_then_signup_again(self, client):
        """Test that a student can sign up again after unregistering"""
        email = "testuser2@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Verify signup
        response1 = client.get("/activities")
        assert email in response1.json()[activity]["participants"]
        
        # Unregister
        client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Verify unregistered
        response2 = client.get("/activities")
        assert email not in response2.json()[activity]["participants"]
        
        # Sign up again
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response3.status_code == 200
        
        # Verify re-signup
        response4 = client.get("/activities")
        assert email in response4.json()[activity]["participants"]


class TestActivityFormats:
    """Tests for activity data formats."""

    def test_activity_names_are_strings(self, client):
        """Test that activity names are strings"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name in data.keys():
            assert isinstance(activity_name, str)

    def test_participant_emails_are_valid_format(self, client):
        """Test that participant emails contain @ symbol"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_details in data.values():
            for email in activity_details["participants"]:
                assert "@" in email, f"Invalid email format: {email}"

    def test_max_participants_is_positive_integer(self, client):
        """Test that max_participants is a positive integer"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_details in data.values():
            assert isinstance(activity_details["max_participants"], int)
            assert activity_details["max_participants"] > 0
