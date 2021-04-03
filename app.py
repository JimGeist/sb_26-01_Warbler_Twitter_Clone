import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, MessageForm
from models import db, connect_db, User, Message

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

# import pdb
# pdb.set_trace()

##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:

        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data.strip().lower(),
                password=form.password.data,
                email=form.email.data.strip().lower(),
                image_url=form.image_url.data.strip() or User.image_url.default.arg.strip(),
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data.strip().lower(),
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    import pdb
    pdb.set_trace()
    do_logout()

    if g.user:
        flash(f"{g.user.username} successfully logged out.", "success")
        g.user = None
    else:
        flash(f"User was logged out.", "success")

    return redirect("/login")


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    # print(f"\n\nusers_show: user = {user}, Flush=True)
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if g.user:

        user_curr = User.query.get_or_404(g.user.id)

        # remember the values before changes, if any
        user_archive = {
            "username": user_curr.username,
            "email": user_curr.email,
            "image_url": user_curr.image_url,
            "header_image_url": user_curr.header_image_url,
            "location": user_curr.location,
            "bio": user_curr.bio
        }
        form = UserEditForm(obj=user_curr)

        if form.validate_on_submit():
            # user may have changed their username in the form, but the
            #  password is associated with the unchanged username.
            db_user = User.authenticate(user_archive["username"],
                                        form.password.data)
            if db_user:

                # db_change_user(g.user.id, user_update, user_archive)
                db_user.username = form.username.data.lower().strip()
                db_user.email = form.email.data.lower().strip()
                db_user.image_url = form.image_url.data.lower().strip()
                db_user.header_image_url = form.header_image_url.data.lower().strip()
                db_user.location = form.location.data.strip()
                db_user.bio = form.bio.data.strip()

                try:
                    db.session.commit()
                    # print(
                    #     f'\n\nprofile: before: username {user_archive["username"]},  email {user_archive["email"]}, image_url {user_archive["image_url"]},  header_image_url {user_archive["header_image_url"]}, location {user_archive["location"]},  bio {user_archive["bio"]}', flush=True)
                    # print(
                    #     f'          after: username {db_user.username},  email {db_user.email}, image_url {db_user.image_url},  header_image_url {db_user.header_image_url}, location {db_user.location},  bio {db_user.bio}\n\n', flush=True)
                    # flash(
                    #     "Placeholder code.", "success")
                    # redirect to home page when changes were not possible.

                    return redirect(f"/users/{g.user.id}")

                except IntegrityError as err:

                    db.session.rollback()

                    results = {"success": False}

                    error_msg = err.orig.args[0].lower()
                    tests = [("key (username)", "username"),
                             ("key (email)", "email")]

                    if ("key (username)" in error_msg):
                        # Username was NOT change from '' to ''. Username '' already exists
                        form.username.errors = f"ERROR: Username '{form.username.data}' already exists."
                        flash(
                            f"Username was NOT change from '{user_archive['username']}' to '{form.username.data}'. Username '{form.username.data}' already exists.", "danger")
                    else:
                        if ("key (email)" in error_msg):
                            form.email.errors = f"ERROR: Email '{form.email.data}' already exists."
                            flash(
                                f"Email was NOT change from '{user_archive['email']}' to '{form.email.data}'. Email '{form.email.data}' already exists.", "danger")
                        else:
                            # catch all
                            flash(
                                "Username and/or email are not unique. Update did NOT occur.", "danger")

                    return render_template("users/edit.html", form=form, user_id=g.user.id)

                except:
                    db.session.rollback()
                    flash(
                        "An unexpected error occurred. Update(s) did NOT occur.", "danger")
                    return redirect("/")

            else:
                # FUTURE CODE - try a few times before bouncing to home?
                flash(
                    "DENIED! Password is incorrect. Your profile was NOT updated.", "danger")
                # redirect to home page when changes were not possible.
                return redirect("/")

        else:
            return render_template("users/edit.html",
                                   form=form, user_id=g.user.id)

    else:
        flash("Access unauthorized.", "danger")
        return redirect("/")


@ app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@ app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@ app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@ app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@ app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        messages = (Message
                    .query
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')

# SELECT   msg.id, msg.text, msg.timestamp, msg.user_id, usr.username
# FROM     messages AS msg
# JOIN     follows AS fol ON fol.user_being_followed_id = msg.user_id
# JOIN     users AS usr ON msg.user_id = usr.id
# WHERE    user_following_id = 1
# ORDER BY msg.timestamp desc;

# Follows.session.query.filter(Follows.user_following_id == 90).all

# db.session.query(Message.id, Message.text, Message.timestamp, Message.user_id, User.username)
# .join(Follows)


# SELECT msg.id, msg.text, msg.timestamp, msg.user_id, usr.username
# FROM   messages AS msg  JOIN   follows AS fol ON fol.user_being_followed_id = msg.user_id
# JOIN users AS usr ON msg.user_id = usr.id WHERE  user_following_id = 1  ORDER BY msg.timestamp desc;

# SELECT msg.id, msg.text, msg.timestamp, msg.user_id, usr.username FROM   messages AS msg  JOIN   follows AS fol ON fol.user_being_followed_id = msg.user_id  JOIN users AS usr ON msg.user_id = usr.id WHERE  user_following_id = 1  ORDER BY msg.timestamp desc;

# SELECT msg.id, msg.text, msg.timestamp, msg.user_id FROM   messages AS msg  JOIN   follows AS fol ON fol.user_being_followed_id = msg.user_id  WHERE  user_following_id = 1  ORDER BY msg.timestamp desc;

##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@ app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
