import flask
import re
import os
import json
import requests
import git
from flask import request, Response

app = flask.Flask(__name__)
app.config["DEBUG"] = True
function_switch = "ON"
telegram_system_token = os.environ.get('TELEGRAM_TOKEN')
request_session = os.environ.get("REQUEST_SESSION")
base_url_telegram = "https://api.telegram.org/bot{}".format(telegram_system_token)
send_message_url = base_url_telegram + "/sendMessage"


@app.route('/runCommand', methods=['POST'])
def api():
    data = request.get_json()
    request_token = request.args.get('token')
    message = data.get('message')
    if telegram_system_token == request_token and message is not None:
        try:
            send_message(process_command(load_input_dictionary(), message), message)
        except ValueError:
            return Response(status=200)
        return Response(status=200)
    else:
        # token doesn't match or message not valid,
        print("token doesn't match or message not valid; invalid request {}".format(request_token))
        return Response(status=200)


def process_command(inputs, message):
    if message.get("text") is not None:
        if message.get("text").startswith("/"):
            # SERVICE MAINTENANCE CHECK
            if function_switch == "OFF":
                print("Service down for maintenance")
                return inputs["serviceDown"]

            print("Current request json {}".format(message))
            command_raw = message.get("text")
            bot_index_identifier = command_raw.find('@')
            if bot_index_identifier != -1:
                command_raw = command_raw[:bot_index_identifier]
            print("Found a new interaction with amaze bot for message: {}".format(command_raw))
            if inputs and command_raw in inputs:
                result_command = inputs[command_raw]
                print("Found resultCommand {}".format(result_command))
                command_keyword = re.findall("##.+##", result_command)
                if len(command_keyword) != 0:
                    print("Processing regex {} for result command {}".format(command_keyword[0], result_command))
                    return result_command.replace(command_keyword[0], "\n" + format_command(inputs, command_keyword[0]))
                else:
                    return result_command
            else:
                print("Didn't find resultCommand for {}".format(command_raw))
                message["text"] = "/help"
                return inputs["default"], process_command(inputs, message)
        else:
            # SERVICE MAINTENANCE CHECK
            if function_switch == "OFF":
                print("Service down for maintenance")
                raise ValueError("Unable to handle operation")

            issue_number = re.findall("#\d{4}", message.get("text"))
            if len(issue_number) != 0:
                print("Current request json {}".format(message))
                print("Found request for issue number {}".format(issue_number[0]))
                return git.parse_issue(issue_number[0][1:])
            else:
                print("Unable to handle operation for chat id {}".format(message.get("chat").get("id")))
                raise ValueError("Unable to handle operation")
    elif message.get("new_chat_member"):
        # SERVICE MAINTENANCE CHECK
        if function_switch == "OFF":
            print("Service down for maintenance")
            raise ValueError("Unable to handle operation")
        print("Current request json {}".format(message))
        print("New member added to group: {}".format(message.get("new_chat_member")))
        return inputs["member"].format(message.get("new_chat_member").get("first_name")), inputs["member2"]


def format_command(inputs, command_keyword):
    command_keyword = command_keyword[2:-2]
    if command_keyword == "help":
        result = ""
        for x in inputs.keys():
            if not x.startswith("/"):
                continue
            result += "{}\n".format(x)
        print("Found help keyword response {}".format(result))
        return result
    elif command_keyword == "version":
        return git.parse_version()
    elif command_keyword == "dependencies":
        return git.parse_dependencies()
    elif command_keyword == "requestfeature":
        if request_session == "OPEN":
            return inputs["requestSessionOpen"]
        else:
            return inputs["requestSessionClosed"]
    elif command_keyword == "changelog":
        return git.parse_milestones()
    else:
        return "_Command Not Found_"


def send_message(command_result, data):
    if type(command_result) is tuple:
        print("Send multiple responses from bot")
        for x in command_result:
            send_message_request = build_post_message_request(x, data)
            print("Send post message request {} to url {}".format(send_message_request, send_message_url))
            # requests.post(send_message_url, data=send_message_request, headers={"Accept": "application/json"})
    else:
        print("Send single response from bot")
        send_message_request = build_post_message_request(command_result, data)
        print("Send post message request {} to url {}".format(send_message_request, send_message_url))
        # requests.post(send_message_url, data=send_message_request, headers={"Accept": "application/json"})


def build_post_message_request(command_result, data):
    return {"chat_id": data.get("chat").get("id"), "text": command_result, "parse_mode": "MARKDOWN"}


def load_input_dictionary():
    input_file_stream = open(r"inputs.json")
    return json.loads(input_file_stream.read())


app.run()
