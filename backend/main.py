import re
import os
import spacy
import shutil
import tempfile
from PIL import Image
import pytesseract
from fuzzywuzzy import fuzz
from typing import Dict
import fitz  

# --- FastAPI Imports ---
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- Load AI Model ---
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Spacy model 'en_core_web_sm' not found.")
    print("Please run: python -m spacy download en_core_web_sm")
    exit()

# --- Initialize FastAPI App ---
app = FastAPI(title="Smart KYC Checker API")

# --- Add CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Logic---
def extract_text_from_file(file_path: str, content_type: str) -> str:
    text = ""
    try:
        if content_type in ["image/jpeg", "image/png", "image/jpg"]:
            # Use Tesseract for images
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            
        elif content_type == "application/pdf":
            # Use PyMuPDF (fitz) for PDFs
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
        else:
            print(f"Unsupported file type: {content_type}")
            return ""
            
        return text
    except Exception as e:
        print(f"Error processing file {file_path} (type: {content_type}): {e}")
        return ""

def extract_smart(text: str) -> dict:

    if not text:
        return {}
        
    doc = nlp(text)
    details = {}

    # 1. Regex for IDs 
    pan_pattern = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]{1}')
    pan_match = pan_pattern.search(text)
    details["pan_number"] = pan_match.group(0) if pan_match else None
    
    aadhar_pattern = re.compile(r'[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}')
    aadhar_match = aadhar_pattern.search(text)
    details["aadhar_number"] = aadhar_match.group(0) if aadhar_match else None

    # 2. NER for Names and Dates 
    name_candidates = []
    dob_candidates = []
    
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            if len(ent.text.split()) > 1:
                name_candidates.append(ent.text.strip().replace('\n', ' '))
                
        elif ent.label_ == "DATE":
            match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})', ent.text)
            if match:
                dob_candidates.append(match.group(0))
    
    # 3. Improved Fallback Heuristic 
    if not name_candidates:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            
            # Heuristic 1: Line after "Name" (for PAN)
            if ("Name" in line or "NAME" in line) and i + 1 < len(lines):
                name_candidates.append(lines[i+1])
                break # Found it
            
            # Heuristic 2: Line before "DOB" (for Aadhar)
            if ("DOB" in line or "fafa" in line) and i - 1 >= 0:
                prev_line = lines[i-1]
                # Check if the previous line is a plausible name
                if 1 < len(prev_line.split()) < 4 and not any(char.isdigit() for char in prev_line):
                    name_candidates.append(prev_line)
                    break # Found it
                
    details["name"] = name_candidates[0] if name_candidates else None
    details["dob"] = dob_candidates[0] if dob_candidates else None
    
    return details

def check_for_fraud_api(doc1_details: dict, doc2_details: dict) -> dict:

    report = {
        "status": "PASSED",
        "message": "Details are consistent.",
        "issues": [],
        "name_check": {"status": "NOT_CHECKED", "doc1": None, "doc2": None, "similarity": 0},
        "dob_check": {"status": "NOT_CHECKED", "doc1": None, "doc2": None}
    }
    issues_found = False

    # 1. Compare Name
    name1 = doc1_details.get("name")
    name2 = doc2_details.get("name")
    report["name_check"]["doc1"] = name1
    report["name_check"]["doc2"] = name2

    if name1 and name2:
        similarity = fuzz.token_sort_ratio(name1.lower(), name2.lower())
        report["name_check"]["similarity"] = similarity
        if similarity < 80:  # 80% similarity threshold
            issues_found = True
            issue_msg = f"Name mismatch (Similarity: {similarity}%)"
            report["issues"].append(issue_msg)
            report["name_check"]["status"] = "MISMATCH"
        else:
            report["name_check"]["status"] = "MATCH"
    else:
        report["name_check"]["status"] = "MISSING_DATA"

    # 2. Compare Date of Birth
    dob1 = doc1_details.get("dob")
    dob2 = doc2_details.get("dob")
    report["dob_check"]["doc1"] = dob1
    report["dob_check"]["doc2"] = dob2

    if dob1 and dob2:
        if dob1.replace('-', '/') != dob2.replace('-', '/'):
            issues_found = True
            report["issues"].append("DOB mismatch")
            report["dob_check"]["status"] = "MISMATCH"
        else:
            report["dob_check"]["status"] = "MATCH"
    else:
        report["dob_check"]["status"] = "MISSING_DATA"

    # Final Status
    if issues_found:
        report["status"] = "FAILED"
        report["message"] = "Fraud check FAILED. Mismatched details found."
    
    return report

#  API ENDPOINT (MODIFIED)

@app.post("/check-kyc/")
async def create_kyc_check(doc1: UploadFile = File(...), doc2: UploadFile = File(...)):
    """
    The main API endpoint.
    1. Receives two uploaded files (images or PDFs).
    2. Saves them to temporary files.
    3. Runs text extraction (OCR or PDF parse).
    4. Runs fraud check.
    5. Cleans up files and returns the report.
    """
    temp_dir = tempfile.mkdtemp()
    doc1_path = os.path.join(temp_dir, doc1.filename)
    doc2_path = os.path.join(temp_dir, doc2.filename)

    try:
        # Save files temporarily
        with open(doc1_path, "wb") as buffer:
            shutil.copyfileobj(doc1.file, buffer)
        with open(doc2_path, "wb") as buffer:
            shutil.copyfileobj(doc2.file, buffer)

        # --- Run KYC Pipeline ---
        
        # 1. Extract text (MODIFIED)
        #    We now pass the content_type to our new function
        doc1_text = extract_text_from_file(doc1_path, doc1.content_type)
        doc2_text = extract_text_from_file(doc2_path, doc2.content_type)
        
        if not doc1_text or not doc2_text:
            raise HTTPException(
                status_code=400, 
                detail="Could not read text from one or both files. Please upload clearer images or valid, text-based PDFs."
            )

        # 2. Extract details
        doc1_details = extract_smart(doc1_text)
        doc2_details = extract_smart(doc2_text)

        # 3. Perform fraud check
        report = check_for_fraud_api(doc1_details, doc2_details)
        
        # Add extracted (parsed) details to the final report
        report["extracted_data"] = {
            "doc1": doc1_details,
            "doc2": doc2_details,
        }
        
        # Add the raw extracted text to the report
        report["debug_raw_text"] = {
            "doc1": doc1_text,
            "doc2": doc2_text
        }
        
        return report

    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        # Clean up: Always remove the temp files and directory
        if os.path.exists(doc1_path):
            os.remove(doc1_path)
        if os.path.exists(doc2_path):
            os.remove(doc2_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        
        await doc1.close()
        await doc2.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart KYC Checker API. Please use the /check-kyc endpoint to upload documents."}

# --- To run the server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)