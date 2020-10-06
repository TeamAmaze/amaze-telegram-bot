import requests
import datetime
import base64

GITHUB_API_URI = "https://api.github.com"
AMAZE_OWNER = "TeamAmaze"
AMAZE_REPO = "AmazeFileManager"


def parse_version():
    version = ""
    for x in parse_releases():
        name = x["name"]
        date = datetime.datetime.strptime(x['published_at'], '%Y-%m-%dT%H:%M:%SZ').date()
        current_asset = x["assets"][0]
        download = current_asset["browser_download_url"]
        if not x["prerelease"]:
            version += "*Release*:\n_{}_\n*Released On:*\n{}\n\n[Download Here]({})\n\n".format(name, date, download)
        elif x["prerelease"]:
            version += "*Beta*\n_{}_\n*Released On:*\n{}\n\n[Download Here]({})\n\n".format(name, date, download)
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
    if data["_links"]["issue"] is not None and data["_links"]["issue"]["href"] is not None:
        issue_string = data["_links"]["issue"]["href"]
        details += "\nFixes issue: {}".format(issue_string[-4:])
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
