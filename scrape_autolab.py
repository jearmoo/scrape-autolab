import requests
from bs4 import BeautifulSoup
from slugify import slugify
import re
import os


class cd:
    """Context manager for changing the current working directory"""

    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

# BEGIN
# replace this section with information from autolab network request


cookies = {
    'browser.timezone': 'America/Los_Angeles',
    '_autolab3_session': '_autolab3_session_value',
    '_session_id': '_session_id_value',
}

headers = {
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Referer': 'https://autolab.andrew.cmu.edu/courses/10405-s18/course_user_data/112931',
    'Accept-Language': 'en-US,en;q=0.9',
    'If-None-Match': 'W/"d10db62142119c47702085c94c3effc5"',
}

# END

AUTOLAB_URL = 'https://autolab.andrew.cmu.edu/'

# the path where files will be outputted to
OUTPUT_PATH = "~/autolab_assignments/"


def request_autolab(path):
    if not(path.startswith(AUTOLAB_URL)):
        path = requests.compat.urljoin(AUTOLAB_URL, path)
    response = requests.get(path, headers=headers, cookies=cookies)
    return response


def soup_autolab(path):
    response = request_autolab(path)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


def get_cards(soup):
    return soup.findAll("div", {"class": "card"})


def get_card_title(card):
    card_title = card.find("span", {"class": "card-title"})
    assert card_title is not None
    card_title = slugify(card_title.string)
    return card_title


def get_courses():
    print("GETTING COURSES:")
    soup = soup_autolab("/")
    cards = get_cards(soup)
    cards = list(
        filter(
            lambda x: x.find(
                "div", {
                    "class": "col s3"}) is None, cards))
    courses = []
    for c in cards:
        course_title = get_card_title(c)
        print(course_title)
        a = c.find('a', href=True)
        course_link = a['href']
        print(course_link)
        courses.append((course_title, course_link))

    return courses


def get_tasks(card):
    tasks = []
    anchors = card.findAll("a", {"class": "collection-item"}, href=True)
    for anchor in anchors:
        task_title = slugify(anchor.string)
        task_link = anchor['href']
        tasks.append((task_title, task_link))
    return tasks


def get_assns(soup):
    print("GETTING ASSIGNMENTS")
    cards = get_cards(soup)[1:]

    assns = []

    for c in cards:
        assn_title = get_card_title(c)
        tasks = get_tasks(c)
        assns.append((assn_title, tasks))

    return assns


def is_application_binary(response):
    content_type = response.headers['Content-Type']
    if not(content_type.startswith('application')):
        return False
    return True


def get_filename(response, default="handout.pdf"):
    if 'Content-Disposition' in response.headers:
        filename_matches = re.findall(
            r'filename="(.*)"',
            response.headers['Content-Disposition'])
        assert len(filename_matches) == 1
        return filename_matches[0]
    else:
        assert default is not None
        return default


DOWNLOAD_TITLES = [
    "View the assessment writeup",
    "Download handout materials and starter code",
    "Download Submission",
]


def process_assn(assn, course_title):
    assn_title, tasks = assn
    tasks_downloads = []
    # for each task, download files from DOWNLOAD_TITLES if they exist
    for task_title, task_link in tasks:
        task_downloads = []
        task_dir = os.path.expanduser(
            os.path.join(
                OUTPUT_PATH,
                course_title,
                assn_title,
                task_title))
        print(assn_title, task_title)
        soup = soup_autolab(task_link)
        os.makedirs(task_dir, exist_ok=True)
        with cd(task_dir):
            for download_title in DOWNLOAD_TITLES:
                download_link_soup = soup.find(
                    "a", {"title": download_title}, href=True)
                assert download_link_soup is not None or download_title == "Download Submission"
                if download_link_soup is None:
                    continue
                download_link = download_link_soup['href']
                download_response = request_autolab(download_link)
                if not(is_application_binary(download_response)):
                    continue
                filename = get_filename(download_response)
                print(filename, download_response.headers['Content-Type'])
                with open(filename, 'wb') as f:
                    f.write(download_response.content)
                print("->", os.path.join(task_dir, filename))
                task_downloads.append((filename, download_link))
        print()
        if len(task_downloads) > 0:
            tasks_downloads.append((task_title, task_downloads))


def process_course(course):
    course_title, course_link = course
    print()
    print("PROCESSING COURSE ", course)
    soup = soup_autolab(course_link)
    assns = get_assns(soup)
    for assn in assns:
        process_assn(assn, course_title)


if __name__ == "__main__":
    courses = get_courses()
    for course in courses:
        process_course(course)
