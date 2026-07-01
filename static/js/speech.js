const recognition = new webkitSpeechRecognition();

recognition.continuous = true;
recognition.lang = "en-US";

function startSpeech() {
    recognition.start();
}

recognition.onresult = function(event) {

    let transcript =
        event.results[event.results.length - 1][0].transcript;

    document.getElementById("answer").value += transcript + " ";
};