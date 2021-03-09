#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import connect_db, db, Tag
from dbcred import get_database_uri

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

class TagModelTestCase(TestCase):
    """Test cases for Tag ORM."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        Tag.query.delete()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()

    def test_new(self) -> None:
        """Tests the Tag.new class method."""

        self.assertRaises(ValueError, Tag.new, None, "")
        self.assertRaises(ValueError, Tag.new, 1.5, "")
        self.assertRaises(ValueError, Tag.new, 8, "")
        self.assertRaises(ValueError, Tag.new, [], "")
        self.assertRaises(ValueError, Tag.new, {}, "")
        self.assertRaises(ValueError, Tag.new, "", None)
        self.assertRaises(ValueError, Tag.new, "", 1.5)
        self.assertRaises(ValueError, Tag.new, "", 8)
        self.assertRaises(ValueError, Tag.new, "", [])
        self.assertRaises(ValueError, Tag.new, "", {})
        self.assertRaises(ValueError, Tag.new, "", "")
        self.assertRaises(ValueError, Tag.new, "generic", "")
        self.assertRaises(ValueError, Tag.new, "abc", "abc")

        tag1 = Tag.new("generic", "test")
        self.assertEqual(tag1.type, "generic")
        self.assertEqual(tag1._type, Tag.Type.GENERIC)
        self.assertEqual(tag1.name, "test")
        self.assertEqual(tag1.query_name, "#test")
        self.assertEqual(tag1.url_safe_query_name, "%23test")
        self.assertEqual(len(tag1.stories), 0)
        self.assertRaises(ValueError, Tag.new, "generic", "test")

        tag2 = Tag.new("category", "test")
        self.assertEqual(tag2.type, "category")
        self.assertEqual(tag2._type, Tag.Type.CATEGORY)
        self.assertEqual(tag2.name, "test")
        self.assertEqual(tag2.query_name, "category:test")
        self.assertEqual(tag2.url_safe_query_name, "category:test")
        self.assertEqual(len(tag2.stories), 0)
        self.assertRaises(ValueError, Tag.new, "category", "test")

    def test_valid_names(self) -> None:
        """Tests the Tag.is_valid_name method."""

        self.assertFalse(Tag.is_valid_name(""))
        self.assertFalse(Tag.is_valid_name("a"))
        self.assertFalse(Tag.is_valid_name("ab"))
        self.assertFalse(Tag.is_valid_name("  "))
        self.assertFalse(Tag.is_valid_name("\n"))
        self.assertFalse(Tag.is_valid_name("_ "))
        self.assertFalse(Tag.is_valid_name("((("))
        self.assertFalse(Tag.is_valid_name(")))"))
        self.assertFalse(Tag.is_valid_name("+%  "))
        self.assertFalse(Tag.is_valid_name("category:test"))
        self.assertFalse(Tag.is_valid_name("2+2=4"))
        self.assertFalse(Tag.is_valid_name("x2>5"))
        self.assertFalse(Tag.is_valid_name("!!!"))
        self.assertFalse(Tag.is_valid_name("???"))
        self.assertFalse(Tag.is_valid_name("\n\t\t\t\b\x00"))
        self.assertFalse(Tag.is_valid_name("a" * (Tag.NAME_LENGTH + 1)))

        self.assertTrue(Tag.is_valid_name("abc"))
        self.assertTrue(Tag.is_valid_name("test"))
        self.assertTrue(Tag.is_valid_name("abc123"))
        self.assertTrue(Tag.is_valid_name("see_me_after_dinner"))

    def test_valid_types(self) -> None:
        """Tests the Tag.is_valid_type method."""

        self.assertFalse(Tag.is_valid_type(""))
        self.assertFalse(Tag.is_valid_type(1))
        self.assertFalse(Tag.is_valid_type(2.5))
        self.assertFalse(Tag.is_valid_type(None))
        self.assertFalse(Tag.is_valid_type("abcdefg"))

        for member in Tag.Type.__members__.keys():
            self.assertTrue(Tag.is_valid_type(member.lower()))

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
