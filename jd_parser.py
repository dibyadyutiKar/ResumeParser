import os
import json
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import PyPDF2
from openai import OpenAI
import io
from dotenv import load_dotenv

jd_router = APIRouter()

load_dotenv()


# Initialize OpenAI client
client = OpenAI(api_key= os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-2024-08-06"  # Fixed valid model name

# Helper: Extract text from PDF/text files
async def extract_text(file: UploadFile) -> str:
    try:
        content = await file.read()
        if file.filename.lower().endswith(".pdf"):
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(400, f"File read error: {str(e)}")

# Generic OpenAI parser with enhanced error handling
async def call_parser(text: str, system_prompt: str, function_schema: dict):
    try:
        # Validate input
        if not text.strip():
            raise ValueError("Empty text content")
            
        # API call
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            functions=[function_schema],
            function_call={"name": function_schema["name"]}
        )
        print("token usage:", resp.usage.total_tokens)
        
        # Validate response
        if not resp.choices[0].message.function_call:
            raise ValueError("No function call in response")
            
        # Parse arguments
        args = resp.choices[0].message.function_call.arguments
        print(f"Raw OpenAI response: {args}")
        return json.loads(args)
        
    except json.JSONDecodeError:
        raise HTTPException(500, "Failed to parse OpenAI response")
    except Exception as e:
        raise HTTPException(500, f"OpenAI API error: {str(e)}")

# ===== JD-Specific Schemas and Prompts =====

# 1. Module-Specific Experience
SYSTEM_JD_MODULE_SPECIFIC_PROMPT = """
You are an SAP job description parser trained on SAP Activate, SPRO/IMG, WRICEF, and BPML references.

🎯 Task:
Extract structured module_specific_experience from the JD using SAP Activate phases and SPRO/IMG-aligned configuration and delivery tasks.

📘 Reference Schema:
- Pre-Implementation → requirements_gathering, gap_fit_analysis, third_party_advisory
- Design → solution_design, process_mapping, functional_specs, workshops
- Build → spro_configuration, integration_design, data_migration, mdm
- Testing → uat_support, defect_resolution
- Cutover → cutover_planning, go_no_go_meetings
- Post-Go-Live → hypercare, change_requests
(All mapped to SAP Activate and SPRO/IMG)

📄 Input: Job Description

🧾 Output Format:
```json
{
  "module_specific_experience": {
    "SAP TM": {
      "Design": {
        "solution_design": [...],
        "process_mapping": [...]
      },
      "Build": {
        "spro_configuration": [...],
        "integration_design": [...]
      },
      "summary": {
        "Blueprinting": true,
        "SPRO Configuration": true
      }
    }
  }
}
"""

JSON_SCHEMA_JD_MODULE_SPECIFIC = {
    "name": "parse_jd_module_specific_experience",
    "description": "Extract module-specific implementation experience",
    "parameters": {
        "type": "object",
        "properties": {
            "module_specific_experience": {
                "type": "object",
                "properties": {
                    "Pre-Implementation": {"type": "object"},
                    "Design": {"type": "object"},
                    "Build": {"type": "object"},
                    "Testing": {"type": "object"},
                    "Cutover": {"type": "object"},
                    "Post-Go-Live": {"type": "object"},
                    "summary": {"type": "object"}
                }
            }
        },
        "required": ["module_specific_experience"]
    }
}

@jd_router.post("/module_specific")
async def parse_jd_module_specific(file: UploadFile = File(...)):
    text = await extract_text(file)
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text, SYSTEM_JD_MODULE_SPECIFIC_PROMPT, JSON_SCHEMA_JD_MODULE_SPECIFIC)
    return JSONResponse(content=result)

# 2. Business Process Experience
SYSTEM_JD_BPM_PROMPT = """
You are a job description parser trained in SAP BPML and Best Practices.

🎯 Task:
Extract module-specific `business_process_experience` from the JD, listing the business process names mentioned (e.g., 'Freight Order Management', 'Inbound Processing', 'Order to Cash').

📘 Use only real SAP process flows from:
- SAP Best Practices Explorer
- SAP BPML by module
- SAP Solution Manager

🧾 Reference Output Format:
json
{
  "business_process_experience": {
    "SAP TM": ["Freight Order Management", "Transportation Planning"],
    "SAP EWM": ["Inbound Processing", "Outbound Processing"]
  }
}

📝 Examples:
1. JD text: "Responsible for configuring and testing warehouse inbound and outbound processes in SAP EWM."
   Output: {"business_process_experience": {"SAP EWM": ["Inbound Processing", "Outbound Processing"]}}

2. JD text: "Managed freight planning and execution in SAP TM."
   Output: {"business_process_experience": {"SAP TM": ["Freight Order Management"]}}
"""

JSON_SCHEMA_JD_BPM = {
    "name": "parse_jd_business_process_experience",
    "description": "Extract business process experience",
    "parameters": {
        "type": "object",
        "properties": {
            "business_process_experience": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "required": ["business_process_experience"],
        "additionalProperties": False
    }
}


@jd_router.post("/business_process")
async def parse_jd_bpm(file: UploadFile = File(...)):
    text = await extract_text(file)
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text,SYSTEM_JD_BPM_PROMPT , JSON_SCHEMA_JD_BPM)    
    return JSONResponse(content=result)

# 3. Integration Experience
SYSTEM_JD_INTEGRATION_PROMPT = """
You are an expert at parsing job descriptions (JDs) to identify integration experience.
Your task is to extract integration-related experience and output it in the specified JSON schema.

📝 Guidelines:
- Use lowercase strings with underscores for clarity (e.g., `configured_tm_sd_integration`).
- Include the technology (e.g., `_idoc`, `_cpi`, `_odata`) if specified in the JD.
- If no technology is mentioned but integration with specific modules is implied, use a generic format like `configured_[module1]_[module2]_integration`.
- For general integration responsibilities (e.g., "Integration with other SAP modules like SD/MM"), assume standard integrations and list them (e.g., `configured_tm_sd_integration`, `configured_tm_mm_integration`).
- Only include integrations that are reasonably implied by the JD text.

📄 Examples:
1. JD text: "Configured SAP TM to SAP SD integration using IDocs."
   Output: {
     "integration_experience": {
       "SAP TM": ["configured_tm_sd_integration_idoc"]
     }
   }
2. JD text: "Responsible for integration of SAP TM with other modules like SD and MM."
   Output: {
     "integration_experience": {
       "SAP TM": ["configured_tm_sd_integration", "configured_tm_mm_integration"]
     }
   }
"""

JSON_SCHEMA_JD_INTEGRATION = {
    "name": "parse_jd_integration_experience",
    "description": "Extract integration experience",
    "parameters": {
        "type": "object",
        "properties": {
            "integration_experience": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "required": ["integration_experience"],
        "additionalProperties": False
    }
}

@jd_router.post("/integration")
async def parse_jd_integration(file: UploadFile = File(...)):
    text = await extract_text(file)
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text, SYSTEM_JD_INTEGRATION_PROMPT, JSON_SCHEMA_JD_INTEGRATION)
    
    # Add a message if no integrations are found
    if not result.get("integration_experience"):
        result["message"] = "No specific integration experience found, but general integration responsibilities are mentioned."
    return JSONResponse(content=result)

# 4. WRICEF Requirements
SYSTEM_JD_WRICEF_PROMPT = """
You are a parser trained in SAP WRICEF (Workflows, Reports, Interfaces, Conversions, Enhancements, Forms) requirements.

🎯 Task:
Extract `wricef_development_experience` from the JD, identifying specific requirements or tasks related to Reports, Interfaces, Conversions, Enhancements, Forms, and Workflows. Format each task as a concise string describing the WRICEF component.

📘 Align with SAP-specific WRICEF concepts:
- Reports: Custom reports (e.g., ALV, SAP Query, BI reports).
- Interfaces: Data exchange between systems (e.g., IDocs, BAPIs, RFCs, CPI).
- Conversions: Data migration or conversion programs (e.g., LSMW, BDC).
- Enhancements: Customizations (e.g., User Exits, BADIs, enhancement points).
- Forms: Output forms (e.g., SAPScript, Smart Forms, Adobe Forms).
- Workflows: Business process automation (e.g., SAP Workflow, BRF+).

🧾 Output Format:
json
{
  "wricef_development_experience": {
    "Reports": ["developed_alv_report_for_tm", "created_bi_report_for_freight"],
    "Interfaces": ["configured_tm_sd_idoc_interface"],
    "Conversions": ["implemented_lsmw_for_tm_master_data"],
    "Enhancements": ["developed_badi_for_carrier_selection"],
    "Forms": ["designed_smart_form_for_freight_order"],
    "Workflows": ["configured_brfplus_workflow_for_tendering"]
  }
}

📝 Guidelines:
- Use lowercase strings with underscores for clarity (e.g., `developed_alv_report_for_tm`).
- Include the technology or method (e.g., `_alv`, `_idoc`, `_lsmw`) if specified in the JD.
- If no technology is mentioned, use a generic format like `developed_[category]_for_[module]` (e.g., `developed_report_for_tm`).
- If the JD mentions general WRICEF tasks (e.g., "preparing functional specifications" or "testing development objects"), infer relevant categories based on context (e.g., Enhancements or Reports).
- Only include explicitly mentioned or reasonably inferred WRICEF tasks.

📄 Examples:
1. JD text: "Developed custom ALV reports for SAP TM and configured IDoc interfaces for TM-SD integration."
   Output: {
     "wricef_development_experience": {
       "Reports": ["developed_alv_report_for_tm"],
       "Interfaces": ["configured_tm_sd_idoc_interface"],
       "Conversions": [],
       "Enhancements": [],
       "Forms": [],
       "Workflows": []
     }
   }

2. JD text: "Prepared functional specifications and tested development objects for SAP TM enhancements."
   Output: {
     "wricef_development_experience": {
       "Reports": [],
       "Interfaces": [],
       "Conversions": [],
       "Enhancements": ["developed_enhancement_for_tm"],
       "Forms": [],
       "Workflows": []
     }
   }

3. JD text: "Implemented LSMW for TM master data migration and designed Smart Forms for freight orders."
   Output: {
     "wricef_development_experience": {
       "Reports": [],
       "Interfaces": [],
       "Conversions": ["implemented_lsmw_for_tm_master_data"],
       "Enhancements": [],
       "Forms": ["designed_smart_form_for_freight_order"],
       "Workflows": []
     }
   }

4. JD text: "Configured BRF+ workflows for tendering in SAP TM."
   Output: {
     "wricef_development_experience": {
       "Reports": [],
       "Interfaces": [],
       "Conversions": [],
       "Enhancements": [],
       "Forms": [],
       "Workflows": ["configured_brfplus_workflow_for_tendering"]
     }
   }
"""

JSON_SCHEMA_JD_WRICEF = {
    "name": "parse_jd_wricef_requirements",
    "description": "Extract WRICEF development needs from a job description",
    "parameters": {
        "type": "object",
        "properties": {
            "wricef_development_experience": {
                "type": "object",
                "properties": {
                    "Reports": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Custom reports (e.g., ALV, SAP Query, BI reports)"
                    },
                    "Interfaces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Data exchange between systems (e.g., IDocs, BAPIs)"
                    },
                    "Conversions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Data migration or conversion programs (e.g., LSMW, BDC)"
                    },
                    "Enhancements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Customizations (e.g., User Exits, BADIs)"
                    },
                    "Forms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Output forms (e.g., SAPScript, Smart Forms)"
                    },
                    "Workflows": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Business process automation (e.g., SAP Workflow, BRF+)"
                    }
                },
                "required": ["Reports", "Interfaces", "Conversions", "Enhancements", "Forms", "Workflows"],
                "additionalProperties": False
            }
        },
        "required": ["wricef_development_experience"],
        "additionalProperties": False
    }
}

@jd_router.post("/wricef")
async def parse_jd_wricef(file: UploadFile = File(...)):
    text = await extract_text(file)
    print(f"Extracted text: {text[:500]}...")  # Log the first 500 characters for debugging
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text, SYSTEM_JD_WRICEF_PROMPT, JSON_SCHEMA_JD_WRICEF)
    return JSONResponse(content=result)

# 5. Integration & Testing Flows
SYSTEM_JD_INT_TST_PROMPT = """
You are a parser trained in SAP integration and testing requirements.

🎯 Task:
Extract structured integration flow descriptions from the JD, identifying flows between SAP modules (e.g., SAP TM to SAP SD) or with external systems. For each flow, include the connected module/system, direction, interface type, technologies, methodologies, and any notes. Focus on integration tasks that involve testing or configuration.

📘 Align with SAP-specific integration concepts:
- Modules: SAP TM, SD, MM, EWM, FI, etc., or external systems (e.g., 3rd-party logistics platforms).
- Direction: Outbound (data sent from primary module), Inbound (data received), Bidirectional.
- Interface Types: IDoc, BAPI, RFC, API, File-Based, etc.
- Technologies: SAP PI/PO, CPI, SAP Integration Suite, OData, Proxy, etc.
- Methodologies: Batch, Asynchronous, Real-Time, Middleware-Based, Direct.
- Notes: Brief context or purpose of the integration (e.g., "Freight order data to SD").

🧾 Output Format:
json
{
  "Integration_And_Testing": {
    "integration_experience": [
      {
        "with_module": "string",  // e.g., "SAP SD" or "External Logistics Platform"
        "direction": "string",    // e.g., "Outbound", "Inbound", "Bidirectional"
        "interface_type": "string", // e.g., "IDoc", "API"
        "integration_methodologies": ["string"], // e.g., ["Asynchronous", "Middleware-Based"]
        "integration_technologies": ["string"], // e.g., ["SAP PO", "CPI"]
        "notes": "string"        // e.g., "Freight order IDoc to SD using PO"
      }
    ]
  }
}

📝 Guidelines:
- Use lowercase for field values where applicable (e.g., "sap_sd" for with_module).
- Infer direction, interface type, and methodologies if not explicitly stated but implied (e.g., "Integration with SD" implies bidirectional IDoc for TM-SD).
- If technologies are not specified, use "unknown" or infer common ones (e.g., IDoc for SAP-SAP integration).
- For general integration mentions (e.g., "Integration with SD/MM"), assume standard flows and note the lack of specificity.
- Only include flows explicitly mentioned or reasonably inferred from the JD.

📄 Examples:
1. JD text: "Tested SAP TM to SAP SD integration using IDocs via SAP PO for freight order data."
   Output: {
     "Integration_And_Testing": {
       "integration_experience": [
         {
           "with_module": "sap_sd",
           "direction": "outbound",
           "interface_type": "idoc",
           "integration_methodologies": ["asynchronous", "middleware-based"],
           "integration_technologies": ["sap_po"],
           "notes": "freight order idoc to sd using po"
         }
       ]
     }
   }

2. JD text: "Responsible for integration of SAP TM with SAP EWM and MM modules."
   Output: {
     "Integration_And_Testing": {
       "integration_experience": [
         {
           "with_module": "sap_ewm",
           "direction": "bidirectional",
           "interface_type": "idoc",
           "integration_methodologies": ["asynchronous"],
           "integration_technologies": ["unknown"],
           "notes": "assumed standard tm-ewm integration"
         },
         {
           "with_module": "sap_mm",
           "direction": "bidirectional",
           "interface_type": "idoc",
           "integration_methodologies": ["asynchronous"],
           "integration_technologies": ["unknown"],
           "notes": "assumed standard tm-mm integration"
         }
       ]
     }
   }

3. JD text: "Configured SAP TM integration with 3rd-party logistics systems using CPI."
   Output: {
     "Integration_And_Testing": {
       "integration_experience": [
         {
           "with_module": "external_logistics_platform",
           "direction": "bidirectional",
           "interface_type": "api",
           "integration_methodologies": ["real-time"],
           "integration_technologies": ["cpi"],
           "notes": "tm integration with external logistics via cpi"
         }
       ]
     }
   }
"""

JSON_SCHEMA_JD_INT_TST = {
    "name": "parse_jd_integration_testing",
    "description": "Extract integration and testing workflows from a job description",
    "parameters": {
        "type": "object",
        "properties": {
            "Integration_And_Testing": {
                "type": "object",
                "properties": {
                    "integration_experience": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "with_module": {
                                    "type": "string",
                                    "description": "The module or system integrated with (e.g., sap_sd)"
                                },
                                "direction": {
                                    "type": "string",
                                    "enum": ["outbound", "inbound", "bidirectional"],
                                    "description": "Direction of data flow"
                                },
                                "interface_type": {
                                    "type": "string",
                                    "description": "Type of interface (e.g., idoc, api)"
                                },
                                "integration_methodologies": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Methodologies used (e.g., asynchronous, real-time)"
                                },
                                "integration_technologies": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Technologies used (e.g., sap_po, cpi)"
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Brief context or purpose of the integration"
                                }
                            },
                            "required": [
                                "with_module",
                                "direction",
                                "interface_type",
                                "integration_methodologies",
                                "integration_technologies",
                                "notes"
                            ],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["integration_experience"],
                "additionalProperties": False
            }
        },
        "required": ["Integration_And_Testing"],
        "additionalProperties": False
    }
}

@jd_router.post("/integration_testing")
async def parse_jd_integration_testing(file: UploadFile = File(...)):
    text = await extract_text(file)
    print(f"Extracted text: {text[:500]}...")  # Log the first 500 characters for debugging
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text, SYSTEM_JD_INT_TST_PROMPT, JSON_SCHEMA_JD_INT_TST)
    return JSONResponse(content=result)

# 6. Module & Tech Stack
SYSTEM_JD_MODULE_TECH_PROMPT = """
You are a parser trained in SAP modules and technical skills for job descriptions (JDs).

🎯 Task:
Extract key SAP modules and technical skills required from the JD. Categorize modules as primary (core focus of the role) or secondary (supporting or integrated modules). Include sub-modules where applicable and estimate proficiency levels (Expert, Intermediate, Beginner) based on JD context.

📘 Align with SAP-specific concepts:
- Modules: SAP TM, SD, MM, EWM, FI, S/4HANA, etc.
- Sub-modules: Specific functionalities (e.g., Freight Order Management for TM, Putaway for EWM).
- Technical Skills: BRF+, PPF, BOPF, ABAP, OData, SAP Integration Suite, etc.
- Proficiency Levels: 
  - Expert: Lead-level expertise, configuration, or design responsibilities.
  - Intermediate: Configuration or support with some independence.
  - Beginner: Basic knowledge or exposure.
- Primary vs. Secondary Modules:
  - Primary: Core module of the role (e.g., SAP TM for a TM Consultant).
  - Secondary: Modules integrated with or supporting the primary module (e.g., SD, MM for TM integrations).

🧾 Output Format:
json
{
  "Module_And_Tech_Stack": {
    "primary_modules": [
      {
        "name": "string",  // e.g., "sap_tm"
        "type": "string",  // e.g., "functional", "technical"
        "level": "string", // e.g., "expert", "intermediate", "beginner"
        "sub_modules": [
          {
            "name": "string",  // e.g., "freight_order_management"
            "level": "string"  // e.g., "expert"
          }
        ]
      }
    ],
    "secondary_modules": [
      {
        "name": "string",
        "type": "string",
        "level": "string",
        "sub_modules": [
          {
            "name": "string",
            "level": "string"
          }
        ]
      }
    ],
    "technical_skills": [
      {
        "name": "string",  // e.g., "brfplus"
        "level": "string"  // e.g., "intermediate"
      }
    ]
  }
}

📝 Guidelines:
- Use lowercase with underscores for field values (e.g., "sap_tm", "freight_order_management").
- Infer primary modules from the role’s core focus (e.g., SAP TM for a TM Consultant).
- Infer secondary modules from integration mentions (e.g., SD, MM for TM integrations).
- Estimate proficiency based on context (e.g., "lead design" implies Expert, "knowledge of" implies Beginner).
- Include sub-modules only if explicitly mentioned or strongly implied (e.g., "Freight Order Management" for TM).
- If technical skills or proficiency are not specified, infer common ones for the role (e.g., BRF+ for TM).

📄 Examples:
1. JD text: "Lead SAP TM implementation, configure Freight Order Management, and integrate with SAP SD using IDocs. Knowledge of BRF+ and ABAP."
   Output: {
     "Module_And_Tech_Stack": {
       "primary_modules": [
         {
           "name": "sap_tm",
           "type": "functional",
           "level": "expert",
           "sub_modules": [
             {
               "name": "freight_order_management",
               "level": "expert"
             }
           ]
         }
       ],
       "secondary_modules": [
         {
           "name": "sap_sd",
           "type": "functional",
           "level": "intermediate",
           "sub_modules": []
         }
       ],
       "technical_skills": [
         {
           "name": "brfplus",
           "level": "beginner"
         },
         {
           "name": "abap",
           "level": "beginner"
         }
       ]
     }
   }

2. JD text: "Support SAP EWM configuration, including Putaway and Picking, with integration to SAP TM. Familiarity with OData."
   Output: {
     "Module_And_Tech_Stack": {
       "primary_modules": [
         {
           "name": "sap_ewm",
           "type": "functional",
           "level": "intermediate",
           "sub_modules": [
             {
               "name": "putaway",
               "level": "intermediate"
             },
             {
               "name": "picking",
               "level": "intermediate"
             }
           ]
         }
       ],
       "secondary_modules": [
         {
           "name": "sap_tm",
           "type": "functional",
           "level": "beginner",
           "sub_modules": []
         }
       ],
       "technical_skills": [
         {
           "name": "odata",
           "level": "beginner"
         }
       ]
     }
   }

3. JD text: "Lead SAP TM design and integration with SD, MM, EWM. Strong knowledge of BRF+, PPF, BOPF."
   Output: {
     "Module_And_Tech_Stack": {
       "primary_modules": [
         {
           "name": "sap_tm",
           "type": "functional",
           "level": "expert",
           "sub_modules": []
         }
       ],
       "secondary_modules": [
         {
           "name": "sap_sd",
           "type": "functional",
           "level": "intermediate",
           "sub_modules": []
         },
         {
           "name": "sap_mm",
           "type": "functional",
           "level": "intermediate",
           "sub_modules": []
         },
         {
           "name": "sap_ewm",
           "type": "functional",
           "level": "intermediate",
           "sub_modules": []
         }
       ],
       "technical_skills": [
         {
           "name": "brfplus",
           "level": "expert"
         },
         {
           "name": "ppf",
           "level": "expert"
         },
         {
           "name": "bopf",
           "level": "expert"
         }
       ]
     }
   }
"""

JSON_SCHEMA_JD_MODULE_TECH = {
    "name": "parse_jd_module_tech_stack",
    "description": "Extract required SAP modules and technical skills from a job description",
    "parameters": {
        "type": "object",
        "properties": {
            "Module_And_Tech_Stack": {
                "type": "object",
                "properties": {
                    "primary_modules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the SAP module (e.g., sap_tm)"
                                },
                                "type": {
                                    "type": "string",
                                    "enum": ["functional", "technical"],
                                    "description": "Type of module expertise"
                                },
                                "level": {
                                    "type": "string",
                                    "enum": ["expert", "intermediate", "beginner"],
                                    "description": "Proficiency level"
                                },
                                "sub_modules": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Name of the sub-module (e.g., freight_order_management)"
                                            },
                                            "level": {
                                                "type": "string",
                                                "enum": ["expert", "intermediate", "beginner"],
                                                "description": "Proficiency level for the sub-module"
                                            }
                                        },
                                        "required": ["name", "level"],
                                        "additionalProperties": False
                                    },
                                    "description": "List of sub-modules"
                                }
                            },
                            "required": ["name", "type", "level", "sub_modules"],
                            "additionalProperties": False
                        }
                    },
                    "secondary_modules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the SAP module (e.g., sap_sd)"
                                },
                                "type": {
                                    "type": "string",
                                    "enum": ["functional", "technical"],
                                    "description": "Type of module expertise"
                                },
                                "level": {
                                    "type": "string",
                                    "enum": ["expert", "intermediate", "beginner"],
                                    "description": "Proficiency level"
                                },
                                "sub_modules": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Name of the sub-module"
                                            },
                                            "level": {
                                                "type": "string",
                                                "enum": ["expert", "intermediate", "beginner"],
                                                "description": "Proficiency level for the sub-module"
                                            }
                                        },
                                        "required": ["name", "level"],
                                        "additionalProperties": False
                                    },
                                    "description": "List of sub-modules"
                                }
                            },
                            "required": ["name", "type", "level", "sub_modules"],
                            "additionalProperties": False
                        }
                    },
                    "technical_skills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the technical skill (e.g., brfplus)"
                                },
                                "level": {
                                    "type": "string",
                                    "enum": ["expert", "intermediate", "beginner"],
                                    "description": "Proficiency level"
                                }
                            },
                            "required": ["name", "level"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["primary_modules", "secondary_modules", "technical_skills"],
                "additionalProperties": False
            }
        },
        "required": ["Module_And_Tech_Stack"],
        "additionalProperties": False
    }
}

@jd_router.post("/module_tech_stack")
async def parse_jd_module_tech_stack(file: UploadFile = File(...)):
    text = await extract_text(file)
    print(f"Extracted text: {text[:500]}...")  # Log the first 500 characters for debugging
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text, SYSTEM_JD_MODULE_TECH_PROMPT, JSON_SCHEMA_JD_MODULE_TECH)
    return JSONResponse(content=result)

# 7. Deployment Context
SYSTEM_JD_DEPLOYMENT_PROMPT = """
You are a parser trained in SAP deployment contexts for job descriptions (JDs).

🎯 Task:
Extract system versions, deployment models, and project types from the JD. Include specific versions of SAP systems, the deployment approach (e.g., On-Premise, Cloud, Embedded), and the types of projects (e.g., Implementation, Upgrade).

📘 Align with SAP-specific concepts:
- System Versions: Specific SAP releases (e.g., SAP TM 9.5, S/4HANA 2020, ECC 6.0).
- Deployment Models: On-Premise, Cloud (Public/Private), Hybrid, Embedded (e.g., TM embedded in S/4HANA).
- Project Types: Greenfield Implementation, Brownfield Implementation, Upgrade, Support, Rollout, Migration.
- Additional Notes: Context or clarifications (e.g., "TM embedded in S/4HANA").

🧾 Output Format:
json
{
  "deployment_context": {
    "system_versions": [
      {
        "name": "string",  // e.g., "sap_tm_9.5"
        "notes": "string"  // e.g., "primary module version"
      }
    ],
    "deployment_models": [
      {
        "name": "string",  // e.g., "embedded"
        "notes": "string"  // e.g., "tm embedded in s4hana"
      }
    ],
    "project_types": [
      {
        "name": "string",  // e.g., "implementation"
        "notes": "string"  // e.g., "greenfield implementation"
      }
    ]
  }
}

📝 Guidelines:
- Use lowercase with underscores for field values (e.g., "sap_tm_9.5", "on_premise").
- Infer system versions from explicit mentions (e.g., "SAP TM 9.5") or context (e.g., "S/4HANA" implies a recent version).
- Infer deployment models from terms like "embedded," "cloud," or context (e.g., S/4HANA often implies Cloud or Hybrid).
- Infer project types from terms like "implementation," "upgrade," "support," or context (e.g., "new SAP TM deployment" implies Greenfield).
- Include notes for clarity (e.g., "assumed based on S/4HANA mention").
- If details are vague, use reasonable defaults for the role (e.g., S/4HANA implies Implementation or Upgrade).
- Only include explicitly mentioned or reasonably inferred items.

📄 Examples:
1. JD text: "Lead SAP TM 9.5 implementation and S/4HANA upgrade projects, including embedded TM."
   Output: {
     "deployment_context": {
       "system_versions": [
         {
           "name": "sap_tm_9.5",
           "notes": "primary module version"
         },
         {
           "name": "s4_hana",
           "notes": "embedded tm host"
         }
       ],
       "deployment_models": [
         {
           "name": "embedded",
           "notes": "tm embedded in s4hana"
         }
       ],
       "project_types": [
         {
           "name": "implementation",
           "notes": "sap tm deployment"
         },
         {
           "name": "upgrade",
           "notes": "s4hana upgrade"
         }
       ]
     }
   }

2. JD text: "Support SAP ECC 6.0 and migrate to S/4HANA Cloud."
   Output: {
     "deployment_context": {
       "system_versions": [
         {
           "name": "ecc_6.0",
           "notes": "current system"
         },
         {
           "name": "s4_hana",
           "notes": "target system"
         }
       ],
       "deployment_models": [
         {
           "name": "cloud",
           "notes": "s4hana cloud migration"
         }
       ],
       "project_types": [
         {
           "name": "support",
           "notes": "ecc system support"
         },
         {
           "name": "migration",
           "notes": "migration to s4hana"
         }
       ]
     }
   }

3. JD text: "Implement SAP TM in S/4HANA environment with integration to EWM."
   Output: {
     "deployment_context": {
       "system_versions": [
         {
           "name": "s4_hana",
           "notes": "assumed recent version"
         },
         {
           "name": "sap_tm",
           "notes": "assumed embedded in s4hana"
         }
       ],
       "deployment_models": [
         {
           "name": "embedded",
           "notes": "tm embedded in s4hana"
         }
       ],
       "project_types": [
         {
           "name": "implementation",
           "notes": "greenfield tm implementation"
         }
       ]
     }
   }
"""

JSON_SCHEMA_JD_DEPLOYMENT = {
    "name": "parse_jd_deployment_context",
    "description": "Extract SAP deployment context from a job description",
    "parameters": {
        "type": "object",
        "properties": {
            "deployment_context": {
                "type": "object",
                "properties": {
                    "system_versions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the SAP system version (e.g., sap_tm_9.5)"
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Context or clarification for the version"
                                }
                            },
                            "required": ["name", "notes"],
                            "additionalProperties": False
                        },
                        "description": "List of SAP system versions"
                    },
                    "deployment_models": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "enum": ["on_premise", "cloud", "hybrid", "embedded"],
                                    "description": "Deployment model (e.g., cloud, embedded)"
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Context or clarification for the model"
                                }
                            },
                            "required": ["name", "notes"],
                            "additionalProperties": False
                        },
                        "description": "List of deployment models"
                    },
                    "project_types": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "enum": [
                                        "greenfield_implementation",
                                        "brownfield_implementation",
                                        "upgrade",
                                        "support",
                                        "rollout",
                                        "migration"
                                    ],
                                    "description": "Type of project (e.g., implementation)"
                                },
                                "notes": {
                                    "type": "string",
                                    "description": "Context or clarification for the project type"
                                }
                            },
                            "required": ["name", "notes"],
                            "additionalProperties": False
                        },
                        "description": "List of project types"
                    }
                },
                "required": ["system_versions", "deployment_models", "project_types"],
                "additionalProperties": False
            }
        },
        "required": ["deployment_context"],
        "additionalProperties": False
    }
}

@jd_router.post("/deployment_context")
async def parse_jd_deployment_context(file: UploadFile = File(...)):
    text = await extract_text(file)
    print(f"Extracted text: {text[:500]}...")  # Log the first 500 characters for debugging
    if not text.strip():
        raise HTTPException(400, "Empty file content")
    result = await call_parser(text, SYSTEM_JD_DEPLOYMENT_PROMPT, JSON_SCHEMA_JD_DEPLOYMENT)
    return JSONResponse(content=result)