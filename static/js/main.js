// Client-side form validation (Section 4.5 - Programming)
// Provides real-time feedback before the form reaches the server
document.addEventListener("DOMContentLoaded", function () {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            let valid = true;
            const messages = [];

            form.querySelectorAll("[required]").forEach(function (field) {
                field.style.border = "";
                if (!field.value.trim()) {
                    valid = false;
                    field.style.border = "1.5px solid #d64545";
                    messages.push(field.previousElementSibling ? field.previousElementSibling.textContent + " is required." : "This field is required.");
                }
            });

            const emailField = form.querySelector('input[type="email"]');
            if (emailField && emailField.value && !emailPattern.test(emailField.value)) {
                valid = false;
                emailField.style.border = "1.5px solid #d64545";
                messages.push("Please enter a valid email address.");
            }

            const passwordField = form.querySelector('input[type="password"]');
            if (passwordField && passwordField.value && passwordField.value.length < 8) {
                valid = false;
                passwordField.style.border = "1.5px solid #d64545";
                messages.push("Password must be at least 8 characters.");
            }

            if (!valid) {
                e.preventDefault();
                alert(messages.join("\n"));
            }
        });
    });
});