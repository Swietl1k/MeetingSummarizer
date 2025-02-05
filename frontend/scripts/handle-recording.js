import { ApiClient } from "./ApiClient.js";
import { resetTimer, refreshTimerDisplay } from "./timer.js";
import { getCookie } from "./get-cookie.js";


const apiClient = new ApiClient("http://127.0.0.1:8000/SummarizerApp");
let interval;
const timerDispaly = document.querySelector(".timer-display");

const startButtton = document.querySelector(".btn-start-recording");

startButtton.addEventListener("click", () => {
    const title = document.querySelector(
        ".recording-support input[placeholder='Title']"
    ).value;

    if (title === "") {
        alert("Please fill in input field.");
        return;
    }

    if (interval === undefined && localStorage.getItem("startTime") === null) {
        console.log(getCookie("csrftoken"));
        apiClient.makeRequest({
            url: "/start_recording/",
            method: "post",
            data: {
                title: title
            },
            withCredentials: true,
            headers: {
                "X-CSRFToken": getCookie("csrftoken")
            }
        })
            .then(() => {
                resetTimer(timerDispaly);
                const startTime = new Date().getTime();
                localStorage.setItem("startTime", startTime);
                interval = setInterval(() => {
                    refreshTimerDisplay(timerDispaly);
                }, 1000);
            })
            .catch((error) => {
                alert("Error: " + error.message);
                console.log("Error: ", error.message);
            });
    }   
});


const stopButton = document.querySelector(".btn-stop-recording");

stopButton.addEventListener("click", () => {
    if (interval || localStorage.getItem("startTime")) {
        apiClient.makeRequest({
            url: "/end_recording",
            method: "get",
            withCredentials: true
        })
            .then((message) => {
                alert(message);
                interval = clearInterval(interval);
                localStorage.removeItem("startTime");
            })
            .catch((error) => {
                alert("Errror: " + error.message);
                console.log("Error: ", error.message);
            });
    }
});


// document.querySelector(".btn-cancel-recording").addEventListener("click", () => {
//     interval = clearInterval(interval);
//     localStorage.removeItem("startTime");
//     resetTimer();
// })

window.addEventListener("load", () => {
    if (localStorage.getItem("startTime") !== null) {
        interval = setInterval(() => {
            refreshTimerDisplay(timerDispaly);
        }, 1000);
    }
});