export function resetTimer(timerDisplay) {
    timerDisplay.innerHTML = "00: 00: 00";
}

export function refreshTimerDisplay(timerDisplay) {
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
     
    timerDisplay.innerHTML = 
    `${hours.toString().padStart(2, "0")}:
    ${minutes.toString().padStart(2, "0")}:
    ${seconds.toString().padStart(2, "0")}`;
}




    


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
