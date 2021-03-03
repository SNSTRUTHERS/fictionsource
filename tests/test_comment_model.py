#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import connect_db, db, User, Story, Chapter, Comment
from dbcred import get_database_uri

from datetime import date, timedelta

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

class CommentModelTestCase(TestCase):
    """Test cases for Comment ORM."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)

    def setUp(self) -> None:
        super().setUp()

        db.drop_all()
        db.create_all()

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

        self.teststory = Story.new(self.testuser, "Hello world")
        self.testchapter = Chapter.new(self.teststory, None, "This is a test from Speakonia")
        self.testchapter.private = False
        db.session.commit()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()

    def test_new(self) -> None:
        """Tests the Comment.new class method."""

        # text must be non-whitespace string post-parse
        self.assertRaises(ValueError, Comment.new, self.testuser, None, self.testchapter)
        self.assertRaises(ValueError, Comment.new, self.testuser, 123, self.testchapter)
        self.assertRaises(ValueError, Comment.new, self.testuser, 0.66, self.testchapter)
        self.assertRaises(ValueError, Comment.new, self.testuser, [], self.testchapter)
        self.assertRaises(ValueError, Comment.new, self.testuser, "", self.testchapter)
        self.assertRaises(ValueError, Comment.new, self.testuser, "   \t ", self.testchapter)
        self.assertRaises(ValueError,
            Comment.new,
            self.testuser, "![a](b)\n- - -", self.testchapter
        )

        # of must be Chapter or Comment
        self.assertRaises(ValueError, Comment.new, self.testuser, "test", None)
        self.assertRaises(ValueError, Comment.new, self.testuser, "test", 123)
        self.assertRaises(ValueError, Comment.new, self.testuser, "test", self.testuser2)

        comment = Comment.new(self.testuser, "test", self.testchapter)
        self.assertIn(comment, self.testchapter.comments)
        self.assertEqual(comment.author, self.testuser)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.replies), 0)
        self.assertEqual(len(comment.liked_by), 0)
        self.assertEqual(comment.of_chapter, self.testchapter)
        self.assertIsNone(comment.reply_of)
        self.assertEqual(comment.parent, self.testchapter)
        self.assertEqual(comment.posted, comment.modified)

        reply = Comment.new(self.testuser2, "test", comment)
        self.assertIn(reply, comment.replies)
        self.assertEqual(len(comment.replies), 1)
        self.assertEqual(reply.author, self.testuser2)
        self.assertEqual(reply.text, "test")
        self.assertEqual(len(reply.replies), 0)
        self.assertEqual(len(reply.liked_by), 0)
        self.assertIsNone(reply.of_chapter, None)
        self.assertEqual(reply.reply_of, comment)
        self.assertEqual(reply.parent, comment)
        self.assertEqual(reply.posted, reply.modified)
    
    def test_update(self) -> None:
        """Tests the Comment.update class method."""

        comment = Comment.new(self.testuser, "test", self.testchapter)

        self.assertEqual(len(comment.update(text=1)), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text=0.1)), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text=[])), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text={})), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text="")), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text="\n\n\n\n\n")), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text="${}${/}")), 1)
        self.assertEqual(comment.text, "test")
        self.assertEqual(len(comment.update(text="ABCDEFG")), 0)
        self.assertEqual(comment.text, "ABCDEFG")
        self.assertGreater(comment.modified, comment.posted)
        
        modified = comment.modified + timedelta(seconds=0)
        self.assertEqual(len(comment.update(text="ABCDEFG")), 0)
        self.assertEqual(comment.text, "ABCDEFG")
        self.assertEqual(comment.modified, modified)

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
