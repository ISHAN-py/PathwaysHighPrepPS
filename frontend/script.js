document.addEventListener("DOMContentLoaded", () => {
    const kycForm = document.getElementById("kyc-form");
    const submitBtn = document.getElementById("submit-btn");
    const loader = document.getElementById("loader");
    const resultsContainer = document.getElementById("results-container");
    const resultsJson = document.getElementById("results-json");

    // The URL of your FastAPI backend
    const API_URL = "http://127.0.0.1:8000/check-kyc/";

    kycForm.addEventListener("submit", async (e) => {
        e.preventDefault(); // Prevent default form submission

        const doc1Input = document.getElementById("doc1");
        const doc2Input = document.getElementById("doc2");

        // Basic validation
        if (doc1Input.files.length === 0 || doc2Input.files.length === 0) {
            alert("Please upload both documents.");
            return;
        }

        // Show loader and disable button
        loader.classList.remove("hidden");
        resultsContainer.classList.add("hidden");
        submitBtn.disabled = true;
        submitBtn.textContent = "Checking...";

        // Create FormData to send files
        const formData = new FormData();
        formData.append("doc1", doc1Input.files[0]);
        formData.append("doc2", doc2Input.files[0]);

        try {
            const response = await fetch(API_URL, {
                method: "POST",
                body: formData,
                // Note: Don't set 'Content-Type' header
                // The browser will automatically set it to 'multipart/form-data'
                // with the correct boundary.
            });

            const data = await response.json();

            // Display results
            if (!response.ok) {
                // Handle API errors (e.g., 400, 500)
                throw new Error(data.detail || "An error occurred");
            }

            displayResults(data);

        } catch (error) {
            // Handle network errors or API errors
            displayResults({
                status: "ERROR",
                message: "Failed to connect to the API or an error occurred.",
                error: error.message,
            });
        } finally {
            // Hide loader and re-enable button
            loader.classList.add("hidden");
            submitBtn.disabled = false;
            submitBtn.textContent = "Check Documents";
        }
    });

    function displayResults(data) {
        // Format the JSON for pretty printing
        const formattedJson = JSON.stringify(data, null, 2);
        resultsJson.textContent = formattedJson;

        // Add color coding based on status
        if (data.status === "FAILED" || data.status === "ERROR") {
            resultsJson.style.color = "#d32f2f"; // Red
        } else if (data.status === "PASSED") {
            resultsJson.style.color = "#388e3c"; // Green
        } else {
            resultsJson.style.color = "#333"; // Default
        }

        resultsContainer.classList.remove("hidden");
    }
});