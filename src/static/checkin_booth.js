/**
 * RoboRegistry check-in booth script to auto reload upon completion.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    document.querySelector("iframe").addEventListener("load", handleLoad);
    function handleLoad() {
        const iframe = document.querySelector("iframe");

        // Remove the footer from the iframe as it is already on the page
        const footer = iframe.contentDocument.querySelector("footer");
        footer.remove();

        // Check the DOM to see if the form has been submitted and it has gone through successfully
        // Also reload the page if the user navigates away from the page and onto the view page
        const success = iframe.contentDocument.querySelector(".headertext");
        if ((success && success.textContent === "Check in successful") || (!iframe.contentDocument.title.includes("Checking in") && !iframe.contentDocument.title.includes("Event Register"))) {
            // Restart the iframe by making a brand new one
            const newIframe = document.createElement("iframe");
            newIframe.src = iframe.src;
            newIframe.width = iframe.width;
            newIframe.height = iframe.height;
            newIframe.classList = iframe.classList;

            // Replace the old one
            document.querySelector(".container").appendChild(newIframe);
            iframe.remove();
            newIframe.addEventListener("load", handleLoad);

            if (success && success.textContent === "Check in successful") {
                alert("Check in successful!");
            }
        }
    }
});