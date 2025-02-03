import { ApiClient } from "./api-client.js";


const apiClient = new ApiClient("http://127.0.0.1:8000/SummarizerApp");

const loginLink = document.querySelector(".login-form a");
const registerLink = document.querySelector(".register-form a");
const loginForm = document.querySelector(".login-form");
const registerForm = document.querySelector(".register-form");

registerForm.style.display = "none";

loginLink.addEventListener("click", () => {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
});

registerLink.addEventListener("click", () => {
    registerForm.style.display = "none";
    loginForm.style.display = "block";
});


const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const signInBtn = document.querySelector(".login-form .btn");

signInBtn.addEventListener("click", () => {
    apiClient.makeRequest({
        url: "/login/", 
        method: "post", 
        withCredentials: true,
        headers: {
            'X-CSRFToken': crsfToken,
        },
        data: {
            username: document.querySelector(".login-form input[placeholder='Username']").value,
            password: document.querySelector(".login-form input[placeholder='Password']").value
        }})
            .then(() => {
                window.location.replace("../views/recording.html")
            })
            .catch((error) => {
                alert("Error: " + error.message);
                console.error("Error:", error.message);
            })
});
    


const signUpBtn = document.querySelector(".register-form .btn");

signUpBtn.addEventListener("click", () => {
    apiClient.makeRequest({
        url: "/register/", 
        method: "post", 
        data: {
            email: document.querySelector(".register-form input[placeholder='E-mail']").value,
            username: document.querySelector(".register-form input[placeholder='Username']").value,
            password: document.querySelector(".register-form input[placeholder='Password']").value
        }})
            .then(() => {
                registerForm.style.display = "none";
                loginForm.style.display = "block";
            })
            .catch((error) => {
                alert("Error: " + error.message);
                console.error("Error:", error.message);
            })
})





