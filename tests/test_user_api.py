#!/usr/bin/env python

"""User API tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import connect_db, db, FollowingUser, from_timestamp, RefImage, Story, User
from dbcred import get_database_uri

from tests.test_api import generate_basicauth_credentials, USERDATA

from app import CURR_USER_KEY, app

# == TEST CASE =================================================================================== #

class UserAPITestCase(TestCase):
    """Test cases for User API entrypoints."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

        db.session.add_all((
            RefImage(_url=User.DEFAULT_IMAGE_URI),
            RefImage(_url=Story.DEFAULT_THUMBNAIL_URI)
        ))
        db.session.commit()

    def setUp(self) -> None:
        super().setUp()

        for img in RefImage.query.filter(~RefImage.id.in_({1, 2})).all():
            db.session.delete(img)

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
        
    def test_get(self) -> None:
        """Tests retrieving a user's information."""

        # nonexistant user request
        response: Response = self.client.get("/api/user/nonexistantuser")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid username.", response.json['errors'])

        # anonymous/unprivileged user data request
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
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertNotIn('comments', data)
        self.assertNotIn('allow_risque', data)
        
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]
        
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
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertNotIn('comments', data)
        self.assertNotIn('allow_risque', data)
        
        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]
        
        # priviledged user data request
        response = self.client.get(f"/api/user/{USERDATA[0]['username']}", headers={
            "Authorization": generate_basicauth_credentials(
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
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertEqual(data["comments"], [])
        self.assertEqual(data['allow_risque'], USERDATA[0]['flags'] & User.Flags.ALLOW_RISQUE > 0)

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
        self.assertEqual(data["stories"], [])
        self.assertEqual(data["following"], [])
        self.assertEqual(data["followed_by"], [])
        self.assertEqual(data["favorite_stories"], [])
        self.assertEqual(data["followed_stories"], [])
        self.assertEqual(data["comments"], [])
        self.assertEqual(data['allow_risque'], USERDATA[0]['flags'] & User.Flags.ALLOW_RISQUE > 0)

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
        self.assertIn("Expected object; got list.", response.json['errors'])
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

    if len(argv) > 1:
        app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
            "fictionsource-test",
            argv[1],
            argv[2] if len(argv) > 2 else None,
            cred_file = ".dbtestcred"
        )

    main()
