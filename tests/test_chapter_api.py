#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import connect_db, db, Chapter, Story, User
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

# == TEST CASE =================================================================================== #

class ChapterAPITestCase(TestCase):
    """Test cases for Story ORM."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        Chapter.query.delete()
        Story.query.delete()
        User.query.delete()
        
        self.testuser = User.register(
            username = 'testuser',
            password = 'testuser',
            email = 'testuser@gmail.com',
            birthdate = date(1997, 3, 16)
        )
        self.testuser.allow_risque = True

        self.testuser2 = User.register(
            username = 'testuser2',
            password = 'testuser2',
            email = 'testuser2@gmail.com',
            birthdate = date(1997, 3, 17)
        )

        self.testuser3 = User.register(
            username = 'testuser3',
            password = 'testuser3',
            email = 'testuser3@gmail.com',
            birthdate = date(1997, 3, 18)
        )
        self.testuser3.allow_risque = True

        self.teststory = Story.new(self.testuser, "Test")

        self.client = app.test_client()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()

    @staticmethod
    def generate_basicauth_credentials(username: str, password: str):
        credentials = b64encode(bytes(f'{username}:{password}', 'utf-8')).decode('utf-8')
        return f"Basic {credentials}"
        
    def test_get(self) -> None:
        """Tests retrieving a chapter's information."""

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
