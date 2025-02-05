export function dateTimeInfo(dateObj) {

    return {
        year: dateObj.getFullYear().toString(),
        month: (dateObj.getMonth() + 1).toString().padStart(2, "0"),
        day: dateObj.getDate().toString().padStart(2, "0"),
        hours: dateObj.getHours().toString().padStart(2, "0"),
        minutes: dateObj.getMinutes().toString().padStart(2, "0")
    };
}

export function formatDateTime(dateTimeStr) {
    const dateTimeInfoObj = dateTimeInfo(new Date(dateTimeStr));
        const [year, month, day, hours, minutes] = Object.values(dateTimeInfoObj);

        const fDateTime = `${day}.${month}.${year} (${hours}:${minutes})`;

        return fDateTime;
}