#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import connect_db, db, from_timestamp, User, Story, Chapter, Tag
from dbcred import get_database_uri

from datetime import date

from base64 import b64encode

from app import app
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

class StoryAPITestCase(TestCase):
    """Test cases for Story ORM."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        Story.query.delete()
        User.query.delete()

        self.client = app.test_client()

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

        self.teststory = Story.new(
            self.testuser,
            "Test Story",
            "This is a Simon test"
        )
        self.testchapter1 = Chapter.new(self.teststory, None, "hello world")
        self.testchapter1.update(private=False)
        self.testchapter2 = Chapter.new(self.teststory, None, "chapter 2")
        self.testchapter2.update(private=False)
        self.teststory.update(private=False)

        self.client = app.test_client()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()

    @staticmethod
    def generate_basicauth_credentials(username: str, password: str):
        credentials = b64encode(bytes(f'{username}:{password}', 'utf-8')).decode('utf-8')
        return f"Basic {credentials}"
        
    def test_get(self):
        """Tests retrieving a story's information."""

        # nonexistant story request
        response = self.client.get("/api/story/1444")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # anonymous/unprivileged story data request on public story
        print(Story.query.all())
        response: Response = self.client.get(f"/api/story/{self.teststory.id}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.teststory.id)
        self.assertEqual(data['author'], self.teststory.author.username)
        self.assertEqual(data['summary'], self.teststory.summary)
        self.assertEqual(data['thumbnail'], self.teststory.thumbnail)
        self.assertEqual(from_timestamp(data['posted'], self.teststory.posted))
        self.assertEqual(from_timestamp(data['modified'], self.teststory.modified))
        self.assertEqual(data['chapters'], [self.testchapter1.id, self.testchapter2.id])
        self.assertEqual(data['is_risque'], self.teststory.is_risque)
        self.assertEqual(data['can_comment'], self.teststory.can_comment)

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
