#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import connect_db, db, User, Story, Chapter
from dbcred import get_database_uri

from datetime import date

from app import app

# == TEST CASE =================================================================================== #

class ChapterModelTestCase(TestCase):
    """Test cases for Chapter ORM."""

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

        self.teststory = Story.new(self.testuser, "test")

        self.client = app.test_client()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()
        
    def test_new(self) -> None:
        """Tests the Chapter.new class method."""

        # name must be a string with at least one non-whitespace character or null
        self.assertRaises(ValueError, Chapter.new, self.teststory, 1.5)
        self.assertRaises(ValueError, Chapter.new, self.teststory, True)
        self.assertRaises(ValueError, Chapter.new, self.teststory, -5)
        self.assertRaises(ValueError, Chapter.new, self.teststory, [])
        self.assertRaises(ValueError, Chapter.new, self.teststory, {})
        self.assertRaises(ValueError, Chapter.new, self.teststory, "")
        self.assertRaises(ValueError, Chapter.new, self.teststory, " ")

        # text must be a string
        self.assertRaises(ValueError, Chapter.new, self.teststory, text = None)
        self.assertRaises(ValueError, Chapter.new, self.teststory, text = 125)
        self.assertRaises(ValueError, Chapter.new, self.teststory, text = False)
        self.assertRaises(ValueError, Chapter.new, self.teststory, text = -6.28)
        self.assertRaises(ValueError, Chapter.new, self.teststory, text = [])
        self.assertRaises(ValueError, Chapter.new, self.teststory, text = {})

        # author_notes must be a string or null
        self.assertRaises(ValueError, Chapter.new, self.teststory, author_notes = 3.6)
        self.assertRaises(ValueError, Chapter.new, self.teststory, author_notes = True)
        self.assertRaises(ValueError, Chapter.new, self.teststory, author_notes = 1)
        self.assertRaises(ValueError, Chapter.new, self.teststory, author_notes = [])
        self.assertRaises(ValueError, Chapter.new, self.teststory, author_notes = {})

        chapter1 = Chapter.new(self.teststory)
        self.assertEqual(chapter1.story_id, self.teststory.id)
        self.assertEqual(chapter1.story, self.teststory)
        self.assertEqual(chapter1.flags, Chapter.Flags.DEFAULT)
        self.assertIsNone(chapter1.name)
        self.assertIsNone(chapter1.author_notes)
        self.assertEqual(chapter1.text, "")
        self.assertEqual(chapter1.index, 0)
        self.assertIsNone(chapter1.number)
        self.assertEqual(len(chapter1.comments), 0)
        self.assertEqual(len(chapter1.reports), 0)
        self.assertEqual(chapter1.posted, chapter1.modified)

        chapter2 = Chapter.new(self.teststory, "  Test  Chapter")
        self.assertEqual(chapter2.story_id, self.teststory.id)
        self.assertEqual(chapter2.story, self.teststory)
        self.assertEqual(chapter2.flags, Chapter.Flags.DEFAULT)
        self.assertEqual(chapter2.name, "Test Chapter")
        self.assertIsNone(chapter2.author_notes)
        self.assertEqual(chapter2.text, "")
        self.assertEqual(chapter2.index, 1)
        self.assertIsNone(chapter2.number)
        self.assertEqual(len(chapter2.comments), 0)
        self.assertEqual(len(chapter2.reports), 0)
        self.assertEqual(chapter2.posted, chapter2.modified)

    def test_flags(self) -> None:
        """Tests Chapter flag getters & setters."""

        chapter = Chapter.new(self.teststory, "test")
        
        chapter.flags = 0
        self.assertFalse(chapter.private)

        chapter.private = True
        self.assertTrue(chapter.private)
        self.assertEqual(chapter.flags, Story.Flags.PRIVATE)

    def test_visibility(self) -> None:
        """Tests chapter visibility based on privacy & NSFW flags."""

        self.teststory.private = False

        chapter1 = Chapter.new(self.teststory, "private chapter", "Text")
        chapter2 = Chapter.new(self.teststory, "visible chapter", "Text")
        chapter2.private = False

        # private chapters are visible only to the author
        self.assertTrue(chapter1.visible(self.testuser))
        self.assertFalse(chapter1.visible(self.testuser2))

        # public chapters are visible to anyone
        self.assertTrue(chapter2.visible(self.testuser))
        self.assertTrue(chapter2.visible(self.testuser2))

        self.teststory.private = True

        # all chapters are visible only to the author for private stories
        self.assertTrue(chapter1.visible(self.testuser))
        self.assertFalse(chapter1.visible(self.testuser2))
        self.assertTrue(chapter2.visible(self.testuser))
        self.assertFalse(chapter2.visible(self.testuser2))

    def test_index_ordering(self) -> None:
        """Tests Chapter.index property and how that affects ordering in Story.chapters."""

        chapter1 = Chapter.new(self.teststory)
        chapter2 = Chapter.new(self.teststory)

        self.assertEqual(self.teststory.chapters[0], chapter1)
        self.assertEqual(self.teststory.chapters[1], chapter2)

        chapter1.index = 1
        chapter2.index = 0
        db.session.commit()

        self.assertEqual(self.teststory.chapters[0], chapter2)
        self.assertEqual(self.teststory.chapters[1], chapter1)

    def test_order_properties(self) -> None:
        """Tests Chapter.number, Chapter.previous, and Chapter.next properties."""

        chapter1 = Chapter.new(self.teststory)
        chapter2 = Chapter.new(self.teststory)
        chapter3 = Chapter.new(self.teststory)

        self.teststory.private = False
        chapter1.private = False
        chapter3.private = False

        self.assertIsNone(chapter1.previous)
        self.assertEqual(chapter1.next, chapter3)
        self.assertEqual(chapter1.number, 1)

        # private chapters aren't given an order, previous, or next; they're used solely
        # for public chapter navigation
        self.assertIsNone(chapter2.previous)
        self.assertIsNone(chapter2.next)
        self.assertIsNone(chapter2.number)

        self.assertEqual(chapter3.previous, chapter1)
        self.assertIsNone(chapter3.next)
        self.assertEqual(chapter3.number, 2)

        # private stories don't have a public ordering for chapters
        self.teststory.private = True

        self.assertIsNone(chapter1.previous)
        self.assertIsNone(chapter1.next)
        self.assertIsNone(chapter1.number)
        self.assertIsNone(chapter2.previous)
        self.assertIsNone(chapter2.next)
        self.assertIsNone(chapter2.number)
        self.assertIsNone(chapter3.previous)
        self.assertIsNone(chapter3.next)
        self.assertIsNone(chapter3.number)

    def test_update(self) -> None:
        """Tests the Chapter.update method."""

        chapter  = Chapter.new(self.teststory, None, "Text")
        chapter2 = Chapter.new(self.teststory, None, "Text")
        chapter3 = Chapter.new(self.teststory, None, "Text")

        chapter.private  = False
        chapter2.private = False
        chapter3.private = False

        self.assertEqual(len(chapter.update()), 0)
        self.assertIsNone(chapter.name)
        self.assertEqual(chapter.text, "Text")
        self.assertEqual(chapter.index, 0)
        self.assertFalse(chapter.private)
        self.assertIsNone(chapter.author_notes)

        self.assertEqual(len(chapter.update(name=True)), 1)
        self.assertIsNone(chapter.name)
        self.assertEqual(len(chapter.update(name=-5)), 1)
        self.assertIsNone(chapter.name)
        self.assertEqual(len(chapter.update(name=123.456)), 1)
        self.assertIsNone(chapter.name)
        self.assertEqual(len(chapter.update(name=[])), 1)
        self.assertIsNone(chapter.name)
        self.assertEqual(len(chapter.update(name={ 'a': True, 'b': True })), 1)
        self.assertIsNone(chapter.name)
        self.assertEqual(len(chapter.update(name="abc")), 0)
        self.assertEqual(chapter.name, "abc")
        self.assertEqual(len(chapter.update(name="  abc")), 0)
        self.assertEqual(chapter.name, "abc")
        self.assertEqual(len(chapter.update(name="")), 0)
        self.assertIsNone(chapter.name)
        self.assertEqual(len(chapter.update(name="    ")), 0)
        self.assertIsNone(chapter.name)

        self.assertEqual(len(chapter.update(author_notes=False)), 1)
        self.assertIsNone(chapter.author_notes)
        self.assertEqual(len(chapter.update(author_notes=2)), 1)
        self.assertIsNone(chapter.author_notes)
        self.assertEqual(len(chapter.update(author_notes=3.6)), 1)
        self.assertIsNone(chapter.author_notes)
        self.assertEqual(len(chapter.update(author_notes=[])), 1)
        self.assertIsNone(chapter.author_notes)
        self.assertEqual(len(chapter.update(author_notes={})), 1)
        self.assertIsNone(chapter.author_notes)
        self.assertEqual(len(chapter.update(author_notes="test notes")), 0)
        self.assertEqual(chapter.author_notes, "test notes")
        self.assertEqual(len(chapter.update(author_notes="more  test    notes ")), 0)
        self.assertEqual(chapter.author_notes, "more test notes")
        self.assertEqual(len(chapter.update(author_notes="")), 0)
        self.assertIsNone(chapter.author_notes)

        self.assertEqual(len(chapter.update(text=True)), 1)
        self.assertEqual(chapter.text, "Text")
        self.assertEqual(len(chapter.update(text=17)), 1)
        self.assertEqual(chapter.text, "Text")
        self.assertEqual(len(chapter.update(text=-5.5)), 1)
        self.assertEqual(chapter.text, "Text")
        self.assertEqual(len(chapter.update(text=["hi", 'there'])), 1)
        self.assertEqual(chapter.text, "Text")
        self.assertEqual(len(chapter.update(text={"go": 'away'})), 1)
        self.assertEqual(chapter.text, "Text")
        self.assertEqual(len(chapter.update(text="# hello\nlolololo")), 0)
        self.assertEqual(chapter.text, "# hello\nlolololo")
        self.assertEqual(len(chapter.update(text="abc   abc")), 0)
        self.assertEqual(chapter.text, "abc   abc")
        self.assertEqual(len(chapter.update(text="\n\nabc\n\nabc\n\n")), 0)
        self.assertEqual(chapter.text, "abc\n\nabc")

        # chapter with no visible text must be private
        self.assertEqual(len(chapter.update(text="")), 0)
        self.assertEqual(chapter.text, "")
        self.assertTrue(chapter.private)
        self.assertEqual(len(chapter.update(text="    # \n> > - []()  ")), 0)
        self.assertEqual(chapter.text, "# \n> > - []()")
        chapter.update(private = False)
        self.assertTrue(chapter.private)
        self.assertEqual(len(chapter.update(text="Text")), 0)
        self.assertEqual(chapter.text, "Text")
        self.assertTrue(chapter.private)
        chapter.update(private = False)
        self.assertFalse(chapter.private)

        self.assertEqual(len(chapter.update(index=False)), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index=1.5)), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index="hello world")), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index=[0, 1, 2, 'test'])), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index={})), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index=-1)), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index=3)), 1)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(len(chapter.update(index=1)), 0)
        self.assertEqual(chapter.index, 1)
        self.assertEqual(chapter2.index, 0)
        self.assertEqual(chapter3.index, 2)
        self.assertEqual(len(chapter.update(index=2)), 0)
        self.assertEqual(chapter.index, 2)
        self.assertEqual(chapter2.index, 0)
        self.assertEqual(chapter3.index, 1)
        self.assertEqual(len(chapter.update(index=0)), 0)
        self.assertEqual(chapter.index, 0)
        self.assertEqual(chapter2.index, 1)
        self.assertEqual(chapter3.index, 2)

        self.assertEqual(len(chapter.update(private=0)), 1)
        self.assertFalse(chapter.private)
        self.assertEqual(len(chapter.update(private=1.5)), 1)
        self.assertFalse(chapter.private)
        self.assertEqual(len(chapter.update(private="")), 1)
        self.assertFalse(chapter.private)
        self.assertEqual(len(chapter.update(private=[55])), 1)
        self.assertFalse(chapter.private)
        self.assertEqual(len(chapter.update(private={'str': 'abc'})), 1)
        self.assertFalse(chapter.private)
        self.assertEqual(len(chapter.update(private=True)), 0)
        self.assertTrue(chapter.private)
        self.assertEqual(len(chapter.update(private=False)), 0)
        self.assertFalse(chapter.private)

        # chapter with no text must be private
        chapter.update(text="")
        self.assertEqual(len(chapter.update(private=False)), 0)
        self.assertTrue(chapter.private)
        self.assertEqual(len(chapter.update(private=True)), 0)
        self.assertTrue(chapter.private)

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
