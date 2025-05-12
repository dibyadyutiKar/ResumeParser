import os
import io
import json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import PyPDF2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Load API key from environment
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")

# Initialize FastAPI and OpenAI client
app = FastAPI()
client = OpenAI(api_key=openai_api_key)
MODEL = "gpt-4o-2024-08-06"

json_schema={
  "type": "object",
  "properties": {
    "solution_design": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "business_process_mapping": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "functional_specifications": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "workshops_and_demos": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "solution_validation": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "authorization_design": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "project_documentation": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "solution_design",
    "business_process_mapping",
    "functional_specifications",
    "workshops_and_demos",
    "solution_validation",
    "authorization_design",
    "project_documentation"
  ],
  "additionalProperties": False
}


# Define the function for the model to "call"
parse_resume_fn = {
  "name": "parse_resume",
  "description": "Extract every field from a résumé according to the schema",
  "parameters": json_schema
}

SYSTEM_PROMPT= """
You are an expert SAP resume parser trained in SAP Activate, Solution Manager, SPRO/IMG, WRICEF, and GRC practices.

Your task:
- Parse the resume into a structured JSON output under the "Design" phase.
- Use only tags that can be logically inferred from the resume.
- Use the reference points provided in the reference JSON to guide your decisions. Do not invent new tags or categories.
- At the end, also return the "summary" block as booleans based on which sections have non-empty outputs.

---

🧾 Reference JSON:
(Insert below as a JSON object, e.g. design_references.json)

```json
{
  "solution_design": [
    "SAP Activate – Explore Phase > Define Solution Design",
    "SAP Solution Manager – Logical Design",
    "SAP Best Practices Explorer – Solution Architecture"
  ],
  "business_process_mapping": [
    "SAP Activate – Explore Phase > Process Modeling",
    "SAP Best Practices Explorer – Business Process Hierarchies",
    "SAP Solution Manager – Business Process Documentation"
  ],
  "functional_specifications": [
    "WRICEF Specification Standards",
    "SAP Solution Manager – Functional Specification Templates",
    "SAP Activate – Explore Phase > Document WRICEF Requirements"
  ],
  "workshops_and_demos": [
    "SAP Activate – Explore Phase > Conduct Walkthroughs & Workshops",
    "SAP Solution Manager – Stakeholder Engagement Activities"
  ],
  "solution_validation": [
    "SAP Activate – Explore Phase > Design Confirmation and Sign-Off",
    "SAP Solution Manager – Requirements Traceability Matrix"
  ],
  "authorization_design": [
    "SAP GRC Access Control – Role and Risk Analysis",
    "SAP Security Best Practices – Role Matrix and SoD",
    "SAP Activate – Explore Phase > Security Design"
  ],
  "project_documentation": [
    "SAP Solution Manager – Blueprint Documentation",
    "SAP Activate – Project Deliverables",
    "SAP Methodology – Document Management in Design Phase"
  ]
}
"""
# Helper: extract text from txt or pdf
async def extract_text(file: UploadFile) -> str:
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        return content.decode("utf-8", errors="ignore")

@app.post("/parse_resume")
async def parse_resume_endpoint(file: UploadFile = File(...)):
    try:
        text = await extract_text(file)
        prompt = SYSTEM_PROMPT + "\n\n" + text + "\n\nPlease output only the final parsed résumé as JSON that matches the schema exactly—no extra text."
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content":text}
            ],
            functions=[parse_resume_fn],
            function_call={"name": "parse_resume"}
        )

        print(f"Tokens used: {resp.usage.total_tokens}")
        args = resp.choices[0].message.function_call.arguments
        parsed = json.loads(args)
               
        return JSONResponse(content=parsed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)