# import os
# import io
# import json
# from fastapi import FastAPI, File, UploadFile, HTTPException
# from fastapi.responses import JSONResponse
# import uvicorn
# import PyPDF2
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()

# # Load API key from environment
# openai_api_key = os.getenv("OPENAI_API_KEY")
# if not openai_api_key:
#     raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")

# # Initialize FastAPI and OpenAI client
# app = FastAPI()
# client = OpenAI(api_key=openai_api_key)
# MODEL = "gpt-4o-2024-08-06"

# json_schema={
#   "type": "object",
#   "properties": {
#     "solution_design": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     },
#     "business_process_mapping": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     },
#     "functional_specifications": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     },
#     "workshops_and_demos": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     },
#     "solution_validation": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     },
#     "authorization_design": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     },
#     "project_documentation": {
#       "type": "array",
#       "items": {
#         "type": "string"
#       }
#     }
#   },
#   "required": [
#     "solution_design",
#     "business_process_mapping",
#     "functional_specifications",
#     "workshops_and_demos",
#     "solution_validation",
#     "authorization_design",
#     "project_documentation"
#   ],
#   "additionalProperties": False
# }


# # Define the function for the model to "call"
# parse_resume_fn = {
#   "name": "parse_resume",
#   "description": "Extract every field from a résumé according to the schema",
#   "parameters": json_schema
# }

# SYSTEM_PROMPT= """
# You are an expert SAP resume parser trained in SAP Activate, Solution Manager, SPRO/IMG, WRICEF, and GRC practices.

# Your task:
# - Parse the resume into a structured JSON output under the "Design" phase.
# - Use only tags that can be logically inferred from the resume.
# - Use the reference points provided in the reference JSON to guide your decisions. Do not invent new tags or categories.
# - At the end, also return the "summary" block as booleans based on which sections have non-empty outputs.

# ---

# 🧾 Reference JSON:
# (Insert below as a JSON object, e.g. design_references.json)

# ```json
# {
#   "solution_design": [
#     "SAP Activate – Explore Phase > Define Solution Design",
#     "SAP Solution Manager – Logical Design",
#     "SAP Best Practices Explorer – Solution Architecture"
#   ],
#   "business_process_mapping": [
#     "SAP Activate – Explore Phase > Process Modeling",
#     "SAP Best Practices Explorer – Business Process Hierarchies",
#     "SAP Solution Manager – Business Process Documentation"
#   ],
#   "functional_specifications": [
#     "WRICEF Specification Standards",
#     "SAP Solution Manager – Functional Specification Templates",
#     "SAP Activate – Explore Phase > Document WRICEF Requirements"
#   ],
#   "workshops_and_demos": [
#     "SAP Activate – Explore Phase > Conduct Walkthroughs & Workshops",
#     "SAP Solution Manager – Stakeholder Engagement Activities"
#   ],
#   "solution_validation": [
#     "SAP Activate – Explore Phase > Design Confirmation and Sign-Off",
#     "SAP Solution Manager – Requirements Traceability Matrix"
#   ],
#   "authorization_design": [
#     "SAP GRC Access Control – Role and Risk Analysis",
#     "SAP Security Best Practices – Role Matrix and SoD",
#     "SAP Activate – Explore Phase > Security Design"
#   ],
#   "project_documentation": [
#     "SAP Solution Manager – Blueprint Documentation",
#     "SAP Activate – Project Deliverables",
#     "SAP Methodology – Document Management in Design Phase"
#   ]
# }
# """
# # Helper: extract text from txt or pdf
# async def extract_text(file: UploadFile) -> str:
#     content = await file.read()
#     if file.filename.lower().endswith(".pdf"):
#         reader = PyPDF2.PdfReader(io.BytesIO(content))
#         return "\n".join(page.extract_text() or "" for page in reader.pages)
#     else:
#         return content.decode("utf-8", errors="ignore")

# @app.post("/parse_resume")
# async def parse_resume_endpoint(file: UploadFile = File(...)):
#     try:
#         text = await extract_text(file)
#         prompt = SYSTEM_PROMPT + "\n\n" + text + "\n\nPlease output only the final parsed résumé as JSON that matches the schema exactly—no extra text."
#         resp = client.chat.completions.create(
#             model=MODEL,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content":text}
#             ],
#             functions=[parse_resume_fn],
#             function_call={"name": "parse_resume"}
#         )

#         print(f"Tokens used: {resp.usage.total_tokens}")
#         args = resp.choices[0].message.function_call.arguments
#         parsed = json.loads(args)
               
#         return JSONResponse(content=parsed)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run(app, host="0.0.0.0", port=port)

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

json_schema_design = {
  "name": "parse_design_phase",
  "description": "Extract every field from a résumé's Design phase according to the schema",
  "parameters": {
    "type": "object",
    "properties": {
      "solution_design": {"type": "array", "items": {"type": "string"}},
      "business_process_mapping": {"type": "array", "items": {"type": "string"}},
      "functional_specifications": {"type": "array", "items": {"type": "string"}},
      "workshops_and_demos": {"type": "array", "items": {"type": "string"}},
      "solution_validation": {"type": "array", "items": {"type": "string"}},
      "authorization_design": {"type": "array", "items": {"type": "string"}},
      "project_documentation": {"type": "array", "items": {"type": "string"}},
      "summary": {"type": "object", "properties": {
        "solution_design": {"type": "boolean"},
        "business_process_mapping": {"type": "boolean"},
        "functional_specifications": {"type": "boolean"},
        "workshops_and_demos": {"type": "boolean"},
        "solution_validation": {"type": "boolean"},
        "authorization_design": {"type": "boolean"},
        "project_documentation": {"type": "boolean"}
      }}
    },
    "required": [
      "solution_design","business_process_mapping","functional_specifications",
      "workshops_and_demos","solution_validation","authorization_design","project_documentation","summary"
    ],
    "additionalProperties": False
  }
}

json_schema_build={
  "name": "parse_build_phase",
  "description": "Extract Build / Configuration fields from a resume",
  "parameters": {
    "type": "object",
    "properties": {
      "sap_configuration": {"type": "array", "items": {"type": "string"}},
      "integration_design": {"type": "array", "items": {"type": "string"}},
      "mdm_and_master_data_governance": {"type": "array", "items": {"type": "string"}},
      "data_migration_support": {"type": "array", "items": {"type": "string"}},
      "version_upgrade_analysis": {"type": "array", "items": {"type": "string"}},
      "summary": {"type": "object", "properties": {
        "sap_configuration": {"type": "boolean"},
        "integration_design": {"type": "boolean"},
        "mdm_and_master_data_governance": {"type": "boolean"},
        "data_migration_support": {"type": "boolean"},
        "version_upgrade_analysis": {"type": "boolean"}
      }}
    },
    "required": ["sap_configuration","integration_design","mdm_and_master_data_governance","data_migration_support","version_upgrade_analysis","summary"],
    "additionalProperties": False
  }
}

json_schema_integration={
  "name": "parse_integration_experience",
  "description": "Extract integration experience from a resume",
  "parameters": {
    "type": "object",
    "properties": {
      "integration_experience": {"type": "array", "items": {"type": "string"}},
      "summary": {"type": "object", "properties": {"integration_experience": {"type": "boolean"}}}
    },
    "required": ["integration_experience","summary"],
    "additionalProperties": False
  }
}

json_schema_wricef={
  "name": "parse_wricef_development_experience",
  "description": "Extract WRICEF development experience from a resume",
  "parameters": {
    "type": "object",
    "properties": {
      "wricef_development_experience": {
        "type": "object",
        "properties": {
          "Reports": {"type": "array", "items": {"type": "string"}},
          "Interfaces": {"type": "array", "items": {"type": "string"}},
          "Conversions": {"type": "array", "items": {"type": "string"}},
          "Enhancements": {"type": "array", "items": {"type": "string"}},
          "Forms": {"type": "array", "items": {"type": "string"}},
          "Workflows": {"type": "array", "items": {"type": "string"}},
          "summary": {
            "type": "object",
            "properties": {
              "Reports": {"type": "boolean"},
              "Interfaces": {"type": "boolean"},
              "Conversions": {"type": "boolean"},
              "Enhancements": {"type": "boolean"},
              "Forms": {"type": "boolean"},
              "Workflows": {"type": "boolean"}
            }
          }
        },
        "required": ["Reports","Interfaces","Conversions","Enhancements","Forms","Workflows","summary"]
      }
    },
    "required": ["wricef_development_experience"],
    "additionalProperties": False
  }
}

json_schema_inttst={
  "name": "parse_integration_and_testing_experience",
  "description": "Extract integration and testing experience from a resume",
  "parameters": {
    "type": "object",
    "properties": {
      "integration_and_testing_experience": {
        "type": "object",
        "properties": {
          "with_module": {"type": "string"},
          "direction": {"type": "string"},
          "interface_type": {"type": "string"},
          "integration_methodologies": {"type": "array", "items": {"type": "string"}},
          "integration_technologies": {"type": "array", "items": {"type": "string"}},
          "notes": {"type": "string"}
        },
        "required": ["with_module","direction","interface_type","integration_methodologies","integration_technologies"],
        "additionalProperties": False
      }
    },
    "required": ["integration_and_testing_experience"],
    "additionalProperties": False
  }
}

json_schema_module_tech={
  "name": "parse_module_and_tech_stack",
  "description": "Extract primary/secondary SAP modules and technical skills from a resume",
  "parameters": {
    "type": "object",
    "properties": {
      "primary_modules": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "type": {"type": "string"},
            "primary_rank": {"type": "integer"},
            "level": {"type": "string"},
            "sub_modules": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "name": {"type": "string"},
                  "rank": {"type": "integer"},
                  "level": {"type": "string"}
                }
              }
            }
          }
        }
      },
      "secondary_modules": {"type": "array", "items": {"type": "object"}},
      "technical_skills": {"type": "array", "items": {"type": "object"}},
      "summary": {"type": "object", "properties": {"derived_from_tags": {"type": "boolean"}}}
    },
    "required": ["primary_modules","secondary_modules","technical_skills","summary"],
    "additionalProperties": False
  }
}

json_schema_deployment={
  "name": "parse_system_deployment_context",
  "description": "Extract system deployment context from a resume",
  "parameters": {
    "type": "object",
    "properties": {
      "system_type": {"type": "string"},
      "system_version": {"type": "string"},
      "system_version_from": {"type": "string"},
      "system_version_to": {"type": "string"},
      "deployment_type": {"type": "string"},
      "deployment_platform": {"type": "string"},
      "project_type": {"type": "string"}
    },
    "required": ["system_type","system_version","deployment_type","deployment_platform","project_type"],
    "additionalProperties": False
  }
}


# Define the function for the model to "call"
# parse_resume_fn = {
#   "name": "parse_resume",
#   "description": "Extract every field from a résumé according to the schema",
#   "parameters": json_schema
# }

SYSTEM_DESIGN_PROMPT= """
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

# === 2. Build / Configuration Phase Endpoint ===
SYSTEM_BUILD_PROMPT="""
You are an SAP resume parser trained in official SAP delivery frameworks including:
- SAP Best Practices Explorer
- SAP BPML (Business Process Master List)
- SAP Solution Manager
- SAP Activate

Your task is to extract *business process experience* from a resume. Use the module and business process context provided in the resume and map it to standardized SAP business process areas.

Do *not invent values* or categories. Use only real SAP processes (e.g., Freight Order Management, Putaway, Billing, etc.) and the activities within them (e.g., creation, execution, posting, etc.).

---

📘 Reference Basis for All Modules:
```json
{
  "business_process_experience": {
    "references": [
      "SAP Best Practices Explorer – Business Process Flows by Module",
      "SAP BPML – Business Process Master List (Module & Subdomain Hierarchies)",
      "SAP Solution Manager – Business Process Documentation and Mapping",
      "SAP Activate – Explore Phase > Process Modeling and Mapping"
    ],
    "summary": {
      "derived_from_tags": true
    }
  }
}
"""

SYSTEM_INTEGRATION_PROMPT="""
You are an SAP resume parser trained in official SAP integration frameworks including:
- SAP SPRO/IMG module integration settings
- SAP Best Practices Explorer
- SAP BPML (Business Process Master List)
- SAP Solution Manager – Interface Design Documentation
- WRICEF standards (for interface specs)
- SAP Integration Suite / CPI / PI / PO / IDoc / RFC / OData APIs

---

🎯 Your Task:
Extract a consultant's *integration experience* across SAP modules from the resume text. Focus on:
- Functional integration (configured interfaces)
- Technical integration (development using IDoc, BAPI, Proxy, OData, etc.)
- Design/documentation of integration flows (e.g., mappings, specs, validations)

Use only activities that are traceable to real SAP integration practices from the references provided below.

---

📘 Integration Experience Reference Basis:
```json
{
  "integration_experience": {
    "references": [
      "SPRO – Integration Settings Between SAP Modules (e.g., TM-SD, TM-MM, TM-EWM)",
      "SAP Best Practices Explorer – Integration Scenarios by Module",
      "SAP Solution Manager – Interface Architecture and Design",
      "SAP BPML – Integration Process Flows",
      "WRICEF – Interface Specification Standards (IDoc, BAPI, Proxy, CPI)",
      "SAP Integration Suite / PO / PI / IDoc / RFC / OData API Documentation"
    ],
    "summary": {
      "derived_from_tags": true
    }
  }
}
"""

SYSTEM_WRICEF_PROMPT="""
You are an SAP resume parser trained in SAP WRICEF methodology based on the following official sources:
- SAP Solution Manager – WRICEF Template (Reports, Interfaces, Conversions, Enhancements, Forms, Workflows)
- SAP Activate – Realize Phase > Custom Object Development
- SAP ABAP Development Guidelines
- SAP LSMW / BDC / Migration Cockpit Documentation
- SAP Integration Suite (PI/PO/CPI)
- SAP Enhancement Framework (BAdIs, Exits)
- SAP Output Management (SmartForms, Adobe Forms)
- SAP Workflow Management and BRF+

---

🎯 Your Task:
Extract WRICEF development experience from the resume under the six WRICEF categories:
- Reports
- Interfaces
- Conversions
- Enhancements
- Forms
- Workflows

Use only SAP-standard terminology and patterns. Do not invent custom tag names. Infer object types and tasks from the resume text using the WRICEF references provided.

---

📘 Reference Basis:
```json
{
  "wricef_development_experience": {
    "Reports": {
      "references": [
        "SAP ABAP Development Guidelines – Report Programming",
        "SAP Solution Manager – WRICEF Template > Report Object",
        "SAP Activate – Realize Phase > Custom Reports"
      ]
    },
    "Interfaces": {
      "references": [
        "SAP Integration Suite / PI / PO / CPI – Interface Scenarios",
        "SAP Solution Manager – WRICEF Template > Interface Object",
        "SAP Help – IDoc, BAPI, Proxy, OData Integration Standards"
      ]
    },
    "Conversions": {
      "references": [
        "SAP LSMW / BDC / S/4HANA Migration Cockpit – Data Migration",
        "SAP Solution Manager – WRICEF Template > Conversion Object",
        "SAP Activate – Realize Phase > Data Load & Mapping"
      ]
    },
    "Enhancements": {
      "references": [
        "SAP Enhancement Framework – BAdIs, Exits, Implicit/Explicit Enhancements",
        "SPRO – Enhancements and Modifications",
        "SAP Solution Manager – WRICEF Template > Enhancement Object"
      ]
    },
    "Forms": {
      "references": [
        "SAP Output Management – SmartForms, Adobe Forms, SAPscript",
        "SAP Solution Manager – WRICEF Template > Form Object",
        "SAP Activate – Realize Phase > Form Output Development"
      ]
    },
    "Workflows": {
      "references": [
        "SAP Business Workflow – Event-Driven and Rule-Based Design",
        "SAP BRF+ and MyInbox Integration",
        "SAP Solution Manager – WRICEF Template > Workflow Object"
      ]
    },
    "summary": {
      "derived_from_tags": true
    }
  }
}
"""

SYSTEM_INTTST_PROMPT="""
You are an SAP resume parser trained in official SAP integration frameworks and testing practices including:
- SAP Solution Manager – Interface Architecture and Mapping
- SAP Activate – Realize Phase > Interface Configuration and Testing
- SAP Best Practices Explorer – Integration Scenarios by Module
- SAP Help Portal – IDoc, BAPI, OData, Proxy, RFC, and Web Service Documentation
- SAP Integration Suite (PO, PI, CPI) and third-party middleware (e.g., MuleSoft, Boomi)

---

🎯 Your Task:
Extract structured *integration and testing experience* from the resume based on the fields listed below. Focus only on real integration flows between SAP modules or SAP with external systems.

---

📘 Reference Schema:
```json
{
  "integration_experience": {
    "fields": {
      "with_module": "SAP module or external system integrated (e.g., SD, MM, EWM, Ariba, TMS)",
      "direction": "Inbound / Outbound / Bidirectional – based on data flow",
      "interface_type": "IDoc / BAPI / Proxy / RFC / OData / REST / SOAP / Web Services / CPI / PO",
      "integration_methodologies": [
        "Middleware-Based",
        "Point-to-Point",
        "Synchronous",
        "Asynchronous",
        "Batch-Driven",
        "Real-Time",
        "Event-Driven"
      ],
      "integration_technologies": [
        "SAP PO",
        "SAP PI",
        "SAP CPI",
        "IDoc/ALE",
        "OData API",
        "REST",
        "SOAP",
        "RFC",
        "Third-Party Middleware"
      ],
      "notes": "Optional free-text field describing specific flow logic, error handling, middleware orchestration, or volume constraints"
    }
  }
}
"""

SYSTEM_MODULE_TECH_PROMPT="""
You are an SAP resume parser trained in SAP’s official module hierarchy, learning paths, and skill-level frameworks.

Your task is to extract a candidate’s *primary and secondary SAP module expertise, **sub-module experience, and **technical skills*, and return it in a structured format using the reference model provided below.

---

📘 Reference Schema:
```json
{
  "Module_And_Tech_Stack": {
    "references": [
      "SAP Modules & Submodules – Official SAP Module Hierarchy",
      "SAP Best Practices Explorer – Process and Submodule Mapping",
      "SAP Learning Hub – Skill Level Definitions (Beginner / Intermediate / Expert)",
      "SAP Activate – Role-Based Proficiency Models",
      "SAP Help Portal – Module and Feature-Level Documentation",
      "SAP BTP / ABAP / UI5 / OData / CPI – SAP Technical Stack Standards"
    ],
    "fields": {
      "primary_modules": {
        "name": "SAP Module (e.g., SAP TM, SAP EWM, SAP SD)",
        "type": "Functional / Technical / Cross-Functional",
        "primary_rank": "1 = strongest module, higher number = lower rank",
        "level": "Expert / Intermediate / Beginner",
        "sub_modules": [
          {
            "name": "Sub-module or process area (e.g., Freight Order Management, Putaway)",
            "rank": "Relative rank within module",
            "level": "Skill level specific to sub-module"
          }
        ]
      },
      "secondary_modules": {
        "same_structure_as_primary_modules": true
      },
      "technical_skills": [
        {
          "name": "Technology (e.g., OData, ABAP, SAP UI5, CPI, CDS Views)",
          "level": "Expert / Intermediate / Beginner",
          "primary_rank": "Optional ranking if multiple tech skills listed"
        }
      ]
    },
    "summary": {
      "derived_from_tags": true
    }
  }
}
"""

SYSTEM_DEPLOYMENT_PROMPT="""
You are an SAP resume parser trained in SAP deployment architectures and transition methodologies including:
- SAP Product Availability Matrix (PAM)
- SAP Activate – Deployment & Transition Paths
- SAP Best Practices – Project Types
- SAP Notes – Upgrade, Migration & Compatibility Guidelines
- SAP RISE, Cloud, and Hybrid Deployment Architectures

---

🎯 Your Task:
Extract structured *system deployment context* for each project or consultant profile using the reference schema below.

Only use SAP-standard values for system types, deployment models, cloud platforms, and project types.

---

📘 Reference Schema:
```json
{
  "System_Deployment_Context": {
    "fields": {
      "system_type": "ECC / S/4HANA / BTP / CRM / SRM / SCM / BW/4HANA / etc.",
      "system_version": "Version used (e.g., 1909, 2020, 7.5)",
      "system_version_from": "If upgrade or migration, original version",
      "system_version_to": "If upgrade or migration, target version",
      "deployment_type": "On-Prem / Cloud / Hybrid",
      "deployment_platform": "RISE / SAP BTP / SAP Cloud Platform / HEC / Azure / AWS / GCP / etc.",
      "project_type": "Implementation / Rollout / Migration / Upgrade / Support / AMS / Pilot / PoC"
    }
  }
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

# Generic function to call OpenAI with a custom system prompt and JSON schema
async def call_parser(text: str, system_prompt: str, function_schema: dict):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        functions=[function_schema],
        function_call={"name":function_schema["name"]}
    )
    print(f"Tokens used: {resp.usage.total_tokens}")
    args = resp.choices[0].message.function_call.arguments
    return json.loads(args)        

@app.post('/parse/design')
async def parse_design(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_DESIGN_PROMPT, json_schema_design)   
  return JSONResponse(content=parsed)   

@app.post('/parse/build')
async def parse_build(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_BUILD_PROMPT, json_schema_build)   
  return JSONResponse(content=parsed)

@app.post('/parse/integration')
async def parse_integration(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_INTEGRATION_PROMPT, json_schema_integration)   
  return JSONResponse(content=parsed)

@app.post('/parse/wricef')
async def parse_wricef(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_WRICEF_PROMPT, json_schema_wricef)   
  return JSONResponse(content=parsed)

@app.post('/parse/integration_and_testing')
async def parse_integration_and_testing(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_INTTST_PROMPT, json_schema_inttst)   
  return JSONResponse(content=parsed)  

@app.post('/parse/module_and_tech_stack')  
async def parse_module_and_tech_stack(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_MODULE_TECH_PROMPT, json_schema_module_tech)   
  return JSONResponse(content=parsed)

@app.post('/parse/system_deployment_context')
async def parse_system_deployment_context(file: UploadFile=File(...)):
  text= await extract_text(file)
  parsed = await call_parser(text, SYSTEM_DEPLOYMENT_PROMPT, json_schema_deployment)   
  return JSONResponse(content=parsed)  











if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)