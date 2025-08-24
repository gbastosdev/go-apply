import re
import pdfplumber
import uvicorn

def read_file(file_path):
    with pdfplumber.open(file_path) as pdf:
        contents = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )
    print(contents)

if __name__ == "__main__":
    read_file("C:\\Users\\GabrielBastos\\Downloads\\MTT 72h zeus - MCF-7 15.08.25 (B).pdf")