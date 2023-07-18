/**
 * Driver for the Html5QrcodeScanner on a QR code reader page.
 * @author Lucas Bubner, 2023
 */

document.addEventListener("DOMContentLoaded", () => {
    const onScanSuccess = (qrCodeMessage) => {
        document.getElementById("event_url").value = qrCodeMessage;
        scanner.clear();
        document.querySelector("form").submit();
    };
    
    const scanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
    scanner.render(onScanSuccess);
});
