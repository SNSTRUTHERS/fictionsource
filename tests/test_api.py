#!/usr/bin/env python

"""General API tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import BCRYPT, Chapter, connect_db, db, RefImage, Story, User
from dbcred import get_database_uri

from datetime import date, datetime, timezone

from base64 import b64encode

from app import CURR_USER_KEY, app

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

STORYDATA = (
    {
        "title": "Test Story",
        "summary": "This is a Simon test :^)",
        "posted": datetime(2021, 2, 5, 15, 24, 11, 234000, timezone.utc),
        "modified": datetime(2021, 2, 5, 15, 24, 11, 234000, timezone.utc),
        "flags": Story.Flags.CAN_COMMENT
    },
    {
        "title": "Test Story",
        "summary": "This is a Simon test :^)",
        "posted": datetime(2021, 2, 8, 11, 56, 11, 411000, timezone.utc),
        "modified": datetime(2021, 2, 8, 11, 56, 11, 411000, timezone.utc),
        "flags": Story.Flags.CAN_COMMENT | Story.Flags.PRIVATE
    },
    {
        "title": "Unsafe for Work Story",
        "summary": "How scandalous!! *shocked face*",
        "posted": datetime(2021, 2, 9, 4, 24, 11, 911000, timezone.utc),
        "modified": datetime(2021, 2, 9, 5, 11, 55, 911000, timezone.utc),
        "flags": Story.Flags.IS_RISQUE
    }
)

CHAPTERDATA1 = (
    {
        "name": None,
        "text": "Hello **world**! I'm a test chapter's text contents! Wheeeeee",
        "author_notes": "Just explainin what this is.",
        "posted":   STORYDATA[0]['posted'],
        "modified": STORYDATA[0]['modified'],
        "flags": Chapter.Flags(0)
    },
    {
        "name": "Chapter 2",
        "text": "More text lol",
        "author_notes": None,
        "posted":   STORYDATA[0]['posted'],
        "modified": STORYDATA[0]['modified'],
        "flags": Chapter.Flags(0),
        "index": 1
    }
)

CHAPTERDATA2 = (
    {
        "name": None,
        "text": "Hello",
        "author_notes": None,
        "posted":   STORYDATA[1]['posted'],
        "modified": STORYDATA[1]['modified'],
        "flags": Chapter.Flags(0),
        "index": 1
    },
    {
        "name": "Blank Chapter",
        "text": "# \n**",
        "author_notes": None,
        "posted":   STORYDATA[1]['posted'],
        "modified": STORYDATA[1]['modified'],
        "index": 0
    }
)

CHAPTERDATA3 = (
    {
        "name": None,
        "text": "<insert risque content here lol>",
        "author_notes": None,
        "posted":   STORYDATA[2]['posted'],
        "modified": STORYDATA[2]['modified'],
        "flags": Chapter.Flags(0)
    },
    {
        "name": "Private Chapter",
        "text": "# Heading\n*Hello I have stuff in me yay*",
        "author_notes": None,
        "posted":   STORYDATA[2]['posted'],
        "modified": STORYDATA[2]['modified'],
        "index": 1
    }
)

def generate_basicauth_credentials(username: str, password: str) -> str:
    """Generates Basic Authorization HTTP header data.
    
    Parameters
    ==========
    username: `str`
        The username to log in with.

    password: `str`
        The password to log in with.

    Returns
    =======
    `str`
        String to place in as the value of an Authorization request header.
    """

    credentials = b64encode(bytes(f'{username}:{password}', 'utf-8'))
    return "Basic " + credentials.decode('utf-8')

# == TEST CASES ================================================================================== #

class GeneralAPITestCase(TestCase):
    """Test cases for general API functionality."""

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

        self.client = app.test_client()
        
        User.query.delete()
        
        self.testuser = User.register(
            username = 'testuser',
            password = 'testuser',
            email = 'testuser@gmail.com',
            birthdate = date(1997, 3, 16)
        )

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
            "Authorization": generate_basicauth_credentials(
                self.testuser.username, 'abcdef'
            )
        })
        self.assertEqual(response.json['code'], 401)
        self.assertIn('Invalid credentials.', response.json['errors'])

        # valid credentials
        response = self.client.get("/api/", headers={
            "Authorization": generate_basicauth_credentials(
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

