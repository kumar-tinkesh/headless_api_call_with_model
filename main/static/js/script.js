async function submitForm(event) {
    event.preventDefault(); // Prevent default form submission

    // Retrieve the input value
    const query = document.getElementById('query').value;

    // Show loading indicator
    const loadingIndicator = document.getElementById('loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }

    try {
        const response = await fetch('/process-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });

        if (response.ok) {
            const result = await response.json();
            console.log("Full response:", result);

            const externalApiResponse = result.external_api_response;
            const usrDateFromMdl = result.updated_mdl_res_with_value;
            const url = usrDateFromMdl.endpoint_url;
            const payloadDataFromMdl = usrDateFromMdl.payload;

            // Update API response section
            document.getElementById('api-response-content').innerText = JSON.stringify(externalApiResponse, null, 2);

            // Update URL container
            document.getElementById('url-container').innerText = `Endpoint: ${url}`;

            // Update summary
            let summaryText = result.summary?.summary || "No summary available.";
            document.getElementById('summary-container').innerHTML = formatSummaryWithSectionsAndBulletPoints(summaryText);

            // Notify about missing keys
            const keysWithoutValues = Object.fromEntries(
                Object.entries(payloadDataFromMdl).filter(([_, value]) => !value)
            );

            const missingKeysContainer = document.getElementById('missing-keys-container');
            if (Object.keys(keysWithoutValues).length > 0) {
                missingKeysContainer.innerHTML = 'The following keys are missing values:<ul>' +
                    Object.keys(keysWithoutValues).map(key => `<li>${key}</li>`).join('') +
                    '</ul>';
            } else {
                missingKeysContainer.innerHTML = '';
            }

        } else {
            console.error("Error response:", await response.json());
            document.getElementById('response-container').innerText = "Error submitting query.";
        }
    } catch (error) {
        console.error("Error:", error);
        document.getElementById('response-container').innerText = "An unexpected error occurred.";
    } finally {
        // Hide loading indicator after processing (whether success or error)
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}



// Function to format the summary text based on **bold** as section titles and *italic* as bullet points
function formatSummaryWithSectionsAndBulletPoints(summaryText) {
    // Regex to match **bold** (section titles) and *italic* (bullet points)
    const boldRegex = /\*\*(.*?)\*\*/g; // Matches **bold** sections (for titles)
    const italicRegex = /\*(.*?)\*/g;  // Matches *italic* text (for bullet points)

    // Replace **bold** with <strong> and add two line breaks for spacing
    let formattedText = summaryText.replace(boldRegex, (match, p1) => {
        // Remove the colon from the bold section to keep it on the same line
        let cleanedTitle = p1.trim().endsWith(':') ? p1.trim() : p1 + ':';
        return `<br><strong>${cleanedTitle}</strong><br><br>`; // Adds extra space for separation
    });

    // Replace *italic* with <li> for bullet points and ensure spacing
    formattedText = formattedText.replace(italicRegex, (match, p1) => {
        return `<li>${p1}</li><br>`; // Adds a line break after each bullet point
    });

    // Ensure bullet points are wrapped properly in a <ul>
    formattedText = `<ul>\n${formattedText}\n</ul><br>`;

    return formattedText;
}