# *FictionSource*
## Capstone Project 1

A user-generated Markdown-based fiction repository with search functionality.

~~This took way too long to make lmao~~

## Link
https://fictionsource.herokuapp.com

## Tools
- Flask (server engine)
- SQLAlchemy (database interface)
  - PostgreSQL (database engine)
- [Markdown.WASM](https://github.com/rsms/markdown-wasm) (markdown engine)
- [FontAwesome](https://fontawesome.com) (user interface icons)

## Features
- Markdown editor which updates in real-time as you type.
  - Tons of people are familiar with how Markdown works, and it can at times be easier to use
    than a bog-standard WYSIWYG GUI interface. To make it still be convenient to use, I yoinked
    a very fast Markdown-to-HTML converter from GitHub and used it to display and parse the
    Markdown text content of the website and in the writing interface in real time.
- Pagified search by tag, user, or phrase. Can sort with various criterion in ascending or 
  descending order.
  - It's the main of finding stories through the website if the homepage doesn't list any
    stories of interest.
  - Tags use the search function to collate their related stories.
- User-definable tags.
  - Used to group stories together.
- An NSFW filter (turned on by default and when not logged in).
  - Allows the site to host content not safe for younger users (i.e. 13-17 year-olds) without
    totally restricting access to general purpose content.
  - Cannot be turned off unless done so after the account's listed birthdate + 18 years has been
    passed.
- Following Stories & Users
  - Allows users to keep track of which stories are being updated via the homepage.
- Favoriting Stories
  - Allows for *de facto* recommendations via user pages.
- RESTful API
  - Allows for ease of accessing & interacting with the website's data.

## Personal Notes
The biggest thing I learned from this project, mainly due to the absurd length of time it look to
develop it, is the importance of recognizing feature/scope creep and to be sure I don't fall victim
to it in future. Several features of the site had to be cut out for it to be submitted even in this
very much untimely manner, but in spite of this I am still proud of what I've been able to
accomplish with this.

If I ever do have any spare time in the future, I might come back and finish up the unfinished or
excluded features from the website, and I hope it's enjoyed for what it is in its current form.

## API Basics
**Base URL:** `https://fictionsource.herokuapp.com/api`

The API is accessible via the base URL listed above and uses JSON as the data format in in requests
and responses.

A URL used to access functionality provided by the API is called an **entrypoint**, and is made up
of an HTTP request method (e.g. `GET`, `POST`, `PUT`) and a suffix to the base URL listed above.

### Type Definitions
The following data types are used in API requests and responses:
- `int`: a signed integer.
- `datetime`: a JavaScript timestamp.
- `string`: a fixed sequence of characters.
- `bool`: a boolean value; either **true** or **false**.
- `uint`: an integer restricted to positive values or 0.
- `enum`: a `string` restricted to a set of known values.
- `url`: a `string` restricted to the format of a URL.
- optional (e.g. `int?`): either the given type or **null**.
- array (e.g. `uint[]`): a list of numbers
- `object`: a mapping of strings to arbitrary values.
- `any`: any of the above types

### Response Format
All responses returned by the API return their data as a JSON object with the following fields:
- **type** (type: `enum { "error", "success"  }`)
  - The type of response being received.
- **code** (type: `uint`)
  - The HTTP status code of the response.

Error responses have the following additional fields defined:
- **errors** (type: `string[]`)
  - List of errors made by the request or by the server.

Success responses have the following additional fields defined:
- **data** (type: `any`)
  - The data returned by the entrypoint.

### Access Types
All API entrypoints are publically accessible, but some won't return sensitive or protected data
unless you access the API with a user account registered on the website. These latter entrypoints
require **privleged** access. Entrypoints that do not require specific credentials to receive
useful data when accessing them allow for **unprivleged** access. Accessing an API entrypoint
without requiring one to log in to an account when requesting data is **anonymous** access.

There are two methods which can log in to an account when access data: **cookies** or **HTTP Basic
Authorization**. If one accesses an API entrypoint from a session which has already logged on to
the website, the API is accessed via the session's logged in account. Alternatively, setting the
**Authorization** HTTP header in an API entrypoint request with the appropriate credentials will
allow one to access the API via the explicitly specified account. If invalid credentials are
provided in the **Authorization** header, a `401` error response is returned with the message
`"Insufficient credentials."` listed as an error.

## API Entrypoints
(NOTE: this section is presently incomplete, but will be fully filled in later)

### Get User Data
Retrieves information relating to a given user.

#### Entrypoint
> `GET /user/<username>`


#### Returns
- `200 OK`
  - **username** (type: `string`)
    - The username listed in the entrypoint URL.
  - **birthdate** (type: `datetime`)
    - This user's date of birth.
  - **joined** (type: `datetime`)
    - When this user registered to the website.
  - **image** (type: `url`)
    - URL pointing to this user's profile picture.
  - **description** (type: `string?`)
    - This user's profile description, if provided.
  - **is_moderator** (type: `bool`)
    - **true** if this user is a site moderator.
  - **favorite_stories** (type: `uint[]`)
    - List of story IDs this user has favorited.
  - **followed_stories** (type: `uint[]`)
    - List of story IDs this user is following.
  - **following** (type: `string[]`)
    - List of usernames this user is following.
  - **followed_by** (type: `string[]`)
    - List of usernames that follow this user.
  - **stories** (type: `uint[]`)
    - *Anonymous or unprivleged*: List of story IDs of stories this user has posted.
    - *Privleged*: List of story IDs of stories this user has created.
  - **allow_risque** (type: `bool`)
    - Whether or not this user allows themselves to view NSFW content.
    - Only accessible if *privleged*.
- `404 NOT FOUND`
  - If `<username>` doesn't match the username of a registered user.

### Update User Data
Updates a user's information with new data.

#### Entrypoint
> `PATCH /user/<username>`

#### Parameters
- **image** (type: `url?`)
  - If not **null**, URL pointing to the user's profile picture.
  - *Default*: **null**
- **description** (type: `string?`)
  - If not **null**, the user's profile description.
  - *Default*: **null**
- **allow_risque** (type: `bool?`)
  - If not **null**, whether or not to allow risque content to be seen by this user.
  - *Default*: **null**
  - If the user is under 18 years of age, this value will always be set to **true** even if
    explicitly overriden.

#### Returns
- `200 OK` (*privleged*)
  - No body returned.
- `401 UNAUTHORIZED` (*unprivleged*, *anonymous*)
- `404 NOT FOUND`
  - If `<username>` doesn't match the username of a registered user.


### Follow User
Follows a user.

#### Entrypoint
> `POST /user/<username>/follow`


### Unollow User
Unfollows a user.

#### Entrypoint
> `DELETE /user/<username>/follow`


### Create Story
Creates a new story.

#### Entrypoint
> `POST /story`


### Get Story Details
Retrieves information regarding a story.

#### Entrypoint
> `GET /story/<uint:story_id>`


### Update Story
Updates a story's general information.

#### Entrypoint
> `PATCH /story/<uint:story_id>`


### Delete Story
Removes a story from existence.

#### Entrypoint
> `DELETE /story/<uint:story_id>`


### List Story Tags
Lists the tags associated with a given story.

#### Entrypoint
> `GET /story/<uint:story_id>/tags`


### Insert Story Tags
Associates a set of new tags with a given story.

#### Entrypoint
> `PUT /story/<uint:story_id>/tags`


### Remove Story Tags
Removes a set of tags associated with a given story.

#### Entrypoint
> `DELETE /story/<uint:story_id>/tags`


### Favorite Story
Favorites a story.

#### Entrypoint
> `POST /story/<uint:story_id>/favorite`


### Unfavorite Story
Unfavorites a story.

#### Entrypoint
> `DELETE /story/<uint:story_id>/favorite`


### Follow Story
Follows a story.

#### Entrypoint
> `POST /story/<uint:story_id>/follow`


### Unfollow Story
Unfollows a story.

#### Entrypoint
> `DELETE /story/<uint:story_id>/follow`


### List Story Chapters
Lists the chapters in a given story.

#### Entrypoint
> `GET /story/<uint:story_id>/chapters`


### Create Chapter
Creates a new chapter associated with a given story.

#### Entrypoint
> `POST /story/<uint:story_id>/chapters`


### Get Chapter
Retrieves a chapter's details an information.

#### Entrypoint
> `GET /chapter/<uint:chapter_id>`


### Update Chapter
Updates a chapter's details with new information.

#### Entrypoint
> `PATCH /chapter/<uint:chapter_id>`


### Delete Chapter
Removes a chapter from existence.

#### Entrypoint
> `DELETE /chapter/<uint:chapter_id>`


### Search
Searches for stories according to the provided restrictions. Similar to the search route on the
website.

#### Entrypoint
> `GET /search`

#### Parameters
- **offset** (type: `uint`)
  - How many results to skip from the list of total results.
  - *Default*: 0
- **count** (type: `uint`)
  - The maximum number of results to receive.
  - *Default*: 25
- **sort_by** (type: `enum { "modified", "posted", "favorites", "follows" }`)
  - What quantity to sort the results by.
  - *Default*: `"modified"`
- **descending** (type: `bool`)
  - Whether or not to order the results in descending order.
  - *Default*: **true**
- **filter_risque** (type: `bool?`)
  - If **true**, excludes any NSFW content from the search results.
  - If **false**, excludes any non-NSFW content from the search results.
  - If **null**, no effect.
  - *Default*: **true**
  - *Note*: If accessed anonymously or by a user less than 18 years of age, this value will always
    be set to **true**, even if explicitly overriden by a different value.
- **include_tags** (type: `string[]`)
  - List of tag query names that stories must have to be included in the search results.
  - *Default*: `[]`
- **exclude_tags** (type: `string[]`)
  - List of tag query names that stories must not have to be included in the search results.
  - *Default*: `[]`
- **include_users** (type: `string[]`)
  - List of usernames whose stories will exclusively appear in the search results.
  - *Default*: `[]`
- **exclude_users** (type: `string[]`)
  - List of usernames whose stories will be excluded from the search results.
  - *Default*: `[]`
- **include_phrases** (type: `string[]`)
  - List of words or phrases that must appear in either the story's title, summary, chapters'
    author's notes, or chapters' content to be included in the search results.
  - *Default*: `[]`
- **exclude_phrases** (type: `string[]`)
  - List of words or phrases that must not appear in either the story's title, summary, chapters'
    author's notes, or chapters' content to be included in the search results.
  - *Default*: `[]`

#### Returns
- `200 OK` on success.
- `400 BAD REQUEST` on request doesn't list parameters as an `object` or if any of the above
  parameters don't match their associated types.
