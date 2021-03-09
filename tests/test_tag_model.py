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

        for raise_case in (
            (None, ""),
            (1.5, ""),
            (8, ""),
            ([], ""),
            ({}, ""),
            ("", None),
            ("", 1.5),
            ("", 8),
            ("", []),
            ("", {}),
            ("", ""),
            ("generic", ""),
            ("abc", "abc")
        ):
            self.assertRaises(ValueError, Tag.new, *raise_case)

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

        for false_case in (
            "",
            "a",
            "ab",
            "  ",
            "\n",
            "_ ",
            "(((",
            ")))",
            "+%  ",
            "category:test",
            "2+2=4",
            "x2>5",
            "!!!",
            "???",
            "\n\t\t\t\b\x00",
            "a" * (Tag.NAME_LENGTH + 1)
        ):
            self.assertFalse(Tag.is_valid_name(false_case))

        for true_case in (
            "abc",
            "test",
            "abc123",
            "see_me_after_dinner"
        ):
            self.assertTrue(Tag.is_valid_name(true_case))

    def test_valid_types(self) -> None:
        """Tests the Tag.is_valid_type method."""

        for false_case in (
            "",
            1,
            2.5,
            None,
            "abcdefg"
        ):
            self.assertFalse(Tag.is_valid_type(false_case))

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
