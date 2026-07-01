function sendMessage(){

let answer =
document.getElementById("answer").value;

let box =
document.getElementById("chat-box");

box.innerHTML +=
`<div class="user-message">${answer}</div>`;

document.getElementById("answer").value = "";

}

function startVoice(){

let recognition =
new webkitSpeechRecognition();

recognition.start();

recognition.onresult =
function(event){

document.getElementById("answer")
.value =
event.results[0][0].transcript;

}

}

let timeLeft = 300;

setInterval(function(){

if(timeLeft > 0){

timeLeft--;

document.getElementById("time")
.innerHTML = timeLeft;

}

},1000);