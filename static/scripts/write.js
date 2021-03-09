/**
 * @file write.js
 * @author Simon Struthers
 * @description General editing page interaction logic.
 */

/** @typedef {{
 *      author_notes: string?,
 *      text: string,
 *      name: string,
 *      modified: number,
 *      posted: number,
 *      id: number,
 *      previous: number?,
 *      next: number?,
 *      number: number?,
 *      story: number,
 *      private: boolean,
 *      protected: boolean
 *  }} APIChapter
 */

/** @typedef {{
 *      title: string,
 *      author: string,
 *      summary: string,
 *      thumbnail: string,
 *      id: number,
 *      chapters: (number | APIChapter)[],
 *      posted: number,
 *      modified: number,
 *      tags: string[],
 *      favorited_by: string[],
 *      num_favorites: number,
 *      followed_by: string[],
 *      num_follows: number,
 *      private: boolean,
 *      protected: boolean,
 *      can_comment: boolean,
 *      is_risque: boolean
 *  }} APIStory
 */

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

// String#replaceAll polyfill
String.prototype.replaceAll = String.prototype.replaceAll || function(str, newStr) {
    if (Object.prototype.toString.call(str).toLowerCase() === "[object regexp]") {
        return this.replace(str, newStr);
    }

    return this.replace(new RegExp(str, 'g'), newStr);
};

// show/hide cover animation
const toggleCover = () => {
    document.body.classList.toggle("cover");
};

// shows the loading cover
const showCover = () => document.body.classList.add("cover");

// hides the loading cover
const hideCover = () => document.body.classList.remove("cover");

// returns true if the cover is currently hidden
const coverIsHidden = () => !document.body.classList.contains("cover");

/* ============================================================================================== */

let canParseMD = false;

// updates the preview of the markdown output
const updatePreview = () => {
    if (canParseMD) {
        const text = document.getElementById("input").value;
        if (text.trim().length === 0)
            document.getElementById("output").innerHTML = "";
        else
            document.getElementById("output").innerHTML = renderMarkdown(text);
    }
};

window["markdown"].ready.then(() => {
    canParseMD = true;
    updatePreview();
});

window.onload = async () => {
    let saved = true;

    const username = localStorage.getItem("username");

    /** @type {HTMLDivElement} */
    const stories = document.getElementById("stories");

    /** @type {HTMLDivElement} */
    const chapters = document.getElementById("chapters");

    /** @type {HTMLInputElement} */
    const chapterPrivateBox = document.getElementById("chapter-private");
    
    /** @type {HTMLDivElement} */
    const storyFlags = document.getElementById("story-flags");

    /** @type {HTMLTextAreaElement} */
    const inputTextArea = document.getElementById("input");

    /** @type {HTMLTextAreaElement} */
    const summaryTextArea = document.getElementById("story-summary");

    /** @type {HTMLTextAreaElement} */
    const authorNotesTextArea = document.getElementById("chapter-author-notes");

    /** @type {HTMLButtonElement} */
    const saveChapterButton = document.getElementById("save-chapter");

    /** @type {HTMLFormElement} */
    const storyTagsForm = document.getElementById("story-tags");

    /** @type {HTMLInputElement} */
    const tagInput = document.getElementById("tag");

    /** @type {HTMLDivElement} */
    const tagOptionsList = document.getElementById("tag-options");

    /** @type {HTMLDivElement} */
    const storyThumbnail = document.getElementById("story-thumbnail");

    /** @type {HTMLFormElement} */
    const storyImageForm = document.getElementById("story-image-form");

    /**
     * Retrieves the currently selected story.
     */
    const currentStory = () => stories.getElementsByClassName("selected")[0];

    /**
     * Retrieves the currently selected chapter.
     */
    const currentChapter = () => chapters.getElementsByClassName("selected")[0];

    /**
     * Saves the current chapter.
     */
    const saveChapter = async () => {
        if (!saved) {
            if (saveChapterButton.classList.contains("loading"))
                return;
            
            saveChapterButton.classList.add("loading");
            showCover();

            if (stories.getElementsByClassName("selected").length === 0)
                return;

            await Promise.all([
                apiCall(`chapter/${currentChapter().dataset["id"]}`, "PATCH", {
                    text: inputTextArea.value,
                    author_notes: authorNotesTextArea.value
                }),
                apiCall(`story/${currentStory().dataset["id"]}`, "PATCH", {
                    summary: summaryTextArea.value
                })
            ]);

            if (inputTextArea.value.trim().length === 0)
                chapterPrivateBox.checked = true;
            
            hideCover();
            saveChapterButton.classList.remove("loading");

            saved = true;
        }
    };
    saveChapterButton.onclick = saveChapter;

    /**
     * Toggles the given chapter's private state.
     */
    chapterPrivateBox.onchange = async () => {
        if (chapterPrivateBox.classList.contains("loading"))
            return;
        
        chapterPrivateBox.classList.add("loading");
        showCover();

        try {
            await apiCall(`chapter/${currentChapter().dataset["id"]}`, "PATCH", {
                private: chapterPrivateBox.checked
            });
        } catch {
            chapterPrivateBox.checked = !chapterPrivateBox.checked;
        }
        
        hideCover();
        chapterPrivateBox.classList.remove("loading");
    };

    /**
     * Sets story-specific flags.
     */
    storyFlags.onchange = async (event) => {
        if (storyFlags.classList.contains("loading"))
            return;

        storyFlags.classList.add("loading");
        showCover();

        try {
            await apiCall(`story/${currentStory().dataset["id"]}`, "PATCH", {
                [event.target.dataset["flag"]]: event.target.checked
            });
        } catch {
            event.target.checked = !event.target.checked;
        }

        hideCover();
        storyFlags.classList.remove("loading");
    };

    /**
     * Creates a new row for the stories list.
     * 
     * @param {APIStory} story A story from the fictionsource API.
     * @return {HTMLElement} A row to add to the stories list.
     */
    const newStoryRow = ({ id, title }) => {
        const story = document.createElement("div");
        story.dataset["id"] = id;

        const delBtn = document.createElement("i");
        delBtn.className = "delete fas fa-times";
        story.append(delBtn);

        const div = document.createElement("div");
        div.innerText = title;
        story.appendChild(div);

        const renBtn = document.createElement("i");
        renBtn.className = "rename fas fa-edit";
        story.append(renBtn);

        return story;
    };

    /**
     * Creates a new row for the chapters list.
     * 
     * @param {APIChapter} chapter A chapter from the fictionsource API.
     * @return {HTMLElement} A row to add to the chapters list.
     */
    const newChapterRow = ({ id, name }) => {
        const chapter = document.createElement("div");
        chapter.dataset["id"] = id;

        const delBtn = document.createElement("i");
        delBtn.className = "delete fas fa-times";
        chapter.append(delBtn);

        const div = document.createElement("div");
        div.innerText = name;
        chapter.append(div);

        [
            "move-up fas fa-angle-up",
            "move-down fas fa-angle-down",
            "rename fas fa-edit"
        ].forEach((className) => {
            const button = document.createElement("i");
            button.className = className;
            chapter.append(button);
        });

        return chapter;
    };

    /**
     * Creates a new row for the tags list.
     * 
     * @param {string} name The tag name.
     * @return {HTMLElement} A row to add to the tags list.
     */
    const newTagRow = (name) => {
        const tag = document.createElement("div");
        tag.classList.add("tag");
        
        if (name.includes(':')) {
            const split = name.split(':')
            tag.classList.add(split[0])
            name = split[1]
        } else if (name.startsWith('#')) {
            name = name.slice(1);
        }
        
        tag.appendChild(document.createElement("span"));

        const span = document.createElement("div");
        span.innerText = name;
        tag.appendChild(span);

        const i = document.createElement("i");
        i.className = "delete fas fa-times";
        tag.appendChild(i);

        return tag;
    };

    /**
     * Process for creating a new story.
     * 
     * @returns {Promise<boolean>} True if a new story was created.
     */
    const newStory = async () => {
        const newStoryDiv = document.getElementById("new-story");
        if (newStoryDiv === undefined)
            return false;

        if (!saved) {
            if (!confirm(`Save changes to "${
                stories.getElementsByClassName("selected")[0] !== undefined ?
                    stories.getElementsByClassName("selected")[0].children[0].innerText :
                    "Untitled"
                }"?`
            ))
                return false;

            await saveChapter();
        }

        const storyName = prompt("Insert story name:");

        if (storyName !== null && storyName.trim().length > 0) {
            newStoryDiv.remove();
            showCover();

            /** @type {APIStory} */
            const storyInfo = await apiCall("story", "POST", {
                title: storyName.trim()
            });

            stories.appendChild(newStoryRow(storyInfo));
            stories.append(newStoryDiv);

            hideCover();
            return true;
        }

        return false;
    };

    /**
     * Sets the current chapter being displayed by the UI to a new ID.
     * @param {number} chapterId The ID of the chapter to load.
     */
    const setChapter = async (chapterId) => {
        chapterId = Number(chapterId);
        
        showCover();
        chapterPrivateBox.disabled = true;
        authorNotesTextArea.disabled = true;
        inputTextArea.disabled = true;

        if (chapterId > 0) {
            /** @type {APIChapter} */
            const { text, private, author_notes } = await apiCall(`chapter/${chapterId}`, "GET");

            chapterPrivateBox.checked = private;
            chapterPrivateBox.disabled = false;

            inputTextArea.value = text.trim();
            inputTextArea.disabled = false;

            authorNotesTextArea.value = author_notes ? author_notes : "";
            authorNotesTextArea.disabled = false;

            updatePreview();
        } else {
            document.getElementById("output").innerHTML = "";
            inputTextArea.value = "";
        }

        saved = true;
        hideCover();
    };

    /**
     * Sets the current story being displayed by the UI to a new ID.
     * @param {number} storyId The ID of the story to load.
     */
    const setStory = async (storyId) => {
        storyId = Number(storyId);

        showCover();

        if (!saved && confirm(`Save changes to "${
            currentChapter() ? currentChapter().getElementsByTagName("div")[0].innerText : ""
        }"?`))
            await saveChapter();

        const newChapterDiv = document.getElementById("new-chapter");
        newChapterDiv.remove();
        chapters.innerHTML = "";

        inputTextArea.value = "";
        inputTextArea.disabled = true;
        document.getElementById("output").innerHTML = "";
        
        tagInput.disabled = true;
        tagInput.value = "";
        tagInput.parentElement.remove();
        storyTagsForm.innerHTML = "";

        chapterPrivateBox.disabled = true;
        summaryTextArea.disabled = true;

        /** @type {APIStory} */
        const storyInfo = (storyId > 0) ?
            await apiCall(`story/${storyId}?expand`, "GET") :
            {
                chapters: [],
                tags: [],
                summary: "",
                thumbnail: "/static/images/thumbnails/default0.png"
            }
        ;

        storyInfo.chapters.forEach((chapter) => chapters.appendChild(newChapterRow(chapter)));
        chapters.appendChild(newChapterDiv);

        document.getElementById("story-thumbnail").src = storyInfo.thumbnail;

        if (storyInfo.chapters.length > 0) {
            chapters.children[0].classList.add("selected");
            await setChapter(storyInfo.chapters[0].id);
        }

        summaryTextArea.value = storyInfo.summary;
        summaryTextArea.disabled = false;

        storyInfo.tags.forEach((tagName) => storyTagsForm.appendChild(newTagRow(tagName)));
        storyTagsForm.appendChild(tagInput.parentElement);

        if (storyId !== 0) {
            tagInput.disabled = false;
            storyImageForm.action = `/write/${storyId}`;

            document.getElementById("story-private").checked = storyInfo.private;
            document.getElementById("can-comment").checked = storyInfo.can_comment;
            document.getElementById("is-risque").checked = storyInfo.is_risque;
        } else {
            storyImageForm.action = "";
        }

        saved = true;

        hideCover();
    };

    /**
     * Process for creating a new chapter.
     */
    const newChapter = async () => {
        const newChapterDiv = document.getElementById("new-chapter");
        if (newChapterDiv === undefined)
            return;

        const chapterName = prompt("Insert chapter name:");

        if (chapterName !== null && chapterName.trim().length > 0) {
            newChapterDiv.remove();
            showCover();

            /** @type {APIChapter} */
            const chapterInfo = await apiCall(
                `story/${currentStory().dataset["id"]}/chapters`,
                "POST",
                {
                    name: chapterName.trim()
                }
            );

            chapters.appendChild(newChapterRow(chapterInfo));
            chapters.appendChild(newChapterDiv);

            hideCover();
        }
    };

    stories.onclick = async (event) => {
        /** @type {HTMLElement} */
        const parent = event.target.parentElement;

        switch (event.target.nodeName.toLowerCase()) {
        case "i":
            const storyTitle = parent.getElementsByTagName("div")[0].innerText;

            if (event.target.classList.contains("delete")) {
                const pwd = prompt(`To delete "${storyTitle}", you must enter your password:`);

                if (pwd !== null) {
                    showCover();

                    try {
                        await apiCall("", "GET", undefined, {
                            username: username,
                            password: pwd
                        });

                        await apiCall(`story/${parent.dataset["id"]}`, "DELETE");

                        if (parent.classList.contains("selected")) {
                            const switchTo = parent.previousElementSibling ?
                                parent.previousElementSibling :
                                (parent.nextElementSibling ? parent.nextElementSibling : null)
                            ;

                            if (switchTo !== null) {
                                switchTo.classList.add("selected");
                                await setStory(switchTo.dataset["id"]);
                            } else {
                                await setStory(0);
                            }
                        }

                        parent.remove();
                    } catch (e) {
                        alert("Invalid credentials provided.");
                    }

                    hideCover();
                }
            } else if (event.target.classList.contains("rename")) {
                const newTitle = prompt(`Rename story "${storyTitle}":`);

                if (!!newTitle &&
                    newTitle.trim() !== storyTitle &&
                    newTitle.trim().length > 0
                ) {
                    showCover();

                    await apiCall(`story/${parent.dataset["id"]}`, "PATCH", {
                        title: newTitle.trim()
                    });
                    parent.getElementsByTagName("div")[0].innerText = newTitle;

                    hideCover();
                }
            }
            break;

        case "div":
            if (parent.classList.contains("selected") || parent.dataset["id"] === undefined)
                return;

            currentStory().classList.remove("selected");
            parent.classList.add("selected");

            await setStory(parent.dataset["id"]);
            break;
        }
    };

    chapters.onclick = async (event) => {
        /** @type {HTMLElement} */
        const parent = event.target.parentElement;

        switch (event.target.nodeName.toLowerCase()) {
        case "i":
            if (event.target.classList.contains("delete")) {
                const 
                    chapterTitle = parent.getElementsByTagName("div")[0].innerText,
                    pwd = prompt(`To delete "${chapterTitle}", you must enter your password:`)
                ;

                if (pwd !== null) {
                    showCover();

                    try {
                        await apiCall("", "GET", undefined, {
                            username: username,
                            password: pwd
                        });

                        await apiCall(`chapter/${parent.dataset["id"]}`, "DELETE");
                        
                        const switchTo = parent.previousElementSibling ?
                            parent.previousElementSibling :
                            (parent.nextElementSibling ? parent.nextElementSibling : null)
                        ;

                        if (switchTo !== null) {
                            switchTo.classList.add("selected");
                            await setChapter(switchTo.dataset["id"]);
                        } else {
                            await setChapter(0);
                        }
                        parent.remove();
                    } catch (e) {
                        alert("Invalid credentials provided.");
                    }

                    hideCover();
                }
            } else if (event.target.classList.contains("rename")) {
                const 
                    chapterName = parent.getElementsByTagName("div")[0].innerText,
                    newName = prompt(`Rename chapter "${chapterName}":`);
                ;

                if (!!newName &&
                    newName.trim() !== chapterName &&
                    newName.trim().length > 0
                ) {
                    showCover();

                    await apiCall(`chapter/${parent.dataset["id"]}`, "PATCH", {
                        name: newName.trim()
                    });
                    parent.getElementsByTagName("div")[0].innerText = newName;

                    hideCover();
                }
            } else if (
                event.target.classList.contains("move-up") &&
                parent.previousElementSibling
            ) {
                const sibling = parent.previousElementSibling;
                const index = Array.from(parent.parentElement.children).indexOf(parent) - 1;
                showCover();

                await apiCall(`chapter/${parent.dataset["id"]}`, "PATCH", { index });
                sibling.before(parent);

                hideCover();
            } else if (
                event.target.classList.contains("move-down") &&
                parent.nextElementSibling !== document.getElementById("new-chapter")
            ) {
                const sibling = parent.nextElementSibling;
                const index = Array.from(parent.parentElement.children).indexOf(parent) + 1;
                showCover();

                await apiCall(`chapter/${parent.dataset["id"]}`, "PATCH", { index });
                sibling.after(parent);

                hideCover();
            }
            break;

        case "div":
            if (parent.classList.contains("selected") || parent.dataset["id"] === undefined)
                return;

            if (!saved && confirm(`Save changes to "${
                    parent.getElementsByTagName("div")[0].innerText
                }"?`)
            )
                await saveChapter();

            currentChapter().classList.remove("selected");
            parent.classList.add("selected");

            await setChapter(parent.dataset["id"]);

            hideCover();
            break;
        }
    };

    // get list of story tags from markup
    const getTags = () => Array.from(
        storyTagsForm.children
    ).slice(
        0, storyTagsForm.childElementCount - 1
    ).map((element) =>
        (element.classList.contains("generic")) ?
            `#${element.children[1].innerText}` :
            `${element.className.replace("tag", "").trim()}:${element.children[1].innerText}`
    );

    // focus/blur handlers for tag options list
    tagInput.onfocus = () => tagOptionsList.style.visibility = "";
    tagInput.onblur = (event) => {
        if (!storyTagsForm.contains(event.relatedTarget))
            tagOptionsList.style.visibility = "hidden";
    };

    // update tag options listing
    const updateTagOptions = (tagQueryName = tagInput.value.trim()) => apiCall(
        "tag", "POST",
        {
            tag: tagQueryName,
            count: 10,
            exclude: getTags()
        }
    ).then((tags) => {
        tagOptionsList.innerHTML = "";
        
        tags.forEach(([tag, count], index) => {
            const t = document.createElement("div");
            t.className = "tag-listing";
            t.tabIndex = 0;
            t.onblur = tagInput.onblur;

            const text = document.createElement("span");
            text.innerText = tag;
            t.appendChild(text);

            const num = document.createElement("small");
            num.innerText = count !== null ? count : "(tag type)";
            t.appendChild(num);

            tagOptionsList.appendChild(t);
        });
    });

    // search tags
    tagInput.oninput = () => {
        const tagQueryName = tagInput.value.trim();
        if (tagQueryName.length >= 1)
            updateTagOptions();
        else
            tagOptionsList.innerHTML = "";
    };

    // copy tag in options listing to input box
    const setTagInput = (item) => {
        tagInput.value = item.children[0].innerText;
        if (item.children[1].innerText === "(tag type)")
            tagInput.value += ':';

        if (tagInput.value === "generic:")
            tagInput.value = '#';

        tagInput.focus();
        updateTagOptions();
    };

    // copy tag in options listing to input box
    tagOptionsList.onclick = (event) => {
        /** @type {HTMLDivElement} */
        const target = event.target.parentElement;
        
        if (target.className !== "tag-listing")
            return;

        setTagInput(target);
    };

    storyTagsForm.onkeydown = (event) => {
        if (event.target.className !== "tag-listing" && event.target !== tagInput) {
            return;
        } else if (event.target === tagInput) {
            if (event.key === "ArrowDown" && tagOptionsList.childElementCount > 0) {
                event.preventDefault();
                tagOptionsList.children[0].focus();
            }
        } else {
            // tag options list keyboard navigation
            switch (event.key) {
            case " ":
            case "Enter":
                event.preventDefault();
                setTagInput(event.target);
                break;

            case "ArrowDown":
                event.preventDefault();
                if (event.target === tagOptionsList.children[tagOptionsList.childElementCount - 1])
                    event.target.blur();
                else
                    event.target.nextElementSibling.focus();
                break;

            case "ArrowUp":
                event.preventDefault();
                if (event.target === tagOptionsList.children[0])
                    tagInput.focus();
                else
                    event.target.previousElementSibling.focus();
                break;
            }
        }
    };

    // remove tag
    storyTagsForm.onclick = async (event) => {
        const target = event.target.parentElement;
        if (target.classList.contains("tag") && event.target.classList.contains("delete")) {
            if (!coverIsHidden())
                return;
            showCover();

            const tagType = target.className.replace("tag", "").trim();
            const tagPrefix = tagType === "generic" ? "#" : tagType + ':';
            const tagQueryName = tagPrefix + target.children[1].innerText;

            await apiCall(`story/${currentStory().dataset['id']}/tags`, "DELETE", [
                tagQueryName
            ]);

            target.remove();
            hideCover();
        }
    };

    // add new tag
    storyTagsForm.onsubmit = async (event) => {
        event.preventDefault();

        if (storyTagsForm.classList.contains("loading") ||!coverIsHidden())
            return;

        if (getTags().indexOf(tagInput.value.trim()) >= 0) {
            tagInput.value = "";
            return;
        }
        
        storyTagsForm.classList.add("loading");
        showCover();

        const tagQueryName = tagInput.value.trim();
        if (tagQueryName.indexOf(':') < 0 && tagQueryName[0] !== '#') {
            alert("ERROR:\nTag must have a type (e.g. genre:tagname) or start with a hash (#).");

            storyTagsForm.classList.remove("loading");
            hideCover();
            return;
        }

        try {
            await apiCall(`story/${currentStory().dataset['id']}/tags`, "PUT", [
                tagQueryName
            ]);

            const newTagElement = newTagRow(tagQueryName);
            storyTagsForm.children[storyTagsForm.childElementCount - 1].before(newTagElement);
        } catch (e) {
            alert("ERROR:\n" + e.errors.join('\n'));
        }

        tagInput.value = "";
        tagOptionsList.innerHTML = "";
        storyTagsForm.classList.remove("loading");
        hideCover();
    };

    // bring up change thumbnail dialog
    storyThumbnail.onclick = () => {
        if (!coverIsHidden() || storyImageForm.action === "")
            return;
        
        showCover();
        storyImageForm.style.visibility = "visible";

        const cover = document.getElementById("cover");
        cover.onclick = (event) => {
            if (event.target === cover) {
                storyImageForm.style.visibility = "";
                hideCover();

                cover.onclick = undefined;
            }
        };
    };

    // submit new story image
    storyImageForm.onsubmit = (event) => {
        if (storyImageForm.action === "")
            event.preventDefault();
    };

    // create a new story
    document.getElementById("new-story").children[0].onclick = newStory;

    // create a new chapter
    document.getElementById("new-chapter").children[0].onclick = newChapter;
    
    inputTextArea.oninput = () => {
        saved = false;
        updatePreview();
    }
    summaryTextArea.oninput = () => { saved = false };
    authorNotesTextArea.oninput = () => { saved = false };
    
    if (inputTextArea.value.length > 0)
        updatePreview();
    
    window.onbeforeunload = (event) => {
        if (!saved) {
            const confirmationMessage = "If you leave before saving, your changes will be lost.";
            event.returnValue = confirmationMessage;
            return confirmationMessage;
        }
    };

    toggleCover();
};
