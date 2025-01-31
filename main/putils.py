import re
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

def extract_and_format_key_value_pairs_from_user_prompt(query):
    # Load API key
    load_dotenv()
    groq_api_key = os.getenv('GROQ_API_KEY')
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192", temperature=0)

    # Correct common typos in the query
    query = query.replace("categoriy", "category")  # Fix "categoriy" to "category"
    
    # Define separator words to split query intent from details
    separator_words = ['and', 'with', ',', ';', 'or', 'the']

    # Split the query into intent and additional details
    query_parts = re.split(r'\b(?:' + '|'.join(map(re.escape, separator_words)) + r')\b', query, maxsplit=1)
    query_intent = query_parts[0].strip()
    additional_details = query_parts[1].strip() if len(query_parts) > 1 else ""

    # Adjusted prompt to handle extracted query parts
    prompt = ChatPromptTemplate.from_template(
        "Extract key-value pairs from the following details. "
        "Ensure the response strictly follows this format without deviation, and use underscores between words for keys: \n\n"
        "{{\n"
        "  \"key_value_pairs\": {{\n"
        "    \"query_intent\": \"<intent>\",\n"
        "    \"additional_keys\": {{<additional_key_value_pairs>}}\n"
        "    \"requested_by\": \"<email>\",\n"
        "    \"assigned_to\": \"<email>\",\n"
        "    \"assigned_by\": \"<email>\",\n"
        "    \"assigner_name\": \"<value>\",\n"
        "    \"assignee_name\": \"<value>\",\n"
        "    \"requestor_name\": \"<value>\",\n"
        "  }}\n"
        "}}\n\n"
        "If a field value is not provided, leave it blank (e.g., \"field1\": \"\"). "
        "The 'query_intent' key should represent the main user question or request in free text without using underscores between words."
        "Extract additional details as key-value pairs. Ignore filler words like 'is,' 'and,' 'are,' etc. "
        "Query Intent: {query_intent}\nDetails: {additional_details}\n"
        "Ensure all keys use underscores between words but do not start with an underscore unless explicitly mentioned in the query (e.g., '_id')."
    )

    # Format the prompt
    formatted_prompt = prompt.format(query_intent=query_intent, additional_details=additional_details)
    response = llm.invoke(formatted_prompt)

    # Extract and parse response content
    output = response.content.strip()

    # Fallback: Ensure 'query_intent' is included
    if "query_intent" not in output:
        output = f"{{\"query_intent\": \"{query_intent}\"}},\n" + output

    # Extract key-value pairs with regex
    matches = re.findall(r'"([^"]+)":\s*"([^"]+)"', output)

    # Map extracted pairs to keys like 'requested_by', 'assigned_to', and 'assigned_by' if email is found
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    matches = [(key, value) for key, value in matches if value not in [None, '']]

    # Flags to track the roles (to avoid duplicate assignments)
    assigned_to_found = False
    assigned_by_found = False
    requested_by_found = False

    # Map extracted pairs to keys like 'requested_by', 'assigned_to', and 'assigned_by' if email is found
    for i, (key, value) in enumerate(matches):
        # Validate if the value is a valid email
        if re.match(email_pattern, value):
            if 'assigned to' in query.lower() and not assigned_to_found:
                matches[i] = ('assigned_to', value)  # Map to assigned_to
                assigned_to_found = True
            elif 'assigned by' in query.lower() and not assigned_by_found:
                matches[i] = ('assigned_by', value)  # Map to assigned_by
                assigned_by_found = True
            elif 'requester' in query.lower() and not requested_by_found:
                matches[i] = ('requested_by', value)  # Map to requested_by
                requested_by_found = True
        else:
            # Explicitly check for "assignee name" and "assigner name"
            if "assignee name" in key.lower():
                matches[i] = ("assignee_name", value)
            elif "assigner name" in key.lower():
                matches[i] = ("assigner_name", value)    
            elif "requestor name" in key.lower():  # Add this check
                matches[i] = ("requestor_name", value)


    # Filter out requested_by and assigned_by if their value is '<email>' or empty
    filtered_matches = [
        (key, value) for key, value in matches
        if (key not in ['requested_by', 'assigned_by'] or value != '<email>' and value != '')
    ]

    # Remove 'task_' prefix from keys if they belong to task attributes
    cleaned_matches = []
    for key, value in filtered_matches:
        if key.startswith('task_'):
            # Corrected handling: keep 'task_' in the key (no change needed)
            cleaned_matches.append((key, value))
        else:
            cleaned_matches.append((key, value))

    # Remove '_email' suffix from keys (e.g., 'requested_by_email' becomes 'requested_by')
    cleaned_matches_no_email = []
    for key, value in cleaned_matches:
        if key == 'task_title':
            cleaned_matches_no_email.append(('title', value))
        if key.endswith('_email'):
            cleaned_matches_no_email.append((key[:-6], value))  # Remove the '_email' suffix
        else:
            cleaned_matches_no_email.append((key, value))

    # Format extracted key-value pairs into a structured string
    formatted_string = ",".join(f"{key}={value}" for key, value in cleaned_matches_no_email)

    # Create a list of key-value pairs
    key_value_list = [{key: value} for key, value in cleaned_matches_no_email]

    return formatted_string, key_value_list


# query = "Create a new task titled 'Sample title', and assigned to suresh@jukshio.com, with status 'Opened'. and requested by sanketh_consultant@jukshio.com, and the category is 'Electronics', with the sub-category 'Supplies'. and message is 'Sample remark for testing category notification.' The task is assigned by sanketh_consultant@jukshio.com, and the requestor name is sanketh. The category ID is '20' and the sub-category ID is '32'. and assignee name is suresh, the action is 'Opened', and assigner name is sanketh."
# formatted_string, key_value_list = extract_and_format_key_value_pairs_from_user_prompt(query)
# print("\nkey_value_list", key_value_list)



# import re
# from langchain_core.prompts import ChatPromptTemplate
# from dotenv import load_dotenv
# import os
# from langchain_groq import ChatGroq

# def extract_and_format_key_value_pairs_from_user_prompt(query):
#     # Load API key
#     load_dotenv()
#     groq_api_key = os.getenv('GROQ_API_KEY')
#     llm = ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192", temperature=0)

#     # Correct common typos in the query
#     query = query.replace("categoriy", "category")  # Fix "categoriy" to "category"
    
#     # Define separator words to split query intent from details
#     separator_words = ['and', 'with', ',', ';', 'or', 'the']

#     # Split the query into intent and additional details
#     query_parts = re.split(r'\b(?:' + '|'.join(map(re.escape, separator_words)) + r')\b', query, maxsplit=1)
#     query_intent = query_parts[0].strip()
#     additional_details = query_parts[1].strip() if len(query_parts) > 1 else ""

#     # Adjusted prompt to handle extracted query parts
#     prompt = ChatPromptTemplate.from_template(
#         "Extract key-value pairs from the following details. "
#         "Ensure the response strictly follows this format without deviation, and use underscores between words for keys: \n\n"
#         "{{\n"
#         "  \"key_value_pairs\": {{\n"
#         "    \"query_intent\": \"<intent>\",\n"
#         "    \"additional_keys\": {{<additional_key_value_pairs>}}\n"
#         "    \"requested_by\": \"<email>\",\n"
#         "    \"assigned_to\": \"<email>\",\n"
#         "    \"assigned_by\": \"<email>\",\n"
#         "    \"assigner_name\": \"<value>\",\n"
#         "    \"assignee_name\": \"<value>\",\n"
#         "    \"requestor_name\": \"<value>\",\n"
#         "  }}\n"
#         "}}\n\n"
#         "If a field value is not provided, leave it blank (e.g., \"field1\": \"\"). "
#         "The 'query_intent' key should represent the main user question or request in free text without using underscores between words."
#         "Extract additional details as key-value pairs. Ignore filler words like 'is,' 'and,' 'are,' etc. "
#         "Query Intent: {query_intent}\nDetails: {additional_details}\n"
#         "Ensure all keys use underscores between words but do not start with an underscore unless explicitly mentioned in the query (e.g., '_id')."
#     )

#     # Format the prompt
#     formatted_prompt = prompt.format(query_intent=query_intent, additional_details=additional_details)
#     response = llm.invoke(formatted_prompt)

#     # Extract and parse response content
#     output = response.content.strip()

#     # Fallback: Ensure 'query_intent' is included
#     if "query_intent" not in output:
#         output = f"{{\"query_intent\": \"{query_intent}\"}},\n" + output

#     # Extract key-value pairs with regex
#     matches = re.findall(r'"([^"]+)":\s*"([^"]+)"', output)

#     # Map extracted pairs to keys like 'requested_by', 'assigned_to', and 'assigned_by' if email is found
#     email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

#     matches = [(key, value) for key, value in matches if value not in [None, '']]

#     # Flags to track the roles (to avoid duplicate assignments)
#     assigned_to_found = False
#     assigned_by_found = False
#     requested_by_found = False

#     # Map extracted pairs to keys like 'requested_by', 'assigned_to', and 'assigned_by' if email is found
#     for i, (key, value) in enumerate(matches):
#         # Validate if the value is a valid email
#         if re.match(email_pattern, value):
#             if 'assigned to' in query.lower() and not assigned_to_found:
#                 matches[i] = ('assigned_to', value)  # Map to assigned_to
#                 assigned_to_found = True
#             elif 'assigned by' in query.lower() and not assigned_by_found:
#                 matches[i] = ('assigned_by', value)  # Map to assigned_by
#                 assigned_by_found = True
#             elif 'requested by' in query.lower() and not requested_by_found:
#                 matches[i] = ('requested_by', value)  # Map to requested_by (email)
#                 requested_by_found = True
#         else:
#             # Explicitly check for "assignee name" and "assigner name"
#             if "assignee name" in key.lower():
#                 matches[i] = ("assignee_name", value)
#             elif "assigner name" in key.lower():
#                 matches[i] = ("assigner_name", value)    
#             elif "requestor name" in key.lower():  # Add this check
#                 matches[i] = ("requestor_name", value)  # Explicitly map 'requestor_name' to 'requested_by'

#     # Ensure 'requested_by' and 'assigned_by' are populated with the same email if they match
#     for i, (key, value) in enumerate(matches):
#         if key == 'requested_by' and value == 'sanketh_consultant@jukshio.com':
#             matches[i] = ('assigned_by', value)  # Also assign 'assigned_by' with the same email

#     # Filter out requested_by and assigned_by if their value is '<email>' or empty
#     filtered_matches = [
#         (key, value) for key, value in matches
#         if (key not in ['requested_by', 'assigned_by'] or value != '<email>' and value != '')
#     ]

#     # Remove 'task_' prefix from keys if they belong to task attributes
#     cleaned_matches = []
#     for key, value in filtered_matches:
#         if key.startswith('task_'):
#             # Corrected handling: keep 'task_' in the key (no change needed)
#             cleaned_matches.append((key, value))
#         else:
#             cleaned_matches.append((key, value))

#     # Remove '_email' suffix from keys (e.g., 'requested_by_email' becomes 'requested_by')
#     cleaned_matches_no_email = []
#     for key, value in cleaned_matches:
#         if key == 'task_title':
#             cleaned_matches_no_email.append(('title', value))
#         if key.endswith('_email'):
#             cleaned_matches_no_email.append((key[:-6], value))  # Remove the '_email' suffix
#         else:
#             cleaned_matches_no_email.append((key, value))

#     # Format extracted key-value pairs into a structured string
#     formatted_string = ",".join(f"{key}={value}" for key, value in cleaned_matches_no_email)

#     # Create a list of key-value pairs
#     key_value_list = [{key: value} for key, value in cleaned_matches_no_email]

#     return formatted_string, key_value_list


# # Sample query to test
# query = "Create a new task titled Sample title and assigned to suresh@jukshio.com with status Opened and requested by sanketh_consultant@jukshio.com and the category is Electronics and sub-category Supplies and message is Sample remark for testing category notification The task is assigned by sanketh_consultant@jukshio.com and requestor name is sanketh The category ID is 20 and sub-category ID is 32 and assignee name is suresh and action is Opened and assigner name is sanketh"
# formatted_string, key_value_list = extract_and_format_key_value_pairs_from_user_prompt(query)
# print("\nkey_value_list", key_value_list)
