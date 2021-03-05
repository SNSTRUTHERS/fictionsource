#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from flask.testing import FlaskClient
from flask.wrappers import Response
from flask_bcrypt import generate_password_hash

from models import BCRYPT, connect_db, db, from_timestamp, FollowingUser, Story, User
from dbcred import get_database_uri

from datetime import date, datetime, timezone

from base64 import b64encode

from app import CURR_USER_KEY, app
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
    "fictionsource-test",
    cred_file = ".dbtestcred",
    save = False
)
if app.config['SQLALCHEMY_DATABASE_URI'] is None:
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
        "fictionsource-test",
        cred_file = None,
        save = False
    )

app.config['SQLALCHEMY_ECHO'] = False

# == TEST CASE =================================================================================== #

USERDATA = (
    {
        "username": "testuser",
        "password": BCRYPT.generate_password_hash("testpass").decode('utf-8'),
        "description": None,
        "email": "testuser@gmail.com",
        "birthdate": date(1997, 3, 16),
        "joined": datetime(2021, 1, 5, 11, 5, 9, 155000, timezone.utc),
        "flags": User.Flags.ALLOW_RISQUE
    },
    {
        "username": "testuser2",
        "password": BCRYPT.generate_password_hash("testpass").decode('utf-8'),
        "description": None,
        "email": "testuser2@gmail.com",
        "birthdate": date(1997, 3, 17),
        "joined": datetime(2021, 1, 12, 7, 12, 9, 363000, timezone.utc)
    },
    {
        "username": "testuser3",
        "password": BCRYPT.generate_password_hash("testpass").decode('utf-8'),
        "description": None,
        "email": "testuser3@gmail.com",
        "birthdate": date(1997, 3, 18),
        "joined": datetime(2021, 1, 25, 3, 22, 18, 796000, timezone.utc),
        "flags": User.Flags.ALLOW_RISQUE
    }
)

class UserAPITestCase(TestCase):
    """Test cases for User API views."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        FollowingUser.query.delete()
        Story.query.delete()
        User.query.delete()

        self.client = app.test_client()

        users = [ User(**data) for data in USERDATA ]
        db.session.add_all(users)
        db.session.commit()
        self.user_ids = [ id for id in map(lambda user: user.id, users) ]

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()

    @staticmethod
    def generate_basicauth_credentials(username: str, password: str):
        credentials = b64encode(bytes(f'{username}:{password}', 'utf-8')).decode('utf-8')
        return f"Basic {credentials}"
        
    def test_get(self) -> None:
        """Tests retrieving a user's information."""

        # nonexistant user request
        response = self.client.get("/api/user/nonexistantuser")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid username.", response.json['errors'])

        # anonymous/unprivileged user data request
        response: Response = self.client.get(f"/api/user/{USERDATA[0]['username']}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data["username"], USERDATA[0]['username'])
        self.assertEqual(from_timestamp(data['birthdate'], True), USERDATA[0]['birthdate'])
        self.assertEqual(data["description"], USERDATA[0]['description'])
        self.assertEqual(data["image"], User.DEFAULT_IMAGE_URI)
        self.assertEqual(from_timestamp(data['joined']), USERDATA[0]['joined'])
        self.assertFalse(data['is_moderator'])
        self.assertEqual(data['allow_risque'], USERDATA[0]['flags'] & User.Flags.ALLOW_RISQUE > 0)
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertNotIn('comments', data)
        
        # priviledged user data request
        response = self.client.get(f"/api/user/{USERDATA[0]['username']}", headers={
            "Authorization": self.generate_basicauth_credentials(
                USERDATA[0]['username'], 'testpass'
            )
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data["username"], USERDATA[0]['username'])
        self.assertEqual(from_timestamp(data['birthdate'], True), USERDATA[0]['birthdate'])
        self.assertEqual(data["description"], USERDATA[0]['description'])
        self.assertEqual(data["image"], User.DEFAULT_IMAGE_URI)
        self.assertEqual(from_timestamp(data['joined']), USERDATA[0]['joined'])
        self.assertFalse(data['is_moderator'])
        self.assertEqual(data['allow_risque'], USERDATA[0]['flags'] & User.Flags.ALLOW_RISQUE > 0)
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertEqual(data["comments"], [])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        response = self.client.get(f"/api/user/{USERDATA[0]['username']}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data["username"], USERDATA[0]['username'])
        self.assertEqual(from_timestamp(data['birthdate'], True), USERDATA[0]['birthdate'])
        self.assertEqual(data["description"], USERDATA[0]['description'])
        self.assertEqual(data["image"], User.DEFAULT_IMAGE_URI)
        self.assertEqual(from_timestamp(data['joined']), USERDATA[0]['joined'])
        self.assertFalse(data['is_moderator'])
        self.assertEqual(data['allow_risque'], USERDATA[0]['flags'] & User.Flags.ALLOW_RISQUE > 0)
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertEqual(data["comments"], [])

    def test_patch(self):
        """Tests modifying user data."""

        # nonexistant user request
        response: Response = self.client.patch("/api/user/nonexistantuser", json={
            "image": "https://via.placeholder.com/150"
        })
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid username.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        # anonymous unprivileged user edit request
        response = self.client.patch("/api/user/testuser", json={
            "image": "https://via.placeholder.com/150"
        })
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Insufficient credentials.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)
        
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]

        # unprivileged user edit request
        response = self.client.patch("/api/user/testuser", json={
            "image": "https://via.placeholder.com/150"
        })
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Insufficient credentials.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)
        
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # errnoenous privledged user edit requests
        response = self.client.patch("/api/user/testuser", json=[1, 2, 3])
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected dict; got list.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        response = self.client.patch("/api/user/testuser", json={
            "image": 155,
            "description": False
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("'image' must be a string.", response.json['errors'])
        self.assertIn("'description' must be a string.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 2)
        
        response = self.client.patch("/api/user/testuser", json={
            "allow_risque": [1, 2, 3]
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("'allow_risque' must be a boolean.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        # valid privledged user edit requests
        response = self.client.patch("/api/user/testuser", json={
            "image": "https://via.placeholder.com/150"
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertEqual(response.json['data']['image'], "https://via.placeholder.com/150")

        response = self.client.patch("/api/user/testuser", json={
            "image": ""
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertEqual(response.json['data']['image'], User.DEFAULT_IMAGE_URI)

        response = self.client.patch("/api/user/testuser", json={
            "allow_risque": False
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertFalse(response.json['data']['allow_risque'])

        response = self.client.patch("/api/user/testuser", json={
            "description": "  Hello everyone! Don't mind me       "
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertEqual(response.json['data']['description'], "Hello everyone! Don't mind me")

        response = self.client.patch("/api/user/testuser", json={
            "description": ""
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertIsNone(response.json['data']['description'])

        response = self.client.patch("/api/user/testuser", json={
            "description": "        \t   "
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertIsNone(response.json['data']['description'])

    def test_follow(self):
        """Tests following users."""
        
        # nonexistant user follow request
        response = self.client.post("/api/user/nonexistantuser/follow")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid username.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        # unprivileged user follow request
        response = self.client.post("/api/user/testuser2/follow")
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Must be logged in to follow a user.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)
        
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # self-follow request
        response = self.client.post("/api/user/testuser/follow")
        self.assertEqual(response.json['code'], 403)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Cannot follow yourself.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        # privledged user follow request
        response = self.client.post("/api/user/testuser2/follow")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertIn("testuser2", response.json['data']['following'])
        self.assertEqual(len(response.json['data']['following']), 1)
        self.assertEqual(len(response.json['data']['followed_by']), 0)

        response = self.client.get("/api/user/testuser2")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertIn("testuser", response.json['data']['followed_by'])
        self.assertEqual(len(response.json['data']['followed_by']), 1)
        self.assertEqual(len(response.json['data']['following']), 0)

        # user re-follow request
        response = self.client.post("/api/user/testuser2/follow")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("You already followed this user.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

    def test_unfollow(self):
        """Tests unfollowing users."""
        
        # nonexistant user unfollow request
        response = self.client.delete("/api/user/nonexistantuser/follow")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid username.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        # unprivileged user unfollow request
        response = self.client.delete("/api/user/testuser2/follow")
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Must be logged in to unfollow a user.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)
        
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # self-unfollow request
        response = self.client.delete("/api/user/testuser/follow")
        self.assertEqual(response.json['code'], 403)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Cannot unfollow yourself.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

        # privledged user unfollow request
        self.client.post("/api/user/testuser2/follow")
        self.client.post("/api/user/testuser3/follow")
        response = self.client.delete("/api/user/testuser3/follow")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get("/api/user/testuser")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertIn("testuser2", response.json['data']['following'])
        self.assertEqual(len(response.json['data']['following']), 1)
        self.assertEqual(len(response.json['data']['followed_by']), 0)

        response = self.client.get("/api/user/testuser2")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertIn("testuser", response.json['data']['followed_by'])
        self.assertEqual(len(response.json['data']['followed_by']), 1)
        self.assertEqual(len(response.json['data']['following']), 0)

        response = self.client.get("/api/user/testuser3")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(len(response.json['data']['followed_by']), 0)
        self.assertEqual(len(response.json['data']['following']), 0)

        # attempt to unfollow user who isn't being followed
        response = self.client.delete("/api/user/testuser3/follow")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("You haven't followed this user.", response.json['errors'])
        self.assertEqual(len(response.json['errors']), 1)

if __name__ == "__main__":
    from sys import argv

    if len(argv) > 1:
        app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
            "fictionsource-test",
            argv[1],
            argv[2] if len(argv) > 2 else None,
            cred_file = ".dbtestcred"
        )

    main()
