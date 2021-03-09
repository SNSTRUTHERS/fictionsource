#!/usr/bin/env python

"""Tag API tests."""

from unittest import TestCase, main

from flask.wrappers import Response

from models import connect_db, db, Story, StoryTag, Tag, User
from dbcred import get_database_uri

from tests.test_api import USERDATA, STORYDATA

from app import CURR_USER_KEY, app

# == TEST CASE =================================================================================== #

class TagAPITestCase(TestCase):
    """Test cases for Tag-related entrypoints."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        StoryTag.query.delete()
        Tag.query.delete()
        Story.query.delete()
        User.query.delete()

        users = [ User(**data) for data in USERDATA ]
        db.session.add_all(users)

        tags = (
            Tag.new("category", "fanfiction", commit=False),
            Tag.new("category", "original",   commit=False),
            Tag.new("category", "crossover",  commit=False),
            Tag.new("genre",    "action",     commit=False),
            Tag.new("genre",    "adventure",  commit=False),
            Tag.new("genre",    "romance",    commit=False),
            Tag.new("genre",    "suspense",   commit=False),
            Tag.new("genre",    "thriller",   commit=False),
            Tag.new("generic",  "abcdef",     commit=False)
        )

        db.session.add_all(tags)
        db.session.commit()

        self.tags = [ (tag.url_safe_query_name, tag.name, tag.type) for tag in tags ]
        self.user_ids = [ id for id in map(lambda user: user.id, users) ]

        stories = [
            Story(**STORYDATA[i], author_id=self.user_ids[i]) for i in range(len(STORYDATA))
        ]
        db.session.add_all(stories)
        db.session.commit()
        self.story_ids = [ id for id in map(lambda story: story.id, stories) ]

        stories[0].tags.append(tags[0])
        stories[0].tags.append(tags[4])
        
        stories[1].tags.append(tags[1])
        stories[1].tags.append(tags[6])
        
        stories[2].tags.append(tags[2])
        stories[2].tags.append(tags[4])
        stories[2].tags.append(tags[7])
        stories[2].tags.append(tags[8])
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()
        
    def test_get(self) -> None:
        """Tests retrieving tag information."""

        response: Response = self.client.get("/api/tag/test")
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("No tag type provided.", response.json["errors"])

        response = self.client.get("/api/tag/user:test")
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Invalid tag type \"user\".", response.json["errors"])

        response = self.client.get("/api/tag/%23test")
        self.assertEqual(response.json["code"], 404)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Tag with name \"#test\" doesn't exist.", response.json["errors"])

        for index, lst in (
            (5, []),
            (3, []),
            (0, [self.story_ids[0]]),
            (2, []),
            (4, [self.story_ids[0]]),
            (1, [])
        ):
            (tag, name, type) = self.tags[index]
            response = self.client.get(f"/api/tag/{tag}")
            self.assertEqual(response.json["code"], 200)
            self.assertEqual(response.json["type"], "success")

            data = response.json["data"]
            self.assertEqual(data['name'], name)
            self.assertEqual(data['type'], type)
            self.assertEqual(data['query_name'], tag.replace('%23', '#'))
            self.assertEqual(data['stories'], lst)

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        for index, lst in (
            (5, []),
            (3, []),
            (0, [self.story_ids[0]]),
            (2, [self.story_ids[2]]),
            (4, [self.story_ids[0], self.story_ids[2]]),
            (1, [])
        ):
            (tag, name, type) = self.tags[index]
            response = self.client.get(f"/api/tag/{tag}")
            self.assertEqual(response.json["code"], 200)
            self.assertEqual(response.json["type"], "success")

            data = response.json["data"]
            self.assertEqual(data['name'], name)
            self.assertEqual(data['type'], type)
            self.assertEqual(data['query_name'], tag.replace('%23', '#'))
            self.assertEqual(data['stories'], lst)

    def test_add_tag(self) -> None:
        """Tests adding tags to stories."""

        for id in (1445, self.story_ids[0]):
            response = self.client.put(f"/api/story/{id}/tags")
            self.assertEqual(response.json["code"], 401)
            self.assertEqual(response.json["type"], "error")
            self.assertIn("Must be logged in to add tags to a story.", response.json["errors"])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[2]

        response: Response = self.client.put(f"/api/story/1445/tags")
        self.assertEqual(response.json["code"], 404)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Invalid story ID.", response.json["errors"])

        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags")
        self.assertEqual(response.json["code"], 401)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Insufficient credentials.", response.json["errors"])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json={})
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Expected list; got object.", response.json["errors"])
        
        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=15)
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Expected list; got integer.", response.json["errors"])

        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#ab"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Tag name must be at least 3 characters long.", response.json["errors"])

        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#" + ('a' * (Tag.NAME_LENGTH + 1))
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn(
            "Tag name must not be greater than 96 characters in length.",
            response.json["errors"]
        )
        
        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "user:abcdef"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Invalid tag type \"user\".", response.json["errors"])
        
        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#\tab;def"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Invalid tag name \"\tab;def\".", response.json["errors"])
        
        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "category:cat"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Cannot create new tag of type \"category\".", response.json["errors"])
        
        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "category:cat", "user:abcdef"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("[0]: Cannot create new tag of type \"category\".", response.json["errors"])
        self.assertIn("[1]: Invalid tag type \"user\".", response.json["errors"])

        response = self.client.put(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#abcdef", "#hello_world"
        ])
        self.assertEqual(response.json["code"], 200)
        self.assertEqual(response.json["type"], "success")
        self.assertEqual(self.client.get("/api/tag/%23hello_world").json['code'], 200)
        self.assertIn(
            self.story_ids[0], 
            self.client.get("/api/tag/%23abcdef").json['data']['stories']
        )
        self.assertIn(
            self.story_ids[0],
            self.client.get("/api/tag/%23hello_world").json['data']['stories']
        )

    def test_remove_tag(self) -> None:
        """Tests removing tags from stories."""

        for id in (1445, self.story_ids[0]):
            response = self.client.delete(f"/api/story/{id}/tags")
            self.assertEqual(response.json["code"], 401)
            self.assertEqual(response.json["type"], "error")
            self.assertIn("Must be logged in to remove tags from a story.", response.json["errors"])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[2]

        response: Response = self.client.delete(f"/api/story/1445/tags")
        self.assertEqual(response.json["code"], 404)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Invalid story ID.", response.json["errors"])

        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags")
        self.assertEqual(response.json["code"], 401)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Insufficient credentials.", response.json["errors"])

        with self.client.session_transaction() as session:
            session[CURR_USER_KEY] = self.user_ids[0]

        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json={})
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Expected list; got object.", response.json["errors"])
        
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=True)
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Expected list; got boolean.", response.json["errors"])

        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#ab"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Tag name must be at least 3 characters long.", response.json["errors"])

        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#" + ('a' * (Tag.NAME_LENGTH + 1))
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn(
            "Tag name must not be greater than 96 characters in length.",
            response.json["errors"]
        )
        
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=[
            "user:abcdef"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("Invalid tag type \"user\".", response.json["errors"])
        
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=[
            "category:cat", "user:abcdef"
        ])
        self.assertEqual(response.json["code"], 400)
        self.assertEqual(response.json["type"], "error")
        self.assertIn("[0]: Tag does not exist.", response.json["errors"])
        self.assertIn("[1]: Invalid tag type \"user\".", response.json["errors"])
        
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#abcdef", "category:fanfiction"
        ])
        self.assertEqual(response.json["code"], 200)
        self.assertEqual(response.json["type"], "success")
        self.assertNotIn(
            self.story_ids[0], 
            self.client.get("/api/tag/%23abcdef").json['data']['stories']
        )
        self.assertNotIn(
            self.story_ids[0],
            self.client.get("/api/tag/category:fanfiction").json['data']['stories']
        )
        
        response = self.client.delete(f"/api/story/{self.story_ids[0]}/tags", json=[
            "#abcdef", "category:fanfiction"
        ])
        self.assertEqual(response.json["code"], 200)
        self.assertEqual(response.json["type"], "success")

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
