import { ApiClient } from "./ApiClient.js";


const apiClient = new ApiClient("http://127.0.0.1:8000/SummarizerApp");

const loginLink = document.querySelector(".login-form a");
const registerLink = document.querySelector(".register-form a");
const loginForm = document.querySelector(".login-form");
const registerForm = document.querySelector(".register-form");


apiClient.makeRequest({
    url: "/test",
    method: "get",
    withCredentials: true
})
    .then((data) => {
        if (data.uid !== null) {
            window.location.replace("../views/recording.html");
        }
    })
    .catch((error) => {
        alert("Error: " + error.message);
        console.error("Error:", error.message);
    })

registerForm.style.display = "none";

loginLink.addEventListener("click", () => {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
});

registerLink.addEventListener("click", () => {
    registerForm.style.display = "none";
    loginForm.style.display = "block";
});


const signInBtn = document.querySelector(".login-form .btn");

signInBtn.addEventListener("click", () => {
    apiClient.makeRequest({
        url: "/login/", 
        method: "post", 
        withCredentials: true,
        data: {
            username: document.querySelector(".login-form input[placeholder='Username']").value,
            password: document.querySelector(".login-form input[placeholder='Password']").value
        }})
            .then((response) => {
                console.log(response);
                window.location.replace("../views/recording.html");
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
            .then((response) => {
                registerForm.style.display = "none";
                loginForm.style.display = "block";
                console.log(response);
            })
            .catch((error) => {
                alert("Error: " + error.message);
                console.error("Error:", error.message);
            })
})





