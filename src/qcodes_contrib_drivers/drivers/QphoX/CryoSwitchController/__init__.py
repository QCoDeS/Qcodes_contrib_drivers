import os
import json


# Function to create a port template
def create_port_template():
    return {"contact_1": 0, "contact_2": 0, "contact_3": 0, "contact_4": 0, "contact_5": 0, "contact_6": 0}


# Function to create the main JSON structure with all values initially set to 0
def create_json_structure():
    ports = ["port_A", "port_B", "port_C", "port_D"]
    json_data = {}

    for sn in ["SN", "SN0", "SN12", "SN22", "SN23", "SN24", "SN25", "SN26", "SN300", "SN6", "SN65535"]:
        json_data[sn] = {port: create_port_template() for port in ports}

    # Set exceptions where values should be 1
    json_data["SN24"]["port_B"]["contact_1"] = 1
    json_data["SN24"]["port_B"]["contact_3"] = 1
    json_data["SN24"]["port_B"]["contact_4"] = 1
    json_data["SN24"]["port_B"]["contact_5"] = 1
    json_data["SN24"]["port_B"]["contact_6"] = 1

    json_data["SN6"]["port_A"]["contact_1"] = 1
    json_data["SN6"]["port_A"]["contact_2"] = 1
    json_data["SN6"]["port_A"]["contact_3"] = 1
    json_data["SN6"]["port_A"]["contact_4"] = 1
    json_data["SN6"]["port_A"]["contact_5"] = 1
    json_data["SN6"]["port_A"]["contact_6"] = 1

    return json_data


# Specify the file path
file_path = os.path.dirname(__file__) + "/states_empty.json"

# Check if the file exists
if not os.path.exists(file_path):
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Create the JSON structure
    json_data = create_json_structure()

    # Write the JSON data to the file
    with open(file_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)
