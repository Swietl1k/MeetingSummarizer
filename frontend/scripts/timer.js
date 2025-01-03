let interval;

document.querySelector(".btn-start-recording").addEventListener("click", () => {
    // sending info to the server
    // getting the response from the server
    if (interval === undefined && localStorage.getItem("startTime") === null) {
        resetTimer();
        const startTime = new Date().getTime();
        localStorage.setItem("startTime", startTime);
        interval = setInterval(refreshTimerDisplay, 1000);
    }
})

document.querySelector(".btn-stop-recording").addEventListener("click", () => {
    // sending info to the server
    // getting the response from the server
    interval = clearInterval(interval);
    localStorage.removeItem("startTime");
})

document.querySelector(".btn-cancel-recording").addEventListener("click", () => {
    interval = clearInterval(interval);
    localStorage.removeItem("startTime");
    resetTimer();
})


window.addEventListener("load", () => {
    if (localStorage.getItem("startTime") !== null) {
        interval = setInterval(refreshTimerDisplay, 1000);
    }
})



function resetTimer() {
    document.querySelector(".timer-display").innerHTML = "00: 00: 00";
}

function refreshTimerDisplay() {
    const currentTime = new Date().getTime();
    const startTime = localStorage.getItem("startTime");
    const elapsedTime = currentTime - startTime;
    
    const hours = Math.floor(elapsedTime / (60 * 60 * 1000));
    const minutes = Math.floor((elapsedTime / (60 * 1000)) % 60);
    const seconds = Math.floor((elapsedTime / 1000) % 60);
    
    // if (seconds !== 59) {
    //     seconds += 1;
    // } else {
    //     seconds = 0;
    //     if (minutes !== 59) {
    //         minutes += 1;
    //     } else {
    //         minutes = 0;
    //         if (hours !== 23) {
    //             hours += 1;
    //         } else {
    //             hours = 0;
    //         }
    //     }
    // }
     
    document.querySelector(".timer-display").innerHTML = 
    `${hours.toString().padStart(2, "0")}:
    ${minutes.toString().padStart(2, "0")}:
    ${seconds.toString().padStart(2, "0")}`;
}
    


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
