let time = 60;

let countdown = setInterval(function () {

    time--;

    document.getElementById("timer").innerHTML = time;

    if (time <= 0) {
        clearInterval(countdown);
        alert("Time Up!");
    }

}, 1000);