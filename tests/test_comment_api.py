#!/usr/bin/env python

# """Comment API tests."""

# from unittest import TestCase, main

# from models import connect_db, db, Story, User
# from dbcred import get_database_uri

# from app import app

# # == TEST CASE =================================================================================== #

# class CommentAPITestCase(TestCase):
#     """Test cases for Comment API entrypoints."""

#     @classmethod
#     def setUpClass(cls) -> None:
#         super().setUpClass()

#         connect_db(app)
#         db.drop_all()
#         db.create_all()

#     def setUp(self) -> None:
#         super().setUp()

#         Story.query.delete()
#         User.query.delete()

#         self.client = app.test_client()

#     def tearDown(self) -> None:
#         super().tearDown()
#         db.session.rollback()
        

# if __name__ == "__main__":
#     from sys import argv
    
#     app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
#         "fictionsource-test",
#         cred_file = ".dbtestcred",
#         save = False
#     )
#     if app.config['SQLALCHEMY_DATABASE_URI'] is None:
#         app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
#             "fictionsource-test",
#             cred_file = None,
#             save = False
#         )
#     app.config['SQLALCHEMY_ECHO'] = False

#     if len(argv) > 1:
#         app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
#             "fictionsource-test",
#             argv[1],
#             argv[2] if len(argv) > 2 else None,
#             cred_file = ".dbtestcred"
#         )

#     main()
