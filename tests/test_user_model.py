#!/usr/bin/env python

"""Story model tests."""

from unittest import TestCase, main

from models import connect_db, db, User, Story
from dbcred import get_database_uri

from datetime import date
from dateutil.relativedelta import relativedelta

from app import app

# == TEST CASE =================================================================================== #

class UserModelTestCase(TestCase):
    """Test cases for User ORM."""

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
    
    def test_register(self):
        """Tests the User.register class method."""

        self.assertRaises(ValueError, User.register,
            "",
            "abcdefg",
            "test@gmail.com",
            date.today() + relativedelta(years=-13, months=-5)
        )
        self.assertRaises(ValueError, User.register,
            "testuser",
            "abc",
            "test@gmail.com",
            date.today() + relativedelta(years=-13, months=-5)
        )
        self.assertRaises(ValueError, User.register,
            "testuser",
            "abc",
            "test@gmail.com",
            date.today() + relativedelta(years=-6, months=-5)
        )
        self.assertRaises(ValueError, User.register,
            "testuser",
            "abcdefg",
            "test@gmail.com",
            date(year=1899, month=12, day=31)
        )
        self.assertRaises(ValueError, User.register,
            "testuser",
            "abcdefg",
            "test.com",
            date.today() + relativedelta(years=-13, months=-5)
        )
        self.assertRaises(ValueError, User.register,
            "a" * (User.USERNAME_LENGTH + 1),
            "abcdefg",
            "test@gmail.com",
            date.today() + relativedelta(years=-13, months=-5)
        )

        bday = date.today() + relativedelta(years=-20, months=-3, days=-11)
        user = User.register("testuser", "abcdefg", "test@gmail.com", bday)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(user.birthdate, bday)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertIsNone(user.description)
        self.assertEqual(user.flags, User.Flags.DEFAULT)
        self.assertFalse(user.is_moderator)
        self.assertEqual(len(user.stories), 0)
        self.assertEqual(len(user.comments), 0)
        self.assertEqual(len(user.following), 0)
        self.assertEqual(len(user.followed_by), 0)
        self.assertEqual(len(user.favorite_stories), 0)
        self.assertEqual(len(user.followed_stories), 0)
        self.assertRaises(ValueError, User.register, "testuser", "abcdefg", "test@gmail.com", bday)

    def test_authenticate(self):
        """Tests the User.authenticate class method."""

        bday = date.today() + relativedelta(years=-20, months=-3, days=-11)
        user = User.register("testuser", "abcdefg", "test@gmail.com", bday)

        self.assertIsNone(User.authenticate("abcdefg", "abcdefg"))
        self.assertIsNone(User.authenticate("testuser", "abckakfma"))
        self.assertEqual(User.authenticate("testuser", "abcdefg"), user)

    def test_flags(self):
        """Tests User flag properties."""

        bday = date.today() + relativedelta(years=-20, months=-3, days=-11)
        user = User.register("testuser", "abcdefg", "test@gmail.com", bday)

        user.flags = 0
        self.assertFalse(user.allow_risque)
        
        user.allow_risque = True
        self.assertEqual(user.flags, User.Flags.ALLOW_RISQUE)

        user.allow_risque = False
        self.assertEqual(user.flags, User.Flags(0))

    def test_update(self):
        """Tests the User.update method."""

        bday = date.today() + relativedelta(years=-20, months=-3, days=-11)
        user = User.register("testuser", "abcdefg", "test@gmail.com", bday)
        User.register("testuser2", "abcdefg", "test@gmail.com", bday)

        self.assertEqual(user.username, "testuser")
        self.assertFalse(user.allow_risque)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertIsNone(user.description)
        hashed_pwd = user.password

        self.assertEqual(len(user.update(username=True)), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username=123)), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username=5.5)), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username=[1, 2, 3])), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username={})), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username="")), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username="x"*(User.USERNAME_LENGTH + 1))), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username="\n\a\0")), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username="testuser2")), 1)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(len(user.update(username="tester")), 0)
        self.assertEqual(user.username, "tester")

        self.assertEqual(len(user.update(password=False)), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password=55)), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password=0.76)), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password=[])), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password={'a': True})), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password="")), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password="abcde")), 1)
        self.assertEqual(user.password, hashed_pwd)
        self.assertEqual(len(user.update(password="newpasswordboiiiii")), 0)
        self.assertNotEqual(user.password, hashed_pwd)

        self.assertEqual(len(user.update(email=True)), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email=0)), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email=1.0)), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email=[])), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email={})), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email="abcdefg")), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email="gmail.com")), 1)
        self.assertEqual(user.email, "test@gmail.com")
        self.assertEqual(len(user.update(email="test2@gmail.com")), 0)
        self.assertEqual(user.email, "test2@gmail.com")

        self.assertEqual(len(user.update(image=False)), 1)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertEqual(len(user.update(image=100)), 1)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertEqual(len(user.update(image=11.1111)), 1)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertEqual(len(user.update(image=[])), 1)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertEqual(len(user.update(image={'lol': 'abcd'})), 1)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)
        self.assertEqual(len(user.update(image="image_url")), 0)
        self.assertEqual(user.image, "image_url")
        self.assertEqual(len(user.update(image="")), 0)
        self.assertEqual(user.image, User.DEFAULT_IMAGE_URI)

        self.assertEqual(len(user.update(description=True)), 1)
        self.assertIsNone(user.description)
        self.assertEqual(len(user.update(description=55555)), 1)
        self.assertIsNone(user.description)
        self.assertEqual(len(user.update(description=6.28)), 1)
        self.assertIsNone(user.description)
        self.assertEqual(len(user.update(description=[False, True])), 1)
        self.assertIsNone(user.description)
        self.assertEqual(len(user.update(description={})), 1)
        self.assertIsNone(user.description)
        self.assertEqual(len(user.update(description="abcdefg")), 0)
        self.assertEqual(user.description, "abcdefg")
        self.assertEqual(len(user.update(description="   abcdefg")), 0)
        self.assertEqual(user.description, "abcdefg")
        self.assertEqual(len(user.update(description="")), 0)
        self.assertIsNone(user.description)

        self.assertEqual(len(user.update(allow_risque=1)), 1)
        self.assertFalse(user.allow_risque)
        self.assertEqual(len(user.update(allow_risque=-5.0)), 1)
        self.assertFalse(user.allow_risque)
        self.assertEqual(len(user.update(allow_risque="abcdefg")), 1)
        self.assertFalse(user.allow_risque)
        self.assertEqual(len(user.update(allow_risque=[1,2,3,4,5])), 1)
        self.assertFalse(user.allow_risque)
        self.assertEqual(len(user.update(allow_risque={'1': 'one', '2': 'two'})), 1)
        self.assertFalse(user.allow_risque)
        self.assertEqual(len(user.update(allow_risque=True)), 0)
        self.assertTrue(user.allow_risque)

    def test_visible_stories(self):
        """Tests the User.visible_stories method."""

        bday = date.today() + relativedelta(years=-20, months=-3, days=-11)
        user1 = User.register("testuser", "abcdefg", "test@gmail.com", bday)
        user2 = User.register("testuser2", "abcdefg", "test@gmail.com", bday)

        user2.allow_risque = True

        story1 = Story.new(user2, "Test")
        story1.is_risque = True
        story1.private = False

        story2 = Story.new(user2, "Test")
        story2.private = False

        story3 = Story.new(user2, "Test")
        
        stories = user2.visible_stories().all()
        self.assertNotIn(story1, stories)
        self.assertIn(story2, stories)
        self.assertNotIn(story3, stories)

        stories = user2.visible_stories(user1).all()
        self.assertNotIn(story1, stories)
        self.assertIn(story2, stories)
        self.assertNotIn(story3, stories)

        stories = user2.visible_stories(user2).all()
        self.assertIn(story1, stories)
        self.assertIn(story2, stories)
        self.assertNotIn(story3, stories)

        stories = user1.visible_stories()
        self.assertNotIn(story1, stories)
        self.assertNotIn(story2, stories)
        self.assertNotIn(story3, stories)

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
