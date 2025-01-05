function dateTimeInfo(dateObj) {

    return {
        year: dateObj.getFullYear().toString(),
        month: (dateObj.getMonth() + 1).toString().padStart(2, "0"),
        day: dateObj.getDate().toString().padStart(2, "0"),
        hours: dateObj.getHours(),
        minutes: dateObj.getMinutes()
    };
}

function upadateCalendarParameters(dateStr, instance) {
        const currentDateTime = new Date();
        const currentDateTimeInfoObj = dateTimeInfo(currentDateTime);
        const [year, month, day, hours, minutes] = Object.values(currentDateTimeInfoObj);
        const currentDateTimeStr = `${year}-${month}-${day} ${hours}:${minutes}`;

        const minDateTime = instance.config.minDate;
        const minDateTimeInfoObj = dateTimeInfo(minDateTime);
        const [minYear, minMonth, minDay, minHours, minMinutes] = Object.values(minDateTimeInfoObj);
        const minDateTimeStr = `${minYear}-${minMonth}-${minDay} ${minHours}:${minMinutes}`;
        
        const chosenDateTimeStr = dateStr;
        
        
        if (minDateTime < currentDateTime) {
            instance.set("minDate", currentDateTimeStr);
        }

        if (chosenDateTimeStr.split(" ")[0] === minDateTimeStr.split(" ")[0]) {
            instance.set("defaultHour", minHours);
            instance.set("defaultMinute", minMinutes);
        } else {
            instance.set("defaultHour", "12");
            instance.set("defaultMinute", "0");
        }
}



flatpickr("#first-input-container", {
    enableTime: true,
    dateFormat: "Y-m-d H:i",
    altInput: true,
    altFormat: "d F Y (H:i K)",
    time_24hr: true,
    minDate: new Date(),
    minuteIncrement: 1,
    wrap: true,
    onOpen: function(selectedDates, dateStr, instance) {
        const endInputDateTime = document.querySelector(
            ".recording-planning input[placeholder='End date and time']"
        ).value;
        
        const currentDateTime = new Date();
        const currentDateTimeInfoObj = dateTimeInfo(currentDateTime);
        const [year, month, day, hours, minutes] = Object.values(currentDateTimeInfoObj);
        const currentDateTimeStr = `${year}-${month}-${day} ${hours}:${minutes}`;

        instance.set("minDate", currentDateTimeStr);

        if (endInputDateTime !== "" && new Date(endInputDateTime) > instance.config.minDate) {
            instance.set("maxDate", endInputDateTime);
        } else {
            instance.set("maxDate", "");
        }
    },
    onChange: function(selectedDates, dateStr, instance) {
        upadateCalendarParameters(dateStr, instance);
        
    }
  });

flatpickr("#second-input-container", {
    enableTime: true,
    dateFormat: "Y-m-d H:i",
    altInput: true,
    altFormat: "d F Y (H:i K)",
    time_24hr: true,
    minDate: new Date(),
    minuteIncrement: 1,
    wrap: true,
    onOpen: function(selectedDates, dateStr, instance) {
        const startInputDateTime = document.querySelector(
            ".recording-planning input[placeholder='Start date and time']"
        ).value;

        const currentDateTime = new Date();
        const currentDateTimeInfoObj = dateTimeInfo(currentDateTime);
        const [year, month, day, hours, minutes] = Object.values(currentDateTimeInfoObj);
        const currentDateTimeStr = `${year}-${month}-${day} ${hours}:${minutes}`;

        if (startInputDateTime === "" || new Date(startInputDateTime) < currentDateTime) {
            instance.set("minDate", currentDateTimeStr);
        } else {
            instance.set("minDate", startInputDateTime);
        }      
    },
    onChange: function(selectedDates, dateStr, instance) {
        upadateCalendarParameters(dateStr, instance);
    }
  });


document.querySelector(".recording-planning button").addEventListener("click", () => {
    const startDateTimeStr = document.querySelector(
        ".recording-planning input[placeholder='Start date and time']"
    ).value;
    
    const endDateTimeStr = document.querySelector(
        ".recording-planning input[placeholder='End date and time']"
    ).value;
    
    

    if (startDateTimeStr === "" || endDateTimeStr === "") {
        alert("Please fill in both date and time fields.");
        return;
    } else {
        const startDateTime = new Date(startDateTimeStr);
        const endDateTime = new Date(endDateTimeStr);

        if (startDateTime >= endDateTime) {
            alert("Start date should be earlier than end date.");
            return;
        }
    }

    const data = {
        start: startDateTimeStr, 
        end: endDateTimeStr
    }

    console.log(data);

    axios.post("/api", data)
    .then((response) => {
        console.log(response);
    })
    .catch((error) => {
        console.log(error);
    });
});