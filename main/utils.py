import os
from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from putils import extract_and_format_key_value_pairs_from_user_prompt
from create_task import create_task

# Load environment variables
load_dotenv()

groq_api_key = os.getenv('GROQ_API_KEY')
llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192", temperature=0)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

vectors = None
response = None

# Define the prompt template
prompt = ChatPromptTemplate.from_template(
    "Retrieve the most relevant endpoint(s) from the provided context based on the user's query. "
    "Ensure the response strictly follows this format without deviation: \n\n"
    "{{\n"
    "  \"endpoint_url\": \"<URL>\",\n"
    "  \"payload\": {{\n"
    "    \"field1\": \"<value>\",\n"
    "    \"field2\": \"<value>\"\n"
    "    \"field3\": \"<value>\"\n"
    "    // Add additional fields as required\n"
    "  }}\n"
    "}}\n\n"
    "If a field value is not provided, leave it blank (e.g., \"field1\": \"\"). "
    "Replace <URL> with the actual endpoint URL and <value> with default or placeholder values for each field. "
    "Do not include additional text, explanations, or comments outside this JSON format.\n\n"
    "Context: {context}\n\nQuery: {input}\n"
)

# Make vector embedding asynchronous and use file reading properly
def vector_embedding(file_path):
    global vectors
    embeddings = HuggingFaceEmbeddings()

    print("Vector is creating...")

    with open(file_path, 'r') as file:
        text = file.read()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=2000)
    chunks = text_splitter.split_text(text)

    documents = [Document(page_content=chunk) for chunk in chunks]
    vectors = FAISS.from_documents(documents, embeddings)
    vectors.save_local("data/faiss_index")
    print("Vector embeddings created and saved.")


# Retrieval Function
def retrieval(query):
    global vectors, response
    if not vectors:
        print("Vector store not initialized. Please run the embedding function first.")
        return None

    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = vectors.as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)

    response = retrieval_chain.invoke({'context': 'Your context here', 'input': query})

    try:
        answer = response['answer']
        return answer
    except Exception as e:
        print(f"Error: {e}")
        return None

# Function to extract and format key-value pairs from the user prompt
def process_query_prompt(query):
    model_response, parsed_res = extract_and_format_key_value_pairs_from_user_prompt(query)
    # print("user query : ",model_response)
    query_intents = []
    for key_value in parsed_res:
        if 'query_intent' in key_value:
            query_intents.append(key_value['query_intent'])

    return query_intents, parsed_res

# Function to assign status based on parsed response
def assign_status(parsed_res):
    status = "Unknown"  # Default status if no valid status is found
    warnings = []

    for key_value in parsed_res:
        if 'status' in key_value:
            status_value = key_value['status'].lower()
            if status_value in ['opened', 'closed', 'assigned']:
                status = status_value.capitalize()  # Capitalize the status value
            else:
                warnings.append(f"Invalid status value: '{key_value['status']}'")
            break  # Stop after finding the first status

    return status, warnings


# Function to update response with missing keys
def update_response(parsed_response, value):
    missing_keys = []

    def recursive_update(response, updates):
        for item in updates:
            for key, val in item.items():
                if isinstance(response, dict):
                    if 'payload' in response:
                        # Check for 'page' and 'limit' conditions
                        if 'page' in response['payload'] and not response['payload']['page']:
                            response['payload']['page'] = 1
                        if 'limit' in response['payload'] and not response['payload']['limit']:
                            response['payload']['limit'] = 10
                        
                        if key not in response['payload']:
                            missing_keys.append(key)
                            # Add the missing key with its value
                            response['payload'][key] = val
                        else:
                            response['payload'][key] = val
                    elif key not in response:
                        missing_keys.append(key)
                        # Add the missing key with its value
                        response[key] = val
                    
                    # Recursively handle nested dictionaries
                    if isinstance(val, dict):
                        recursive_update(response[key], [val])
    
    recursive_update(parsed_response, value)
    missing_keys = [key for key in missing_keys if key != 'query_intent']
    return missing_keys


import requests
def call_api(endpoint_url, payload):
    """Send an API request to the specified URL with the given payload as form-data."""
    BToken = os.getenv('BearerToken')  # Get Bearer token from environment variable
    headers = {
        "Authorization": f"Bearer {BToken}"
    }

    try:
        print(f"Sending API request to: {endpoint_url}")
        
        # Ensure the payload is a dictionary before proceeding
        if isinstance(payload, dict):
            form_data = {key: str(value) for key, value in payload.items()}
            
            response = requests.post(endpoint_url, headers=headers, data=form_data)
            
            if response.status_code == 200:
                print("API call successful!")
                return response.json()
            else:
                print(f"API call failed with status code {response.status_code}.")
                print("Response:", response.text)
                return {"error": "API call failed", "status_code": response.status_code, "response": response.text}
        else:
            print("Invalid payload. Must be a dictionary.")
            return {"error": "Invalid payload", "message": "Payload must be a dictionary."}
    
    except Exception as e:
        print(f"Error: API call failed with exception: {e}")
        return {"error": "Exception occurred", "message": str(e)}
    
import json
def summarize_api_response(api_response):
    api_response_str = str(api_response)  # Or json.dumps(api_response, indent=2) for better formatting
    
    summary_prompt = ChatPromptTemplate.from_template(
        "Summarize the following API response in short summary but covering all key details:\n\n"
        "{response}\n\n"
        "Summary:"
    )
    
    # Now using the `RunnableSequence` chaining method
    summarization_chain = summary_prompt | llm  # This is the updated chaining method
    
    sumry_api_response = summarization_chain.invoke({"response": api_response_str})
    sumry_api_response_content = sumry_api_response.content
    # print("sumry_api_response : ",type(sumry_api_response))
    # print("sumry_api_response_content : ",type(sumry_api_response_content))

    # print("sumry_api_response_content : ",sumry_api_response_content)
    # Convert the response to a dictionary (if it's a string that looks like a JSON object)
    try:
        return json.loads(sumry_api_response_content)
    except (TypeError, json.JSONDecodeError):
        return {"summary": sumry_api_response_content}