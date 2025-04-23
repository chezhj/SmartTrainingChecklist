document.addEventListener("DOMContentLoaded", function () {
    const pilotRoleSwitch = document.getElementById("pilot_role");
    const captainRoleSwitch = document.getElementById("captain_role");

    function updateSessionRoles(callback) {
        const pilotRole = pilotRoleSwitch.checked ? "PM" : "PF";
        const captainRole = captainRoleSwitch.checked ? "FO" : "C";

        // Send an AJAX request to update the session
        fetch("/update-session-role/", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value, // Include CSRF token
            },
            body: new URLSearchParams({
                pilot_role: pilotRole,
                captain_role: captainRole,
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    console.log("Session updated:", data);
                    // Call the callback function if provided
                    if (typeof callback === "function") {
                        callback();
                    }
                } else {
                    console.error("Failed to update session.");
                }
            })
            .catch((error) => {
                console.error("Error:", error);
            });
    }

    // Add event listeners to the switches
    if (pilotRoleSwitch && captainRoleSwitch) {
        pilotRoleSwitch.addEventListener("change", () => updateSessionRoles());
        captainRoleSwitch.addEventListener("change", () => updateSessionRoles());
    }

    // Expose the function to the global scope
    window.updateSessionRoles = updateSessionRoles;
});