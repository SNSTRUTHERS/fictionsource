#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from flask.testing import FlaskClient
from flask.wrappers import Response

from models import connect_db, db, User
from dbcred import get_database_uri

from datetime import date

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

class UserAPITestCase(TestCase):
    """Test cases for general API functionality."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        self.client = app.test_client()
        
        User.query.delete()
        
        self.testuser = User.register(
            username = 'testuser',
            password = 'testuser',
            email = 'testuser@gmail.com',
            birthdate = date(1997, 3, 16)
        )

    @staticmethod
    def generate_basicauth_credentials(username: str, password: str):
        credentials = b64encode(bytes(f'{username}:{password}', 'utf-8')).decode('utf-8')
        return f"Basic {credentials}"

    def test_structure(self):
        """Tests the structure of API responses."""

        for entrypoint in [
            "/api/",
            "/api/user/testuser",
            "/api/user/testuser/follow",
            "/api/zzzz"
        ]:
            response: Response = self.client.get(entrypoint)
            self.assertEqual(response.status_code, response.json['code'])
            
            if response.status_code // 100 != 2:
                self.assertEqual(response.json['type'], 'error')
                self.assertEqual(type(response.json['errors']), list)
                self.assertGreaterEqual(len(response.json['errors']), 1)
            else:
                self.assertEqual(response.json['type'], 'success')

    def test_authorization(self):
        """Tests being able to log in via Basic Authorization and Flask session."""

        # bad credentials
        response = self.client.get("/api/", headers={
            "Authorization": self.generate_basicauth_credentials(
                self.testuser.username, 'abcdef'
            )
        })
        self.assertEqual(response.json['code'], 401)
        self.assertIn('Invalid credentials.', response.json['errors'])

        # valid credentials
        response = self.client.get("/api/", headers={
            "Authorization": self.generate_basicauth_credentials(
                self.testuser.username, 'testuser'
            )
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['data'], self.testuser.username)

        # control: no user in session
        response = self.client.get("/api/")
        self.assertEqual(response.json['code'], 200)
        self.assertNotIn('data', response.json)

        # Flask session
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.testuser.id
        response = self.client.get("/api/")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['data'], self.testuser.username)

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

