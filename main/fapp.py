from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from utils import vector_embedding, retrieval, process_query_prompt, update_response, assign_status, call_api,summarize_api_response
from fastapi.staticfiles import StaticFiles
from typing import Optional
from utils import create_task 
# FastAPI setup
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models for API request and response
class UserQuery(BaseModel):
    query: str
    
# FastAPI startup event to load vector embeddings
@app.on_event("startup")
async def load_vector_store():
    file_path = "data/api.txt"  # Path to your input text file
    vector_embedding(file_path)

class APIResponse(BaseModel):
    query_intent: str
    status: str = "Unknown"  # Ensure that a default value is set
    warnings: list = []
    errors: list = []
    updated_mdl_res_with_value: dict = None
    external_api_response: Optional[dict] = None
    missing_keys: list = []
    empty_values_from_use_qry: list = []
    given_values_from_usr_qry: list = []
    summary: Optional[dict] = None

# FastAPI route to process query
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def get_query_form(request: Request):
    # Render HTML template
    return templates.TemplateResponse("index.html", {"request": request})

import re
EMAIL_REGEX = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
# Modify the part in process_query function:
@app.post("/process-query", response_model=APIResponse)
async def process_query(user_query: UserQuery):
    query = user_query.query
    try:
        # Extract key-value pairs from the user prompt
        query_intents, parsed_res = process_query_prompt(query)

        response = retrieval(query_intents[0])
        print("user query : ", parsed_res)
        print("model_response : ", response)
        if not response:
            raise HTTPException(status_code=500, detail="No valid response from the model")

        updated_mdl_res_with_value = json.loads(response)
        missing_keys = update_response(updated_mdl_res_with_value, parsed_res)
        # print("updated model response with value : ", updated_mdl_res_with_value)
        # Assign the status and capture warnings
        status, status_warnings = assign_status(parsed_res)

        # Now, instead of returning the response directly, we automatically call the external API
        endpoint_url = updated_mdl_res_with_value.get("endpoint_url")
        payload = updated_mdl_res_with_value.get("payload")
        payload["status"] = status
        
        # with open('data/payload.json', 'w') as f:
        #     json.dump(payload, f, indent=4)
        
        given_values_from_usr_qry = []
        empty_values_from_use_qry = []

        # Iterate over the payload and check the corresponding values in the model response
        for key, value in payload.items():
            model_value = updated_mdl_res_with_value.get(key)

            if value:  # If the payload has a non-empty value
                given_values_from_usr_qry.append(key)
            else:
                empty_values_from_use_qry.append(key)

        # Check if there are any keys in empty_values
        if empty_values_from_use_qry:
            # If empty_values has any keys, set external_api_response to None and skip the API call
            external_api_response = None
        else:
            if endpoint_url == "https://amt-gcp-dev.soham.ai/inventory-task/v1/create_task":
                # Call the create_task function and capture the response
                external_api_response = create_task(endpoint_url,payload)
                print("Create Task API call successful!")
                # print("external_api_response :", external_api_response)# Now this will return the response
                print("create external_api_response :", type(external_api_response))#
            else:
                # Handle other cases
                if endpoint_url and payload:
                    external_api_response = call_api(endpoint_url, payload)
                    print("external_api_response :", type(external_api_response))#
                else:
                    external_api_response = None
                    raise HTTPException(status_code=500, detail="Missing endpoint_url or payload")

        summary = None
        if external_api_response:
            summary = summarize_api_response(external_api_response)
            # print("summary type", type(summary))
            # print("summary : ", summary)

        return APIResponse(
            query_intent=query_intents[0],
            status=status,
            warnings=status_warnings + [f"Missing keys in payload: {', '.join(missing_keys)}"] if missing_keys else [],
            errors=[],
            missing_keys=missing_keys,
            updated_mdl_res_with_value=updated_mdl_res_with_value,  # Return the parsed response here
            external_api_response=external_api_response,  # Set to None or actual API response
            given_values_from_usr_qry=given_values_from_usr_qry,  # Return populated values
            empty_values_from_use_qry=empty_values_from_use_qry,
            summary=summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
# To run the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)