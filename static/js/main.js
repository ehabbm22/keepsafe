// document.getElementById('startButton').addEventListener('click', function() {
//     document.getElementById('startButtonContainer').style.display = 'none';
//     document.getElementById('formContainer').style.display = 'block';
// });

AOS.init({
    offset: 120,
    delay: 0,
    duration: 900,
    easing: 'ease',
    once: false,
    mirror: false,
    anchorPlacement: 'top-bottom',


});

// نموذج استقبال الرابط

// document.getElementById('linkForm').addEventListener('submit', function(event) {
//     event.preventDefault(); // منع الإرسال الافتراضي للنموذج

//     var modal = new bootstrap.Modal(document.getElementById('resultModal'));
//     modal.show();
// });