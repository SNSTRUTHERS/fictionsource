#!/usr/bin/env python

"""Flask application setup & routes."""

# == IMPORTS & SETUP ============================================================================= #

# ---- Builtin Python modules -------------------------------------------------------------------- #

import datetime
from dateutil.relativedelta import relativedelta

from math import ceil
from os import path
from random import shuffle
from secrets import token_urlsafe

from wtforms.validators import ValidationError

# ---- SQLAlchemy, WTForms, and Flask ------------------------------------------------------------ #

from forms import LogInForm, RegisterForm
from flask_wtf.csrf import generate_csrf, validate_csrf

from flask import (
    flash, Flask, g, get_flashed_messages, jsonify, make_response, render_template,
    redirect, Response, request, send_file, session
)
from flaskkey import get_key
from werkzeug import exceptions

from sqlalchemy.exc import IntegrityError

from models import *
from dbcred import get_database_uri

CURR_USER_KEY = "current_user"

app = Flask(__name__)
app.config['SECRET_KEY'] = get_key()
app.config['MAX_CONTENT_PATH'] = 1 << 22

app.config['SQLALCHEMY_ECHO'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if app.config['SQLALCHEMY_DATABASE_URI'] is None:
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(
        "fictionsource",
        cred_file = None,
        save = False
    )

def to_jsontype(t: type):
    """Converts a Python type to a string."""

    return {
        "NoneType": "null",
        "bool": "boolean",
        "str": "string",
        "int": "integer",
        "float": "float",
        "list": "list",
        "dict": "object"
    }.get(t.__name__, t.__name__.lower())

def allowed_file(filename: str):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in {
            'png', 'jpg', 'jpeg', 'gif', 'webp', 'tif', 'tiff', 'svg'
        }
    )

# ---- Search engine ----------------------------------------------------------------------------- #

from search import *

# == API RESPONSES =============================================================================== #

def make_success_response(
    data: JSONType = None,
    code: int = 200,
    **kwargs
) -> Response:
    """Creates a successful JSON response for the API routes.
    
    Parameters
    ==========
    data: `JSONType` = `None`
        A JSON object to send in the response. Can be None.
    
    code: `int` = 200
        The response code.
    
    Keyword Parameters
    ==================
    type: `str`
        The type of response this is. Defaults to "success".
    
    Any other keyword parameter is allowed, as long as its associated value can be serialized
    to JSON.

    Returns
    =======
    `Response`
        A Flask response.
    """

    json = {
        "type": kwargs.get("type", "success"),
        "code": code,
        "data": data,
        **kwargs
    }

    if data is None:
        del json["data"]
    
    return make_response(jsonify(json), code)

def make_error_response(
    *errors: str,
    code: int = 404,
    **kwargs
) -> Response:
    """Creates a erroneous JSON response for the API routes.
    
    Parameters
    ==========
    errors: `str`
        Errors to return in the response.

        If no errors are provided, no errors are given in the response.

    code: `int` = 404
        The response code.

    Keyword Parameters
    ==================
    type: `str`
        The type of response this is. Defaults to "error".
    
    Any other keyword parameter is allowed, as long as its associated value can be serialized
    to JSON.

    Returns
    =======
    `Response`
        A Flask response.
    """
    
    json = {
        "type": kwargs.get("type", "error"),
        "code": code,
        "errors": errors,
        **kwargs
    }
    if len(errors) < 1:
        del json["errors"]

    return make_response(jsonify(json), code)

# == ERROR PAGES ================================================================================= #

@app.errorhandler(400)
def error_400(error):
    """Error handling page for unauthorized routes."""

    if request.path.startswith("/api"):
        if type(error) == exceptions.BadRequest:
            return make_error_response(
                str(error).split(":", 1)[1].strip(),
                code = 400
            )
        return make_error_response("Bad request.", code=400)

    return render_template("error.html.j2", g=g, message="400 Bad Request")

@app.errorhandler(401)
def error_401(error):
    """Error handling page for unauthorized routes."""

    if request.path.startswith("/api"):
        if type(error) == exceptions.Unauthorized:
            return make_error_response(
                str(error).split(":", 1)[1].strip(),
                code = 401
            )
        return make_error_response("Invalid credentials.", code=401)

    return render_template("error.html.j2", g=g, message="401 Unauthorized")

@app.errorhandler(404)
def error_404(error):
    """Error handling page for invalid routes."""

    if request.path.startswith("/api"):
        if type(error) == exceptions.NotFound:
            return make_error_response(
                str(error).split(":", 1)[1].strip(),
                code = 404
            )
        return make_error_response("Invalid entrypoint.", code=404)

    return render_template("error.html.j2", g=g, message="404 Not Found")

@app.errorhandler(405)
def error_405(error):
    """Error handling page for accessing a route with the wrong method."""

    if request.path.startswith("/api"):
        if type(error) == exceptions.MethodNotAllowed:
            return make_error_response(
                str(error).split(":", 1)[1].strip(),
                code = 405
            )
        return make_error_response("Invalid entrypoint.", code=405)

    return render_template("error.html.j2", g=g, message="405 Bad Method")

@app.errorhandler(413)
def error_413(error):
    """Error handling page for accessing a route with the wrong method."""

    if request.path.startswith("/api"):
        if type(error) == exceptions.RequestEntityTooLarge:
            return make_error_response(
                str(error).split(":", 1)[1].strip(),
                code = 413
            )
        return make_error_response("Payload too large.", code=413)

    return render_template("error.html.j2", g=g, message="413 Payload Too Large")

@app.errorhandler(500)
def error_500(error):
    """Error handling page for internal server errors."""

    if request.path.startswith("/api"):
        if type(error) == exceptions.InternalServerError:
            return make_error_response(
                str(error).split(":", 1)[1].strip(),
                code = 500
            )
        return make_error_response("Internal server error.", code=500)

    return render_template("error.html.j2", g=g, message="500 Internal Server Error")

# == USER AUTHENTICATION & GLOBAL SETUP=========================================================== #

@app.before_request
def setup_flask_globals():
    """Adds convenience functions amongst other things to Flask globals."""

    g.format_time = format_time
    g.search_sort_by = SearchSortEnum.good_values()
    g.generate_csrf = generate_csrf
    g.DEFAULT_THUMBNAIL_URI = Story.DEFAULT_THUMBNAIL_URI
    g.get_flashed_messages = get_flashed_messages

    if request.authorization is not None:
        g.user = User.authenticate(
            request.authorization["username"],
            request.authorization["password"]
        )

        if g.user is None:
            return error_401(None)
    elif CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None

def do_login(user: User):
    """Log in user."""

    session[CURR_USER_KEY] = user.id

def do_logout():
    """Logs out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

# == HTML ROUTES ================================================================================= #

@app.route("/")
def root():
    """Renders the site's homepage."""

    genres: List[Tag] = Tag.query.filter(Tag._type == Tag.Type.GENRE).all()
    shuffle(genres)
    genres = genres[0:4]

    sections: List[str, Mapping[str, Any]] = [
        {
            "id": "newest-stories",
            "name": "Newest Stories",
            "stories": Story.visible_stories(g.user).order_by(
                Story.posted.desc()
            ).slice(0, 10),
            "link": "/read?q=*&sort_by=posted"
        }
    ]

    if g.user != None:
        people_following = Story.visible_stories(g.user).filter(
            Story.author_id.in_([ user.id for user in g.user.following ])
        ).order_by(
            Story.modified.desc()
        ).slice(0, 10).all()

        if len(people_following) > 0:
            sections.append({
                "id": "following",
                "name": "People You're Following",
                "stories": people_following,
                "link": "^following"
            })

        stories_following = Story.visible_stories(g.user).filter(
            Story.id.in_([ story.id for story in g.user.followed_stories ])
        ).order_by(
            Story.modified.desc()
        ).slice(0, 10).all()

        if len(stories_following) > 0:
            sections.append({
                "id": "followed-stories",
                "name": "Stories You're Following",
                "stories": stories_following,
                "link": "^following"
            })

    for genre in genres:
        sections.append({
            "id": genre.name,
            "name": " ".join([
                string.capitalize()
                for string in genre.name.split('_')
            ]),
            "stories": Story.visible_stories(g.user).join(
                Story.tags
            ).filter(
                Tag._type == Tag.Type.GENRE
            ).filter(
                Tag.name == genre.name
            ).order_by(
                Story.modified.desc()
            ).slice(0, 10)
        })

    return render_template("homepage.html.j2", g=g, sections=sections)

@app.route("/manifest.json")
def android_jsonmanifest():
    """Sends manifest.json for Android phones regarding favicon info."""

    return app.send_static_file("manifest.json")

@app.route("/browserconfig.xml")
def ms_browserconfig():
    """Sends browserconfig.xml for Windows regarding favicon info."""

    return app.send_static_file("browserconfig.xml")

@app.route("/static/scripts/markdown.wasm")
def markdown_wasm():
    """Sends WASM for Markdown."""

    return send_file("static/scripts/markdown.wasm", mimetype="application/wasm")

# ---- AUTHENTICATION ROUTES --------------------------------------------------------------------- #

@app.route("/register", methods=["GET", "POST"])
def register_page():
    """Route for registering a new account."""

    if g.user:
        return redirect("/")

    form = RegisterForm()
    form.birthday.render_kw["max"] = datetime.date.today() - relativedelta(years=+13)

    if form.validate_on_submit():
        try:
            user = User.register(
                form.username.data,
                form.password.data,
                form.email.data,
                form.birthday.data
            )

            do_login(user)
            return redirect("/")
        
        except IntegrityError:
            form.username.errors.append("Invalid credentials.")
        except ValueError:
            form.birthday.errors.append("Invalid birthdate.")

    return render_template("register.html.j2", form=form, g=g)

@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Route for logging in to an existing account."""

    if g.user:
        return redirect("/")

    form = LogInForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user is not None:
            do_login(user)
            return redirect("/")

        form.username.errors.append("Invalid credentials.")

    return render_template("login.html.j2", form=form, g=g)

@app.route("/logout")
def log_out():
    """Route for logging out."""

    if g.user is None:
        return error_401(None)
    
    do_logout()
    return redirect("/")

# ---- USER ROUTES ------------------------------------------------------------------------------- #

@app.route("/user/<username>", methods=["GET"])
def user_page(username: str):
    """Route for rendering a user page."""
    
    user: Optional[User] = User.query.filter_by(username=username).first()
    if user is None:
        return error_404(None)
    
    return render_template("user.html.j2", user=user, g=g)

@app.route("/user/<username>", methods=["POST"])
def edit_user_details(username: str):
    """Edits a user's details."""
    
    user: Optional[User] = User.query.filter_by(username=username).first()
    if user is None or g.user != user:
        flash("Must be logged in as user to edit page.", "error")
        return redirect(f"/user/{username}")

    try:
        validate_csrf(request.form["csrf_token"])
    except ValidationError:
        flash("Invalid user edit request.", "error")
        return redirect(f"/user/{username}")
    
    if User.authenticate(username, request.form["password"]) is None:
        flash("Insufficient credentials.", "error")
        return redirect(f"/user/{username}")

    errors = []
    updates = {}
    
    if request.form["username"] not in {"", username}:
        updates['username'] = request.form["username"]

    if request.form["new_password"] != "":
        new_password = request.form["new_password"]
        if new_password != request.form["confirm_new_password"]:
            errors.append("New passwords don't match.")
        else:
            updates['password'] = new_password
        
    if request.form["description"] != "":
        updates['description'] = request.form["description"]

    if request.form["type"] == "file": # file upload
        f = request.files["file"]
        
        ext = f.filename.rsplit('.', 1)[1]
        if allowed_file(f.filename):
            filename = f"/static/images/users/{token_urlsafe(64)}.{ext}"
            while path.exists(filename[1:]):
                filename = f"/static/images/users/{token_urlsafe(64)}.{ext}"

            f.save(filename)

            updates['image'] = filename
    elif request.form["type"] == "url" and request.form["url"] != "": # url
        updates['image'] = request.form["url"]

    if len(errors) == 0:
        errors = user.update(**updates)
    
    for error in errors:
        flash(error, "error")
    
    return redirect(f"/user/{username}")

@app.route("/write", methods=["GET"])
def write_page():
    """Route for managing stories."""

    if g.user is None:
        return error_401(None)

    chapter_id: int = 0
    chapter: Optional[Chapter] = None
    try:
        chapter_id = int(request.args.get("chapter", 0))
    except ValueError:
        chapter_id = 0
    
    if chapter_id > 0:
        chapter = Chapter.query.get(chapter_id)
        if chapter is not None and chapter.story.author_id != g.user.id:
            chapter = None
    
    story: Optional[Story] = None
    if chapter is not None:
        story = chapter.story
    
    return render_template("write.html.j2", g=g, estory=story, echapter=chapter)

@app.route("/write/<int:story_id>", methods=["POST"])
def change_story_thumbnail(story_id: int):
    """Route for changing a story's thumbnail."""

    if g.user is None:
        return error_401(None)

    try:
        validate_csrf(request.form["csrf_token"])
    except ValidationError:
        return redirect("/write")

    story: Story = Story.query.get(story_id)
    if story is None or story.author_id != g.user.id:
        return redirect("/write")

    filename: str = None
    if request.form["type"] == "file": # file upload
        f = request.files["file"]
        
        ext = f.filename.rsplit('.', 1)[1]
        if allowed_file(f.filename):
            filename = f"/static/images/thumbnails/{token_urlsafe(64)}.{ext}"
            while path.exists(filename[1:]):
                filename = f"/static/images/thumbnails/{token_urlsafe(64)}.{ext}"

            f.save(filename)
    elif request.form["type"] == "url": # url
        filename = request.form["url"]

    if filename is not None:
        story.update(thumbnail=filename)

    if len(story.chapters) > 0:
        return redirect(f"/write?chapter={story.chapters[0].id}")
    else:
        return redirect("/write")

# ---- STORY/CHAPTER ROUTES ---------------------------------------------------------------------- #

@app.route("/read/<int:chapter_id>")
def read_page(chapter_id: int):
    """Route for rendering a chapter page."""

    chapter: Chapter = Chapter.query.get_or_404(chapter_id)
    if not chapter.visible(g.user):
        return error_404(None)

    if chapter.story.author_id == g.user.id and chapter.story.private or chapter.story.protected:
        return redirect(f"/write?chapter={chapter_id}")

    return render_template("read.html.j2", g=g, chapter=chapter)

@app.route("/read/<int:chapter_id>.md")
def read_page_md(chapter_id: int):
    """Route for returning a chapter page as Markdown."""

    chapter: Chapter = Chapter.query.get_or_404(chapter_id)
    if not chapter.story.visible(g.user):
        return error_404(None)

    resp = make_response(IMarkdownModel.format_markdown(chapter.text))
    resp.content_type = "text/markdown"
    return resp

# ---- SEARCH ROUTE ------------------------------------------------------------------------------ #

@app.route("/read")
def search_page():
    """Route for rendering search results."""

    results: Optional[SearchResults] = None

    offset = 0
    try:
        offset = int(request.args.get("offset", 0))
        if offset < 0:
            offset = 0
    except ValueError:
        pass

    count = 0
    try:
        count = int(request.args.get("offset", 25))
        if count < 0:
            count = 25
    except ValueError:
        pass

    descending = request.args.get("descending", "true").lower() in (
        "true", "t", "y", "yes", "1"
    )

    sort_by = request.args.get("sort_by", "modified")
    if sort_by not in SearchSortEnum.good_values():
        sort_by = "modified"

    filter_risque = 0
    try:
        filter_risque = int(request.args.get("filter_risque", 0))
    except ValueError:
        pass
    
    if filter_risque < 0:
        filter_risque = -1
    elif filter_risque > 0:
        filter_risque = 1
    if filter_risque < 1 and (g.user is None or not g.user.allow_risque):
        filter_risque = 1
    
    if filter_risque > 0:
        filter_risque = True
    elif filter_risque < 0:
        filter_risque = False
    else:
        filter_risque = None

    if "q" in request.args and len(request.args["q"].strip()) > 0:
        include_tags = set()
        exclude_tags = set()
        include_users = set()
        exclude_users = set()
        include_phrases = set()
        exclude_phrases = set()

        query = reduce_whitespace(request.args['q'])
        negate = False
        while len(query) > 0:
            text = ""

            if query.startswith(' '):
                query = query[1:]
                continue
            elif query.startswith('!'):
                negate = not negate
                query = query[1:]
                continue
            elif query.startswith('"'): # text group
                escape = False
                query = query[1:]

                while len(query) > 0:
                    char = query[0]
                    query = query[1:]

                    if char == '"' and not escape:
                        break
                    elif char == '\\' and not escape:
                        escape = True
                        continue

                    text += char
                    escape = False

                if len(query) > 0 and query[0] == ' ':
                    query = query[1:]

                if len(text) >= 3:
                    if negate:
                        exclude_phrases.add(text)
                    else:
                        include_phrases.add(text)
            else: # generic
                while len(query) > 0:
                    char = query[0]
                    query = query[1:]

                    if char == ' ':
                        break
                    elif char == '"':
                        query = char + query
                        break

                    text += char

                parts = text.split(':', 1)

                if ':' in text and parts[0] == 'user': # user
                    username = parts[1]
                    if User.is_valid_username(username):
                        if negate:
                            exclude_users.add(username)
                        else:
                            include_users.add(username)
                elif (
                    ':' in text and all([ len(x) > 0 for x in parts ]) or
                    text.startswith('#')
                ): # tags
                    if text.startswith('#'):
                        text = text[1:]
                        parts[0] = parts[0][1:]
                    
                    if (Tag.is_valid_name(parts[-1]) and
                        (len(parts) == 1 or len(parts) == 2 and Tag.is_valid_type(parts[0]))
                    ):
                        if negate:
                            exclude_tags.add(text)
                        else:
                            include_tags.add(text)
                elif len(text) >= 3 and ':' not in text: # one-word phrase
                    if negate:
                        exclude_phrases.add(text)
                    else:
                        include_phrases.add(text)

            negate = False

        results = SearchResults(
            user            = g.user,
            offset          = offset,
            count           = count,
            sort_by         = sort_by,
            descending      = descending,
            filter_risque   = filter_risque,
            include_tags    = include_tags,
            exclude_tags    = exclude_tags,
            include_users   = include_users,
            exclude_users   = exclude_users,
            include_phrases = include_phrases,
            exclude_phrases = exclude_phrases
        )

        query = reduce_whitespace(request.args['q'])

        prev_querystrs = [
            (
                f"q={query}&offset={n * count}&" +
                f"sort_by={sort_by}&descending={int(descending)}&" +
                f"filter_risque={filter_risque}"
            ) for n in range(0, ceil((results.end - results.start - 1) / count))
        ]
        next_querystrs = [
            (
                f"q={query}&offset={(n * count) + results.end}&" +
                f"sort_by={sort_by}&descending={int(descending)}&" +
                f"filter_risque={filter_risque}"
            ) for n in range(0, ceil((results.num_results - results.end) / count))
        ]

        return render_template("search.html.j2", g=g,
            query          = query,
            results        = results.results,
            num_results    = results.num_results,
            start          = results.start,
            end            = results.end,
            sort_by        = sort_by,
            descending     = descending,
            filter_risque  = filter_risque,
            count          = count,
            prev_querystrs = prev_querystrs,
            next_querystrs = next_querystrs
        )
    else:       
        return render_template("search.html.j2", g=g,
            sort_by       = sort_by,
            descending    = descending,
            filter_risque = filter_risque,
            count         = count
        )

# == API ROUTES ================================================================================== #

@app.route("/api")
@app.route("/api/")
def null_route():
    """Always returns success response if no errors happen before processing request."""

    if g.user is None:
        return make_success_response()
    else:
        return make_success_response(g.user.username)

# ---- Search ------------------------------------------------------------------------------------ #

@app.route("/api/search", methods=["GET"])
def api_search():
    """API entrypoint for query-based search."""

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    try:
        results = SearchResults(
            user            = g.user,
            offset          = request.json.get("offset", 0),
            count           = request.json.get("count", 25),
            sort_by         = request.json.get("sort_by"),
            descending      = request.json.get("descending", True),
            filter_risque   = (
                request.json.get("filter_risque", True)
                if g.user.allow_risque else True
            ),
            include_tags    = request.json.get("include_tags", set()),
            exclude_tags    = request.json.get("exclude_tags", set()),
            include_users   = request.json.get("include_users", set()),
            exclude_users   = request.json.get("exclude_users", set()),
            include_phrases = request.json.get("include_phrases", set()),
            exclude_phrases = request.json.get("exclude_phrases", set()),
        )
        return make_success_response(results.to_json())
    except ValueError as e:
        errors = str(e).split('\n')
        return make_error_response(*errors, code=400)

# ---- User routes ------------------------------------------------------------------------------- #

@app.route("/api/user/<username>", methods=["GET"])
def get_user(username: str):
    """Returns information regarding a given user."""

    user: Optional[User] = User.query.filter_by(username=username).first()
    if user is None:
        return make_error_response("Invalid username.")
    
    return make_success_response(user.to_json(g.user, "expand" in request.args))

@app.route("/api/user/<username>", methods=["PATCH"])
def update_user(username: str):
    """Updates user information."""

    user: Optional[User] = User.query.filter_by(username=username).first()
    if user is None:
        return make_error_response("Invalid username.")
        
    if g.user is None or user.id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    errors = user.update(
        image        = request.json.get("image"),
        description  = request.json.get("description"),
        allow_risque = request.json.get("allow_risque")
    )

    if len(errors) > 0:
        return make_error_response(*errors, code=400)
    
    return make_success_response()

@app.route("/api/user/<username>/follow", methods=["POST"])
def follow_user(username: str):
    """Follows a user."""
    
    user: Optional[User] = User.query.filter_by(username=username).first()
    if user is None:
        return make_error_response("Invalid username.")

    if g.user is None:
        return make_error_response("Must be logged in to follow a user.", code=401)

    if user.username == g.user.username:
        return make_error_response("Cannot follow yourself.", code=403)

    if user not in g.user.following:
        g.user.following.append(user)
        db.session.commit()

        return make_success_response()

    return make_error_response("You already followed this user.", code=400)

@app.route("/api/user/<username>/follow", methods=["DELETE"])
def unfollow_user(username: str):
    """Unfollows a user."""
    
    user: Optional[User] = User.query.filter_by(username=username).first()
    if user is None:
        return make_error_response("Invalid username.")

    if g.user is None:
        return make_error_response("Must be logged in to unfollow a user.", code=401)

    if user.username == g.user.username:
        return make_error_response("Cannot unfollow yourself.", code=403)

    if user in g.user.following:
        g.user.following.remove(user)
        db.session.commit()

        return make_success_response()

    return make_error_response("You haven't followed this user.", code=400)

# ---- Story routes ------------------------------------------------------------------------------ #

@app.route("/api/story", methods=["POST"])
def new_story():
    """Creates a new story."""

    if g.user is None:
        return make_error_response("Must be logged in to post a new story.", code=401)

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )
    
    try:
        story = Story.new(
            author    = g.user,
            title     = request.json.get("title"),
            summary   = request.json.get("summary", ""),
            thumbnail = request.json.get("thumbnail", Story.DEFAULT_THUMBNAIL_URI)
        )
        return make_success_response(story.to_json(g.user), code=201)
    except ValueError as e:
        errors = str(e).split('\n')
        return make_error_response(*errors, code=400)

@app.route("/api/story/<int:story_id>", methods=["GET"])
def get_story(story_id: int):
    """Returns information regarding a given story."""

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    return make_success_response(story.to_json(g.user, "expand" in request.args))

@app.route("/api/story/<int:story_id>", methods=["PATCH"])
def update_story(story_id: int):
    """Update story information."""
    
    if g.user is None:
        return make_error_response("Must be logged in to update an existing story.", code=401)

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")
    
    if story.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )
    
    is_risque = None
    if "is_risque" in request.json:
        if type(request.json['is_risque']) == bool:
            is_risque = request.json['is_risque'] if g.user.allow_risque else False
        else:
            is_risque = request.json['is_risque']
    
    errors = story.update(
        title       = request.json.get("title"),
        thumbnail   = request.json.get("thumbnail"),
        summary     = request.json.get("summary"),
        private     = request.json.get("private"),
        protected   = request.json.get("protected"),
        can_comment = request.json.get("can_comment"),
        is_risque   = is_risque
    )

    if len(errors) > 0:
        return make_error_response(*errors, code=400)
    
    return make_success_response()

@app.route("/api/story/<int:story_id>", methods=["DELETE"])
def delete_story(story_id: int):
    """Deletes an existing story."""

    if g.user is None:
        return make_error_response("Must be logged in to delete an existing story.", code=401)

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)
    
    db.session.delete(story)
    db.session.commit()

    return make_success_response()

@app.route("/api/story/<int:story_id>/tags", methods=["GET"])
def list_tags(story_id: int):
    """Lists a story's tags."""

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    return make_success_response([ tag.query_name for tag in story.tags ])

@app.route("/api/story/<int:story_id>/tags", methods=["PUT"])
def add_tags(story_id: int):
    """Adds tags to a story."""

    if g.user is None:
        return make_error_response("Must be logged in to add tags to a story.", code=401)

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)

    if type(request.json) != list:
        return make_error_response(
            f"Expected list; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    new_tags = []
    tags = []
    errors = []
    for i in range(len(request.json)):
        try:
            tag_str = request.json[i]
            tag = Tag.get(tag_str)

            if tag is None:
                ttype = "generic"
                if tag_str.startswith('#'):
                    tag_str = tag_str[1:]
                elif ':' in tag_str:
                    ttype, tag_str = tag_str.split(':', 1)
                
                if (ttype not in {"generic", "character", "series"} and
                    (g.user is None or g.user is not None and not g.user.is_moderator)
                ):
                    errors.append(f"Cannot create new tag of type \"{ttype}\".")
                    continue
                    
                tag = Tag.new(ttype, tag_str, False)
                new_tags.append(tag)

            tags.append(tag)
        except ValueError as e:
            prefix = "" if len(request.json) == 1 else f"[{i}]: "
            errors += [ prefix + err for err in str(e).split('\n') ]
    
    if len(errors) > 0:
        if len(new_tags) > 0:
            db.session.rollback()
        return make_error_response(*errors, code=400)

    if len(new_tags) > 0:
        db.session.commit()
    
    for tag in tags:
        if tag not in story.tags:
            story.tags.append(tag)
    db.session.commit()

    return make_success_response()

@app.route("/api/story/<int:story_id>/tags", methods=["DELETE"])
def remove_tags(story_id: int):
    """Removes tags from a story."""

    if g.user is None:
        return make_error_response("Must be logged in to remove tags from a story.", code=401)

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)

    if type(request.json) != list:
        return make_error_response(
            f"Expected list; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    tags: List[Tag] = []
    errors = []
    for i in range(len(request.json)):
        try:
            tag = Tag.get(request.json[i])
            if tag is None:
                errors.append(f"items[{i}]: Tag does not exist.")
            tags.append(tag)
        except ValueError as e:
            errors += [ f"items[{i}]: " + err for err in str(e).split('\n') ]
    
    if len(errors) > 0:
        return make_error_response(*errors, code=400)

    rm_tags = set()
    for tag in tags:
        if tag in story.tags:
            story.tags.remove(tag)

            if len(tag.stories) == 0 and tag.type in {"generic", "character", "series"}:
                rm_tags.add(tag)
    db.session.commit()

    for tag in rm_tags:
        db.session.delete(tag)
    db.session.commit()

    return make_success_response()

@app.route("/api/story/<int:story_id>/favorite", methods=["POST"])
def favorite_story(story_id: int):
    """Favorites a story."""

    if g.user is None:
        return make_error_response("Must be logged in to favorite a story.", code=401)
    
    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id == g.user.id:
        return make_error_response("Cannot favorite your own story.", code=403)

    if story not in g.user.favorite_stories:
        g.user.favorite_stories.append(story)
        db.session.commit()

        return make_success_response()

    return make_error_response("You already favorited this story.", code=400)

@app.route("/api/story/<int:story_id>/favorite", methods=["DELETE"])
def unfavorite_story(story_id: int):
    """Unfavorites a story."""

    if g.user is None:
        return make_error_response("Must be logged in to unfavorite a story.", code=401)
    
    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id == g.user.id:
        return make_error_response("Cannot unfavorite your own story.", code=403)

    if story in g.user.favorite_stories:
        g.user.favorite_stories.remove(story)
        db.session.commit()

        return make_success_response()

    return make_error_response("You haven't favorited this story.", code=400)

@app.route("/api/story/<int:story_id>/follow", methods=["POST"])
def follow_story(story_id: int):
    """Favorites a story."""

    if g.user is None:
        return make_error_response("Must be logged in to follow a story.", code=401)
    
    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id == g.user.id:
        return make_error_response("Cannot follow your own story.", code=403)

    if story not in g.user.followed_stories:
        g.user.followed_stories.append(story)
        db.session.commit()

        return make_success_response()

    return make_error_response("You already followed this story.", code=400)

@app.route("/api/story/<int:story_id>/follow", methods=["DELETE"])
def unfollow_story(story_id: int):
    """Unfavorites a story."""

    if g.user is None:
        return make_error_response("Must be logged in to unfollow a story.", code=401)
    
    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id == g.user.id:
        return make_error_response("Cannot unfollow your own story.", code=403)

    if story in g.user.followed_stories:
        g.user.followed_stories.remove(story)
        db.session.commit()

        return make_success_response()

    return make_error_response("You haven't followed this story.", code=400)

@app.route("/api/story/<int:story_id>/chapters", methods=["POST"])
def new_chapter(story_id: int):
    """Creates a new chapter."""

    if g.user is None:
        return make_error_response("Must be logged in to create a new chapter.", code=401)
    
    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    if story.author_id != g.user.id:
        return make_error_response("Insufficient credentials.", code=401)

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )
    
    try:
        chapter = Chapter.new(
            story        = story,
            name         = request.json.get("name"),
            text         = request.json.get("text", ""),
            author_notes = request.json.get("author_notes")
        )
        return make_success_response(chapter.to_json(g.user), code=201)
    except ValueError as e:
        errors = str(e).split('\n')
        return make_error_response(*errors, code=400)

@app.route("/api/story/<int:story_id>/chapters", methods=["GET"])
def list_chapters(story_id: int):
    """Lists the chapters in a story."""

    story: Optional[Story] = Story.query.get(story_id)
    if story is None or not story.visible(g.user):
        return make_error_response("Invalid story ID.")

    offset = 0
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return make_error_response("'offset' must be an integer.")

    count = 10
    try:
        count = int(request.args.get("count", 10))
    except ValueError:
        return make_error_response("'count' must be an integer.")

    chapters = story.chapters

    return make_success_response([
        chapter.to_json(g.user) for chapter in filter(
            lambda c: c.visible(g.user),
            chapters[offset:count]
        )
    ])
    
# ---- Chapter routes ---------------------------------------------------------------------------- #

@app.route("/api/chapter/<int:chapter_id>", methods=["GET"])
def get_chapter(chapter_id: int):
    """Returns information regarding a given chapter."""

    chapter: Optional[Chapter] = Chapter.query.get(chapter_id)
    if chapter is None or not chapter.visible(g.user):
        return make_error_response("Invalid chapter ID.")
    
    return make_success_response(chapter.to_json(g.user, "expand" in request.args))

@app.route("/api/chapter/<int:chapter_id>", methods=["PATCH"])
def update_chapter(chapter_id: int):
    """Updates a given chapter."""
    
    if g.user is None:
        return make_error_response("Must be logged in to update an existing chapter.", code=401)

    chapter: Optional[Chapter] = Chapter.query.get(chapter_id)
    if chapter is None or not chapter.visible(g.user):
        return make_error_response("Invalid chapter ID.")

    if chapter.story.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    errors = chapter.update(
        name         = request.json.get("name"),
        author_notes = request.json.get("author_notes"),
        text         = request.json.get("text"),
        index        = request.json.get("index"),
        private      = request.json.get("private"),
        protected    = request.json.get("protected")
    )

    if len(errors) > 0:
        return make_error_response(*errors, code=400)
    
    return make_success_response()

@app.route("/api/chapter/<int:chapter_id>", methods=["DELETE"])
def remove_chapter(chapter_id: int):
    """Removes a given chapter."""

    if g.user is None:
        return make_error_response("Must be logged in to delete an existing chapter.", code=401)

    chapter: Optional[Chapter] = Chapter.query.get(chapter_id)
    if chapter is None or not chapter.visible(g.user):
        return make_error_response("Invalid chapter ID.")

    if chapter.story.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)
    
    chapters = chapter.story.chapters[:]
    index = chapter.index
    for ch in chapters[index:]:
        ch.index -= 1

    db.session.delete(chapter)
    db.session.commit()

    return make_success_response()

@app.route("/api/chapter/<int:chapter_id>/comments", methods=["GET"])
def list_chapter_comments(chapter_id: int):
    """Retrieves the comments on a given chapter."""

    chapter: Optional[Chapter] = Chapter.query.get(chapter_id)
    if chapter is None or not chapter.visible(g.user):
        return make_error_response("Invalid chapter ID.")

    offset = 0
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return make_error_response("'offset' must be an integer.")

    count = 10
    try:
        count = int(request.args.get("count", 10))
    except ValueError:
        return make_error_response("'count' must be an integer.")

    before = None
    try:
        before = None if "before" not in request.args else int(request.args["before"])
    except ValueError:
        return make_error_response("'before' must be an integer.")

    comments = [ comment for comment in reversed(chapter.comments) ]

    if before is not None:
        before = from_timestamp(before)
        comments = filter(lambda x: x.posted < before, comments)

    sort_by: str = request.args.get("order", "posted")
    if sort_by == "modified":
        comments = sorted(comments, key=lambda comment: comment.modified)
    elif sort_by != "posted":
        return make_error_response("'order' must be \"posted\" or \"modified\".")

    return make_success_response([
        comment.to_json(g.user) for comment in comments[offset:count]
    ])

@app.route("/api/chapter/<int:chapter_id>/comments", methods=["POST"])
def new_chapter_comment(chapter_id: int):
    """Creates a new chapter comment."""

    if g.user is None:
        return make_error_response("Must be logged in to post a new comment.", code=401)

    chapter: Optional[Chapter] = Chapter.query.get(chapter_id)
    if chapter is None or not chapter.visible(g.user):
        return make_error_response("Invalid chapter ID.")

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    try:
        comment = Comment.new(
            user = g.user,
            text = request.json.get("text"),
            of   = chapter
        )
        return make_success_response(comment.to_json(g.user), code=201)
    except ValueError as e:
        errors = str(e).split('\n')
        return make_error_response(*errors, code=400)

# ---- Comment routes ---------------------------------------------------------------------------- #

@app.route("/api/comment/<int:comment_id>", methods=["GET"])
def get_comment(comment_id: int):
    """Returns information regarding a given comment."""

    comment: Optional[Comment] = Comment.query.get(comment_id)
    if comment is None:
        return make_error_response("Invalid comment ID.")
    
    return make_success_response(comment.to_json(g.user, "expand" in request.args))
    
@app.route("/api/comment/<int:comment_id>", methods=["PATCH"])
def update_comment(comment_id: int):
    """Updates a given comment."""
    
    if g.user is None:
        return make_error_response("Must be logged in to update an existing comment.", code=401)

    comment: Optional[Comment] = Comment.query.get(comment_id)
    if comment is None:
        return make_error_response("Invalid comment ID.")

    if comment.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)

    errors = comment.update(
        text = request.json.get("text")
    )

    if len(errors) > 0:
        return make_error_response(*errors, code=400)
    
    return make_success_response()

@app.route("/api/comment/<int:comment_id>", methods=["DELETE"])
def delete_comment(comment_id: int):
    """Deletes a given comment."""

    if g.user is None:
        return make_error_response("Must be logged in to delete an existing comment.", code=401)

    comment: Optional[Comment] = Comment.query.get(comment_id)
    if comment is None:
        return make_error_response("Invalid comment ID.")

    if comment.author_id != g.user.id and not g.user.is_moderator:
        return make_error_response("Insufficient credentials.", code=401)
    
    db.session.delete(comment)
    db.session.commit()

    return make_success_response()

@app.route("/api/comment/<int:comment_id>/replies", methods=["GET"])
def list_comment_replies(comment_id: int):
    """Retrieves the replies of a comment."""

    comment: Optional[Comment] = Comment.query.get(comment_id)
    if comment is None:
        return make_error_response("Invalid comment ID.")

    offset = 0
    try:
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return make_error_response("'offset' must be an integer.")

    count = 10
    try:
        count = int(request.args.get("count", 10))
    except ValueError:
        return make_error_response("'count' must be an integer.")

    before = None
    try:
        before = None if "before" not in request.args else int(request.args["before"])
    except ValueError:
        return make_error_response("'before' must be an integer.")

    replies = [ reply for reply in reversed(comment.replies) ]

    if before is not None:
        before = from_timestamp(before)
        replies = filter(lambda x: x.posted < before, replies)

    sort_by: str = request.args.get("order", "posted")
    if sort_by == "modified":
        replies = sorted(replies, key=lambda comment: comment.modified)
    elif sort_by != "posted":
        return make_error_response("'order' must be \"posted\" or \"modified\".")

    return make_success_response([
        reply.to_json(g.user, False) for reply in replies[offset:count]
    ])

@app.route("/api/comment/<int:comment_id>/replies", methods=["POST"])
def new_comment_reply(comment_id: int):
    """Creates a new reply to a comment."""
    
    if g.user is None:
        return make_error_response("Must be logged in to post a new comment.", code=401)

    comment: Optional[Comment] = Comment.query.get(comment_id)
    if comment is None:
        return make_error_response("Invalid comment ID.")

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )

    try:
        reply = Comment.new(
            user = g.user,
            text = request.json.get("text"),
            of   = comment
        )
        return make_success_response(reply.to_json(g.user), code=201)
    except ValueError as e:
        errors = str(e).split('\n')
        return make_error_response(*errors, code=400)

# ---- Tag routes -------------------------------------------------------------------------------- #

@app.route("/api/tag", methods=["GET", "POST"])
def tag_search():
    """Conducts a search on existing tags."""

    errors = []
    excludes = set()
    results = []
    count = 25

    if type(request.json) != dict:
        return make_error_response(
            f"Expected object; got {to_jsontype(type(request.json))}.",
            code = 400
        )
    
    if "tag" not in request.json:
        errors.append("Missing required argument 'tag'.")
    elif type(request.json["tag"]) != str:
        errors.append("'tag' must be a string.")

    if "count" in request.json:
        if type(request.json["count"]) != int:
            errors.append("'count' must be an integer.")
        elif request.json["count"] < 1:
            errors.append("'count' must be at least 1.")
        else:
            count = request.json["count"]

    if "exclude" in request.json:
        if type(request.json['exclude']) != list:
            errors.append("'exclude' must be a list.")
        
        try:
            tags = Tag.get(*request.json['exclude'])
            if type(tags) != Tag:
                excludes = set(tags)
            else:
                excludes = { tags }

            if None in excludes:
                excludes.remove(None)
            excludes = set(map(lambda tag: tag.id, excludes))
        except ValueError as e:
            errors += str(e).split('\n')

    if len(errors) > 0:
        return make_error_response(*errors, code=400)

    ttype: Optional[Tag.Type] = None
    search_str: str = request.json["tag"].lower()

    # tag types
    if not search_str.startswith('#') and ':' not in search_str:
        types = { k: search_str in k for k in Tag.tag_types() }
        if any(types.values()):
            results += [
                (item[0], None) for item in filter(lambda x: x[1], types.items())
            ][:count]
            results.sort(key = lambda x: x[0])
    elif search_str.startswith('#'):
        search_str = search_str[1:]
        ttype = Tag.Type.GENERIC
    elif search_str.split(':', 1)[0] not in Tag.tag_types():
        return make_success_response(results)
    else:
        parts = search_str.split(':', 1)
        ttype = Tag.Type.__members__[parts[0].upper()]
        search_str = parts[1]

    query = Tag.query
    
    if len(search_str) > 0:
        query = query.filter(Tag.name.contains(search_str))
    if ttype is not None:
        query = query.filter(Tag._type == ttype)
    if len(excludes) > 0:
        query = query.filter(~Tag.id.in_(excludes))

    query = query.join(
        Tag.stories,
        isouter = True
    ).group_by(
        Tag.id
    ).order_by(
        func.count(Story.id).desc()
    ).distinct(
        Tag.id, func.count(Story.id)
    )
    
    # tag names
    for tag in query.slice(0, max(0, count - len(results))).all():
        results.append((tag.query_name, len(tag.stories)))

    return make_success_response(results)

@app.route("/api/tag/<tag_name>", methods=["GET"])
def tag_listing(tag_name: str):
    """Retrieves a listing for a given tag name."""

    tag: Optional[Tag] = None
    try:
        tag = Tag.get(tag_name)

        if tag is None:
            return make_error_response(f"Tag with name \"{tag_name}\" doesn't exist.", code=400)
    except ValueError as e:
        errors = str(e).split('\n')
        return make_error_response(*errors, code=400)

    return make_success_response(tag.to_json(), code=200)

# ---- Report routes (site moderators only) ------------------------------------------------------ #


# TODO


# == START SERVER ================================================================================ #

if __name__ == "__main__":
    from flask_debugtoolbar import DebugToolbarExtension
    from sys import argv

    from os import system
    system("color")

    from seed import seed_db

    if "--no-debug-toolbar" not in argv:
        debug = DebugToolbarExtension(app)
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

    app.config['SQLALCHEMY_ECHO'] = True
    connect_db(app)

    if "--clear-database" in argv or "--seed-database" in argv:
        db.drop_all()
        db.create_all()

        if "--seed-database" in argv:
            seed_db(db)
    
    app.run()
