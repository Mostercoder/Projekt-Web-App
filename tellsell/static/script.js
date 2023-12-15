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