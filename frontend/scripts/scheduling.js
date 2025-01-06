import {updateListElements} from "./list.js"

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
    dateFormat: "Y-m-dTH:i:S",
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
    dateFormat: "Y-m-dTH:i:S",
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
    
    const title = document.querySelector(
        ".recording-planning input[placeholder='Title']"
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

    const scheduleData = {
        title: title,
        time_start: startDateTimeStr, 
        time_end: endDateTimeStr
    }

    console.log(scheduleData);

    axios.post("http://127.0.0.1:8000/SummarizerApp/schedule_recording", scheduleData)
        .then((response) => {
            const data = response.data;
        
            if (data.message == "Recording scheduled correctly") {
                axios.get("http://127.0.0.1:8000/SummarizerApp/get_recordings")
                    .then((response) => {
                        if ("results" in response) {
                            updateListElements(response.data.results)
                        } else {
                            alert(response.data.message)
                        }
                    })
                    .catch((error) => {
                        console.log(error);
                    })

            } else if ("message" in data) {
                alert(data.message);
            } else if ("error" in data) {
                alert(data.error);
            } else {
                alert(data)
            }
    })
    .catch((error) => {
        console.log(error);
    });
});