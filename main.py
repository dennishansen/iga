import subprocess
import langchain
import openai
import click

api_key = "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"

actions = ["TALK_TO_USER", "RUN_SHELL_COMMAND", "THINK"]

def talk_to_user(rational, message):
    print("RATIONALE")
    print(rational)
    print("MESSAGE")
    print(message)

def run_shell_command(rational, command):
    print("RATIONALE")
    print(rational)
    print("RUN_SHELL_COMMAND")
    print(command)
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    response = result.stdout.strip() if result.stdout.strip() else "EMPTY"
    print(response)
    if(response):
        return response
    else:
        return "EMPTY"

def think(rationale, prompt):
    print("RATIONALE")
    print(rationale)
    print("THINK")
    print(prompt)
    return "NEXT_ACTION"

def get_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content

def parse_response(response):
    lines = response.split("\n")
    current_key = ''
    rationale = ''
    action = ''
    content = ''
    for line in lines:
        if line == '':
            continue
        elif line.startswith("RATIONALE"):
            current_key = "RATIONALE"
        elif line.startswith(tuple(actions)):
            current_key = line
            action = line
        elif current_key == "RATIONALE":
            rationale += line + "\n"
        elif current_key in actions:
            content += line + '\n'
    return {"action": action, "rationale": rationale, "content": content, "response_raw": response}
    

def process_message(messages):
    # Replace this with your OpenAI API key
    openai.api_key = api_key

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=2048,
        temperature=0.2,
    )

    generated_response = response.choices[0]['message']['content'].strip()
    parsed_response = parse_response(generated_response)
    return parsed_response

def handle_action(messages):
    response_data = process_message(messages)
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
        return handle_action(messages)
    elif action == "THINK":
        next_message = think(rationale, content)
        messages.append({"role": "user", "content": next_message})
        return handle_action(messages)
    else:
        print("Unknown action. Please try again.")

    return messages

@click.command()
def chat_cli():
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]

    while True:
        user_input = input("User: ")
        messages.append({"role": "user", "content": user_input})
        handle_action(messages)

if __name__ == "__main__":
    chat_cli()