"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

bcrypt = Bcrypt()
db = SQLAlchemy()


class Follows(db.Model):
    """Connection of a follower <-> followed_user."""

    __tablename__ = 'follows'

    user_being_followed_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )

    user_following_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        primary_key=True,
    )


class Likes(db.Model):
    """Mapping user likes to warbles."""

    __tablename__ = 'likes'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade')
    )

    message_id = db.Column(
        db.Integer,
        db.ForeignKey('messages.id', ondelete='cascade'),
        unique=True
    )


class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    image_url = db.Column(
        db.Text,
        default="/static/images/default-pic.png",
    )

    header_image_url = db.Column(
        db.Text,
        default="/static/images/warbler-hero.jpg"
    )

    bio = db.Column(
        db.Text,
    )

    location = db.Column(
        db.Text,
    )

    password = db.Column(
        db.Text,
        nullable=False,
    )

    messages = db.relationship('Message')

    followers = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_being_followed_id == id),
        secondaryjoin=(Follows.user_following_id == id)
    )

    following = db.relationship(
        "User",
        secondary="follows",
        primaryjoin=(Follows.user_following_id == id),
        secondaryjoin=(Follows.user_being_followed_id == id)
    )

    likes = db.relationship(
        'Message',
        secondary="likes"
    )

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    def is_followed_by(self, other_user):
        """Is this user followed by `other_user`?"""

        found_user_list = [
            user for user in self.followers if user == other_user]
        return len(found_user_list) == 1

    def is_following(self, other_user):
        """Is this user following `other_use`?"""

        found_user_list = [
            user for user in self.following if user == other_user]
        return len(found_user_list) == 1

    @classmethod
    def signup(cls, username, email, password, image_url):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False


class Message(db.Model):
    """An individual message ("warble")."""

    __tablename__ = 'messages'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    text = db.Column(
        db.String(140),
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow(),
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    user = db.relationship('User')


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)


def db_change_user(user_obj, user_update_in, user_archive):
    """ Perform the changes to a user. The user_obj is a User model object that 
        already had the password authenticated for username (note that username
        CAN change). user_update_in and user_archive are dictionaries that contain
        the values from the form and values before an update.

    """

    user_update = {}
    # we are dealing with strings entirely. Strip whitespace. The cleanup is performed
    #  here so we know it is getting done properly.
    for key in user_update_in.keys():
        user_update[key] = user_update_in[key].strip()

    user_obj.image_url = user_update["image_url"]
    user_obj.header_image_url = user_update["header_image_url"]
    user_obj.location = user_update["location"]
    user_obj.bio = user_update["bio"]

    # username and email are unique fields. To aid the uniqueness, username and email
    #  are chanced to lowercase.
    # lowercase was also added to login and signup functions.
    user_obj.username = user_update["username"].lower()
    user_obj.email = user_update["email"].lower()

    # did the username change? 
    if (user_update["username"] == user_archive["username"]):
        msg_username = ""
    else:
        msg_username = f" (formerly '{user_archive['username']}')"

    try:
        db.session.commit()

        result = {
            "successful": True,
            "msg": {
                "msg_type": ("success", "", ""),
                "msg_text": f"'{user_obj.username}'{msg_username} was updated successfully.",
                "class": "success"
            }
        }
        # return redirect(f"/users/{g.user.id}")

    except IntegrityError as err:
        # IngegrityError would occur on either username or email changes.
        db.session.rollback()

        result = {"successful": False}

        error_msg = err.orig.args[0].lower()

        if ("key (username)" in error_msg):
            # Username was NOT change from '' to ''. Username '' already exists
            result["msg"] = {
                "msg_type": ("error-integrity", "username", f"ERROR: Username '{user_update['username']}' already exists."),
                "msg_text": f"Username was NOT change from '{user_archive['username']}' to '{user_update['username']}'. Username '{user_update['username']}' already exists.",
                "class": "danger"
            }

        else:
            if ("key (email)" in error_msg):
                result["msg"] = {
                    "msg_type": ("error-integrity", "email", f"ERROR: Email '{user_update['email']}' already exists."),
                    "msg_text": f"Email was NOT change from '{user_archive['email']}' to '{user_update['email']}'. Email '{user_update['email']}' already exists.",
                    "class": "danger"
                }

            else:
                # catch all
                result["msg"] = {
                    "msg_type": ("error-integrity-catchall", "", ""),
                    "msg_text": "Username and/or email are not unique. Update(s) did NOT occur.",
                    "class": "danger"
                }

    except:
        db.session.rollback()

        result = {
            "successful": False,
            "msg": {
                "msg_type": ("error-unexpected", "", ""),
                "msg_text": "An unexpected error occurred. Update(s) did NOT occur.",
                "class": "danger"
            }
        }

        
    return result
