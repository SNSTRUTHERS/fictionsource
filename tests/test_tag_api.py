#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import connect_db, db, User, Story
from dbcred import get_database_uri

from datetime import date

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

class TagAPITestCase(TestCase):
    """Test cases for Story ORM."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        connect_db(app)
        db.drop_all()
        db.create_all()

    def setUp(self) -> None:
        super().setUp()

        Story.query.delete()
        User.query.delete()

        self.client = app.test_client()

    def tearDown(self) -> None:
        super().tearDown()
        db.session.rollback()
        

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
