function notification() {
    alert("Button clicked!");
}

function Animals() {
    alert("you wanna buy some animals?");
}

// Attaching the function to the button click event
document.getElementById("button_1").addEventListener("click", notification);

document.getElementById("cat_1").addEventListener("click", Animals);