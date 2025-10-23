

-----
DEMO VIDEO DRIVE LINK --> https://drive.google.com/file/d/1MKc3rrOSyex1RZOaQOoQdzBLflNWz_tA/view?usp=sharing

# Smart KYC Checker

This is a simple AI-powered KYC checker. You upload two documents (like an Aadhar and a PAN card), and it uses OCR and AI to extract the text, find key details (like name and DOB), and check if they match.

## How to Set Up and Test

### 1\. System Prerequisite (Super Important\!)

This project relies on Google's Tesseract-OCR engine. You **must** install it on your system first (this is *not* a Python package).

  * **On macOS:** `brew install tesseract`
  * **On Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
  * **On Windows:** Download and run the installer from [this page](https://www.google.com/search?q=https://github.com/UB-Mannheim/tesseract/wiki).

### 2\. Set Up the Backend

In your terminal, navigate to the `kyc_project/backend` folder:

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # (On Mac/Linux)
.\venv\Scripts\activate  # (On Windows)

# 2. Install all the required Python packages
pip install -r requirements.txt

# 3. Download the spaCy AI model
python -m spacy download en_core_web_sm
```

### 3\. Run the App\!

1.  **Start the backend server:**
    (Make sure you're still in the `backend` folder with your environment active)

    ```bash
    uvicorn main:app --reload
    ```

    Your server is now running at `http://127.0.0.1:8000`.

2.  **Open the frontend:**
    Navigate to the `kyc_project/frontend` folder and just **double-click the `index.html` file** to open it in your web browser.

That's it\! You can now upload your files and test the checker.

## What Makes This Work (Libraries & Models)

  * **FastAPI:** The backend framework used to build our API endpoint.
  * **Uvicorn:** The server that runs our FastAPI application.
  * **PyTesseract:** The Python wrapper for Tesseract; this is what performs the actual OCR on images.
  * **Pillow (PIL):** Used to open and read the uploaded image files.
  * **PyMuPDF (fitz):** Used to extract text directly from text-based `.pdf` files.
  * **SpaCy (`en_core_web_sm`):** The pre-trained AI model we use for Named Entity Recognition (NER) to find `PERSON` (names) and `DATE` (dates) in the raw text.
  * **FuzzyWuzzy:** Used for "fuzzy" string matching to get a similarity score between two names (e.g., "Ishan Srivastava" vs. "ISHAN SRIVASTAVA").
  * **Vanilla HTML/CSS/JS:** The simple, no-framework frontend that lets you upload files and see the JSON response.
