from flask_bcrypt import generate_password_hash
from models import *
from datetime import date, datetime, timezone

def seed_db(db: SQLAlchemy) -> None:
    """Seeds the database with a predetermined data set."""

    GEN_PASSW = lambda s: generate_password_hash(s).decode("utf-8")
    
    # Add users
    users = (
        User(
            username   = "simondoesficsrc",
            password   = GEN_PASSW("seemeafterdinner"),
            email      = "snstruthers@gmail.com",
            birthdate  = date(2000, 2, 15),
            joined     = datetime(
                year   = 2020,
                month  = 12,
                day    = 5,
                hour   = 11,
                minute = 44,
                second = 15,
                tzinfo = timezone.utc
            ),
            flags      = User.Flags.ALLOW_RISQUE
        ),
        User(
            username   = "seen6",
            password   = GEN_PASSW("abcdef"),
            email      = "test2@gmail.com",
            birthdate  = date(1999, 6, 24),
            joined     = datetime(
                year   = 2020,
                month  = 12,
                day    = 17,
                hour   = 8,
                minute = 12,
                second = 54,
                tzinfo = timezone.utc
            ),
            flags      = User.Flags.ALLOW_RISQUE
        ),
        User(
            username   = "chicago94",
            password   = GEN_PASSW("hello_world"),
            email      = "test@gmail.com",
            birthdate  = date(1994, 12, 1),
            joined     = datetime(
                year   = 2020,
                month  = 12,
                day    = 15,
                hour   = 17,
                minute = 6,
                second = 3,
                tzinfo = timezone.utc
            )
        )
    )
    db.session.add_all(users)
    db.session.commit()

    # Add tags
    tags = (
        Tag(
            _type = Tag.Type.CATEGORY,
            name = "fanfiction",
            description = "Works not based on pre-existing intellectual property."
        ),
        Tag(
            _type = Tag.Type.CATEGORY,
            name = "original",
            description = "Works based on one's own ideas."
        ),
        Tag(
            _type = Tag.Type.CATEGORY,
            name = "crossover",
            description = "Works that involve multiple continuities interacting with each other."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "action",
            description = "Action packed."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "angst",
            description = "Dripping with teenage angst."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "adventure",
            description = "Exciting & adventurous."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "comedy",
            description = "Laid back & comedic."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "drama",
            description = "Dramatic storytelling."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "fantasy",
            description = "Fantastical and out-of-this-world."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "friendship",
            description = "Tales of kinship."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "horror",
            description = "Horror stories."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "melodrama",
            description = "Overly dramatic storytelling."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "psychothriller",
            description = "Psychological thrillers."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "romance",
            description = "For all the shippers."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "science_fiction",
            description = "Literally out-of-this-world."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "suspense",
            description = "Nail biting."
        ),
        Tag(
            _type = Tag.Type.GENRE,
            name = "thriller",
            description = "So exciting you can't look away."
        )
    )

    db.session.add_all(tags)
    db.session.commit()

    # Add stories
    stories = (
        Story(
            author_id  = users[0].id,
            title      = "The Youth Revolution",
            posted     = datetime(
                year   = 2020,
                month  = 12,
                day    = 29,
                hour   = 16,
                minute = 3,
                second = 6,
                tzinfo = timezone.utc,
            ),
            modified   = datetime(
                year   = 2020,
                month  = 12,
                day    = 29,
                hour   = 16,
                minute = 3,
                second = 6,
                tzinfo = timezone.utc
            ),
            summary = "A young, naive, and upstart politician with high ambitions " +
                "runs for president and is dealt an uphill battle and a swift dose " +
                "of reality.",
            flags = Story.Flags.DEFAULT
        ),
    )

    db.session.add_all(stories)
    db.session.commit()

    stories[0].tags.append(tags[1])
    stories[0].tags.append(tags[15])


    # Add chapters
    chapters = (
        Chapter.new(stories[0], "Regarding the Capornicians",
"""
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam a sapien sed sem rhoncus hendrerit.
Morbi ac ipsum a diam scelerisque scelerisque. Sed sed facilisis neque. Aliquam erat volutpat.
Aliquam erat volutpat. Etiam sem lectus, placerat quis porta a, ultricies in libero. Nulla ac sem
non eros rhoncus ullamcorper vitae id lectus. Cras luctus nunc ac velit auctor, ac sollicitudin
risus rhoncus. Praesent sit amet iaculis velit, nec mattis elit. Proin pretium odio diam, id
vestibulum diam posuere non. Aliquam erat volutpat.

Nunc vitae neque dictum, venenatis erat non, laoreet urna. Nam condimentum orci in sem tempus
lobortis. Maecenas tempor venenatis tincidunt. Ut malesuada interdum dolor, at molestie nisl tempor
ut. Etiam volutpat turpis semper tincidunt tincidunt. Sed fermentum nisl at justo porttitor, non
suscipit turpis vehicula. Donec aliquet fermentum neque. Morbi sagittis orci quis pharetra
convallis. Maecenas sed dolor convallis, blandit nunc vitae, congue mi. Donec ornare hendrerit
sagittis. Quisque scelerisque mauris quis elit elementum suscipit. Sed eu dictum quam, id auctor
mi. Morbi malesuada, quam eu condimentum faucibus, urna velit sollicitudin mauris, eu rhoncus augue
nisi ut metus. Phasellus accumsan eros nibh, non ornare velit maximus a. Duis in ex ligula. Sed
posuere mattis justo ut luctus.

Cras lorem ligula, egestas sit amet hendrerit eleifend, lobortis non dui. Mauris a pretium eros.
Aenean sit amet justo a risus vehicula vestibulum. Proin tincidunt molestie dolor, auctor venenatis
purus condimentum sit amet. Fusce mi ex, vulputate vitae sagittis ut, lobortis nec leo. Praesent vel
scelerisque tortor, sit amet aliquet augue. In eget sodales justo. Nullam fringilla aliquet eros, ut
dignissim dolor dapibus at. Mauris a felis arcu. Pellentesque habitant morbi tristique senectus et
netus et malesuada fames ac turpis egestas.

Praesent ullamcorper velit nec mollis luctus. Morbi at arcu tincidunt, rhoncus urna feugiat, posuere
sem. Aenean semper quam a aliquet volutpat. Vivamus facilisis, justo feugiat euismod placerat, sem
massa vestibulum lacus, nec bibendum sapien eros vel quam. Integer dignissim lobortis dolor,
consectetur venenatis lectus vulputate at. Curabitur quis eleifend nisi, et accumsan sapien.
Vestibulum bibendum eleifend consectetur. Phasellus lectus ipsum, iaculis sit amet pellentesque ut,
luctus vel ante. Aenean tincidunt justo a velit luctus auctor. Nunc interdum risus a massa
consectetur, varius varius massa tincidunt. Proin tristique urna a nulla scelerisque porta. Cras
mattis, sapien ac dignissim consequat, nulla ante scelerisque mi, nec maximus velit mauris in magna.
Fusce massa erat, interdum in facilisis ac, dignissim ac quam. Praesent id turpis et lorem interdum
varius. Morbi non ultrices metus.

Mauris viverra pellentesque faucibus. Praesent tortor lectus, feugiat id purus quis, maximus posuere
odio. Mauris massa lorem, tristique commodo imperdiet quis, congue sed nisi. Fusce consequat porta
eleifend. Vivamus condimentum nulla sed congue dictum. Sed congue tincidunt tortor ut ultrices.
Nulla urna nibh, scelerisque at ex quis, suscipit vulputate quam. Fusce ultricies lorem ut mollis
tempus. Vivamus imperdiet nisi at mauris porta pellentesque ac ac ante. Vivamus fringilla a elit non
molestie. Vestibulum vehicula nibh ac nulla tempus, et rutrum ipsum molestie. Praesent pharetra
gravida massa, vitae mollis diam. 
"""
        ),
        Chapter.new(stories[0], "Meeting with the Party Elites"),
        Chapter.new(stories[0], "The February Debate"),
        Chapter.new(stories[0], "The Campaign Begins")
    )

    chapters[0].update(private=False)
    stories[0].update(private=False)

    # Add comments
    c1 = Comment.new(users[1], "Hello world!", chapters[0])
    c2 = Comment.new(users[0], "Hello seen6!", c1)

    c2.liked_by.append(users[1])
    db.session.commit()
