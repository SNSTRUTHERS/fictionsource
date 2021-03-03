/**
 * @file read.js
 * @author Simon Struthers
 * @description General chapter reading interaction logic.
 */

/** @typedef {{
 *      id: number,
 *      author: string,
 *      text: string,
 *      replies: number[],
 *      posted: number,
 *      modified: number,
 *      parent: {id: number, type: string}
 *  }} APIComment
 */

// used to make sure we only load comments from before this given time
const currentTime = Date.now();

// shows the loading cover
const showCover = () => document.body.classList.add("cover");

// hides the loading cover
const hideCover = () => document.body.classList.remove("cover");

// returns true if the cover is currently hidden
const coverIsHidden = () => !document.body.classList.contains("cover");

/**
 * Converts a Date to a <time> element.
 * @param {Date} date A JavaScript date.
 */
const dateToTimeElement = (date) => {
    const time = document.createElement("time");
    time.dateTime = `${
        date.getUTCFullYear()
    }/${
        date.getUTCMonth() + 1
    }/${
        date.getUTCDate()
    } ${
        (date.getUTCHours() % 12) + 12
    }:${
        date.getUTCMinutes() + 1
    }:${
        date.getUTCSeconds() + 1
    } UTC`;

    time.innerText = date.toLocaleString(
        undefined,
        {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: 'numeric',
            minute: 'numeric',
            second: 'numeric'
        }
    );

    return time;
};

/**
 * Renders a comment to HTML.
 * 
 * @param {APIComment} commentObj A comment object returned from the fictionsource API.
 * 
 * @returns {HTMLElement} A comment as an HTML node.
 */
const renderComment = ({
    id,
    author,
    text,
    replies,
    posted,
    modified,
    of: {type: parentType}
}) => {
    const comment = document.createElement("div");
    comment.dataset["id"] = id;

    let p = document.createElement("p");

    const a = document.createElement("a");
    a.href = `/user/${author}`;
    a.innerText = `${author} ${parentType === "chapter" ? "says" : "replies"}...`;
    p.appendChild(a);
    comment.appendChild(p);

    const article = document.createElement("article");
    article.innerHTML = renderMarkdown(text);
    comment.appendChild(article);

    p = document.createElement("p");
    const small = document.createElement("small");
    p.appendChild(small);

    small.appendChild(document.createTextNode("posted "));
    small.appendChild(dateToTimeElement(new Date(posted)));
    small.appendChild(document.createTextNode("; modified "));
    small.appendChild(dateToTimeElement(new Date(modified)));

    comment.appendChild(small);

    if (replies.length > 0) {
        const button = document.createElement("button");
        button.innerText = "Show Replies";
        comment.appendChild(button);
    }

    return comment;
};

/* ============================================================================================== */

/**
 * Makes a call to the fictionsource API.
 * @type {(
    *      apiPath: string,
    *      method: string = "GET",
    *      reqData: *,
    *      authorization: {username: string, password: string}? = undefined
    * ) => Promise}
    * 
    * @param apiPath       API path to access.
    * @param method        HTTP method. Defaults to "GET".
    * @param reqData       Request data. Optional.
    * @param authorization Login credentials. Optional.
    * 
    * @returns Data returned from the API.
    */
const apiCall = window["apiCall"];

/**
 * Renders a fictionsource Markdown document as HTML.
 * @type {(markdownText: string) => string}
 * 
 * @param markdownText The text to translate into HTML.
 * @returns HTML fragment that can be inserted via `HTMLElement.innerHTML`.
 */
const renderMarkdown = window["renderMarkdown"];

const commentList = document.getElementById("comment-list");

/** @type {number} */
const chapterId = document.getElementsByTagName("main")[0].dataset["chapterId"];

/** @type {number} */
const storyId = document.getElementsByTagName("main")[0].dataset["storyId"];

let numComments = commentList.childElementCount;

commentList.onclick = async (event) => {
    if (event.target.tagName.toLowerCase() === "button") {
        if (event.target.classList.contains("loading") || !coverIsHidden())
            return;
        event.target.classList.add("loading");

        /** @type {HTMLDivElement} */
        const parent = event.target.parentElement;

        /** @type {APIComment[]} */
        const replies = await apiCall(`comment/${parent.dataset["id"]}/replies?${
            event.target.classList.contains("more-replies") ?
                `offset=${parent.childElementCount - 1}&` :
                ""
        }count=11`);

        const repliesList = document.createElement("div");
        repliesList.className = "replies";
        
        replies.slice(0, 10).forEach(
            (reply) => repliesList.appendChild(renderComment(reply))
        );

        if (replies.length === 11) {
            const button = document.createElement("button");
            button.innerText = "Show More Replies";
            button.className = "more-replies";
            comment.appendChild(button);
        }

        event.target.parentNode.appendChild(repliesList);
        event.target.remove();
    }
};

/** @type {HTMLButtonElement} */
const moreCommentsButton = document.getElementById("more-comments");
if (moreCommentsButton !== null) {
    moreCommentsButton.onclick = async () => {
        if (moreCommentsButton.classList.contains("loading") || !coverIsHidden())
            return;
        moreCommentsButton.classList.add("loading");

        const parent = moreCommentsButton.parentElement;
        moreCommentsButton.remove();

        showCover();

        /** @type {APIComment[]} */
        const comments = await apiCall(`/chapter/${
            chapterId
        }/comments?offset=${
            numComments
        }&count=11`);

        comments.slice(0, 10).forEach(
            (comment) => commentList.appendChild(renderComment(comment))
        );

        if (comments.length === 11)
            parent.appendChild(moreCommentsButton);

        numComments += comments.length - 1;
        
        hideCover();
        moreCommentsButton.classList.remove("loading");
    };
}

document.getElementById("comments").onsubmit = async (event) => {
    if (event.target.id == "new-comment") {
        event.preventDefault();

        if (event.target.classList.contains("loading") || !coverIsHidden())
            return;

        showCover();
        event.target.classList.add("loading");

        const apiPath = event.target.dataset["id"] === undefined ?
            `chapter/${chapterId}/comments` :
            `comment/${event.target.dataset["id"]}/replies`
        ;

        /** @type {APIComment} */
        const newComment = await apiCall(apiPath, "POST", {
            "text": event.target.getElementsByTagName("textarea")[0].value
        });

        const commentHTML = renderComment(newComment);

        event.target.classList.remove("loading");
        hideCover();
    }
};

if (document.getElementById("favorite")) {
    /** @type {HTMLElement} */
    const favoriteButton = document.getElementById("favorite");

    /** @type {HTMLElement} */
    const followButton = document.getElementById("follow");

    /**
     * Handler for toggle API settings.
     * @param {Event} event An onclick event.
     */
    const handleToggleable = async (event) => {
        /** @type {HTMLElement} */
        const target = (event.target.tagName.toLowerCase() === "label") ?
            document.getElementById(event.target.htmlFor) :
            event.target
        ;

        if (target.classList.contains("loading") || !coverIsHidden())
            return;
        
            target.classList.add("loading");
        showCover();

        const apiTarget = (target === favoriteButton) ?
            `story/${storyId}/favorite` :
            `story/${storyId}/follow`
        ;

        const method = target.classList.contains("far") ? "POST" : "DELETE";

        await apiCall(apiTarget, method);
        
        if (target.classList.contains("far")) {
            target.classList.remove("far");
            target.classList.add("fas");

            target.nextElementSibling.innerText =
                "Un" + 
                target.nextElementSibling.innerText[0].toLowerCase() +
                target.nextElementSibling.innerHTML.slice(1)
            ;
        } else {
            target.classList.remove("fas");
            target.classList.add("far");

            target.nextElementSibling.innerText =
                target.nextElementSibling.innerText[2].toUpperCase() +
                target.nextElementSibling.innerHTML.slice(3)
            ;
        }

        hideCover();
        target.classList.remove("loading");
    };

    followButton.onclick = handleToggleable;
    followButton.nextElementSibling.onclick = handleToggleable;
    favoriteButton.onclick = handleToggleable;
    favoriteButton.nextElementSibling.onclick = handleToggleable;
}
