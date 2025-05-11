import json
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta
from typing import Literal
import pyperclip

from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, Page, BrowserContext
from postgenerator import PostGenerator

from dotenv import load_dotenv

from git import Repo

load_dotenv()


def next_day_at_time(target_day: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
                     hour, minute=0):
    # Convert day name to its index (0 for Monday, 1 for Tuesday, etc.)
    days = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    # Get the index of the target day (case insensitive)
    day_index = days.get(target_day.lower())
    if day_index is None:
        raise ValueError(f"Day '{target_day}' not recognized. Please use a valid weekday.")

    today = datetime.now()
    current_day = today.weekday()

    # Calculate the number of days until the next target day
    days_until_target = (day_index - current_day) % 7

    # If we are on the target day after the specified time, take the target day of next week
    if days_until_target == 0 and (today.hour > hour or (today.hour == hour and today.minute >= minute)):
        days_until_target = 7

    next_day = today + timedelta(days=days_until_target)
    next_day = next_day.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return next_day


def unescape_unicode(text):
    """Convertit les séquences d'échappement Unicode en leurs caractères correspondants."""
    import codecs
    import re

    # Pattern pour trouver les séquences Unicode comme \u00e9
    pattern = r'\\u([0-9a-fA-F]{4})'

    # Fonction qui remplace chaque séquence trouvée par son caractère Unicode
    def replace(match):
        hex_code = match.group(1)
        return chr(int(hex_code, 16))

    # Remplacer toutes les séquences trouvées
    return re.sub(pattern, replace, text)


def remove_markdown(text):
    if not isinstance(text, str):
        return text

    # Retirer le formatage gras
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)

    # Ajouter d'autres règles si nécessaire
    # ...

    return text

class LinkedInBot:
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), "GeneratedPostDatabase/database.json")
    TEXT_PATH = os.path.join(os.path.dirname(__file__), "text.json")
    POST_URL_PATH = os.path.join(os.path.dirname(__file__), "post_url.json")
    SUBJECT_PATH = os.path.join(os.path.dirname(__file__), "subject.txt")

    def __init__(self):
        self.generator = PostGenerator()
        self.page: Page | None = None
        self.__playwright = sync_playwright().start()
        self.__context: BrowserContext | None = None
        self.generator = PostGenerator()
        self.__session_open = False

    def post(self, msg: str, date: datetime, poll=False):
        self.page.get_by_role("button", name="Commencer un post").click()
        self.page.get_by_label("Éditeur de texte pour créer du contenu").fill(msg)
        time.sleep(1)

        if poll:
            self.create_poll("Quel model vous a-t-il le plus convaincu?")

        self.page.get_by_label("Programmer un post").click()
        self.page.get_by_role("textbox", name="Date").fill(date.strftime("%d/%m/%Y"))
        self.page.get_by_label("Time").fill(f"{date.hour}:{date.minute}")
        self.page.get_by_role("button", name="Suivant").click()
        if self.page.get_by_role("button", name="Suivant").is_visible():
            self.page.get_by_role("button", name="Suivant").click()
        self.page.get_by_role("button", name="Programmer", exact=True).click()

    def create_poll(self, msg: str):
        self.page.get_by_role("button", name="Plus").click()
        self.page.get_by_label("Créer un sondage").click()
        self.page.locator(".polls-detour__question-field").fill(msg)

        for _ in range(2):
            self.page.get_by_role("button", name="Ajouter une option").click()

        model_choice = ["Claude", "ChatGPT", "Mistral", "Gemini"]

        for id, model in enumerate(model_choice):
            self.page.locator(f"#poll-option-{id + 1}").fill(model)
        self.__playwright.selectors.set_test_id_attribute("aria-labelledby")
        self.page.get_by_test_id("polls-duration-label").select_option("1")
        self.page.get_by_label("Terminé").click()

    def open_chromium(self):
        # subprocess.Popen(
        #     " /Applications/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=1234".split())
        # time.sleep(2)
        user_data_dir = os.path.join(os.getcwd(), "chromium_profile")

        self.__context = self.__playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False  # Met à True si tu ne veux pas afficher la fenêtre
        )
        self.page = self.__context.new_page()

    def get_new_page(self):
        return self.__context.new_page()

    def authenticate_on_linkedin(self):
        self.page.goto("https://www.linkedin.com/home")
        authenticate_button = self.page.get_by_role("link", name="\n          S’identifier\n      ", exact=True)
        if authenticate_button.is_visible(timeout=2):
            self.page.get_by_role("link", name="\n          S’identifier\n      ", exact=True).click()
            self.page.get_by_label("E-mail ou téléphone").fill(os.environ["LINKEDIN_USER"])
            self.page.get_by_label("Mot de passe").fill(os.environ["LINKEDIN_PASSWORD"])
            self.page.get_by_label("S’identifier", exact=True).click()
        else:
            raise RuntimeError("Already authenticate")

    def init_session(self):
        if self.__session_open:
            return

        self.open_chromium()

        try:
            self.authenticate_on_linkedin()
        except RuntimeError:
            pass

        self.__session_open = True

    def get_data_from_post(self, post_url, poll_format: bool = False):
        data = {}
        self.page.goto(post_url)

        comments = []
        try:
            # Allow to display all comments
            comment_sort_button = self.page.get_by_role("button", name="Les plus pertinents est l’")
            if comment_sort_button.is_visible(timeout=10):

                comment_sort_button.click()

                # Click on button to display all comments
                self.page.get_by_text("Les plus récents", exact=True).click()
                time.sleep(2)
                more_comments = self.page.get_by_label("Afficher plus de commentaires")
                while more_comments.is_visible(timeout=10):
                    more_comments.click()
                    time.sleep(2)
                    more_comments = self.page.get_by_label("Afficher plus de commentaires")

                locator_id = "text=Voir les réponses précédentes"
                more_comments = self.page.locator(locator_id).all()
                for button in more_comments:
                    if button.is_visible():
                        button.click()
                time.sleep(2)

            soup = BeautifulSoup(self.page.content(), "html.parser")

            for article in soup.find_all(name="article", attrs={"tabindex": '-1'}):
                # Check only main comments and handle reply in relation to the comment
                if "comments-comment-entity--reply" not in article.attrs["class"]:
                    # Find all comments
                    comment_list = article.find_all("div", "update-components-text relative")
                    if comment_list:
                        # Get all account name to remove them when it appears in the text's comment
                        account_name = [name.text.encode('ascii', 'ignore').decode('ascii').strip() for name in
                                        article.find_all("span",
                                                         attrs={"class": "comments-comment-meta__description-title"})]
                        # Remove all link to account and account name to anonymize the data
                        for comment in comment_list:
                            account_link = comment.find_all("a", attrs={"class": "ember-view"})
                            if account_link:
                                for name in account_link:
                                    name.extract()
                            for name in account_name:
                                for word in name.split():
                                    comment.string = comment.text.replace(word, "")

                        # Store the comment in a dictionnary : {"comment": main comment, "reply": list of all reply}
                        comment = {"comment": comment_list[0].text.strip()}
                        if len(comment_list) > 1:
                            comment["reply"] = [reply.text.strip() for reply in comment_list[1:]]
                        comments.append(comment)
        except TimeoutError:
            soup = BeautifulSoup(self.page.content(), "html.parser")

        if poll_format:
            poll_option, number_voter = self.get_data_from_poll(soup)
            data.update({"poll": poll_option, "voters": number_voter})

        self.page.get_by_role("link", name="Voir les statistiques").click()

        selector = 'ul[aria-labelledby="member-analytics-addon-card-1"]'
        self.page.wait_for_selector(selector)
        engagement_text = self.page.query_selector(selector).inner_text().split("\n")
        reaction_number = int(engagement_text[1])
        comment_number = int(engagement_text[3])
        repost_number = int(engagement_text[5])

        data.update({"comments": comments, "comment_number": comment_number, "reaction_number": reaction_number,
                     "repost_number": repost_number})
        return data

    def get_data_from_poll(self, soup: BeautifulSoup):
        poll_option = [poll.text.split("\n") for poll in
                       soup.find_all('div', attrs={"class": "update-components-poll-option"})]
        poll_option = [[p.strip() for p in poll] for poll in poll_option]
        poll_option = [[p for p in poll if p] for poll in poll_option]
        poll_option = [{"choice": p[0], "result": p[1]} for p in poll_option]
        poll_voter = soup.find("div", attrs={"class": "update-components-poll-summary__subtext-container"}).text
        poll_voter = [text for text in poll_voter.split("\n") if text][0]
        number_voter = int(
            re.sub('[^0-9]', '', poll_voter))
        return poll_option, number_voter

    def stop(self):
        self.__playwright.stop()

    def generate_post(self, subject: str = None):
        self.init_session()

        with open(self.DATABASE_PATH, "r",  encoding="utf-8") as f:
            database = json.load(f)

        if not subject:
            with open(self.SUBJECT_PATH, "r", encoding="utf-8") as f:
                data = f.readlines()

            answer = ""
            subject = ""
            while answer != "y":
                subject = unescape_unicode(random.choice(data)).strip()
                print(subject)
                answer = input()

        logging.info(f"Subject: {subject}")

        database["todo"] = {"subject": subject}

        with open(self.TEXT_PATH, "r") as f:
            post_text = json.load(f)

        prepost = post_text["endpost"]

        post = remove_markdown(self.generator.generate_mistral_post(subject))
        database["todo"]["post"] = {"Mistral": {"text": post}}
        self.post(post + prepost.format(model="Mistral", subject=subject),
                  next_day_at_time("monday", hour=10, minute=30))

        try:
            post = remove_markdown(self.generator.generate_gpt_post(subject, self.get_new_page()))
            database["todo"]["post"]["ChatGPT"] = {"text": post}
            self.post(post + prepost.format(model="ChatGPT", subject=subject),
                      next_day_at_time("tuesday", hour=10, minute=30))
        except Exception:
            database["todo"]["post"]["ChatGPT"] = {"text": ""}

        post = remove_markdown(self.generator.generate_gemini_post(subject))
        database["todo"]["post"]["Gemini"] = {"text": post}
        self.post(post + prepost.format(model="Gemini", subject=subject),
                  next_day_at_time("wednesday", hour=10, minute=30))

        post = remove_markdown(self.generator.generate_claude_post(subject))
        database["todo"]["post"]["Claude"] = {"text": post}
        self.post(post + prepost.format(model="Claude", subject=subject),
                  next_day_at_time("thursday", hour=10, minute=30))

        with open(self.DATABASE_PATH, "w",  encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)

    def generate_poll(self):
        # self.get_last_post_url()

        with open(self.DATABASE_PATH, "r", encoding="utf-8") as f:
            subject = json.load(f)["todo"]["subject"]

        with open(self.POST_URL_PATH, "r") as f:
            post_url = json.load(f)

        with open(self.TEXT_PATH, "r") as f:
            post_text = json.load(f)

        self.init_session()
        self.post(
            post_text["poll"].format(subject=subject, mistral_link=post_url["Mistral"], gpt_link=post_url["ChatGPT"],
                                     gemini_link=post_url["Gemini"], claude_link=post_url["Claude"]),
            next_day_at_time("friday", hour=10, minute=30),
            poll=True)

    def get_generated_post_link(self, post_text: str | list[str]):
        self.init_session()
        self.page.goto("https://www.linkedin.com/in/edouard-ducloy-910091a3/recent-activity/all/")

        if type(post_text) is str:
            post_text = [post_text]

        aria_label = "Ouvrir le menu de commandes pour le post de Edouard DUCLOY"
        time.sleep(3)
        for _ in range(10):
            self.page.evaluate(f"window.scrollBy(0, 500)")
            time.sleep(0.5)
        all_div_post = self.page.query_selector_all("div.feed-shared-update-v2__control-menu-container")

        link = []
        for text in post_text:
            text = text.split("\n")[0]

            done = False
            for div in all_div_post:
                div_text = div.inner_text()
                if text in div_text:
                    time.sleep(1)
                    div.query_selector(f'button[aria-label="{aria_label}"]').click()
                    # time.sleep(1)
                    # div.query_selector(f'button[aria-label="{aria_label}"]').click()
                    done = True
                    break

            if done:

                link_option_selector = f'text="Copier le lien vers le post"'

                # Attendre que l'option apparaisse dans la fenêtre contextuelle
                self.page.wait_for_selector(link_option_selector, state="visible")

                # Trouver l'élément contenant le texte cible
                link_element = self.page.query_selector(link_option_selector)

                if link_element:
                    link_element.click()
                    time.sleep(1)
                    link.append(pyperclip.paste())
                else:
                    print(f"Élément avec le texte 'Copier le lien vers le post' non trouvé")
                    return link.append(None)
            else:
                raise RuntimeError("Post not found")
        return link

    def get_last_post_url(self):
        with open(self.DATABASE_PATH, "r", encoding="utf-8") as f:
            database: dict = json.load(f)

        self.init_session()

        todo = database["todo"]

        post_text = [value["text"] for value in todo["post"].values()]

        post_link = {model: url for model, url in zip(todo["post"].keys(), self.get_generated_post_link(post_text))}

        with open(self.POST_URL_PATH, "w") as f:
            json.dump(post_link, f)

    def update_database(self):
        with open(self.DATABASE_PATH, "r", encoding="utf-8") as f:
            database: dict = json.load(f)

        with open(self.POST_URL_PATH, "r") as f:
            post_link = json.load(f)

        self.init_session()

        todo = database["todo"]
        data = todo.copy()

        for model, value in todo["post"].items():
            link = post_link[model]
            if not link:
                raise RuntimeError(f"Link for post of {model} not found")

            post_data = self.get_data_from_post(link)

            data["post"][model].update({"stat": post_data})

        database["todo"].update(data)

        with open(self.DATABASE_PATH, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)

    def get_poll_data(self):

        with open(self.DATABASE_PATH, "r", encoding="utf-8") as f:
            database: dict = json.load(f)

        with open(self.TEXT_PATH, "r") as f:
            text: str = json.load(f)["poll"].split("\n")[2].format(subject=database["todo"]["subject"])

        self.init_session()
        self.page.goto("https://www.linkedin.com/in/edouard-ducloy-910091a3/recent-activity/all/")

        aria_label = "Ouvrir le menu de commandes pour le post de Edouard DUCLOY"
        time.sleep(3)
        for _ in range(5):
            self.page.evaluate(f"window.scrollBy(0, 500)")
            time.sleep(0.5)
        all_div_post = self.page.query_selector_all("div.feed-shared-update-v2__control-menu-container")

        done = False
        for div in all_div_post:
            div_text = div.inner_text()
            if text in div_text:
                div.query_selector(f'button[aria-label="{aria_label}"]').click()
                done = True
                break

        if done:

            link_option_selector = f'text="Copier le lien vers le post"'

            # Attendre que l'option apparaisse dans la fenêtre contextuelle
            self.page.wait_for_selector(link_option_selector, state="visible")

            # Trouver l'élément contenant le texte cible
            link_element = self.page.query_selector(link_option_selector)

            if link_element:
                link_element.click()
                time.sleep(1)
                poll_link = pyperclip.paste()
            else:
                raise RuntimeError(f"Élément avec le texte 'Copier le lien vers le post' non trouvé")
        else:
            raise RuntimeError("Post not found")

        post_data = self.get_data_from_post(poll_link, poll_format=True)

        database["todo"]["poll"] = post_data

        with open(self.DATABASE_PATH, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)

    def commit_database(self):
        with open(self.DATABASE_PATH, "r", encoding="utf-8") as f:
            database: dict = json.load(f)

        database["data"].append(database["todo"])
        database.pop("todo")

        with open(self.DATABASE_PATH, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)

        repo = Repo(os.path.dirname(self.DATABASE_PATH))

        repo.git.add(update=True)
        repo.index.commit(f"Database update from {datetime.today().strftime('%Y/%m/%d')}")
        origin = repo.remote(name="origin")
        origin.push()
