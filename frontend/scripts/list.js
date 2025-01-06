export function updateListElements(data) {
    data.forEach((item) => {
        const title = item.title;
        const dateRange = `${item.time_start} - ${item.time_end}`;
        
        const listElement = `
            <div class="list-element">
                <p>${title}</p>
                <span>${dateRange}</span>
            </div>`;
        
        document.querySelector(".recording-plan-list").appendChild(listElement);
    })
}



