#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import Chapter, connect_db, db, User, Story
from dbcred import get_database_uri

from datetime import date, datetime

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

class StoryModelTestCase(TestCase):
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

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()
    
    def test_new(self) -> None:
        """Tests the Story.new class method."""

        # title must be a string with at least one non-whitespace character
        self.assertRaises(ValueError, Story.new, self.testuser, None)
        self.assertRaises(ValueError, Story.new, self.testuser, 123)
        self.assertRaises(ValueError, Story.new, self.testuser, True)
        self.assertRaises(ValueError, Story.new, self.testuser, -1.5)
        self.assertRaises(ValueError, Story.new, self.testuser, "")
        self.assertRaises(ValueError, Story.new, self.testuser, " ")

        # summary must be a string
        self.assertRaises(ValueError, Story.new, self.testuser, "test", 321)
        self.assertRaises(ValueError, Story.new, self.testuser, "test", False)
        self.assertRaises(ValueError, Story.new, self.testuser, "test", 3.2)

        # thumbnail_url must be a string
        self.assertRaises(ValueError, Story.new, self.testuser, "test", "", None)
        self.assertRaises(ValueError, Story.new, self.testuser, "test", "", True)
        self.assertRaises(ValueError, Story.new, self.testuser, "test", "", 11)
        self.assertRaises(ValueError, Story.new, self.testuser, "test", "", 77.328)
        
        story1 = Story.new(self.testuser, "test")
        self.assertEqual(story1.author, self.testuser)
        self.assertEqual(story1.flags, Story.Flags.DEFAULT)
        self.assertEqual(story1.title, "test")
        self.assertEqual(story1.summary, "")
        self.assertEqual(story1.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertIn(story1, self.testuser.stories)
        self.assertEqual(len(self.testuser.stories), 1)
        self.assertEqual(len(story1.tags), 0)
        self.assertEqual(len(story1.favorited_by), 0)
        self.assertEqual(len(story1.followed_by), 0)
        self.assertEqual(len(story1.reports), 0)
        self.assertEqual(story1.posted, story1.modified)

        story2summary = "This is a test from Speakonia."
        story2 = Story.new(self.testuser, "    test  2 ", story2summary)
        self.assertEqual(story2.author, self.testuser)
        self.assertEqual(story2.flags, Story.Flags.DEFAULT)
        self.assertEqual(story2.title, "test 2")
        self.assertEqual(story2.summary, story2summary)
        self.assertEqual(story2.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertIn(story1, self.testuser.stories)
        self.assertIn(story2, self.testuser.stories)
        self.assertEqual(len(self.testuser.stories), 2)
        self.assertEqual(len(story2.tags), 0)
        self.assertEqual(len(story2.favorited_by), 0)
        self.assertEqual(len(story2.followed_by), 0)
        self.assertEqual(len(story2.reports), 0)
        self.assertEqual(story2.posted, story2.modified)

    def test_flags(self) -> None:
        """Tests Story flag getters & setters."""

        story = Story.new(self.testuser, "test")
        
        story.flags = 0
        self.assertFalse(story.private)
        self.assertFalse(story.can_comment)
        self.assertFalse(story.is_risque)

        story.private = True
        self.assertTrue(story.private)
        self.assertEqual(story.flags, Story.Flags.PRIVATE)

        story.can_comment = True
        self.assertTrue(story.can_comment)
        self.assertEqual(story.flags, Story.Flags.PRIVATE | Story.Flags.CAN_COMMENT)

        story.can_comment = False
        story.is_risque = True
        self.assertFalse(story.can_comment)
        self.assertTrue(story.is_risque)
        self.assertEqual(story.flags, Story.Flags.PRIVATE | Story.Flags.IS_RISQUE)

    def test_visibility(self) -> None:
        """Tests story visibility based on privacy & NSFW flags."""
        
        story = Story.new(self.testuser, "test")

        # private stories are visible only to the author
        self.assertTrue(story.visible(self.testuser))
        self.assertFalse(story.visible(self.testuser2))
        self.assertFalse(story.visible(self.testuser3))
        self.assertFalse(story.visible())

        # public stories are visible to all
        story.private = False
        self.assertTrue(story.visible(self.testuser))
        self.assertTrue(story.visible(self.testuser2))
        self.assertTrue(story.visible(self.testuser3))
        self.assertTrue(story.visible())

        # risque stories are visible only to those who allow themselves to view them
        story.is_risque = True
        self.assertTrue(story.visible(self.testuser))
        self.assertFalse(story.visible(self.testuser2))
        self.assertTrue(story.visible(self.testuser3))
        self.assertFalse(story.visible())

        # user should not have access to stories which are risque, even if they created them
        self.testuser.allow_risque = False
        self.assertFalse(story.visible(self.testuser))
        self.assertFalse(story.visible(self.testuser2))
        self.assertTrue(story.visible(self.testuser3))
        self.assertFalse(story.visible())
    
    def test_favorites(self) -> None:
        """Tests favoriting & following stories."""

        story = Story.new(self.testuser, "test")

        story.favorited_by.append(self.testuser2)
        self.assertEqual(len(story.favorited_by), 1)
        self.assertEqual(len(story.favorited_by), story.favorites)
        self.assertIn(story, self.testuser2.favorite_stories)
        self.assertEqual(len(self.testuser2.favorite_stories), 1)

        story.followed_by.append(self.testuser3)
        self.assertEqual(len(story.followed_by), 1)
        self.assertEqual(len(story.followed_by), story.follows)
        self.assertIn(story, self.testuser3.followed_stories)
        self.assertEqual(len(self.testuser3.followed_stories), 1)

    def test_visible_stories_query(self) -> None:
        """Tests the Story.visible_stories class method."""

        # private
        story1 = Story.new(self.testuser, "test")
        
        # public
        story2 = Story.new(self.testuser2, "test2")
        story2.private = False

        # public nsfw
        story3 = Story.new(self.testuser3, "test3")
        story3.is_risque = True
        story3.private = False

        db.session.commit()

        visible_stories_not_logged_in = Story.visible_stories().all()
        self.assertNotIn(story1, visible_stories_not_logged_in)
        self.assertIn(story2, visible_stories_not_logged_in)
        self.assertNotIn(story3, visible_stories_not_logged_in)
        
        visible_stories_allow_risque = Story.visible_stories(self.testuser3).all()
        self.assertNotIn(story1, visible_stories_allow_risque)
        self.assertIn(story2, visible_stories_allow_risque)
        self.assertIn(story3, visible_stories_allow_risque)

        visible_stories_no_risque = Story.visible_stories(self.testuser2).all()
        self.assertNotIn(story1, visible_stories_no_risque)
        self.assertIn(story2, visible_stories_no_risque)
        self.assertNotIn(story3, visible_stories_no_risque)

        # private stories should be irrelevant are irrelevant in visible stories query
        # even when logged in as story author
        visible_stories_no_risque = Story.visible_stories(self.testuser).all()
        self.assertNotIn(story1, visible_stories_no_risque)
        self.assertIn(story2, visible_stories_no_risque)
        self.assertIn(story3, visible_stories_no_risque)

    def test_update(self) -> None:
        """Tests the Story.update function."""

        story = Story.new(self.testuser, "test")

        # empty update has no effect
        self.assertEqual(len(story.update()), 0)
        self.assertEqual(story.title, "test")
        self.assertEqual(story.summary, "")
        self.assertTrue(story.private)
        self.assertTrue(story.can_comment)
        self.assertFalse(story.is_risque)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        
        self.assertEqual(len(story.update(title=123)), 1)
        self.assertEqual(story.title, "test")
        self.assertEqual(len(story.update(title=False)), 1)
        self.assertEqual(story.title, "test")
        self.assertEqual(len(story.update(title=15.5)), 1)
        self.assertEqual(story.title, "test")
        self.assertEqual(len(story.update(title=[])), 1)
        self.assertEqual(story.title, "test")
        self.assertEqual(len(story.update(title=[1, 2, 3])), 1)
        self.assertEqual(story.title, "test")
        self.assertEqual(len(story.update(title={})), 1)
        self.assertEqual(story.title, "test")
        self.assertEqual(len(story.update(title="  Test ")), 0)
        self.assertEqual(story.title, "Test")

        self.assertEqual(len(story.update(title=122, thumbnail = 5)), 2)
        self.assertEqual(story.title, "Test")
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(len(story.update(private="hello")), 1)
        self.assertTrue(story.private)
        
        self.assertEqual(len(story.update(private=3)), 1)
        self.assertTrue(story.private)
        self.assertEqual(len(story.update(private=15.8)), 1)
        self.assertTrue(story.private)
        self.assertEqual(len(story.update(private="off")), 1)
        self.assertTrue(story.private)
        self.assertEqual(len(story.update(private=[])), 1)
        self.assertTrue(story.private)
        self.assertEqual(len(story.update(private={'1': 2})), 1)
        self.assertTrue(story.private)

        # cannot public a story with no chapters
        self.assertEqual(len(story.update(private=False)), 0)
        self.assertTrue(story.private)

        # cannot public a story with no public chapters
        chapter = Chapter.new(story, None, "")
        self.assertEqual(len(story.update(private=False)), 0)
        self.assertTrue(story.private)

        # can only public a story with public chapters with visible text
        chapter.update(text="Hello world", private=False)
        self.assertEqual(len(story.update(private=False)), 0)
        self.assertFalse(story.private)
        self.assertEqual(len(story.update(private=True)), 0)
        self.assertTrue(story.private)
        
        self.assertEqual(len(story.update(can_comment=1.9)), 1)
        self.assertTrue(story.can_comment)
        self.assertEqual(len(story.update(can_comment=-2)), 1)
        self.assertTrue(story.can_comment)
        self.assertEqual(len(story.update(can_comment="go")), 1)
        self.assertTrue(story.can_comment)
        self.assertEqual(len(story.update(can_comment=[True])), 1)
        self.assertTrue(story.can_comment)
        self.assertEqual(len(story.update(can_comment={})), 1)
        self.assertTrue(story.can_comment)
        self.assertEqual(len(story.update(can_comment=False)), 0)
        self.assertFalse(story.can_comment)
        self.assertEqual(len(story.update(can_comment=True)), 0)
        self.assertTrue(story.can_comment)

        self.assertEqual(len(story.update(is_risque=5)), 1)
        self.assertFalse(story.is_risque)
        self.assertEqual(len(story.update(is_risque=0.001)), 1)
        self.assertFalse(story.is_risque)
        self.assertEqual(len(story.update(is_risque="test")), 1)
        self.assertFalse(story.is_risque)
        self.assertEqual(len(story.update(is_risque=[])), 1)
        self.assertFalse(story.is_risque)
        self.assertEqual(len(story.update(is_risque={"test": 55})), 1)
        self.assertFalse(story.is_risque)
        self.assertEqual(len(story.update(is_risque=True)), 0)
        self.assertTrue(story.is_risque)
        self.assertEqual(len(story.update(is_risque=False)), 0)
        self.assertFalse(story.is_risque)
        
        self.assertEqual(len(story.update(thumbnail=False)), 1)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(len(story.update(thumbnail=125)), 1)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(len(story.update(thumbnail=-0.8)), 1)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(len(story.update(thumbnail=[])), 1)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(len(story.update(thumbnail={})), 1)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)
        self.assertEqual(len(story.update(thumbnail="abc")), 0)
        self.assertEqual(story.thumbnail, "abc")
        self.assertEqual(len(story.update(thumbnail="")), 0)
        self.assertEqual(story.thumbnail, Story.DEFAULT_THUMBNAIL_URI)

        self.assertEqual(len(story.update(summary=True)), 1)
        self.assertEqual(story.summary, "")
        self.assertEqual(len(story.update(summary=12)), 1)
        self.assertEqual(story.summary, "")
        self.assertEqual(len(story.update(summary=0.1)), 1)
        self.assertEqual(story.summary, "")
        self.assertEqual(len(story.update(summary=[])), 1)
        self.assertEqual(story.summary, "")
        self.assertEqual(len(story.update(summary={})), 1)
        self.assertEqual(story.summary, "")
        self.assertEqual(len(story.update(summary="foobar")), 0)
        self.assertEqual(story.summary, "foobar")
        self.assertEqual(len(story.update(summary=" hello     world !  ")), 0)
        self.assertEqual(story.summary, "hello world !")
        self.assertEqual(len(story.update(summary="  ")), 0)
        self.assertEqual(story.summary, "")

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
