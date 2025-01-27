import { resetTimer, refreshTimerDisplay } from "./timer.js";

const successRegex = /20\d/;
const errorRegex = /[4,5]\d{2}/;

async function startRecording(url, title) {
    const response = await axios.post(url, {
            title: title
        })
    
    if (successRegex.test(response.status.toString())) {
        return response.data.message;
    }

    if (errorRegex.test(response.status)) {
        throw new Error(response.data.message);
    }
}

async function endRecording(url) {
    const response = await axios.get(url);

    if (successRegex.test(response.ststus.toString())) {
        return response.data.message;
    }

    if (errorRegex.test(response.status.toString())) {
        throw new Error(response.data.message || response.data.error);
    }
}

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
        startRecording("http://127.0.0.1:8000/SummarizerApp/start_recording", title)
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
})


const stopButton = document.querySelector(".btn-stop-recording");

stopButton.addEventListener("click", () => {
    if (interval || localStorage.getItem("startTime")) {
        endRecording("http://127.0.0.1:8000/SummarizerApp/end_recording")
            .then((message) => {
                alert(message);
                interval = clearInterval(interval);
                localStorage.removeItem("startTime");
            })
            .catch((error => {
                alert("Errror: " + error.message);
                console.log("Error: ", error.message);
            }))
    }
})


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
})