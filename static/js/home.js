// // Clears local storage if it's the user's first time visiting
// if (!sessionStorage.getItem("visited")) {
//     localStorage.clear();

//     sessionStorage.setItem("visited", "true");
// }

// Add an event listener to the search bar that listens for the search query
// and redirects the user to the search results page when they press "enter"
const myInput = document.getElementById("search-query");

myInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter"){
        event.preventDefault();

        const storedInput = Object.entries(localStorage)
        const userInput = myInput.value;

        localStorage.setItem("userInput"+ (storedInput.length+1) , userInput)

        window.location.href = "/search/" + userInput + "/";
    }
});

document.querySelector(".search-bar-backdrop").addEventListener("pointerdown", function(event) {
    event.preventDefault();
    document.querySelector('#search-query').blur();
});
