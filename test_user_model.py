"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, db_change_user, Message, Follows
from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

# db.create_all()


class UserModelTestCase(TestCase):
    """ Test the user model. """

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()


    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()
        user_id = u.id
        self.assertEqual(f"{u}", f"<User #{u.id}: {u.username}, {u.email}>", "test of REPL value")        

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

        # duplicate username, unique email
        u1 = User(
            email="test1@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u1)
        self.assertRaises(IntegrityError, db.session.commit)
        db.session.rollback()

        # unique username, duplicate email
        u2 = User(
            email="test@test.com",
            username="testing123",
            password="HASHED_PASSWORD"
        )

        db.session.add(u2)
        self.assertRaises(IntegrityError, db.session.commit)
        db.session.rollback()


    def test_user_novalues(self):
        """ tests of no values for email, username, and password """
        # no value tests - email
        u3 = User(
            username="testnoemail",
            password="HASHED_PASSWORD"
        )
        db.session.add(u3)
        self.assertRaises(IntegrityError, db.session.commit)
        db.session.rollback()

        # no value tests - username
        u4 = User(
            email="nousername@test.com",
            password="HASHED_PASSWORD"
        )
        db.session.add(u4)
        self.assertRaises(IntegrityError, db.session.commit)
        db.session.rollback()

        # no value tests - password
        u5 = User(
            email="nopassword@test.com",
            username="nopassword"
        )
        db.session.add(u5)
        self.assertRaises(IntegrityError, db.session.commit)
        db.session.rollback()


    def test_user_followings(self):
        """ is_following and is_followed_by tests """
        u1 = User(
            email="follow1@test.com",
            username="followuser1",
            password="HASHED_PASSWORD"
        )
        u2 = User(
            email="follow2@test.com",
            username="followuser2",
            password="HASHED_PASSWORD"
        )
        db.session.add_all([u1, u2])
        db.session.commit()

        # followuser1 is following followuser2 
        f1 = Follows(user_being_followed_id=u2.id, user_following_id=u1.id)
        db.session.add(f1)
        db.session.commit()
        # User 1 (followuser1) is following followuser2
        self.assertEqual(len(u1.following), 1, "u1 is following 1 user")
        self.assertEqual(u1.is_following(u2), True, "u1 is following u2")
        self.assertEqual(len(u1.followers), 0, "u1 is following but has no followers")
        self.assertEqual(u1.is_followed_by(u2), False, "u1 is following u2, u1 has no followers")

        self.assertEqual(len(u2.following), 0, "u2 is following no user")
        self.assertEqual(u2.is_following(u1), False, "u2 is following no user")
        self.assertEqual(len(u2.followers), 1, "u2 is followed by 1 user")
        self.assertEqual(u2.is_followed_by(u1), True, "u2 is followed by u1")
        
        Follows.query.delete()
        db.session.commit()
        # no more following.
        self.assertEqual(len(u1.following), 0, "u1 is following 0 users")
        self.assertEqual(u1.is_following(u2), False, "u1 is not following u2")
        self.assertEqual(len(u1.followers), 0, "u1 is following but has no followers")
        self.assertEqual(u1.is_followed_by(u2), False, "u1 has no followers")

        self.assertEqual(len(u2.following), 0, "u2 is following no user")
        self.assertEqual(u2.is_following(u1), False, "u2 is following no user")
        self.assertEqual(len(u2.followers), 0, "u2 is no longer followed by a user")
        self.assertEqual(u2.is_followed_by(u1), False, "u2 is no longer followed by u1")
        
        
    def test_user_authenitcation(self):
        """ tests of signup and authenticate user class methods """
        passwd = "AUTH_HASHED_PASSWORD"
        u1 = User.signup(
            email="authtest@test.com",
            username="authtesting123",
            password=passwd,
            image_url="/static/images/photo.jpg"
        )
        self.assertNotEqual(u1, False, "signup returned a user object")
        db.session.commit()

        # authenticate user class method test - valid credentials
        self.assertNotEqual(User.authenticate(u1.username, passwd), False, "authenticated user returned") 
        
        # authenticate user class method test - invalid username
        self.assertEqual(User.authenticate("XnotauserX", passwd), False, "authenticate failed - username does not exist") 

        # authenticate user class method test - invalid password
        self.assertEqual(User.authenticate(u1.username, "secret"), False, "authenticate failed - password does not match") 

        
    def test_user_changes(self):
        """ tests of db_user_change -- changes to the user """
        user_from = {
            "email" : "email1@user.com",
            "username" : "changeuser1",
            "image_url" : "",
            "header_image_url" : "",
            "location" : "changeuser1 location",
            "bio" : "bio for changeuser1"
        }

        u1 = User(
            email=user_from["email"],
            username=user_from["username"],
            password="HASHED_PASSWORD",
            image_url=user_from["image_url"],
            header_image_url=user_from["header_image_url"],
            location=user_from["location"],
            bio=user_from["bio"]
        )
        u2 = User(
            email="email2@user.com",
            username="changeuser2",
            password="HASHED_PASSWORD",
            image_url="",
            header_image_url="",
            location="changeuser2 location",
            bio="bio for changeuser2"
        )
        db.session.add_all([u1, u2])
        db.session.commit()
        self.assertNotEqual(u1, False, "signup returned a user object")
        db.session.commit()

        user_to = {
            "email" : user_from["email"],
            "username" : user_from["username"],
            "image_url" : "https://photos.com/person.jpg",
            "header_image_url" : "https://photos.com/background.jpg",
            "location" : "Earth",
            "bio" : "this space intentionally left blank"
        }
        result = db_change_user(u1, user_to, user_from)
        self.assertEqual(result["successful"], True, "successful update") 
        changed_user = User.query.get(u1.id)
        x_check = {
            "email" : str(changed_user.email),
            "username" : str(changed_user.username),
            "image_url" : str(changed_user.image_url),
            "header_image_url" : str(changed_user.header_image_url),
            "location" : str(changed_user.location),
            "bio" : str(changed_user.bio)
        }
        self.assertEqual(x_check, user_to, "to and x_check match") 

        # test of lowercase username and email and removal of whitespace
        user_to_unclean = {
            "email" : f'    {user_from["email"].upper()}    ',
            "username" : f'        {user_from["username"].upper()}        ',
            "image_url" : "   https://photos.com/person.jpg       ",
            "header_image_url" : "        https://photos.com/background.jpg        ",
            "location" : "       Earth         ",
            "bio" : "      this space intentionally left blank           "
        }
        result = db_change_user(changed_user, user_to_unclean, x_check)
        self.assertEqual(result["successful"], True, "successful update") 
        changed_user = User.query.get(u1.id)
        x_check_white = {
            "email" : str(changed_user.email),
            "username" : str(changed_user.username),
            "image_url" : str(changed_user.image_url),
            "header_image_url" : str(changed_user.header_image_url),
            "location" : str(changed_user.location),
            "bio" : str(changed_user.bio)
        }
        self.assertEqual(x_check, x_check_white, "x_check and x_check_white match") 

        # IntegrityError test - changing username to a value that already exists.
        user_to["username"] = str(u2.username)
        result = db_change_user(changed_user, user_to, x_check_white)
        self.assertEqual(result["successful"], False, "update failed") 
        # result["msg"]["msg_text"] has text for the flash message.
        # f"Username was NOT change from '{from['username']}' to '{to['username']}'. Username '{to['username']}' already exists."
        self.assertEqual(result["msg"]["msg_text"], 
        f"Username was NOT change from '{x_check_white['username']}' to '{user_to['username']}'. Username '{user_to['username']}' already exists.",
        "username already exists")
        # test msg_type, the tuple with the error for the form.
        self.assertEqual(result["msg"]["msg_type"][0], "error-integrity", "username update integrity error") 
        self.assertEqual(result["msg"]["msg_type"][1], "username", "username field has the error") 
        self.assertEqual(result["msg"]["msg_type"][2], 
            f"ERROR: Username '{user_to['username']}' already exists.", 
            "username error message for form") 
        
        # IntegrityError test - changing email to a value that already exists.
        user_to["username"] = x_check_white["username"]
        user_to["email"] = str(u2.email)
        result = db_change_user(changed_user, user_to, x_check_white)
        self.assertEqual(result["successful"], False, "update failed") 
        # result["msg"]["msg_text"] has text for the flash message.
        # f"Email was NOT change from '{from['email']}' to '{to['email']}'. Email '{to['email']}' already exists."
        self.assertEqual(result["msg"]["msg_text"], 
        f"Email was NOT change from '{x_check_white['email']}' to '{user_to['email']}'. Email '{user_to['email']}' already exists.",
        "email already exists")
        # test msg_type, the tuple with the error for the form.
        self.assertEqual(result["msg"]["msg_type"][0], "error-integrity", "email update integrity error") 
        self.assertEqual(result["msg"]["msg_type"][1], "email", "email field has the error") 
        self.assertEqual(result["msg"]["msg_type"][2], 
            f"ERROR: Email '{user_to['email']}' already exists.", 
            "email error message for form") 


       