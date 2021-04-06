"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows, Likes

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.session.expire_on_commit = False

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuserview",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        db.session.commit()

        # user will get followed by testuser
        self.followuser = User.signup(username="testusertofollow",
                                    email="test@usertofollow.com",
                                    password="testusertofollow",
                                    image_url=None)
        db.session.commit()

        self.followusermsgtext = "## message to follow ##"
        self.followusermsg = Message(text=self.followusermsgtext,
                                    user_id=self.followuser.id)
        db.session.add(self.followusermsg)
        db.session.commit()
        self.followusermsgid = self.followusermsg.id

    def test_add_message(self):
        """ Can user add a message? """
        msg_text = "!!! Hello Test Message !!!"
        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now that the session setting is saved, so we can perform our tests

            resp = client.post("/messages/new", data={"text": msg_text})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.filter(Message.user_id == self.testuser.id).one()
            self.assertEqual(msg.text, msg_text)

            # check /users/{testuser.id} to ensure the message is listed
            resp = client.get(f"/users/{self.testuser.id}")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(msg_text, html)
            # make sure like thumbs up, fa-thumbs-up does not exist
            self.assertNotIn("fa-thumbs-up", html, "users/{user_id}: no thumbs-up / ability to like")
            self.assertNotIn(f'action="/messages/{{ msg.id }}/likes', html, "users/{user_id}: no post action / ability to like")

            # go to root page. testuserview should appear with 1 message.
            resp = client.get("/")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(f"@{self.testuser.username}", html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">1', html, "root: user exists with 1 message")


    def test_follow_user(self):
        """Can user follow another user and like a message? """
        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            self.assertEqual(User.query.count(), 2)

            followuser = User.query.filter(User.username == "testusertofollow").one()
            follow_username = followuser.username
            follow_userid = followuser.id

            self.assertEqual(followuser.username, "testusertofollow")
            # print(f"\n\ntest_follow_user: followuser.id: {self.followuser.id}, followuser.username: {self.followuser.username}", flush=True)
            
            resp = client.post(f"/users/follow/{followuser.id}",
                               follow_redirects=True)

            # redirects to /users/{testuser.id}/following
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)

            self.assertIn(f"@{follow_username}", html, f"/users/user_id/following: {follow_username} is listed")
            # No idea why the below code yields 
            # Instance <User at 0x2974d5e7d88> is not bound to a Session; attribute refresh 
            #  operation cannot proceed (Background on this error at: http://sqlalche.me/e/bhk3)
            # Adding 'db.session.expire_on_commit = False' did not help. 
            # I am proceeding by querying and then setting variables with the values needed.
            # self.assertIn(f"@{followuser.username}", html, "trying again with followuser.username")

            # does ability to unfollow user exist?
            self.assertIn("Unfollow</button>", html, "/users/{testuser.id}/following: ability to unfollow exists")

            # go to followed user's main page, /users/follow_id to check whether message like exists.
            resp = client.get(f"/users/{follow_userid}")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(self.followusermsgtext, html)
            # make sure like thumbs up, fa-thumbs-up does not exist
            self.assertIn("fa-thumbs-up", html, "users/{follow_userid}: thumbs-up / ability to like exists")
            self.assertIn(f'action="/messages/{ self.followusermsgid }/likes', html, "users/{follow_userid}: post action / ability to like exists")
            self.assertIn("border-secondary btn-light", html, "users/{follow_userid}: like button has a light background")

            # go to root page. session user is now following a user and their message should appear on the root page
            resp = client.get("/")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(self.followusermsgtext, html)
            # make sure like thumbs up, fa-thumbs-up and post action exists
            self.assertIn("fa-thumbs-up", html, "users/{follow_userid}: thumbs-up / ability to like exists")
            self.assertIn(f'action="/messages/{ self.followusermsgid }/likes', html, "users/{follow_userid}: post action / ability to like exists")
            self.assertIn("border-secondary btn-light", html, "users/{follow_userid}: like button has a light background")

            # like the message. existance of 'all' in the post url will redirect us back to root - 'all' messages. 
            resp = client.post(f"messages/{self.followusermsgid}/likes/all",
                               follow_redirects=True)     
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn(self.followusermsgtext, html)
            # make sure like thumbs up, fa-thumbs-up and post action exists and green background because the 
            #  message is liked.
            self.assertIn("fa-thumbs-up", html, "users/{follow_userid}: thumbs-up / ability to like exists")
            self.assertIn(f'action="/messages/{ self.followusermsgid }/likes', html, "users/{follow_userid}: post action / ability to like exists")
            self.assertIn("border-success btn-success", html, "users/{follow_userid}: like button has a green background")
            self.assertEqual(Likes.query.filter(Likes.message_id == self.followusermsgid, Likes.user_id == self.testuser.id).count(), 1, "DB Check: 1 record in the likes table")
            







            





