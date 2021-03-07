#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import (
    Chapter, connect_db, db, FavoriteStory, FollowingStory, from_timestamp, Story, User
)
from dbcred import get_database_uri

from tests.test_api import USERDATA, STORYDATA, CHAPTERDATA1, CHAPTERDATA2, CHAPTERDATA3

from app import app, CURR_USER_KEY

# == TEST CASE =================================================================================== #

class StoryAPITestCase(TestCase):
    """Test cases for Story API entrypoints."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        FavoriteStory.query.delete()
        FollowingStory.query.delete()
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
        
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]

        # priviledged story data request on private story
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
        self.assertIn("Expected object; got string.", response.json['errors'])
        
        response = self.client.post("/api/story", json=144)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got integer.", response.json['errors'])
        
        response = self.client.post("/api/story", json=["hello world", "make me a story dammit"])
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got list.", response.json['errors'])
        
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

        # anonymous story patch request
        for id in (self.story_ids[0], 1444):
            response = self.client.patch(f"/api/story/{id}")
            self.assertEqual(response.json['code'], 401)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn("Must be logged in to update an existing story.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # nonexistant story patch request
        response: Response = self.client.patch("/api/story/1444")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # unprivleged private story patch request
        response = self.client.patch(f"/api/story/{self.story_ids[1]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # unprivleged public story patch request
        response = self.client.patch(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Insufficient credentials.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[2]

        # privleged story patch request with invalid body
        response = self.client.patch(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got null.", response.json['errors'])
        
        response = self.client.patch(f"/api/story/{self.story_ids[2]}", json=55)
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got integer.", response.json['errors'])
        
        response = self.client.patch(f"/api/story/{self.story_ids[2]}", json=[1, 2])
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Expected object; got list.", response.json['errors'])
        
        # privileged story patch request with invalid parameters
        response = self.client.patch(f"/api/story/{self.story_ids[2]}", json={
            "title": 55,
            "thumbnail": False,
            "can_comment": 1
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("'title' must be a string.", response.json['errors'])
        self.assertIn("'thumbnail' must be a string.", response.json['errors'])
        self.assertIn("'can_comment' must be a boolean.", response.json['errors'])
        
        response = self.client.patch(f"/api/story/{self.story_ids[2]}", json={
            "title": "   ",
            "private": False,
            "can_comment": "abc",
            "is_risque": 55
        })
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(
            "'title' must contain at least one non-whitespace character.",
            response.json['errors']
        )
        self.assertIn("'can_comment' must be a boolean.", response.json['errors'])
        self.assertIn("'is_risque' must be a boolean.", response.json['errors'])
        self.assertTrue(all(map(lambda s: 'private' not in s, response.json['errors'])))

        # privileged story patch request with valid parameters
        response = self.client.patch(f"/api/story/{self.story_ids[2]}", json={
            "title": "Hello   world  ",
            "is_risque": False
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(response.json['data']['title'], "Hello world")
        self.assertEqual(response.json['data']['is_risque'], False)

        # privileged story patch request with attempt to modify is_risque for user
        # that filters out risque content
        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]
        
        response = self.client.patch(f"/api/story/{self.story_ids[1]}", json={
            "is_risque": True
        })
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(response.json['data']['is_risque'], False)

    def test_delete(self) -> None:
        """Tests deleting an existing story."""

        # anonymous story delete request
        for id in (self.story_ids[0], 1444):
            response = self.client.delete(f"/api/story/{id}")
            self.assertEqual(response.json['code'], 401)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn(
                "Must be logged in to delete an existing story.",
                response.json['errors']
            )

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # nonexistant story delete request
        response: Response = self.client.delete("/api/story/1444")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # unprivleged private story delete request
        response = self.client.delete(f"/api/story/{self.story_ids[1]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

        # unprivleged public story delete request
        response = self.client.delete(f"/api/story/{self.story_ids[2]}")
        self.assertEqual(response.json['code'], 401)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Insufficient credentials.", response.json['errors'])

        # privleged story delete request
        response = self.client.delete(f"/api/story/{self.story_ids[0]}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get(f"/api/story/{self.story_ids[0]}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

    def _test_fav_fol_base(self, action: str = "favorite"):
        """Tests for favoriting/following a story."""

        lst = "favorite_stories" if action == "favorite" else "followed_stories"
        actioned = action + ('d' if action.endswith('e') else 'ed')

        # anonymous story favorite request
        for id in (self.story_ids[0], 1444):
            response = self.client.post(f"/api/story/{id}/{action}")
            self.assertEqual(response.json['code'], 401)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn(
                f"Must be logged in to {action} a story.",
                response.json['errors']
            )

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # nonexistant/private story favorite request
        for id in (self.story_ids[1], 1444):
            response = self.client.post(f"/api/story/{id}/{action}")
            self.assertEqual(response.json['code'], 404)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn("Invalid story ID.", response.json['errors'])
        
        # story self-favorite request
        response: Response = self.client.post(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 403)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(f"Cannot {action} your own story.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]
        
        # valid story favorite request
        response = self.client.post(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get(f"/api/user/{USERDATA[1]['username']}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertIn(self.story_ids[0], response.json['data'][lst])
        self.assertNotIn(self.story_ids[1], response.json['data'][lst])
        self.assertNotIn(self.story_ids[2], response.json['data'][lst])

        # story refavorite request
        response = self.client.post(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(f"You already {actioned} this story.", response.json['errors'])

        # risque story favorite request for filtered user
        response = self.client.post(f"/api/story/{self.story_ids[2]}/{action}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

    def _test_unfav_unfol_base(self, action: str = "favorite"):
        """Tests for unfavoriting/unfollowing a story."""

        lst = "favorite_stories" if action == "favorite" else "followed_stories"
        unaction = "un" + action
        actioned = action + ('d' if action.endswith('e') else 'ed')

        # anonymous story favorite request
        for id in (self.story_ids[0], 1444):
            response = self.client.delete(f"/api/story/{id}/{action}")
            self.assertEqual(response.json['code'], 401)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn(
                f"Must be logged in to {unaction} a story.",
                response.json['errors']
            )

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        # nonexistant/private story favorite request
        for id in (self.story_ids[1], 1444):
            response = self.client.delete(f"/api/story/{id}/{action}")
            self.assertEqual(response.json['code'], 404)
            self.assertEqual(response.json['type'], 'error')
            self.assertIn("Invalid story ID.", response.json['errors'])
        
        # story self-favorite request
        response: Response = self.client.delete(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 403)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(f"Cannot {unaction} your own story.", response.json['errors'])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[1]
        
        # valid story favorite request
        response = self.client.post(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')

        response = self.client.get(f"/api/user/{USERDATA[1]['username']}")
        self.assertEqual(response.json['code'], 200)
        self.assertEqual(response.json['type'], 'success')
        self.assertEqual(response.json['data'][lst], [])

        # story refavorite request
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/{action}")
        self.assertEqual(response.json['code'], 400)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn(f"You haven't {actioned} this story.", response.json['errors'])

        # risque story favorite request for filtered user
        response = self.client.delete(f"/api/story/{self.story_ids[2]}/{action}")
        self.assertEqual(response.json['code'], 404)
        self.assertEqual(response.json['type'], 'error')
        self.assertIn("Invalid story ID.", response.json['errors'])

    def test_favorite(self) -> None:
        """Tests favoriting a story."""

        self._test_fav_fol_base()

    def test_unfavorite(self) -> None:
        """Tests unfavoriting a story."""

        self._test_unfav_unfol_base()

    def test_follow(self) -> None:
        """Tests following a story."""

        self._test_fav_fol_base("follow")

    def test_unfollow(self) -> None:
        """Tests unfollowing a story."""

        self._test_unfav_unfol_base("follow")

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
