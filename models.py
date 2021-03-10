"""Database models."""

# == IMPORTS ===================================================================================== #

# ---- Flask imports ----------------------------------------------------------------------------- #

from flask import Flask

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy, BaseQuery

# ---- Python standard utility types ------------------------------------------------------------- #

import datetime, time
from dateutil.relativedelta import relativedelta

import enum, re

# ---- Explicit typing --------------------------------------------------------------------------- #

from abc import abstractmethod
from typing import *

# ---- Email validation -------------------------------------------------------------------------- #

import email_validator

# ---- Markdown ---------------------------------------------------------------------------------- #

#from markdown_pywasm import MarkdownWASM, ParseFlags # <-- this shit too slow!
#from markdown_wasm import MarkdownWASM, ParseFlags   # <-- this shit don't work!

# == GLOBALS ===================================================================================== #

BCRYPT = Bcrypt()
#MARKDOWN = MarkdownWASM()

db = SQLAlchemy()

def connect_db(app: Flask) -> None:
    """Connects this database to the given Flask application."""

    db.app = app
    db.init_app(app)

def get_current_time() -> datetime.datetime:
    """Retrieves the current UTC time."""

    dt = datetime.datetime.now(datetime.timezone.utc)
    return datetime.datetime(
        year = dt.year,
        month = dt.month,
        day = dt.day,
        hour = dt.hour,
        minute = dt.minute,
        second = dt.second,
        microsecond = (dt.microsecond // 1000) * 1000,
        tzinfo = datetime.timezone.utc
    )

def format_time(dt: datetime.datetime) -> str:
    """Formats a date as a string."""

    return dt.strftime("%Y/%m/%d %I:%M:%S %p UTC")

def to_timestamp(dt: Union[datetime.datetime, datetime.date]) -> int:
    """Converts a datetime object to a JavaScript timestamp."""

    ms = 0 if type(dt) != datetime.datetime else int(dt.microsecond / 1000)
    return (int(time.mktime(dt.timetuple())) * 1000) + ms

def from_timestamp(timestamp: int, date: bool = False) -> Union[datetime.datetime, datetime.date]:
    """Converts a JavaScript timestamp to a datetime object.
    
    Parameters
    ==========
    timestamp: `int`
        A JavaScript timestamp.

    date: `bool` = `False`
        If True, returns a datetime. If False, returns a date.    
    """

    dt = datetime.datetime.fromtimestamp(int(timestamp / 1000), datetime.timezone.utc)
    return datetime.datetime(
        year = dt.year,
        month = dt.month,
        day = dt.day,
        hour = dt.hour,
        minute = dt.minute,
        second = dt.second,
        microsecond = (timestamp % 1000) * 1000,
        tzinfo = datetime.timezone.utc
    ) if not date else datetime.date(
        dt.year, dt.month, dt.day
    )

def reduce_whitespace(string: str) -> str:
    """Reduces whitespace to single spaces between words."""

    return ' '.join(filter(lambda x: len(x) > 0, string.strip().split(' ')))

def filter_text(string: str) -> str:
    """Filters out Markdown elements for search purposes."""

    return re.sub(r"^#{1,6} (.*?)$", r"\g<1>",                  # heading match
        re.sub(r"^ *[>*-][ >*-]*(.*)$", r"\g<1>",               # blockquote & bullet match
            re.sub(r"^ *([_*-])(?: *\1){2,}$", "",              # hr match
                re.sub(r"\$\{(?:([0-9A-Z \-_]+)|\/?)\}", "",    # span match
                    re.sub("\[(.*)\]\(.*\)", r"\g<1>",          # link match
                        re.sub(r"!\[.*\]\(.*\)", "",            # image match
                            string,
                            flags = re.U
                        ),
                        flags = re.U
                    ),
                    flags = re.U | re.I
                ),
                flags = re.U | re.M
            ),
            flags = re.U | re.M
        ),
        flags = re.U | re.M
    ).strip()

# == INTERFACES ================================================================================== #

JSONType = Union[int, float, bool, None, Collection["JSONType"], Mapping[str, "JSONType"]]

class IJsonableModel(db.Model):
    """Interface specifying a database model that can be serialized into a JSON value."""

    __abstract__ = True

    id: int = db.Column(db.Integer, primary_key=True)

    @abstractmethod
    def to_json(self,
        user: Optional["User"],
        expand: bool = False,
        expanded: Set[Union["IJsonableModel", type]] = set()
    ) -> JSONType:
        """Converts the given object into a dictionary that can be JSONified.
        
        Parameters
        ==========
        user: `Optional[User]` = `None`
            User viewing this data. Used to conditionally include data based on who
            is reading from it.

        expand: `bool` = `False`
            Whether to expand other data types included within the 

        expanded: `Set[Union[IJsonableModel, type]]` = `set()`
            A collection of objects that have already been expanded. Used to avoid recursive
            expansions.

        Returns
        =======
        `JSONType`
            A type that can be directly serialized into a JSON string.
        """

        ...

    @abstractmethod
    def unexpanded(self) -> JSONType:
        return self.id

    def expand(self,
        user: Optional["User"],
        expand: bool,
        expanded: Set[Union["IJsonableModel", type]] = set()
    ) -> JSONType:
        """Conditionally expands this object based on `to_json` conditions.

        Parameters
        ==========
        user: `Optional[User]` = `None`
            User viewing this data. Used to conditionally include data based on who
            is reading from it.

        expand: `bool` = `False`
            Whether to expand other data types included within the 

        expanded: `Set[Union[IJsonableModel, type]]` = `set()`
            A collection of objects that have already been expanded. Used to avoid recursive
            expansions.

        Returns
        =======
        `JSONType`
            A type that can be directly serialized into a JSON string.
        """

        if self in expanded or type(self) in expanded or not expand:
            return self.unexpanded()

        expanded.add(self)
        return self.to_json(user, False, expanded)

class IMarkdownModel(IJsonableModel):
    """Interface specifying how a database model stores Markdown & HTML content."""

    __abstract__ = True

    RE1 = re.compile(r"\<([A-Z][A-Z0-9]*)\b[^>]*>(.*?)?(\<\/\1>)?", re.IGNORECASE)
    RE2 = re.compile(r"\$\{([0-9A-Z \-_]+)?\}", re.IGNORECASE)

    text: str = db.Column(db.Text, nullable=False)
    _html: Optional[str] = db.Column(db.Text)

    _html_dirty: bool = db.Column(db.Boolean, nullable=False, default=True)

    @classmethod
    def format_markdown(cls, markdown: str) -> str:
        """"Converts the website's markdown dialect to common Markdown."""

        return cls.RE2.sub(
            r'<span class="\g<1>">',
            cls.RE1.sub(r"\\<\g<1>\\>\g<2>\g<3>", markdown)
        ).replace(
            '${/}', "</span>"
        ).replace(
            "`", "\\`"
        ).replace(
            "~", "\\~"
        )

    # @classmethod
    # def parse(cls, markdown: str) -> str:
    #     """"Converts Markdown to HTML using the site's restrictions as seen in write.js."""

    #     return MARKDOWN.parse_utf8(
    #         cls.format_markdown(markdown),
    #         ParseFlags(
    #             ParseFlags.NO_INDENTED_CODE_BLOCKS |
    #             ParseFlags.COLLAPSE_WHITESPACE |
    #             ParseFlags.STRIKETHROUGH |
    #             ParseFlags.UNDERLINE
    #         )
    #     )

    # @property
    # def html(self) -> str:
    #     """Retrieves this model's text content as HTML."""

    #     if self._html_dirty:
    #         self._html = self.parse(self.text)
    #         self._html_dirty = False

    #         db.session.commit()

    #     return self._html

# == DATABASE MODELS ============================================================================= #

class RefImage(db.Model):
    """A database image."""

    __tablename__ = "images"

    id: int = db.Column(db.Integer, primary_key=True)

    _url: Optional[str] = db.Column(db.String, index=True)

    data: Optional[bytes] = db.Column(db.LargeBinary)
    content_type: Optional[str] = db.Column(db.String)

    @property
    def url(self) -> str:
        """Retrieves the URL to get this image."""

        return self._url if self._url is not None else f"/image/{self.id}"

class User(IJsonableModel):
    """A `fictionsource` user."""

    class Flags(enum.IntFlag):
        """Enumeration of user flags.
        
        Flags
        =====
        `ALLOW_RISQUE`
            Signifies that the user can see risque content.
        
        Enumerators
        ===========
        `DEFAULT`
            The default user flags.
        """

        ALLOW_RISQUE = 0b0001

        DEFAULT = 0

    __tablename__ = "users"

    DEFAULT_IMAGE_URI = "/static/images/users/default0.png"

    USERNAME_LENGTH = 32

    username: str = db.Column(db.String(USERNAME_LENGTH),
        nullable = False,
        unique   = True
    )

    password: str = db.Column(db.Text,
        nullable = False
    )

    birthdate: datetime.date = db.Column(db.Date,
        nullable = False
    )

    joined: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    email: str = db.Column(db.Text,
        nullable = False
    )

    image_id: int = db.Column(db.Integer,
        db.ForeignKey("images.id"),
        nullable = False,
        default  = 1
    )
    
    description: Optional[str] = db.Column(db.Text)

    flags: Flags = db.Column(db.Integer,
        nullable = False,
        default  = Flags.DEFAULT
    )

    is_moderator: bool = db.Column(db.Boolean,
        nullable = False,
        default  = False
    )

    image: RefImage = db.relationship("RefImage",
        primaryjoin = "(RefImage.id == User.image_id)",
        cascade     = "all,delete",
        uselist     = False
    )

    stories: List["Story"] = db.relationship("Story",
        primaryjoin = "(Story.author_id == User.id)",
        backref     = db.backref("author", uselist=False),
        cascade     = "all,delete",
        order_by    = "Story.modified"
    )

    comments: List["Comment"] = db.relationship("Comment",
        primaryjoin = "(Comment.author_id == User.id)",
        backref     = db.backref("author", uselist=False),
        cascade     = "all,delete",
        order_by    = "Comment.posted"
    )

    following: List["User"] = db.relationship("User",
        secondary     = "followed_users",
        primaryjoin   = "(User.id == FollowingUser.follower_id)",
        secondaryjoin = "(User.id == FollowingUser.following_id)"
    )

    followed_by: List["User"] = db.relationship("User",
        secondary     = "followed_users",
        primaryjoin   = "(User.id == FollowingUser.following_id)",
        secondaryjoin = "(User.id == FollowingUser.follower_id)"
    )

    reports: List["Report"] = db.relationship("Report",
        secondary = "user_reports",
        cascade   = "all,delete",
        backref   = db.backref("user", uselist=False)
    )

    favorite_stories: List["Story"]
    followed_stories: List["Story"]

    def unexpanded(self) -> JSONType:
        return self.username

    def to_json(self,
        user: Optional["User"] = None,
        expand: bool = False,
        expanded: Set[Union[IJsonableModel, type]] = set()
    ) -> JSONType:
        """Converts this User into a dictionary that can be JSONified."""

        expanded.add(self)

        ignore_risque = user.allow_risque if user is not None else False

        d = {
            "username": self.username,
            "birthdate": to_timestamp(self.birthdate),
            "joined": to_timestamp(self.joined),
            "image": self.image.url,
            "description": self.description,

            "is_moderator": self.is_moderator,

            "favorite_stories": [
                story.expand(user, expand, expanded)
                for story in filter(
                    lambda s: s.visible(ignore_risque=ignore_risque),
                    self.favorite_stories
                )
            ],
            "followed_stories": [
                story.expand(user, expand, expanded)
                for story in filter(
                    lambda s: s.visible(ignore_risque=ignore_risque),
                    self.followed_stories
                )
            ],

            "following": [
                u.expand(user, expand, expanded)
                for u in self.following
            ],
            "followed_by": [
                u.expand(user, expand, expanded)
                for u in self.followed_by
            ],

            "stories": [
                story.expand(user, expand, expanded)
                for story in filter(
                    lambda story: story.visible(user, ignore_risque=ignore_risque),
                    reversed(self.stories)
                )
            ]
        }

        if user is not None and user.is_moderator:
            d["reports"] = [
                report.expand(user, expand, expanded)
                for report in self.reports
            ]
        if (user is not None and (user.is_moderator or user.id == self.id)):
            d["comments"] = [
                comment.expand(user, expand, expanded)
                for comment in self.comments
            ]
            d["allow_risque"] = self.allow_risque

        return d

    def update(self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        email: Optional[str] = None,
        image: Optional[str] = None,
        description: Optional[str] = None,
        allow_risque: Optional[bool] = None
    ) -> List[str]:
        """Updates modifiable user information.
        
        Parameters
        ==========
        username: `Optional[str]`

        password: `Optional[str]`

        email: `Optional[str]`

        image: `Optional[str]`

        description: `Optional[str]`

        allow_risque: `Optional[bool]`

        Returns
        =======
        `List[str]`
            List of errors with the given parameters.
        """

        errors = []
        modified = False
        new_image: Optional[RefImage] = None

        if username is not None and username != self.username:
            if type(username) != str:
                errors.append("'username' must be a string.")
            elif len(username) > self.USERNAME_LENGTH:
                errors.append(
                    f"'username' cannot be larger than {self.USERNAME_LENGTH} characters in length."
                )
            elif len(username) < 1:
                errors.append("'username' must be at least 1 character in length.")
            elif not self.is_valid_username(username):
                errors.append("Invalid username.")
            elif User.query.filter_by(username=username).first() is not None:
                errors.append(f"Username '{username}' already taken.")
            else:
                self.username = username
                modified = True

        if password is not None:
            if type(password) != str:
                errors.append("'password' must be a string.")
            elif len(password) < 6:
                errors.append("'password' must be at least 6 characters in length.")
            elif not BCRYPT.check_password_hash(self.password, password):
                self.password = BCRYPT.generate_password_hash(password).decode('UTF-8')
                modified = True

        if email is not None:
            if type(email) != str:
                errors.append("'email' must be a string.")
            elif email != self.email:
                try:
                    email_validator.validate_email(email)
                    
                    self.email = email
                    modified = True
                except email_validator.EmailNotValidError as e:
                    errors.append(str(e))

        if image is not None:
            if type(image) != str:
                errors.append("'image' must be a string.")
            elif image != self.image.url:
                if len(image) == 0:
                    self.image_id = 1
                elif re.match(r"/image/([0-9]+)", image) is not None:
                    self.image_id = int(image[7:])
                else:
                    img = RefImage.query.filter_by(_url=image).first()
                    if img is not None:
                        self.image_id = img.id
                    else:
                        new_image = RefImage(_url=image)
                modified = True

        if description is not None:
            if type(description) != str:
                errors.append("'description' must be a string.")
            else:
                description = reduce_whitespace(description)

                if description != self.description:
                    if description == "":
                        self.description = None
                    else:
                        self.description = description
                    modified = True

        if allow_risque is not None:
            if type(allow_risque) != bool:
                errors.append("'allow_risque' must be a boolean.")
            elif allow_risque and not self.is_18plus:
                errors.append("Must be at least 18 years of age to change this setting.")
            elif allow_risque != self.allow_risque:
                self.allow_risque = allow_risque
                modified = True

        if modified and len(errors) == 0:
            if new_image is not None:
                db.session.add(new_image)
                db.session.commit()
                self.image_id = new_image.id

            db.session.commit()

        return errors

    @property
    def is_18plus(self) -> bool:
        """Returns whether the given user can alter their allow_risque setting."""

        return datetime.date.today() + relativedelta(years=-18) >= self.birthdate

    @property
    def allow_risque(self) -> bool:
        """Checks whether this user allows for risque content to be shown."""

        return not not (self.flags & self.Flags.ALLOW_RISQUE)

    @allow_risque.setter
    def allow_risque(self, value: bool):
        if value:
            self.flags |= self.Flags.ALLOW_RISQUE
        else:
            self.flags ^= self.Flags.ALLOW_RISQUE

    def visible_stories(self, user: Optional["User"] = None) -> BaseQuery:
        """Returns all of a user's publically visible stories as an SQLAlchemy query.
        
        Parameters
        ==========
        user: `Optional[User]` = `None`
            The user looking at self's stories.

        Returns
        =======
            An SQLAlchemy Query.
        """
        
        query: BaseQuery = Story.query.filter(
            Story.author_id == self.id
        ).filter(
            Story.flags.op('&')(Story.Flags.PRIVATE | Story.Flags.PROTECTED) == 0
        )

        if user is None or not user.allow_risque:
            return query.filter(Story.flags.op('&')(Story.Flags.IS_RISQUE) == 0)
        else:
            return query

    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional["User"]:
        """Finds a user with the given username & password.

        Parameters
        ==========
        username: `str`
            Name of the user to log in to.

        password: `str`
            Password to try to log in.

        Returns
        =======
        `Optional[User]`
            User with the given username if the provided credentials match; None otherwise.
        """

        user: Optional[User] = cls.query.filter_by(username=username).first()

        if user is not None and BCRYPT.check_password_hash(user.password, password):
            return user

        return None

    @classmethod
    def register(cls,
        username: str,
        password: str,
        email: str,
        birthdate: datetime.date
    ) -> "User":
        """Registers a new user with the given credentials.

        Parameters
        ==========
        username: `str`
            Name of the new User.

        password: `str`
            The user's password for logging in.

        email: `str`
            The user's email address.

        birthdate: `datetime.date`
            The user's date of birth.

        Returns
        =======
        `User`
            A new user with the provided username
        """

        errors = []
        
        if len(username) > cls.USERNAME_LENGTH:
            errors.append(f"'username' cannot be longer than {cls.USERNAME_LENGTH} characters.")
        elif len(username) < 1:
            errors.append("'username' must be at least 1 character long.")
        elif not cls.is_valid_username(username):
            errors.append("Invalid username.")
        elif cls.query.filter_by(username=username).first() is not None:
            errors.append("Username already taken.")

        if len(password) < 6:
            errors.append("'password' must be at least 6 characters long.")

        if birthdate > datetime.date.today() + relativedelta(years=-13):
            errors.append("Must be at least 13 years of age to register.")
        elif birthdate < datetime.date(year=1900, month=1, day=1):
            errors.append("Invalid birthdate.")

        try:
            email_validator.validate_email(email)
        except email_validator.EmailNotValidError:
            errors.append("Invalid email.")
        
        if len(errors) > 0:
            raise ValueError('\n'.join(errors))

        hashed_pwd = BCRYPT.generate_password_hash(password).decode('utf-8')

        user = cls(
            username  = username,
            password  = hashed_pwd,
            email     = email,
            birthdate = birthdate,
            joined    = get_current_time()
        )

        db.session.add(user)
        db.session.commit()
        
        return user

    @classmethod
    def is_valid_username(cls, username: str) -> bool:
        """Checks whether a given username is valid."""

        if len(username) > cls.USERNAME_LENGTH or len(username) < 1:
            return False

        invalid_chars = { x for x in range(0x30) }
        invalid_chars |= {
            0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40,
            0x5b, 0x5c, 0x5d, 0x5e, 0x60, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0xa0,
            0x1680, 0x180e, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005,
            0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x200b, 0x200c, 0x200d,
            0x2028, 0x2029, 0x2060, 0x202f, 0x205f, 0x3000, 0xfeff
        }

        for char in invalid_chars:
            if chr(char) in username:
                return False
        
        return True

    def __repr__(self) -> str:
        """String representation of a given user."""

        return "{" + f"ID: {self.id}; username: {self.username}" + "}"

class Tag(IJsonableModel):
    """String that groups related content together based on common traits."""

    class Type(enum.IntEnum):
        """Enumeration of tag types.

        Enumerators
        ===========
        
        `GENERIC`: tag has no special meaning
        
        `GENRE`: tag denotes a genre (e.g. action, psychothriller)

        `CATEGORY`: tag denotes a general category
        
        `CHARACTER`: tag denotes a character

        `SERIES`: tag denotes a continuity, fandom, or series
        """

        GENERIC   = 0
        GENRE     = 1
        CATEGORY  = 2
        CHARACTER = 3
        SERIES    = 4

    NAME_MIN_LENGTH = 3
    NAME_LENGTH = 96

    __tablename__ = "tags"

    id: int = db.Column(db.Integer,
        primary_key = True
    )

    _type: Type = db.Column(db.Integer,
        nullable = False,
        default  = Type.GENERIC
    )

    name: str = db.Column(db.String(NAME_LENGTH),
        nullable = False
    )

    stories: List["Story"] = db.relationship("Story", secondary="story_tags")

    def to_json(self,
        user: Optional["User"] = None,
        expand: bool = False,
        expanded: Set[Union[IJsonableModel, type]] = set()
    ) -> JSONType:
        """Converts this Tag into a dictionary that can be JSONified."""

        ignore_risque = user.allow_risque if user is not None else False

        return {
            "name": self.name,
            "query_name": self.query_name,
            "type": self.type,
            "stories": [
                story.expand(user, expand, expanded)
                for story in filter(
                    lambda story: story.visible(ignore_risque=ignore_risque),
                    self.stories
                )
            ]
        }

    @property
    def query_name(self) -> str:
        """Retrieves the queriable name of this tag."""

        if self._type == self.Type.GENERIC:
            return '#' + self.name
        else:
            return f"{self.type}:{self.name}"

    @property
    def url_safe_query_name(self) -> str:
        return self.query_name.replace('#', "%23")

    @property
    def type(self) -> str:
        """Returns the tag type as a string."""

        return self.Type(self._type).name.lower()

    @classmethod
    def get(cls, *query_names: str) -> Union[Optional["Tag"], Collection["Tag"]]:
        """Retrieves a tag given a query name if it exists."""

        tags = []
        errors = []

        for name in query_names:
            ttype = None
            if name.startswith('#'):
                name = name[1:]
                ttype = "generic"
            elif ':' in name:
                ttype, name = name.split(':', 1)
            else:
                errors.append("No tag type provided.")
            
            if ttype is not None and not cls.is_valid_type(ttype):
                errors.append(f"Invalid tag type \"{ttype}\".")
            elif ttype is not None:
                ttype = cls.Type.__members__[ttype.upper()]
            else:
                ttype = cls.Type.GENERIC
            
            if len(name) < cls.NAME_MIN_LENGTH:
                errors.append(f"Tag name must be at least {cls.NAME_MIN_LENGTH} characters long.")
            elif len(name) > cls.NAME_LENGTH:
                errors.append(
                    f"Tag name must not be greater than {cls.NAME_LENGTH} characters in length."
                )
            elif not cls.is_valid_name(name):
                errors.append(f"Invalid tag name \"{name}\".")

            if len(errors) > 0:
                raise ValueError('\n'.join(errors))

            tags.append(cls.query.filter_by(_type=ttype, name=name).first())

        return tags[0] if len(query_names) == 1 else tags
    
    @classmethod
    def new(cls, ttype: str, name: str, commit: bool = True) -> "Tag":
        """Creates a new tag.
        
        Parameters
        ==========
        ttype: `str`
            A tag type.

        name: `str`
            The tag's name.

        commit: `bool` = `True`
            Whether to immediately add the new tag to the database or not.
        """

        errors = []
        if type(ttype) != str:
            errors.append("'type' must be a string.")
        elif not cls.is_valid_type(ttype):
            errors.append("Invalid tag type.")
        else:
            ttype = cls.Type.__members__[ttype.upper()]
        
        if type(name) != str:
            errors.append("'name' must be a string.")
        elif not cls.is_valid_name(name):
            errors.append("Invalid tag name.")
        
        if len(errors) > 0:
            raise ValueError('\n'.join(errors))
        elif Tag.query.filter_by(_type=ttype, name=name).first() is not None:
            raise ValueError("Tag already exists.")
    
        tag = cls(_type=ttype, name=name)
        db.session.add(tag)

        if commit:
            db.session.commit()

        return tag

    @classmethod
    def tag_types(cls) -> Container[str]:
        """Returns a container of strings corresponding to valid tage type names."""

        return map(lambda x: x.lower(), cls.Type.__members__.keys())

    @classmethod
    def is_valid_type(cls, type: str) -> bool:
        """Checks if a tag type is valid."""

        return type in cls.tag_types()

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """Checks if a tag name is valid."""

        if len(name) > cls.NAME_LENGTH or len(name) < cls.NAME_MIN_LENGTH:
            return False

        # names cannot contain whitespace, control chars, or certain other characters:
        invalid_chars = { x for x in range(0x30) }
        invalid_chars |= {
            0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40, 0x5b, 0x5c, 0x5d, 0x5e, 0x60,
            0x1680, 0x180e, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005,
            0x2006, 0x2007, 0x2008, 0x2009, 0x200a, 0x200b, 0x200c, 0x200d,
            0x2028, 0x2029, 0x2060, 0x202f, 0x205f, 0x3000, 0xfeff
        }
        for char in invalid_chars:
            if chr(char) in name:
                return False

        return True

    def __repr__(self):
        return self.query_name

class Story(IJsonableModel):
    """A work of fiction posted by a user."""

    class Flags(enum.IntFlag):
        """Enumeration of story flags.
        
        Flags
        =====
        `PRIVATE`
            The story can only be viewed by the author.
        
        `PROTECTED`
            The story can only be viewed by specific users.

        `CAN_COMMENT`
            Other users can comment on this story's chapters.

        `IS_RISQUE`
            The story contains risque content.
        
        Enumerators
        ===========
        `DEFAULT`
            The default story flags are for a private story & allows comments upon public release.
        """

        PRIVATE     =   0b0001
        PROTECTED   =   0b0010
        CAN_COMMENT =   0b0100
        IS_RISQUE   =   0b1000

        DEFAULT = PRIVATE | CAN_COMMENT

    __tablename__ = "stories"

    DEFAULT_THUMBNAIL_URI = "/static/images/thumbnails/default0.png"

    author_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        nullable = False
    )

    title: str = db.Column(db.Text,
        nullable = False,
        index    = True
    )

    thumbnail_id: int = db.Column(db.Integer,
        db.ForeignKey("images.id"),
        nullable = False,
        default  = 2
    )

    flags: Flags = db.Column(db.Integer,
        nullable = False,
        default = Flags.DEFAULT
    )

    summary: str = db.Column(db.Text,
        nullable = False
    )

    posted: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    modified: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    thumbnail: RefImage = db.relationship("RefImage",
        primaryjoin = "(RefImage.id == Story.thumbnail_id)",
        cascade     = "all,delete",
        uselist     = False
    )

    chapters: List["Chapter"] = db.relationship("Chapter",
        primaryjoin = "(Story.id == Chapter.story_id)",
        backref     = db.backref("story", uselist=False),
        cascade     = "all,delete",
        order_by    = "Chapter.index"
    )

    tags: List[Tag] = db.relationship("Tag",
        secondary = "story_tags"
    )

    favorited_by: List["User"] = db.relationship("User",
        secondary = "favorite_stories",
        backref   = "favorite_stories"
    )

    followed_by: List["User"] = db.relationship("User",
        secondary = "followed_stories",
        backref   = "followed_stories"
    )

    reports: List["Report"] = db.relationship("Report",
        secondary = "story_reports",
        cascade   = "all,delete",
        backref   = db.backref("story", uselist=False)
    )

    author: User

    def to_json(self,
        user: Optional["User"] = None,
        expand: bool = False,
        expanded: Set[Union[IJsonableModel, type]] = set()
    ) -> JSONType:
        """Converts this Story into a dictionary that can be JSONified."""

        expanded.add(self)

        d = {
            "id": self.id,
            "author": self.author.username,
            "title": self.title,
            "summary": self.summary,
            "thumbnail": self.thumbnail.url,

            "chapters": [
                chapter.expand(user, expand, expanded)
                for chapter in filter(
                    lambda chapter: chapter.visible(user),
                    self.chapters
                )
            ],

            "tags": [ tag.query_name for tag in self.tags],

            "posted": to_timestamp(self.posted),
            "modified": to_timestamp(self.modified),
            
            "can_comment": self.can_comment,

            "favorited_by": [
                u.expand(user, expand, expanded)
                for u in self.favorited_by
            ],
            "num_favorites": self.favorites,

            "followed_by": [
                u.expand(user, expand, expanded)
                for u in self.followed_by
            ],
            "num_follows": self.follows,
            "is_risque": self.is_risque
        }

        if user is not None:
            if user.is_moderator:
                d["reports"] = [
                    report.expand(user, expand, expanded)
                    for report in self.reports
                ]
            if user.id == self.author_id:
                d["private"] = self.private
                d["protected"] = self.protected

        return d

    def update(self,
        title: Optional[str] = None,
        thumbnail: Optional[str] = None,
        summary: Optional[str] = None,
        private: Optional[bool] = None,
        protected: Optional[bool] = None,
        can_comment: Optional[bool] = None,
        is_risque: Optional[bool] = None
    ) -> List[str]:
        """Updates modifiable story information.
        
        Parameters
        ==========
        title: `Optional[str]`

        thumbnail: `Optional[str]`

        summary: `Optional[str]`

        private: `Optional[bool]`

        protected: `Optional[bool]`

        can_comment: `Optional[bool]`

        is_risque: `Optional[bool]`

        Returns
        =======
        `List[str]`
            List of errors with given parameters. Empty if successful.
        """

        errors = []
        modified = False
        update_timestamp = False
        new_image: Optional[RefImage] = None

        if title is not None:
            if type(title) != str:
                errors.append("'title' must be a string.")
            elif len(title.strip()) == 0:
                errors.append("'title' must contain at least one non-whitespace character.") 
            else:
                title = reduce_whitespace(title)
                if title != self.title:
                    self.title = title
                    update_timestamp = True

        if thumbnail is not None:
            if type(thumbnail) != str:
                errors.append("'thumbnail' must be a string.")
            elif thumbnail != self.thumbnail.url:
                if len(thumbnail) == 0:
                    self.thumbnail_id = 2
                elif re.match(r"/image/([0-9]+)", thumbnail) is not None:
                    self.thumbnail_id = int(thumbnail[7:])
                else:
                    img = RefImage.query.filter_by(_url=thumbnail).first()
                    if img is not None:
                        self.thumbnail_id = img.id
                    else:
                        new_image = RefImage(_url=thumbnail)
                update_timestamp = True

        if summary is not None:
            if type(summary) != str:
                errors.append("'summary' must be a string.")
            else:
                summary = reduce_whitespace(summary)
                if summary != self.summary:
                    self.summary = summary
                    update_timestamp = True
        
        if can_comment is not None:
            if type(can_comment) != bool:
                errors.append("'can_comment' must be a boolean.")
            elif can_comment != self.can_comment:
                self.can_comment = can_comment
                modified = True
        
        if private is not None:
            if type(private) != bool:
                errors.append("'private' must be a boolean.")
            elif private != self.private:
                if private or (
                    not private and
                    len(self.chapters) > 0 and
                    any(map(lambda c: c.self_visible(), self.chapters))
                ): # only allow public viewing if there's a chapter containing text
                    self.private = private
                    modified = True
        
        if protected is not None:
            if type(protected) != bool:
                errors.append("'protected' must be a boolean.")
            elif protected != self.protected:
                self.protected = protected
                modified = True
        
        if is_risque is not None:
            if type(is_risque) != bool:
                errors.append("'is_risque' must be a boolean.")
            elif is_risque != self.is_risque:
                self.is_risque = is_risque
                modified = True

        if len(errors) == 0 and modified or update_timestamp:
            if update_timestamp:
                self.modified = get_current_time()
            
            if new_image is not None:
                db.session.add(new_image)
                db.session.commit()
                self.thumbnail = new_image
            
            db.session.commit()

        return errors

    def visible(self,
        user: Optional[User] = None,
        ignore_risque: bool = False
    ) -> bool:
        """Retrieves whether this story is visible to a given user or in
        general given the user.
        
        Parameters
        ==========
        user: `Optional[User]` = `None`

        ignore_risque: `bool` = `False`
            Whether to ignore if the risque flag affects visibility.
        
        Returns
        =======
        `bool`
            True if visible; False otherwise.
        """

        if user is not None:
            # user's stories are always visible
            if user.id == self.author_id:
                return not (self.is_risque and not user.allow_risque and not ignore_risque)
            
            # TODO: other user can see another's story if protected & given read access

            return not (self.private or self.protected or
                (self.is_risque and not user.allow_risque and not ignore_risque)
            )

        return not (self.private or self.protected or
            (self.is_risque and not ignore_risque)
        )

    @property
    def favorites(self) -> int:
        """Retrieves how many users have favorited this story."""

        return len(self.favorited_by)

    @property
    def follows(self) -> int:
        """Retrieves how many users have followed this story."""

        return len(self.followed_by)

    @property
    def can_comment(self) -> bool:
        """Retrieves whether comments can be left on this story."""

        return not not (self.flags & self.Flags.CAN_COMMENT)
    
    @can_comment.setter
    def can_comment(self, value: bool):
        if value:
            self.flags |= self.Flags.CAN_COMMENT
        else:
            self.flags ^= self.Flags.CAN_COMMENT

    @property
    def private(self) -> bool:
        """Retrieves whether this story is viewable only by the author."""

        return not not (self.flags & self.Flags.PRIVATE)
    
    @private.setter
    def private(self, value: bool):
        if value:
            self.flags |= self.Flags.PRIVATE
        else:
            self.flags ^= self.Flags.PRIVATE

    @property
    def protected(self) -> bool:
        """Retrieves whether this story is viewable by specific users."""

        return not not (self.flags & self.Flags.PROTECTED)
    
    @protected.setter
    def protected(self, value: bool):
        if value:
            self.flags |= self.Flags.PROTECTED
        else:
            self.flags ^= self.Flags.PROTECTED

    @property
    def is_risque(self) -> bool:
        """Retrieves whether this story contains NSFW or otherwise risque content."""

        return not not (self.flags & self.Flags.IS_RISQUE)
    
    @is_risque.setter
    def is_risque(self, value: bool):
        if value:
            self.flags |= self.Flags.IS_RISQUE
        else:
            self.flags ^= self.Flags.IS_RISQUE

    @classmethod
    def new(cls,
        author: User,
        title: str,
        summary: str = "",
        commit: bool = True
    ) -> "Story":
        """Creates a new story and adds it to the database.
        
        Parameters
        ==========
        author: `User`
            The person creating the story.

        title: `str`
            The title of the story.

        summary: `str` = `""`
            The story's summary.

        commit: `bool` = `True`
            Whether to commit the new story to the database immediately.

        Returns
        =======
        `Story`
            A newly created story.
        """

        errors = []

        if type(summary) != str:
            errors.append("'summary' must be a string.")
        
        if title is None:
            errors.append("Missing parameter 'title'.")
        elif type(title) != str:
            errors.append("'title' must be a string.")
        elif len(title.strip()) == 0:
            errors.append("'title' must contain at least one non-whitespace character.")

        if len(errors) > 0:
            raise ValueError("\n".join(errors))

        current_time = get_current_time()

        story = cls(
            author_id = author.id,
            title     = reduce_whitespace(title),
            summary   = reduce_whitespace(summary),
            posted    = current_time,
            modified  = current_time
        )
        
        db.session.add(story)
        if commit:
            db.session.commit()

        return story

    @classmethod
    def visible_stories(cls, user: Optional[User] = None) -> BaseQuery:
        """Returns all publically visible stories as an SQLAlchemy query.."""
        
        query: BaseQuery = cls.query.filter(
            cls.flags.op('&')(cls.Flags.PRIVATE | cls.Flags.PROTECTED) == 0
        )
        if user is None or not user.allow_risque:
            query = query.filter(cls.flags.op('&')(cls.Flags.IS_RISQUE) == 0)

        return query

class StoryTag(db.Model):
    """Tags affiliated with a story."""

    __tablename__ = "story_tags"

    story_id: int = db.Column(db.Integer,
        db.ForeignKey('stories.id'),
        primary_key = True
    )

    tag_id: int = db.Column(db.Integer,
        db.ForeignKey('tags.id'),
        primary_key = True
    )

class Chapter(IMarkdownModel):
    """A chapter/section of a story."""

    class Flags(enum.IntFlag):
        """Enumeration of chapter flags.
        
        Values
        ======
        `PRIVATE`
            The chapter can only be viewed by the story's author.

        `PROTECTED`
            The chapter can only be viewed by specific users.
        
        Enumerators
        ===========
        `DEFAULT`
            The default chapter flags create a private chapter.
        """

        PRIVATE   =     0b0001
        PROTECTED =     0b0010

        DEFAULT = PRIVATE

    __tablename__ = "chapters"

    story_id: int = db.Column(db.Integer,
        db.ForeignKey('stories.id'),
        nullable = False
    )

    name: Optional[str] = db.Column(db.Text)

    author_notes: Optional[str] = db.Column(db.Text)

    index: int = db.Column(db.Integer,
        nullable = False,
        default  = 0
    )

    flags: Flags = db.Column(db.Integer,
        nullable = False,
        default  = Flags.DEFAULT
    )

    posted: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    modified: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    comments: List["Comment"] = db.relationship("Comment",
        secondary = "chapter_comments",
        backref   = db.backref("of_chapter", uselist=False),
        cascade   = "all,delete",
        order_by  = "Comment.posted"
    )

    reports: List["Report"] = db.relationship("Report",
        secondary = "chapter_reports",
        cascade   = "all,delete",
        backref   = db.backref("chapter", uselist=False)
    )

    story: Story

    @property
    def previous(self) -> Optional["Chapter"]:
        """Retrieves the previous visible chapter in the story."""

        if not self.visible(ignore_risque=True):
            return None

        lst = [
            chapter for chapter in filter(
                lambda x: x.visible(ignore_risque=True),
                self.story.chapters
            )
        ]
        
        if self.number == 1:
            return None
        return lst[self.number - 2]

    @property
    def next(self) -> Optional["Chapter"]:
        """Retrieves the next visible chapter in the story."""

        if not self.visible(ignore_risque=True):
            return None

        lst = [
            chapter for chapter in filter(
                lambda x: x.visible(ignore_risque=True),
                self.story.chapters
            )
        ]
        
        if self.number == len(lst):
            return None
        return lst[self.number]

    @property
    def number(self) -> Optional[int]:
        """Retrieves the visible chapter number."""

        if not self.visible(ignore_risque=True):
            return None
        else:
            return [
                chapter for chapter in filter(
                    lambda x: x.visible(ignore_risque=True),
                    self.story.chapters
                )
            ].index(self) + 1

    def to_json(self,
        user: Optional["User"] = None,
        expand: bool = False,
        expanded: Set[Union[IJsonableModel, type]] = set()
    ) -> JSONType:
        """Converts this Chapter into a dictionary that can be JSONified."""

        expanded.add(self)

        prev = self.previous
        if prev is not None:
            prev = prev.id

        next = self.next
        if next is not None:
            next = next.id

        d = {
            "id": self.id,
            "story": self.story.expand(user, expand, expanded),
            "name": self.name,

            "author_notes": self.author_notes,
            "text": self.text,

            "comments": [
                comment.to_json(user, expand, expanded)
                for comment in self.comments
            ],

            "previous": prev,
            "next": next,
            "number": self.number,

            "posted": to_timestamp(self.posted),
            "modified": to_timestamp(self.modified)
        }

        if user is not None:
            if user.is_moderator:
                d["reports"] = [
                    report.expand(user, expand, expanded)
                    for report in self.reports
                ]
            if user.id == self.story.author_id:
                d["index"] = self.index
                d["private"] = self.private
                d["protected"] = self.protected

        return d

    def update(self,
        name: Optional[str] = None,
        author_notes: Optional[str] = None,
        text: Optional[str] = None,
        index: Optional[int] = None,
        private: Optional[bool] = None,
        protected: Optional[bool] = None
    ) -> List[str]:
        """Updates modifiable chapter information.
        
        Parameters
        ==========
        name: `Optional[str]`

        author_notes: `Optional[str]`

        text: `Optional[str]`

        index: `Optional[int]`

        private: `Optional[bool]`

        protected: `Optional[bool]`

        Returns
        =======
        `List[str]`
            List of errors with given parameters. Empty if successful.
        """

        errors = []
        modified = False
        update_timestamp = False

        flags = self.flags

        if name is not None:
            if type(name) != str:
                errors.append("'name' must be a string.")
            elif len(name.strip()) == 0:
                self.name = None
                modified = True
            else:
                name = reduce_whitespace(name)
                if name != self.name:
                    self.name = name
                    modified = True

        if author_notes is not None:
            if type(author_notes) != str:
                errors.append("'author_notes' must be a string.")
            elif len(author_notes.strip()) == 0:
                self.author_notes = None
                modified = True
            else:
                author_notes = reduce_whitespace(author_notes)
                if author_notes != self.author_notes:
                    self.author_notes = author_notes
                    modified = True

        if text is not None:
            if type(text) != str:
                errors.append("'text' must be a string.")
            else:
                text = text.strip()
                if text != self.text:
                    self.text = text
                    if len(filter_text(self.text)) == 0:
                        self.private = True

                    self._html_dirty = True
                    update_timestamp = True

        if index is not None:
            if type(index) != int:
                errors.append("'index' must be an integer.")
            elif index < 0 or index >= len(self.story.chapters):
                errors.append("'index' out of range.")
            elif index > self.index:
                for chapter in tuple(self.story.chapters[self.index + 1:index + 1]):
                    chapter.index -= 1

                self.index = index
                modified = True
            elif index < self.index:
                for chapter in tuple(self.story.chapters[index:self.index]):
                    chapter.index += 1

                self.index = index
                modified = True
                
        if private is not None:
            if type(private) != bool:
                errors.append("'private' must be a boolean.")
            elif private != self.private and len(filter_text(self.text)) > 0:
                self.private = private
                modified = True

        if protected is not None:
            if type(protected) != bool:
                errors.append("'protected' must be a boolean.")
            elif protected != self.protected:
                self.protected = protected
                modified = True

        if len(errors) == 0 and modified or update_timestamp:
            if update_timestamp:
                current_time = get_current_time()

                if self.flags == 0 or flags == 0:
                    self.story.modifed = current_time
                self.modified = current_time
            
            db.session.commit()

        return errors

    def self_visible(self):
        return (self.flags & (self.Flags.PRIVATE | self.Flags.PROTECTED)) == 0

    def visible(self,
        user: Optional[User] = None,
        ignore_risque: bool = False
    ) -> bool:
        """Retrieves whether this chapter is visible to a given user.
        
        Parameters
        ==========
        user: `Optional[User]` = `None`

        ignore_risque: `bool` = `False`
            Whether to ignore invisibility caused by a story being labeled as risque.
        
        Returns
        =======
        `bool`
            True if visible; False otherwise.
        """

        if user is not None and user.id == self.story.author_id:
            return True

        if not self.story.visible(user, ignore_risque):
            return False

        return self.self_visible()

    @property
    def private(self) -> bool:
        """Returns whether this chapter is only visible to the author."""

        return not not (self.flags & self.Flags.PRIVATE)
    
    @private.setter
    def private(self, value: bool):
        if value:
            self.flags |= self.Flags.PRIVATE
        else:
            self.flags ^= self.Flags.PRIVATE

    @property
    def protected(self) -> bool:
        """Returns whether this chapter is visible to specific users."""

        return not not (self.flags & self.Flags.PROTECTED)
    
    @protected.setter
    def protected(self, value: bool):
        if value:
            self.flags |= self.Flags.PROTECTED
        else:
            self.flags ^= self.Flags.PROTECTED

    @classmethod
    def new(cls,
        story: Story,
        name: Optional[str] = None,
        text: str = "",
        author_notes: Optional[str] = None,
        commit: bool = True
    ) -> "Chapter":
        """Creates a new chapter for a given story & adds it to the database.
        
        Parameters
        ==========
        story: `Story`
            The story this chapter belongs to.

        name: `Optional[str]` = `None`
            The name of this chapter.

        text: `str` = `""`
            The starting text of this given chapter.

        author_notes: `Optional[str]` = `None`
            The chapter's author's notes.

        commit: `bool` = `True`
            Whether to commit the new chapter to the database immediately or not.
        
        Returns
        =======
        `Chapter`
            A newly created chapter.
        """

        errors = []

        if type(name) != str and name is not None:
            errors.append("'name' must be a string or null.")
        elif type(name) == str and len(name.strip()) == 0:
            errors.append("'name' must contain at least one non-whitespace character.")
        
        if type(text) != str:
            errors.append("'text' must be a string.")
        
        if type(author_notes) != str and author_notes is not None:
            errors.append("'author_notes' must be a string or null.")
        
        if len(errors) > 0:
            raise ValueError('\n'.join(errors))
        
        current_time = get_current_time()

        chapter = cls(
            story_id     = story.id,
            name         = reduce_whitespace(name) if type(name) == str else None,
            text         = text.strip(),
            author_notes = reduce_whitespace(author_notes) if type(author_notes) == str else None,
            index        = len(story.chapters),
            flags        = cls.Flags.DEFAULT,
            posted       = current_time,
            modified     = current_time
        )

        db.session.add(chapter)
        if commit:
            db.session.commit()

        return chapter

class Comment(IMarkdownModel):
    """A generic comment."""

    __tablename__ = "comments"

    author_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        nullable = False
    )

    posted: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    modified: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    liked_by: List[User] = db.relationship("User",
        secondary = "liked_comments",
        cascade   = "all,delete"
    )

    replies: List["Comment"] = db.relationship("Comment",
        secondary     = "comment_replies",
        primaryjoin   = "(Comment.id == CommentReply.comment_id)",
        secondaryjoin = "(Comment.id == CommentReply.reply_id)",
        backref       = db.backref("reply_of", uselist=False),
        cascade       = "all,delete"
    )

    reports: List["Report"] = db.relationship("Report",
        secondary = "comment_reports",
        cascade   = "all,delete",
        backref   = db.backref("comment", uselist=False)
    )

    author: User

    of_chapter: Optional[Chapter]

    reply_of: Optional["Comment"]

    def to_json(self,
        user: Optional["User"] = None,
        expand: bool = False,
        expanded: Set[Union[IJsonableModel, type]] = set()
    ) -> JSONType:
        """Converts this Comment into a dictionary that can be JSONified."""

        expanded.add(self)

        parent = self.parent.expand(user, expand, expanded)
        if type(parent) == int: # is parent ID
            parent = { "id": parent }

        d = {
            "id": self.id,
            "author": self.author.expand(user, expand, expanded),
            "text": self.text,

            "of": {
                "type": self.parent.__class__.__name__.lower(),
                **parent
            },

            "replies": [
                comment.expand(user, expand, expanded)
                for comment in self.replies
            ],

            "liked_by": [
                u.expand(user, expand, expanded)
                for u in self.liked_by
            ],

            "posted": to_timestamp(self.posted),
            "modified": to_timestamp(self.modified)
        }

        if user is not None and user.is_moderator:
            d["reports"] = [
                report.expand(user, expand, expanded)
                for report in self.reports
            ]

        return d

    def update(self,
        text: Optional[str] = None
    ) -> List[str]:
        """Updates modifiable comment information.
        
        Parameters
        ==========
        text: `Optional[str]`

        Returns
        =======
        `List[str]`
            List of errors with given parameters. Empty if successful.
        """

        errors = []
        modified = False

        if text is not None and text != self.text:
            if type(text) != str:
                errors.append("'text' must be a string.")
            elif len(filter_text(text)) == 0:
                errors.append(
                    "When parsed, 'text' must contain at least one non-whitespace character."
                )
            else:
                self.text = text.strip()
                self._html_dirty = True
                modified = True

        if modified and len(errors) == 0:
            self.modified = get_current_time()
            db.session.commit()

        return errors

    @property
    def parent(self) -> Union[Chapter, "Comment"]:
        """Retrieves what this comment is a comment of.
        
        Returns
        =======
        `Chapter`
            If this comment is for a Chapter, returns the chapter it's for.
            
        `Comment`
            If this comment is part of a reply chain, returns the previous comment in the chain.
        """

        return self.reply_of or self.of_chapter
        
    @classmethod
    def new(cls,
        user: User,
        text: str,
        of: Union["Comment", Chapter]
    ) -> "Comment":
        """Creates a new comment.

        Parameters
        ==========
        user: `User`
            The user who posted the comment.

        text: `str`
            The content of the new comment.

        of: `Union[Comment, Chapter]`
            What the newly created comment is a comment of.
            If **of** is a Comment, the new comment is a reply in a reply chain.
            If **of** is a Chapter, the new comment is a chapter comment.

        Returns
        =======
        `Comment`
            A new comment placed in the database with the given information.
        """

        errors = []

        if text is None:
            errors.append("Missing parameter 'text'.")
        elif type(text) != str:
            errors.append("'text' must be a string.")
        elif len(filter_text(text)) == 0:
            errors.append(
                "When parsed, 'text' must contain at least one non-whitespace character."
            )
        
        if type(of) not in { Chapter, Comment }:
            errors.append("'of' must be either a Chapter or Comment ORM.")

        if len(errors) > 0:
            raise ValueError("\n".join(errors))

        current_time = get_current_time()

        comment = cls(
            author_id = user.id,
            text      = text.strip(),
            posted    = current_time,
            modified  = current_time
        )

        if type(of) == Comment:
            p = of.parent
            while type(p) != Chapter:
                p = p.parent
            if not p.story.can_comment:
                raise ValueError(f"Story with ID {p.story.id} doesn't allow comments.")

            db.session.add(comment)
            db.session.commit()
            of.replies.append(comment)
        elif type(of) == Chapter:
            if not of.story.can_comment:
                raise ValueError(f"Story with ID {of.story.id} doesn't allow comments.")
            else:
                db.session.add(comment)
                db.session.commit()
                of.comments.append(comment)

        db.session.commit()

        return comment

    def __repr__(self) -> str:
        """A string representation of a given comment."""

        return (
            "{" + f"ID: {self.id}; author: {self.author.username}; " +
            f"posted: {format_time(self.posted)}; modified: {format_time(self.modified)}" +
            ('' if self.parent is None else f"; parent: {self.parent.id}") + "}"
        )

class Report(IJsonableModel):
    """A generic report."""

    __tablename__ = "reports"

    author_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        nullable = False
    )

    text: str = db.Column(db.Text,
        nullable = False
    )

    posted: datetime.datetime = db.Column(db.DateTime,
        nullable = False
    )

    comment: Optional[Comment]
    chapter: Optional[Chapter]
    story: Optional[Story]
    user: Optional[User]

    def to_json(self,
        user: Optional["User"] = None,
        expand: bool = False,
        expanded: Set[Union[IJsonableModel, type]] = set()
    ) -> JSONType:
        """Converts this Report into a dictionary that can be JSONified."""

        expanded.add(self)

    @property
    def parent(self) -> Union[Chapter, Comment, Story, User]:
        """Retrieves what this report pertains to."""

        return self.comment or self.chapter or self.story or self.user

class ChapterComment(db.Model):
    """Comments associated with a chapter."""

    __tablename__ = "chapter_comments"

    chapter_id: int = db.Column(db.Integer,
        db.ForeignKey('chapters.id'),
        primary_key = True
    )

    comment_id: int = db.Column(db.Integer,
        db.ForeignKey('comments.id'),
        primary_key = True
    )

class CommentReply(db.Model):
    """Comments associated with a previous comment."""

    __tablename__ = "comment_replies"

    comment_id: int = db.Column(db.Integer,
        db.ForeignKey('comments.id'),
        primary_key = True,
        unique      = True
    )

    reply_id: int = db.Column(db.Integer,
        db.ForeignKey('comments.id'),
        primary_key = True,
        unique      = True
    )

class CommentReport(db.Model):
    """Reports associated with a comment."""

    __tablename__ = "comment_reports"

    comment_id: int = db.Column(db.Integer,
        db.ForeignKey('comments.id'),
        primary_key = True
    )

    report_id: int = db.Column(db.Integer,
        db.ForeignKey('reports.id'),
        primary_key = True
    )

class ChapterReport(db.Model):
    """Reports associated with a chapter."""

    __tablename__ = "chapter_reports"

    chapter_id: int = db.Column(db.Integer,
        db.ForeignKey('chapters.id'),
        primary_key = True
    )

    report_id: int = db.Column(db.Integer,
        db.ForeignKey('reports.id'),
        primary_key = True
    )

class StoryReport(db.Model):
    """Reports associated with a story."""

    __tablename__ = "story_reports"

    story_id: int = db.Column(db.Integer,
        db.ForeignKey('stories.id'),
        primary_key = True
    )

    report_id: int = db.Column(db.Integer,
        db.ForeignKey('reports.id'),
        primary_key = True
    )

class UserReport(db.Model):
    """Reports associated with a user."""

    __tablename__ = "user_reports"

    user_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        primary_key = True
    )

    report_id: int = db.Column(db.Integer,
        db.ForeignKey('reports.id'),
        primary_key = True
    )

class FavoriteStory(db.Model):
    """Stories a user has favorited."""

    __tablename__ = "favorite_stories"

    user_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        primary_key = True
    )

    story_id: int = db.Column(db.Integer,
        db.ForeignKey('stories.id'),
        primary_key = True
    )

class FollowingStory(db.Model):
    """Stories a user is following."""

    __tablename__ = "followed_stories"

    user_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        primary_key = True
    )

    story_id: int = db.Column(db.Integer,
        db.ForeignKey('stories.id'),
        primary_key = True
    )

class FollowingUser(db.Model):
    """Users a user is following."""

    __tablename__ = "followed_users"

    follower_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        primary_key = True
    )

    following_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        primary_key = True
    )

class LikedComment(db.Model):
    """Comments a user likes."""

    __tablename__ = "liked_comments"

    user_id: int = db.Column(db.Integer,
        db.ForeignKey('users.id'),
        primary_key = True
    )

    comment_id: int = db.Column(db.Integer,
        db.ForeignKey('comments.id'),
        primary_key = True
    )
