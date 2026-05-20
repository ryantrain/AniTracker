const myInput = document.getElementById("search-query");
const storageDisplay = document.getElementsByClassName("search-bar-dropdown");
const body = document.body;

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
    body.classList.remove('search-active');
});


// Populate dropdown from localStorage
function renderStorageDropdown() {
    storageDisplay.innerHTML = '';
    for (let i = localStorage.length; i > 0; i--) {
        const key = localStorage.key(i);
        const value = localStorage.getItem("userInput"+i);
        if (value && value.trim() !== ''){
            const div = document.createElement('a');
            div.classList.add('search-bar-dropdown-item');
            div.setAttribute('href', './search/' + value + '/');
            div.textContent = value;
            div.addEventListener('click', () => {
                storageDisplay.innerHTML = '';  
                window.location.href = "/search/" + value + "/";
            });
            storageDisplay[0].appendChild(div);
        }

    }

}

renderStorageDropdown();

// On enter, save to localStorage and redirect
myInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        const userInput = myInput.value;
        localStorage.setItem("userInput" + (localStorage.length + 1), userInput);
        window.location.href = "/search/" + userInput + "/";
    }
});

// show the global backdrop while the input is focused
myInput.addEventListener('focus', function() {
    body.classList.add('search-active');
});

myInput.addEventListener('blur', function() {
    // small timeout to allow clicks inside dropdown to register
    setTimeout(() => body.classList.remove('search-active'), 0);
});
