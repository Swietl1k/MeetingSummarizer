import { ApiClient } from "./ApiClient.js";
import { formatDateTime } from "./date-time-info.js";
import { getCookie } from "./get-cookie.js";


export function createListElements(data) {
    const scrollbox = document.querySelector(".scrollbox");
    scrollbox.innerHTML = "";
    
    data.forEach((item) => {
        const rid = item.RID;
        const title = item.title;
        const dateRange = `${formatDateTime(item.time_start)} - ${formatDateTime(item.time_end)}`;

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

export function updateListElements(apiClient) {
    apiClient.makeRequest({
        url: "/get_recordings",
        method: "get",
        withCredentials: true
    })
        .then((data) => {
            console.log(data);
            createListElements(data);
        })
        .catch((error) => {
            alert("Error: " + error.message);
            console.error("Error:", error.message);
        })
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


const apiClient = new ApiClient("http://127.0.0.1:8000/SummarizerApp");
updateListElements(apiClient);

let contextMenu = document.getElementById("context-menu");

document.querySelector(".scrollbox").addEventListener("contextmenu", (event) => {
    const listElement = event.target.closest(".list-element");
    
    if (listElement) {
        event.preventDefault();
        updateContextMenuPosition(contextMenu, event.clientX, event.clientY);

        const rid = listElement.getAttribute("id");
        
        contextMenu.replaceWith(contextMenu.cloneNode(true));
        contextMenu = document.getElementById("context-menu");

        contextMenu.addEventListener("click", (event) => {
            if (event.target.closest(".delete-recording")) {
                apiClient.makeRequest({
                    url: "/delete_recording/",
                    method: "post",
                    data: {
                        RID: rid
                    },
                    withCredentials: true,
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken")
                    }
                })
                    .then((response) => updateListElements(apiClient))
                    .catch((error) => {
                        alert("Error: " + error.message);
                        console.error("Error:", error.message);
                    })
            }
        });
    }
});

document.addEventListener("click", () => {
    contextMenu.style.display = "none"; 
})

