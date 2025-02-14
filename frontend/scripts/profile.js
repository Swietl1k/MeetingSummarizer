import { ApiClient } from "./ApiClient.js";

const apiClient = new ApiClient("http://127.0.0.1:8000/SummarizerApp");
const logoutButton = document.querySelector(".btn-logout");

const createUserInfoFields = (username, email) => {
    if (!username) {
        document.querySelector(".username").innerText = "-";
    } else {
        document.querySelector(".username").innerText = username;
    }

    if (!email) {
        document.querySelector(".email").innerText = "-";
    } else {
        document.querySelector(".email").innerText = email;
    }
}

apiClient.makeRequest({
    url: "/test",
    method: "get",
    withCredentials: true
})
    .then((data) => {
        createUserInfoFields(data.username, data.email);
        document.querySelector(".profile-card").style.display = "flex";
    })
    .catch((error) => {
        alert("Error: " + error.message);
        console.error("Error:" , error.message);
    });

    
logoutButton.addEventListener("click", () => {
    apiClient.makeRequest({
        url: "/logout",
        method: "get",
        withCredentials: true
    })
        .then(() => {
            window.location.replace("../views/login-register.html");
        })
        .catch((error) => {
            alert("Error: "+ error.message);
            console.error("Error:", error.message);
        });
});
