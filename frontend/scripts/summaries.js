import { ApiClient } from "./api-client.js";


function createSummariesCards(results) {
    const mainContent = document.querySelector(".main-content");
    mainContent.innerHTML = "";
    
    results.forEach(item => {
        const sid = item.SID;
        const title = item.title;
        const dateRange = `${item.time_start} - ${item.time_end}`;
    
        const summaryCard = document.createElement("div");
        summaryCard.className = "summary-card";
        summaryCard.id = sid;
    
        summaryCard.innerHTML = `
            <div class="header-container">
              <span class="material-symbols-outlined">
                more_vert
              </span>
            </div>
            <div class="docs-symbol-container">
              <span class="material-symbols-outlined">
                docs
              </span>
            </div>
            <div class="description-container">
              <p>
                ${title}
              </p>
              <span>
                ${dateRange}
              </span>
            </div>
        `

        mainContent.appendChild(summaryCard);
    });
}



const apiClient = new ApiClient("http://127.0.0.1:8000/SummarizerApp");

const updateSummariesGrid = (requestConfig) => {
    apiClient.makeRequest(requestConfig)
        .then((data) => createSummariesCards(data.results))
        .catch((error) => {
            alert("Error: " + error.message);
            console.error("Error:", error.message);
        });
};
    
updateSummariesGrid({url: "/get_summaries", method: "get", credentials: "include"});


const summaryCard = null;
const contextMenu = document.querySelector("#context-menu");

document.addEventListener("click", (event) => {
    if (contextMenu.style.display === "block") {
        contextMenu.style.display = "none";
    } else if (event.target.matches(".header-container span")) {
        summaryCard = event.target.parentElement.parentElement;
        
        contextMenu.style.left = summaryCard.offsetLeft + "px";
        contextMenu.style.top = summaryCard.offsetTop + "px"; 
        contextMenu.style.display = "block";        
    }
});



contextMenu.addEventListener("click", (event) => {
    if (event.target.closest(".open-summary")) {
        apiClient.makeRequest({
            url: "/generate_pdf", 
            method: "post", 
            data: {SID: summaryCard.getAttribute("id")},
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/pdf"   
            },
            responseType: "blob"
        })
            .then((data) => {
                pdf = new Blob([data], {type: "application/pdf"});
                url = URL.createObjectURL(pdf);
                open(url, "_blank");
            })
            .catch((error) => {
                alert("Error: " + error.message);
                console.error("Error:", error.message);
            });
    
    } else if (event.target.closest(".delete-summary")) {
        apiClient.makeRequest({url: "/delete_summary/", method: "post", data: {SID: summaryCard.getAttribute("id")}})
            .then(() => updateSummariesGrid({url: "/get_summaries", method: "get"}))
            .catch((error) => {
                alert("Error: " + error.message);
                console.error("Error:", error.message);
            });
    }
});






