import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, MessageForm
from models import db, connect_db, User, Message, Likes, Follows

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
#
# Supporting Functions

def get_user_likes(user_id):
    """ Returns a list of message ids that user_id has liked.
    """

    # build a list of liked messages
    db_likes = Likes.query.filter(
        Likes.user_id == user_id).order_by(Likes.message_id).all()
    user_likes = []
    for like in db_likes:
        user_likes.append(like.message_id)

    return user_likes


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

    # changed the query to a user join query. Even though all the messages belong to
    #  user_id in this route, adding the user details about the user to the messages
    #  means we can use the same (slightly altered) show.html as we do when we show
    #  all the messages that a user liked.

    messages = (db.session.query(User.username, User.image_url,
                                 Message.id, Message.text,
                                 Message.timestamp, Message.user_id)
                .join(Message)
                .filter(Message.user_id == user_id)
                .all())

    # # Legacy query
    # messages = (Message.query.filter(Message.user_id == user_id).order_by(Message.timestamp.desc())
    # .limit(100).all())

    liked_msgs = get_user_likes(g.user.id)

    # 'route' helps control where the redirect will take you when you alter a
    #  like on a message. You should stay on the same page. This gets tricky
    #  since you can like from 3 different places -- the root page, the user's
    #  all message page, or the user's like's.
    return render_template('users/show.html', user=user, messages=messages,
                           likes=liked_msgs,
                           route=user_id)


@ app.route('/users/<int:user_id>/likes', methods=["GET"])
def user_likes(user_id):
    """ Show the user profile page with the messages that user_id has liked. user_id must
        match the currently logged in user, g.user.id.
    """

    if g.user:
        user = User.query.get_or_404(user_id)
        if (user.id == g.user.id):
            if (user.username[-1].lower() == "s"):
                name_possessive = f"{user.username}'"
            else:
                name_possessive = f"{user.username}'s"

            liked_msgs = get_user_likes(user_id)

            messages_users = (db.session.query(User.username, User.image_url,
                                               Message.id, Message.text, Message.timestamp, Message.user_id)
                              .join(Message)
                              .filter(Message.id.in_(liked_msgs))
                              .all())

            # print(f"\n\nusers_show: user = {user}, Flush=True)
            return render_template('users/show.html', user=user, messages=messages_users,
                                   list_type=f"{name_possessive} Likes",
                                   route="MyLikes",
                                   likes=liked_msgs)
        else:
            # for now, block access to another user's likes. I would think that seeing another user's likes
            #  should be restricted to users that g.user.id is following and users who are following g.user.id.
            flash(
                "Access unauthorized - Sorry, but you cannot view the messages another use likes.", "danger")
            # leave g.user on the other user's 'main' page.
            return redirect(f"/users/{user_id}")

    else:
        flash("Access unauthorized.", "danger")
        return redirect("/")


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
            #  password is associated with the unchanged username. A good
            #  amount of this logic should move into models, but it is staying
            #  here for now.
            db_user = User.authenticate(user_archive["username"],
                                        form.password.data)
            if db_user:

                # db_change_user(g.user.id, user_update, user_archive)
                # username and email are unique required fields and must be in lowercase.
                db_user.username = form.username.data.lower().strip()
                db_user.email = form.email.data.lower().strip()
                db_user.image_url = form.image_url.data.strip()
                db_user.header_image_url = form.header_image_url.data.strip()
                db_user.location = form.location.data.strip()
                db_user.bio = form.bio.data.strip()

                try:
                    db.session.commit()

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


@ app.route('/messages/<int:message_id>/likes/<user_id>', methods=["POST"])
def messages_add_del_like(message_id, user_id):
    """ Like or unlike a message message.

        message_id is added to the user's like messagelist (liked) when it does not
        exist in user's list of liked message.

        message_id is deleted from the user's like message list (unliked) when it
        EXISTS in user's list of liked message.

        user_id servers for redirection -- we should stay on the page where the like
        or unlike occurred. It will either have:
        - a user id (integer) when the like occurred from a user page (users/{user_id}),
        - 'All' when the like/unlike occurred from the all messages (home) page (/), or
        - 'MyLikes' when the like/unlike occurred from the current user's likes page
          (/users/{user_id}/likes).

    """

    if g.user:
        msg_check = Message.query.get_or_404(message_id)

        user_likes = get_user_likes(g.user.id)

        if (message_id in user_likes):
            # message_id in list means we need to remove the like.
            like_no_mo = Likes.query.filter(
                Likes.user_id == g.user.id, Likes.message_id == message_id).one_or_none()
            db.session.delete(like_no_mo)

        else:
            # message_id NOT in list means we need to add the like.
            new_like = Likes(message_id=message_id, user_id=g.user.id)
            db.session.add(new_like)

        db.session.commit()

        # Did the like/unlike happen on the root page or from a user page? Leave the user where
        #  they were, don't redirect them somewhere else.
        if user_id.isnumeric():
            return redirect(f"/users/{user_id}")
        else:
            if (user_id == "MyLikes"):
                return redirect(f"/users/{g.user.id}/likes")

        return redirect("/")

    else:
        flash("Access unauthorized.", "danger")
        return redirect("/")


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
    - logged in: 100 most recent messages of followed_users (user_being_followed_id 
        in 'follows' table.)
    """

    if g.user:

        # build a list of followed users
        db_following = (Follows.query.filter(
            Follows.user_following_id == g.user.id).all())

        following = []
        for following_user in db_following:
            following.append(following_user.user_being_followed_id)

        # print(f"\n\nhomepage: following: {following}\n\n", flush=True)

        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        liked_msgs = get_user_likes(g.user.id)
        return render_template('home.html', messages=messages, likes=liked_msgs)

    else:
        return render_template('home-anon.html')

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
