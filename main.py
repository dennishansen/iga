import subprocess
import openai
import click
import os
import time
import threading
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

actions = ["TALK_TO_USER", "RUN_SHELL_COMMAND", "THINK", "READ_FILES", "WRITE_FILE"]

def talk_to_user(rational, message):
    print("Iga's thoughts: " + rational)
    print("Iga: " + message)

def run_shell_command(rational, command):
    print("Iga's thoughts: " + rational)
    print("Iga: Run command: " + command)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    response = result.stdout.strip() if result.stdout.strip() else "EMPTY"
    print(response)
    if(response):
        return response
    else:
        return "EMPTY"

def think(rationale, prompt):
    print("Iga's thoughts: " + rationale)
    print("Iga's thoughts: " + prompt)
    return "NEXT_ACTION"

def read_files(rational, paths):
    print("Iga's thoughts: " + rational)
    print("Iga: Reading files: " + paths)
    files = paths.split("\n")
    files = [file for file in files if file]
    content = ""
    for file in files:
        content += file + '\n'
        content += get_file(file) + '\n'
    print(content)
    return content

def write_file(rational, contents):
    print(contents)
    print("Iga's thoughts: " + rational)
    path = contents.split("\n")[0]
    print("Iga: Writing file:" + path)
    content = contents.split("\n")[1:]
    # Create the file
    with open(path, 'w') as file:
        for line in content:
            file.write(line + '\n')
    return "NEXT_ACTION"

def get_file(path):
    with open(path, 'r') as file:
        content = file.read()
    return content

def parse_response(response):
    lines = response.split("\n")
    current_key = ''
    rationale = ''
    action = ''
    content = ''
    firstActionFound = False
    firstRationaleFound = False
    for line in lines:
        if line == '':
            continue
        elif line.startswith("RATIONALE") and not firstRationaleFound:
            current_key = "RATIONALE"
            firstRationaleFound = True
        elif line.startswith(tuple(actions)) and not firstActionFound:
            current_key = line
            action = line
            firstActionFound = True
        elif current_key == "RATIONALE":
            rationale += line + "\n"
        elif current_key in actions:
            content += line + '\n'
    return {"action": action, "rationale": rationale, "content": content, "response_raw": response}

def process_message(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=2048,
            temperature=0.2,
        )

        generated_response = response.choices[0]['message']['content'].strip()
        parsed_response = parse_response(generated_response)
        parsed_response["success"] = True
        return parsed_response

    except openai.OpenAIError as error:
        print(f"An error occurred while calling the OpenAI API: {error}")
    except ValueError as error:
        print(f"An error occurred while parsing the response: {error}")
    except Exception as error:
        print(f"An unexpected error occurred: {error}")

    return {"success": False}


def handle_action(messages):
    response_data = process_message(messages)
    if response_data["success"]:
        messages.append({"role": "assistant", "content": response_data["response_raw"]})
        # print(messages)
        action = response_data["action"]
        rationale = response_data["rationale"]
        content = response_data["content"]

        if action == "TALK_TO_USER":
            talk_to_user(rationale, content)
        elif action == "RUN_SHELL_COMMAND":
            next_message = run_shell_command(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "THINK":
            next_message = think(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "READ_FILES":
            next_message = read_files(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "WRITE_FILE":
            next_message = write_file(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        else:
            # If it fails, assume they're talking to the user
            talk_to_user("", response_data["response_raw"])
    else:
        print("Failed to process the message. Please try again.")

    return messages

@click.command()
def chat_cli():
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]

     # Add a message from Iga as a welcome message
    welcome_message = "Hello! I'm Iga, your personal AI assistant. How can I help you today?"
    messages.append({"role": "assistant", "content": welcome_message})
    print("Iga: " + welcome_message)

    while True:
        user_input = input("User: ")
        messages.append({"role": "user", "content": user_input})
        handle_action(messages)

if __name__ == "__main__":
    chat_cli()

