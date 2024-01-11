//// script.js
//
//// Define the function to navigate to the sell_item route
//function navigateToSellItem() {
//    window.location.href = '/sell_item';
//  }
//  
//// event listener to the button
//document.getElementById('goto_sell_item').addEventListener('click', navigateToSellItem);
//
//function addItem() {
//  const form = document.getElementById('addItemForm');
//
//  // Use FormData to serialize the form data
//  const formData = new FormData(form);
//
//  // Fetch the /add_item route using the form data
//  fetch('/add_item', {
//    method: 'POST',
//    body: formData,
//  })
//  .then(response => response.json())
//  .then(data => console.log(data))
//  .catch(error => console.error('Error:', error));
//}
//
//document.getElementById('addItemButton').addEventListener('click', addItem);
function toggleHeart() {
    var heartIcon = document.getElementById('heartIcon');
    
    if (heartIcon.getAttribute('name') === 'heart-outline') {
      heartIcon.setAttribute('name', 'heart');
    } else {
      heartIcon.setAttribute('name', 'heart-outline');
    }
    }

function displayOwnerProfile(element) {
  // Get the user_id from the data attribute
  var user_id = element.getAttribute("data-user-id");
  
  // Redirect to the user profile page
  window.location.href = "/user_profile/" + user_id;
}


  function previewImage() {
      var input = document.getElementById('item_picture');
      var preview = document.getElementById('preview');
      
      console.log("File input:", input);
      if (input.files && input.files[0]) {
          console.log("Selected file:", input.files[0]);
          var reader = new FileReader();
          reader.onload = function(e) {
              console.log("FileReader result:", e.target.result);
              preview.src = e.target.result;
              preview.style.display = 'block'; // Show the image
          };
          reader.readAsDataURL(input.files[0]);
      } else {
          console.log("No file selected");
          preview.src = '';
          preview.style.display = 'none'; // Hide the image if no file selected
      }
  }

function toggleDropdown() {
  var sortBtn = document.querySelector('.sort-btn');
  var sortDropdown = document.querySelector('.sort-dropdown');

  sortDropdown.style.display = (sortDropdown.style.display === 'block') ? 'none' : 'block';
  sortBtn.classList.toggle('active', sortDropdown.style.display === 'block');
}

document.addEventListener('click', function (event) {
  var sortContainer   = document.getElementById('sortContainer');
  var sortDropdown    = document.querySelector('.sort-dropdown');
  var sortBtn         = document.querySelector('.sort-btn');

  if (!sortContainer.contains(event.target)) {
    sortDropdown.style.display = 'none';
    sortBtn.classList.remove('active');
  }
});