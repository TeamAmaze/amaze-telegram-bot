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
restricted_commands = os.environ.get("RESTRICTED_COMMANDS")
issue_token = os.environ.get("ISSUE_TOKEN")
users_admins = os.environ.get("USERS_ADMINS")
issue_create_uri = os.environ.get("ISSUE_CREATE_URI")
owner = os.environ.get("OWNER")
repo = os.environ.get("REPOSITORY")
telegram_bot_name = os.environ.get("BOT_NAME")
base_url_telegram = "https://api.telegram.org/bot{}".format(telegram_system_token)
base_url_codacy_stats = "https://app.codacy.com/api/v3/analysis/organizations/gh/{}/repositories/{}/commit-statistics".format(owner, repo)
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
                if command_raw[bot_index_identifier+1:] != telegram_bot_name:
                    print("Not a command for Amaze bot, input command {}".format(command_raw[bot_index_identifier+1:]))
                    raise ValueError()
                command_raw = command_raw[:bot_index_identifier]
            print("Found a new interaction with amaze bot for message: {}".format(command_raw))
            if inputs and command_raw in inputs:
                # authenticate command permission
                if not is_command_permitted(command_raw, message):
                    print("User not permitted for the command {}".format(command_raw))
                    return inputs["commandNotPermitted"]
                result_command = inputs[command_raw]
                print("Found resultCommand {}".format(result_command))
                command_keyword = re.findall("##.+##", result_command)
                if len(command_keyword) != 0:
                    print("Processing regex {} for result command {}".format(command_keyword[0], result_command))
                    try:
                        return result_command.replace(command_keyword[0], "\n" +
                                                      format_command(inputs, message, command_keyword[0]))
                    except Exception as err:
                        return str(err)
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

            issue_number = re.findall("#\d{4}|#\d{3}", message.get("text"))
            if len(issue_number) != 0:
                print("Current request json {}".format(message))
                print("Found request for issue number {}".format(issue_number[0]))
                return git.parse_issue(issue_number[0][1:])
            elif message.get("text").startswith("## Issue explanation (write below this line)"):
                reporter_from = message.get("from")
                user_name = reporter_from.get("username")
                print("Found reporter {}, message {}".format(reporter_from, message.get("text")))
                return inputs["createissue"].format(git.create_issue(issue_create_uri, issue_token, message.get("text"), user_name))
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


def format_command(inputs, message, command_keyword):
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
    elif command_keyword == "loc":
        print("Calling codacy for LOC count at {}".format(base_url_codacy_stats))
        response = requests.get(url=base_url_codacy_stats)
        if response.status_code != 200:
            print("Codacy call fail for LOC at {}".format(base_url_codacy_stats))
            return "over 85k"
        data = response.json()["data"]
        print("Get response from codacy for url {}, {}".format(base_url_codacy_stats, data))
        number_loc = data[0].get("numberLoc")
        print("Found number of loc for repo {} to be {}".format(repo, str(number_loc)))
        return str(number_loc)
    else:
        return "_Command Not Found_"


def is_command_permitted(command, message):
    if command in restricted_commands.split(','):
        message_from = message.get("from")
        user_name = message_from.get("username")
        return user_name in users_admins.split(',')
    else:
        return True


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
