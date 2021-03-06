import requests
import datetime
import base64
import re

GITHUB_API_URI = "https://api.github.com"
AMAZE_OWNER = "TeamAmaze"
AMAZE_REPO = "AmazeFileManager"
GITHUB_AMAZE_ISSUES_URI = "https://github.com/TeamAmaze/AmazeFileManager/issues/{}"
GITHUB_MILESTONES_URI = "https://github.com/TeamAmaze/AmazeFileManager/milestones"


def parse_version():
    version = ""
    for x in parse_releases():
        name = x["name"]
        date = datetime.datetime.strptime(x['published_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        if not x["prerelease"]:
            version += "*Release*\n\n_{}_\n*Released On:*\n{}\n".format(name, date)
        elif x["prerelease"]:
            version += "\n*Beta*\n\n_{}_\n*Released On:*\n{}\n".format(name, date)
        assets = x["assets"]
        if len(assets) > 0:
            current_asset = assets[0]
            download = current_asset["browser_download_url"]
            version += "\n[Download Here]({})\n".format(download)
    print("Found versions {}".format(version))
    return version


def parse_issue(issue_number):
    uri = GITHUB_API_URI + "/repos/{}/{}/issues/{}".format(AMAZE_OWNER, AMAZE_REPO, issue_number)
    print("Get issue details from github uri {}".format(uri))
    response = requests.get(url=uri, headers={"Accept": "application/vnd.github.v3+json"})
    if response.status_code != 200:
        return parse_pr(issue_number)
    data = response.json()
    html_url = data["html_url"]
    if "pull" in html_url:
        return parse_pr(issue_number)
    created_date = datetime.datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ').date()
    details = "*Issue details for #{}*\n\nTitle: {}\nStatus: {}\nCreated date: " \
              "{}\nCreated by: {}".format(issue_number, data["title"], data["state"],
                                          created_date, data["user"]["login"])
    if data["assignee"] is not None:
        details += "\nAssigned to: {}".format(data["assignee"]["login"])
    if data["milestone"] is not None:
        details += "\nMilestone: {}".format(data["milestone"]["title"])
    if data["closed_at"] is not None:
        closed_date = datetime.datetime.strptime(data['closed_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        details += "\nClosed at: {}".format(closed_date)
    if data["closed_by"] is not None:
        details += "\nClosed by: {}".format(data["closed_by"]["login"])
    details += "\n\n" + data["html_url"]
    print("Found issue details {}".format(details))
    return details


def parse_pr(pr_number):
    uri = GITHUB_API_URI + "/repos/{}/{}/pulls/{}".format(AMAZE_OWNER, AMAZE_REPO, pr_number)
    print("Get pr details from github uri {}".format(uri))
    response = requests.get(url=uri, headers={"Accept": "application/vnd.github.v3+json"})
    if response.status_code != 200:
        print("Couldn't resolve either pr or issue for {}".format(pr_number))
        raise ValueError("Couldn't resolve either pr or issue")
    data = response.json()
    created_date = datetime.datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ').date()
    details = "*PR details for #{}*\n\nTitle: {}\nStatus: {}\nCreated date: " \
              "{}\nCreated by: {}".format(pr_number, data["title"], data["state"], created_date, data["user"]["login"])
    if data["assignee"] is not None:
        details += "\nAssigned to: {}".format(data["assignee"]["login"])
    fixes_issue = re.findall("Fixes #\d{4}", data["body"])
    if len(fixes_issue) != 0:
        details += "\nFixes issue(s): "
        for issue_raw in fixes_issue:
            issue = issue_raw[-4:]
            details += "[" + issue + "](" + GITHUB_AMAZE_ISSUES_URI.format(issue) + ")"
    if data["closed_at"] is not None:
        closed_date = datetime.datetime.strptime(data['closed_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        details += "\nClosed at: {}".format(closed_date)
    if not data["mergeable"]:
        details += "\nPR can't be merged"
    if data["merged"] and data["merged_by"] is not None:
        details += "\nMerged by: {}".format(data["merged_by"]["login"])
    if data["merged_at"] is not None:
        merged_at = datetime.datetime.strptime(data['merged_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        details += "\nMerged at: {}".format(merged_at)
    details += "\n\n" + data["html_url"]
    print("Found pr details {}".format(details))
    return details


def parse_dependencies():
    uri = GITHUB_API_URI + "/repos/{}/{}/contents/app/build.gradle".format(AMAZE_OWNER, AMAZE_REPO)
    print("Get dependencies from github uri {}".format(uri))
    response = requests.get(url=uri, headers={"Accept": "application/vnd.github.v3+json"})
    data = response.json()
    deps_raw = base64.b64decode(data["content"]).decode('utf-8')
    deps = ""
    for line in deps_raw.splitlines(True):
        if "implementation" in line:
            deps += line.replace("implementation ", "")
    print("Found deps")
    return deps


def parse_releases():
    uri = GITHUB_API_URI + "/repos/{}/{}/releases".format(AMAZE_OWNER, AMAZE_REPO)
    print("Get releases from github uri {}".format(uri))
    response = requests.get(url=uri, headers={"Accept": "application/vnd.github.v3+json"})
    data = response.json()
    release_found = False
    beta_found = False
    releases_array = []
    for x in data:
        if release_found and beta_found:
            break
        if not x["prerelease"] and not release_found:
            release_found = True
            releases_array.append(x)
        elif x["prerelease"] and not beta_found:
            beta_found = True
            releases_array.append(x)
    return releases_array


def parse_milestones():
    uri = GITHUB_API_URI + "/repos/{}/{}/issues".format(AMAZE_OWNER, AMAZE_REPO)
    milestone_uri = GITHUB_API_URI + "/repos/{}/{}/milestones".format(AMAZE_OWNER, AMAZE_REPO)
    print("Get all milestone from github uri {}".format(milestone_uri))
    response = requests.get(url=milestone_uri, params={"state": "all"},
                            headers={"Accept": "application/vnd.github.v3+json"})
    data = response.json()
    output_map = {}
    milestone_links = {}
    milestone_currently_active = {}
    output = ""
    milestone_titles = []
    for milestone in data:
        milestone_titles.append(milestone["number"])
        milestone_links.update({milestone["title"]: milestone["html_url"]})
        if milestone["state"] == "open":
            milestone_currently_active.update({milestone["title"]: True})
        else:
            milestone_currently_active.update({milestone["title"]: False})
    milestone_titles.sort(reverse=True)
    milestone_titles = milestone_titles[0:3]
    for milestone_number in milestone_titles:
        issues_response = requests.get(url=uri, params={"milestone": milestone_number, "state": "closed"},
                                       headers={"Accept": "application/vnd.github.v3+json"})
        print("Get all issues for milestone {} from github uri {}".format(milestone_number, milestone_uri))
        issues_data = issues_response.json()
        for current_issue in issues_data:
            milestone_data = current_issue["milestone"]
            output_map.update(
                {milestone_data["title"]:
                     "- {}".format(current_issue["title"]) if output_map.get(milestone_data["title"]) is None else
                     "{}\n- {}".format(output_map.get(milestone_data["title"]), current_issue["title"])})
    for current in output_map.items():
        output += "\n\n[{}]({}) - _{}_\n{}".format(current[0], milestone_links.get(current[0]),
                                                   "ONGOING" if milestone_currently_active.get(current[0])
                                                   else "RELEASED", current[1])
    output += "\n\nFind full changelog [here]({})".format(GITHUB_MILESTONES_URI)
    print("Found changelog: {}".format(output))
    return output


def create_issue(uri, token, issue_message, reporter):
    request_body = create_issue_body(issue_message, reporter)
    print("Create issue by {} with request body: {}".format(reporter, request_body))
    response = requests.post(uri, params={"channel": "telegram", "token": token}, json=request_body)
    response_json = response.json()
    print("Get response body from create_issue {}".format(response_json))
    if not response.ok or response_json is None or "message" in response_json:
        raise Exception("Failed to create issue")
    else:
        result = "[{}]({})".format(response_json["number"], response_json["html_url"])
        print("Return createissue response {}".format(result))
        return result


def create_issue_body(issue_message, reporter):
    title = "Crash reported by {}".format(reporter)
    issue_message += "\t\tReporter: {}".format(reporter)
    return {"title": title, "body": issue_message}
