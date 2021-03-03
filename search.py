"""Database search."""

# == IMPORTS ===================================================================================== #

from typing import *
import enum

from models import *
from sqlalchemy import or_, and_, not_, func

# == DEFINES ===================================================================================== #

class SearchSortEnum(enum.Enum):
    MODIFIED = "modified"
    POSTED = "posted"
    FAVORITES = "favorites"
    FOLLOWS = "follows"

    @classmethod
    def good_values(cls) -> List[str]:
        return [ v for v in map(lambda x: x.lower(), cls.__members__.keys()) ]

class SearchResults:
    """An object containing results from a search query."""

    results: List[Story]
    num_results: int
    start: int
    end: int
    query: str
    sort_by: str

    def __init__(self,
        user: Optional[User] = None,
        offset: int = 0,
        count: int = 25,
        sort_by: Optional[str] = None,
        descending: bool = True,
        filter_risque: Optional[bool] = True,
        include_tags: Collection[str] = set(),
        exclude_tags: Collection[str] = set(),
        include_users: Collection[str] = set(),
        exclude_users: Collection[str] = set(),
        include_phrases: Collection[str] = set(),
        exclude_phrases: Collection[str] = set()
    ):
        """Constructs a new search query.
        
        Parameters
        ==========
        user: `Optional[User]` = `None`
            User performing the search. Affects story visibility.

        offset: `int` = `0`
            How far into the results to search for.

        count: `int` = `25`
            How many results to collate.

        sort_by: `Optional[str]` = `None`
            How to sort the search results.

        descending: `bool` = `True`
            Whether the results should be sorted in descending order.

        filter_risque: `Optional[bool]` = `False`
            Whether to include risque (i.e. NSFW) stories in search results.
            None  = No filter applied.
            True  = Filter out risque content.
            False = Filter out non-risque content.

        inlcude_tags: `Collection[str]` = `set()`
            Set of tags to filter in to stories found in the search.

        exclude_tags: `Collection[str]` = `set()`
            Set of tags to filter out from stories found in the search.

        include_users: `Collection[str]` = `set()`
            Set of users to filter in to stories found in the search.

        exclude_users: `Collection[str]` = `set()`
            Set of users to filter out from stories found in the search.

        include_phrases: `Collection[str]` = `set()`
            Set of phrases to filter in to stories found in the search.

        exclude_phrases: `Collection[str]` = `set()`
            Set of phrases to filter out from stories found in the search.
        """

        errors = []

        def check_set(
            name: str,
            collection: Collection[str],
            apply: Optional[Callable[[str], Any]] = None
        ) -> Set[Any]:
            """Checks if a set parameter is valid. If it is, it removes duplicate items and
            optionally applies an additional function to the data.
            
            Parameters
            ==========
            name: `str`
                Name of the set parameter.
            
            collection: `Collection[str]`
                A set, list, or tuple containing strings.
            
            apply: `Optional[Callable[[str], Any]]` = `None`
                A function to apply to all the items in the set.
            """

            nonlocal errors

            if (type(collection) not in (list, set, tuple) and
                not all(isinstance(x, str) for x in collection)
            ):
                errors.append(f"'{name}' must be a list of strings.")
            elif type(collection) != set:
                collection = set(collection)

            if apply is not None:
                new_collection = set()
                for item in collection:
                    try:
                        new_collection.add(apply(item))
                    except Exception:
                        continue
                collection = new_collection

            return collection
        
        def collate_phrase_clauses(phrases: Collection[str]):
            """Generates a query filter expression from a collection of phrases.
            
            Parameters
            ==========
            phrases: `Collection[str]`
                Phrases to search for.
            
            Returns
            =======
                An expression to place in Query.filter()
            """

            clauses = []
            for phrase in phrases:
                escaped_phrase = phrase.replace('/', '//').replace('%', '/%').replace("'", "/'")

                clauses.append(or_(
                    Story.title.ilike(f"'%{escaped_phrase}%'", escape='/'),
                    Story.summary.ilike(f"'%{escaped_phrase}%'", escape='/'),
                    or_(
                        Chapter.author_notes == None,
                        Chapter.author_notes.ilike(f"'%{escaped_phrase}%'", escape='/')
                    ),
                    Chapter.text.ilike(f"'%{escaped_phrase}%'", escape='/')
                ))
            
            return or_(*clauses)

        if type(offset) != int:
            errors.append("'offset' must be an integer.")
        elif offset < 0:
            errors.append("'offset' must be greater than zero.")
            
        if type(count) != int:
            errors.append("'count' must be an integer.")
        elif count < 1:
            errors.append("'count' must be greater than 1.")

        if type(sort_by) != str and sort_by is not None:
            errors.append("'sort_by' must be a string.")
        elif sort_by is None:
            sort_by = "modified"
        elif sort_by not in SearchSortEnum.good_values():
            errors.append(f"'sort_by' must be one of: {', '.join(SearchSortEnum.good_values())}")

        if type(descending) != bool:
            errors.append("'descending' must be a boolean.")

        if filter_risque is not None and type(filter_risque) != bool:
            errors.append("'filter_risque' must be a boolean or null.")
        
        include_tags = check_set("include_tags", include_tags, lambda x: Tag.get(x).id)
        exclude_tags = check_set("exclude_tags", exclude_tags, lambda x: Tag.get(x).id)

        include_users = check_set("include_users", include_users)
        if any({ not User.is_valid_username(x) for x in include_users }):
            errors.append("Items in 'include_users' must be valid usernames.")

        exclude_users = check_set("exclude_users", exclude_users)
        if any({ not User.is_valid_username(x) for x in exclude_users }):
            errors.append("Items in 'exclude_users' must be valid usernames.")
        
        include_phrases = check_set("include_phrases", include_phrases)
        if any({ len(x) < 3 for x in include_phrases }):
            errors.append("Items in 'include_phrases' must be at least 3 characters long.")

        exclude_phrases = check_set("exclude_phrases", exclude_phrases)
        if any({ len(x) < 3 for x in exclude_phrases }):
            errors.append("Items in 'exclude_phrases' must be at least 3 characters long.")
        
        if len(errors) > 0:
            raise ValueError("\n".join(errors))

        results = Story.visible_stories(user)

        # filter tags
        if len(include_tags) + len(exclude_tags) > 0:
            if len(include_tags) > 0:
                results = results.filter(
                    StoryTag.query.filter(and_(
                        StoryTag.story_id == Story.id,
                        StoryTag.tag_id.in_(include_tags)
                    )).exists()
                )
            if len(exclude_tags) > 0:
                results = results.filter(not_(
                    StoryTag.query.filter(and_(
                        StoryTag.story_id == Story.id,
                        StoryTag.tag_id.in_(exclude_tags)
                    )).exists()
                ))

        # filter users
        if len(include_users) + len(exclude_users) > 0:
            results = results.join(Story.author)

            if len(include_users) > 0:
                results = results.filter(User.username.in_(include_users))
            if len(exclude_users) > 0:
                results = results.filter(not_(User.username.in_(exclude_users)))

        # filter phrases
        if len(include_phrases) + len(exclude_phrases) > 0:
            results = results.join(Story.chapters).filter(
                Chapter.flags.op('&')(Chapter.Flags.PRIVATE | Chapter.Flags.PROTECTED) == 0
            )
            if len(include_phrases) > 0:
                results = results.filter(collate_phrase_clauses(include_phrases))
            if len(exclude_phrases) > 0:
                results = results.filter(not_(collate_phrase_clauses(exclude_phrases)))

        # filter risque
        if filter_risque is not None and filter_risque:
            results = results.filter(Story.flags.op('&')(Story.Flags.IS_RISQUE) == 0)
        elif filter_risque is not None and not filter_risque:
            results = results.filter(
                Story.flags.op('&')(Story.Flags.IS_RISQUE) != 0
            )

        ordering = None
        if sort_by == "modified":
            ordering = Story.modified
        elif sort_by == "posted":
            ordering = Story.posted
        elif sort_by == "favorites":
            results = results.join(Story.favorited_by, isouter=True).group_by(Story.id)
            ordering = func.count(User.id)
        elif sort_by == "follows":
            results = results.join(Story.followed_by, isouter=True).group_by(Story.id)
            ordering = func.count(User.id)
        
        results = results.distinct(Story.id, ordering)
        if descending:
           ordering = ordering.desc()
        results = results.order_by(ordering)

        self.num_results = results.count()
        self.results = results.slice(
            min(offset, self.num_results - 1 if self.num_results > 0 else 0),
            offset + count
        ).all()

        self.start = min(offset + 1, self.num_results)
        self.end = min(offset + count, self.num_results)
        
        if filter_risque is None:
            filter_risque = 0
        elif filter_risque:
            filter_risque = 1
        else:
            filter_risque = -1

    def to_json(self) -> JSONType:
        return {
            "query": self.query,
            "results": [ story.id for story in self.results ],
            "num_results": self.num_results,
            "start": self.start,
            "end": self.end
        }
