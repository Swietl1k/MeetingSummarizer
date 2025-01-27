import { getRecordings } from "./scheduling.js";


export function updateListElements(data) {
    const scrollbox = document.querySelector(".scrollbox");
    scrollbox.innerHTML = "";
    
    data.forEach((item) => {
        const rid = item.RID;
        const title = item.title;
        const dateRange = `${item.time_start} - ${item.time_end}`;

        const listElement = document.createElement("div");
        listElement.className = "list-element";
        listElement.id = rid;

        listElement.innerHTML = `
            <p>${title}</p>
            <span>${dateRange}</span>
        `

        scrollbox.appendChild(listElement);
    });
}


async function deleteRecording(url, rid) {
    const response = await axios.post(url, {
            RID: rid
        });

    const successRegex = /20\d/;
    if (successRegex.test(response.status.toString())) {
        return response.data.message;
    }

    const errorRegex = /[4,5]\d{2}/;
    if (errorRegex.test(response.status.toString())) {
        throw new Error(response.data.error || response.data.message);
    }
}



const updateContextMenuPosition = (contextMenu, mousePositionX, mousePositionY) => {
    contextMenu.style.display = "block";

    const maxOffsetX = window.innerWidth - contextMenu.offsetWidth;
    const maxOffsetY = window.innerHeight - contextMenu.offsetHeight;

    contextMenu.style.left = `${mousePositionX}px`;
    contextMenu.style.top = `${mousePositionY}px`;

    if (maxOffsetX <= mousePositionX) {
        contextMenu.style.left = `${mousePositionX - contextMenu.offsetWidth}px`;
    }

    if (maxOffsetY <= mousePositionY) {
        contextMenu.style.top = `${mousePositionY - contextMenu.offsetHeight}px`;
    }
}

const contextMenu = document.getElementById("context-menu");

document.querySelector(".scrollbox").addEventListener("contextmenu", (event) => {
    const listElement = event.target.closest(".list-element");
    
    if (listElement) {
        event.preventDefault();
        updateContextMenuPosition(contextMenu, event.clientX, event.clientY);

        const rid = listElement.getAttribute("id");
        
        contextMenu.addEventListener("click", (event) => {
            if (event.target.closest(".delete-recording")) {
                deleteRecording("http://127.0.0.1:8000/SummarizerApp/delete_recording", rid)
                    .then(() => getRecordings("http://127.0.0.1:8000/SummarizerApp/get_recordings/"))
                    .then((results) => updateListElements(results))
                    .catch((error) => {
                        alert("Error: " + error.message);
                        console.error("Error: ", error.message);
                    });
            }
        });
    }
});

document.addEventListener("click", () => {
    contextMenu.style.display = "none"; 
})

