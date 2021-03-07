#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import Chapter, connect_db, db, from_timestamp, Story, User
from dbcred import get_database_uri

from tests.test_api import USERDATA, STORYDATA, CHAPTERDATA1, CHAPTERDATA2, CHAPTERDATA3

from app import app, CURR_USER_KEY

# == TEST CASE =================================================================================== #

class ChapterAPITestCase(TestCase):
    """Test cases for Chapter API entrypoints."""

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
        
    def test_get(self) -> None:
        """Tests retrieving a chapter's information."""

        # nonexistant chapter request
        response: Response = self.client.get("/api/chapter/1444")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid chapter ID.", response.json['errors'])

        # anonymous/unprivileged chapter data request on public chapter
        response = self.client.get(f"/api/chapter/{self.chapter_ids[0]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.chapter_ids[0])
        self.assertEqual(data['story'], self.story_ids[0])
        self.assertEqual(data['name'], CHAPTERDATA1[0]['name'])
        self.assertEqual(data['text'], CHAPTERDATA1[0]['text'])
        self.assertEqual(data['author_notes'], CHAPTERDATA1[0]['author_notes'])
        self.assertEqual(from_timestamp(data['posted']), CHAPTERDATA1[0]['posted'])
        self.assertEqual(from_timestamp(data['modified']), CHAPTERDATA1[0]['modified'])
        self.assertEqual(data['comments'], [])
        self.assertIsNone(data['previous'])
        self.assertEqual(data['next'], self.chapter_ids[1])
        self.assertEqual(data['number'], 1)
        self.assertNotIn('private', data)
        self.assertNotIn('index', data)

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[2]

        # anonymous/unprivileged chapter data request on private story
        response = self.client.get(f"/api/chapter/{self.chapter_ids[2]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid chapter ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]
        response = self.client.get(f"/api/chapter/{self.chapter_ids[2]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid chapter ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # anonymous/unprivileged/filtered chapter data request on private chapter
        response = self.client.get(f"/api/chapter/{self.chapter_ids[5]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid chapter ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]

        response = self.client.get(f"/api/chapter/{self.chapter_ids[5]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid chapter ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]
        
        response = self.client.get(f"/api/chapter/{self.chapter_ids[5]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid chapter ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]

        # privileged chapter data request
        response = self.client.get(f"/api/chapter/{self.chapter_ids[2]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['id'], self.chapter_ids[2])
        self.assertEqual(data['story'], self.story_ids[1])
        self.assertEqual(data['name'], CHAPTERDATA2[0]['name'])
        self.assertEqual(data['text'], CHAPTERDATA2[0]['text'])
        self.assertEqual(data['author_notes'], CHAPTERDATA2[0]['author_notes'])
        self.assertEqual(from_timestamp(data['posted']), CHAPTERDATA2[0]['posted'])
        self.assertEqual(from_timestamp(data['modified']), CHAPTERDATA2[0]['modified'])
        self.assertEqual(data['comments'], [])
        self.assertIsNone(data['previous'])
        self.assertIsNone(data['next'])
        self.assertIsNone(data['number'])
        self.assertEqual(data['private'], CHAPTERDATA2[0]['flags'] & Chapter.Flags.PRIVATE > 0)
        self.assertEqual(data['index'], CHAPTERDATA2[0]['index'])

    def test_new(self) -> None:
        """Tests creating a new chapter."""

        # anonymous chapter post request
        for id in (1447, self.story_ids[0]):
            response = self.client.post(f"/api/story/{id}/chapters")
            self.assertEqual(response.json['code'], 401)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn("Must be logged in to create a new chapter.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        
        # unprivleged chapter post request on non-existant story
        response: Response = self.client.post("/api/story/1447/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])
        
        # unprivleged chapter post request on private non-authored story
        response = self.client.post(f"/api/story/{self.story_ids[1]}/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # unprivleged chapter post request on public non-authored story
        response = self.client.post(f"/api/story/{self.story_ids[2]}/chapters")
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Insufficient credentials.", response.json['errors'])

        # privleged chapter post request with invalid body
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got null.", response.json['errors'])
        
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters", json=False)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got boolean.", response.json['errors'])
        
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters", json=[])
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got list.", response.json['errors'])
        
        # privleged chapter post request with invalid parameters
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters", json={
            "name": 555,
            "text": []
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("'name' must be a string or null.", response.json['errors'])
        self.assertIn("'text' must be a string.", response.json['errors'])
        
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters", json={
            "name": "   ",
            "author_notes": []
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(
            "'name' must contain at least one non-whitespace character.",
            response.json['errors']
        )
        self.assertIn("'author_notes' must be a string or null.", response.json['errors'])

        # privleged chapter post with correct parameters
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters", json={
            "name": "Test  Post",
            "text": "# Heading\nbody  ",
            "author_notes": "Explanation"
        })
        self.assertEqual(response.json['code'], 201)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['story'], self.story_ids[0])
        self.assertEqual(data['name'], "Test Post")
        self.assertEqual(data['text'], "# Heading\nbody")
        self.assertEqual(data['author_notes'], "Explanation")
        self.assertEqual(data['posted'], data['modified'])
        self.assertEqual(data['comments'], [])
        self.assertIsNone(data['previous'])
        self.assertIsNone(data['next'])
        self.assertIsNone(data['number'])
        self.assertTrue(data['private'])
        self.assertEqual(data['index'], len(CHAPTERDATA1))

        response = self.client.get(f"/api/chapter/{data['id']}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(response.json['data'], data)

        # privleged chapter post with default parameters
        response = self.client.post(f"/api/story/{self.story_ids[0]}/chapters", json={})
        self.assertEqual(response.json['code'], 201)
        self.assertEqual(response.json['type'], 'success')

        data = response.json['data']
        self.assertEqual(data['story'], self.story_ids[0])
        self.assertIsNone(data['name'])
        self.assertEqual(data['text'], "")
        self.assertIsNone(data['author_notes'])
        self.assertEqual(data['posted'], data['modified'])
        self.assertEqual(data['comments'], [])
        self.assertIsNone(data['previous'])
        self.assertIsNone(data['next'])
        self.assertIsNone(data['number'])
        self.assertTrue(data['private'])
        self.assertEqual(data['index'], len(CHAPTERDATA1) + 1)

    def test_list_chapters(self) -> None:
        """Tests listing a story's chapters."""

        # chapter list request on nonexistant story
        response: Response = self.client.get("/api/story/1447/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        
        response = self.client.get("/api/story/1447/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]

        # chapter list request on private story
        response = self.client.get(f"/api/story/{self.story_ids[1]}/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        
        response = self.client.get(f"/api/story/{self.story_ids[1]}/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]

        # chapter list request on filtered story
        response = self.client.get(f"/api/story/{self.story_ids[2]}/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]
        
        response = self.client.get(f"/api/story/{self.story_ids[2]}/chapters")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        with self.client.session_transaction() as session:
            del session[CURR_USER_KEY]
        
        # chapter list request
        response = self.client.get(f"/api/story/{self.story_ids[0]}/chapters")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(len(response.json['data']), len(CHAPTERDATA1))
        self.assertEqual(
            response.json['data'][0],
            self.client.get(f"/api/chapter/{self.chapter_ids[0]}").json['data']
        )
        self.assertEqual(
            response.json['data'][1],
            self.client.get(f"/api/chapter/{self.chapter_ids[1]}").json['data']
        )

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]
        
        response = self.client.get(f"/api/story/{self.story_ids[0]}/chapters")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(len(response.json['data']), len(CHAPTERDATA1))
        self.assertEqual(
            response.json['data'][0],
            self.client.get(f"/api/chapter/{self.chapter_ids[0]}").json['data']
        )
        self.assertEqual(
            response.json['data'][1],
            self.client.get(f"/api/chapter/{self.chapter_ids[1]}").json['data']
        )

        # unprivleged chapter list request on story with private chapters
        response = self.client.get(f"/api/story/{self.story_ids[2]}/chapters")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(len(response.json['data']), len([ x for x in filter(
            lambda x: x['flags'] & Chapter.Flags.PRIVATE == 0 if 'flags' in x else False,
            CHAPTERDATA3
        ) ]))
        self.assertEqual(
            response.json['data'][0],
            self.client.get(f"/api/chapter/{self.chapter_ids[4]}").json['data']
        )

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[2]

        # privleged chapter list request on story with private chapters
        response = self.client.get(f"/api/story/{self.story_ids[2]}/chapters")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(len(response.json['data']), len(CHAPTERDATA3))
        self.assertEqual(
            response.json['data'][0],
            self.client.get(f"/api/chapter/{self.chapter_ids[4]}").json['data']
        )
        self.assertEqual(
            response.json['data'][1],
            self.client.get(f"/api/chapter/{self.chapter_ids[5]}").json['data']
        )

    def test_patch(self) -> None:
        """Tests modifying an existing chapter."""

    def test_delete(self) -> None:
        """Tests deleting an existing chapter."""

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
