/**
 * Dynamically edit the jdenticon when the user changes their name.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    const firstName = document.getElementById("first");
    const lastName = document.getElementById("last");
    const pfp = document.getElementById("dpfp");

    const change = () => {
        pfp.setAttribute("data-jdenticon-value", `${firstName.value} ${lastName.value}`);
        jdenticon.update("#dpfp");
    };

    firstName.addEventListener("input", change);
    lastName.addEventListener("input", change);
});
