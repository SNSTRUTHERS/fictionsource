#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import BCRYPT, connect_db, db, from_timestamp, User, Story, Chapter, Tag
from dbcred import get_database_uri

from datetime import date, datetime, timezone

from base64 import b64encode

from app import app, CURR_USER_KEY
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

        Tag.query.delete()
        Chapter.query.delete()
        Story.query.delete()
        User.query.delete()

        self.client = app.test_client()

        users = [ User(**data) for data in USERDATA ]
        db.session.add_all(users)
        db.session.commit()
        self.user_ids = [ id for id in map(lambda user: user.id, users) ]

        stories = [
            Story(**STORYDATA[i], author_id=self.user_ids[i]) for i in range(len(STORYDATA))
        ]
        db.session.add_all(stories)
        db.session.commit()
        self.story_ids = [ id for id in map(lambda story: story.id, stories) ]

        chapters =  [ Chapter(**data, story_id=self.story_ids[0]) for data in CHAPTERDATA1 ]
        chapters += [ Chapter(**data, story_id=self.story_ids[1]) for data in CHAPTERDATA2 ]
        chapters += [ Chapter(**data, story_id=self.story_ids[2]) for data in CHAPTERDATA3 ]
        db.session.add_all(chapters)
        db.session.commit()
        self.chapter_ids = [ id for id in map(lambda chapter: chapter.id, chapters) ]

        self.client = app.test_client()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()

    @staticmethod
    def generate_basicauth_credentials(username: str, password: str):
        credentials = b64encode(bytes(f'{username}:{password}', 'utf-8')).decode('utf-8')
        return f"Basic {credentials}"
        
    def test_get(self):
        """Tests retrieving a public story's information."""

        # nonexistant story request
        response: Response = self.client.get("/api/story/1444")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # anonymous/unprivileged story data request on public story
        response = self.client.get(f"/api/story/{self.story_ids[0]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.story_ids[0])
        self.assertEqual(data['author'], USERDATA[0]['username'])
        self.assertEqual(data['summary'], STORYDATA[0]['summary'])
        self.assertEqual(data['thumbnail'], Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(from_timestamp(data['posted']), STORYDATA[0]['posted'])
        self.assertEqual(from_timestamp(data['modified']), STORYDATA[0]['modified'])
        self.assertEqual(data['chapters'], self.chapter_ids[0:2])
        self.assertFalse(data['is_risque'])
        self.assertTrue(data['can_comment'])
        self.assertNotIn('private', data)

        # priviledged story data request on public story
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        response = self.client.get(f"/api/story/{self.story_ids[0]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.story_ids[0])
        self.assertEqual(data['author'], USERDATA[0]['username'])
        self.assertEqual(data['summary'], STORYDATA[0]['summary'])
        self.assertEqual(data['thumbnail'], Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(from_timestamp(data['posted']), STORYDATA[0]['posted'])
        self.assertEqual(from_timestamp(data['modified']), STORYDATA[0]['modified'])
        self.assertEqual(data['chapters'], self.chapter_ids[0:2])
        self.assertFalse(data['is_risque'])
        self.assertTrue(data['can_comment'])
        self.assertFalse(data['private'])

        # anonymous/unprivileged story data request on private story
        response = self.client.get(f"/api/story/{self.story_ids[1]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]
        response = self.client.get(f"/api/story/{self.story_ids[1]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # priviledged story data request on private story
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]
        response = self.client.get(f"/api/story/{self.story_ids[1]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.story_ids[1])
        self.assertEqual(data['author'], USERDATA[1]['username'])
        self.assertEqual(data['summary'], STORYDATA[1]['summary'])
        self.assertEqual(data['thumbnail'], Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(from_timestamp(data['posted']), STORYDATA[1]['posted'])
        self.assertEqual(from_timestamp(data['modified']), STORYDATA[1]['modified'])
        self.assertEqual(data['chapters'], [ self.chapter_ids[3], self.chapter_ids[2] ])
        self.assertFalse(data['is_risque'])
        self.assertTrue(data['can_comment'])
        self.assertTrue(data['private'])

        # anonymous/filtered story data request on risque story
        response = self.client.get(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]
        response = self.client.get(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # filtered story data request on risque story
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        response = self.client.get(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.story_ids[2])
        self.assertEqual(data['author'], USERDATA[2]['username'])
        self.assertEqual(data['summary'], STORYDATA[2]['summary'])
        self.assertEqual(data['thumbnail'], Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(from_timestamp(data['posted']), STORYDATA[2]['posted'])
        self.assertEqual(from_timestamp(data['modified']), STORYDATA[2]['modified'])
        self.assertEqual(data['chapters'], [ self.chapter_ids[4] ])
        self.assertTrue(data['is_risque'])
        self.assertFalse(data['can_comment'])
        self.assertNotIn('private', data)

        # privileged story data request on risque story
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[2]
        response = self.client.get(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.story_ids[2])
        self.assertEqual(data['author'], USERDATA[2]['username'])
        self.assertEqual(data['summary'], STORYDATA[2]['summary'])
        self.assertEqual(data['thumbnail'], Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(from_timestamp(data['posted']), STORYDATA[2]['posted'])
        self.assertEqual(from_timestamp(data['modified']), STORYDATA[2]['modified'])
        self.assertEqual(data['chapters'], self.chapter_ids[4:6])
        self.assertTrue(data['is_risque'])
        self.assertFalse(data['can_comment'])
        self.assertFalse(data['private'])

    def test_post(self) -> None:
        """Tests creating a new story."""

        # unprivileged story create request
        response: Response = self.client.post("/api/story")
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Must be logged in to post a new story.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        
        # privileged story create request with invalid body
        response = self.client.post("/api/story", json="hello world")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected dict; got str.", response.json['errors'])
        
        response = self.client.post("/api/story", json=144)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected dict; got int.", response.json['errors'])
        
        response = self.client.post("/api/story", json=["hello world", "make me a story dammit"])
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected dict; got list.", response.json['errors'])
        
        # privileged story create request with invalid parameters
        response = self.client.post("/api/story", json={
            "title": 12345,
            "summary": [1, 2, 3]
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("'title' must be a string.", response.json['errors'])
        self.assertIn("'summary' must be a string.", response.json['errors'])
        
        # privileged story create request with missing parameters
        response = self.client.post("/api/story", json={
            "title": "",
            "thumbnail": 83
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(
            "'title' must contain at least one non-whitespace character.",
            response.json['errors']
        )
        self.assertIn("'thumbnail' must be a string.", response.json['errors'])
        
        # privileged story create request with missing parameters
        response = self.client.post("/api/story", json={
            "thumbnail": False
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Missing parameter 'title'.", response.json['errors'])
        self.assertIn("'thumbnail' must be a string.", response.json['errors'])

        # privileged story create request with correct parameters
        response = self.client.post("/api/story", json={
            "title": "The Road Not Travelled",
            "summary": "A down-to-earth tale.",
            "thumbnail": "https://via.placeholder.com/150"
        })
        self.assertEqual(response.json['code'], 201)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['author'], USERDATA[0]['username'])
        self.assertEqual(data['summary'], "A down-to-earth tale.")
        self.assertEqual(data['thumbnail'], "https://via.placeholder.com/150")
        self.assertEqual(from_timestamp(data['posted']), from_timestamp(data['modified']))
        self.assertEqual(data['chapters'], [])
        self.assertFalse(data['is_risque'])
        self.assertTrue(data['can_comment'])
        self.assertTrue(data['private'])

        # check if newly posted data matches data from get
        response = self.client.get(f"/api/story/{data['id']}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(response.json['data'], data)

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]

        # privileged story create request with default parameter fill-in
        response = self.client.post("/api/story", json={ "title": "A Fine Place" })
        self.assertEqual(response.json['code'], 201)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['author'], USERDATA[1]['username'])
        self.assertEqual(data['summary'], "")
        self.assertEqual(data['thumbnail'], Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(from_timestamp(data['posted']), from_timestamp(data['modified']))
        self.assertEqual(data['chapters'], [])
        self.assertFalse(data['is_risque'])
        self.assertTrue(data['can_comment'])
        self.assertTrue(data['private'])

    def test_patch(self) -> None:
        """Tests updating an existing story."""

    def test_delete(self) -> None:
        """Tests deleting an existing story."""

    def test_get_tags(self) -> None:
        """Tests retrieving a story's list of tags."""

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