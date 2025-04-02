import os
import re
import time
import subprocess
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, Page, Selectors
from postgenerator import PostGenerator

from dotenv import load_dotenv

load_dotenv()


class LinkedInBot:

    def __init__(self):
        self.generator = PostGenerator()
        self.__page: Page|None = None
        self.__playwright = sync_playwright().start()

    def post(self, msg:str, date:datetime, poll=False):
        self.__page.get_by_role("button", name="Commencer un post").click()
        self.__page.get_by_label("Éditeur de texte pour créer du contenu").fill(msg)
        time.sleep(0.5)

        if poll:
            self.create_poll("Quel model vous a-t-il le plus convaincu?")

        self.page.get_by_label("Programmer un post").click()
        self.page.get_by_role("textbox", name="Date").fill(date.strftime("%d/%m/%Y"))
        self.page.get_by_label("Time").fill(f"{date.hour}:00")
        time.sleep(0.5)
        self.page.get_by_role("button", name="Suivant").dblclick()
        self.page.get_by_role("button", name="Programmer", exact=True).click()

    def create_poll(self, msg:str):
        self.page.get_by_role("button", name="Plus").click()
        self.page.get_by_label("Créer un sondage").click()
        self.page.locator("#input-uid-ember180").fill(msg)

        for _ in range(3):
            self.page.get_by_role("button", name="Ajouter une option").click()

        model_choice = ["Claude", "ChatGPT", "Mistral", "Deepseek", "Gemini"]

        for id, model in enumerate(model_choice):
            self.page.locator(f"#poll-option-{id+1}").fill(model)
        self.__playwright.selectors.set_test_id_attribute("aria-labelledby")
        self.page.get_by_test_id("polls-duration-label").select_option("1")
        self.page.get_by_label("Terminé").click()


    def open_chromium(self):
        subprocess.Popen(
            " /Applications/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=1234 --user-data-dir=foo".split())
        time.sleep(2)
        chromium = self.__playwright.chromium
        browser = chromium.connect_over_cdp('http://127.0.0.1:1234')
        context = browser.contexts[0]
        self.page = context.new_page()

    def authenticate_on_linkedin(self):
        self.page.goto("https://www.linkedin.com/home")
        authenticate_button = self.page.get_by_role("link", name="\n          S’identifier\n      ", exact=True)
        if  authenticate_button.is_visible(timeout=2):
            self.page.get_by_role("link", name="\n          S’identifier\n      ", exact=True).click()
            self.page.get_by_label("E-mail ou téléphone").fill(os.environ["LINKEDIN_USER"])
            self.page.get_by_label("Mot de passe").fill(os.environ["LINKEDIN_PASSWORD"])
            self.page.get_by_label("S’identifier", exact=True).click()
        else:
            raise RuntimeError("Already authenticate")

    def get_data_from_post(self, post_url, poll_format:bool=False):
        data = {}
        self.page.goto(post_url)

        # Allow to display all comments
        comment_sort_button = self.page.get_by_role("button", name="Les plus pertinents est l’")
        if not comment_sort_button.is_visible(timeout=10):
            raise TimeoutError("Page load to slowly!")
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

        comments = []
        soup = BeautifulSoup(self.page.content(), "html.parser")

        if poll_format:
            poll_option, number_voter = self.get_data_from_poll(soup)
            data.update({"poll": poll_option, "voters": number_voter})

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

        # Get the reaction number
        reaction_number = soup.find("span", "social-details-social-counts__reactions-count").text
        reaction_number = int(re.sub('[^0-9]', '', reaction_number))

        # Get the repost and comment number
        social = soup.find_all("button", "social-details-social-counts__btn")

        comment_number = int(re.sub('[^0-9]', '', social[0].text)) if len(social) >= 1 else 0
        repost_number = int(re.sub('[^0-9]', '', social[1].text)) if len(social) >= 2 else 0

        data.update({"comments": comments, "comment_number": comment_number, "reaction_number":reaction_number,
                     "repost_number": repost_number})
        return data

    def get_data_from_poll(self, soup:BeautifulSoup):
        poll_option = [poll.text.split("\n") for poll in soup.find_all('div', attrs={"class": "update-components-poll-option"})]
        poll_option = [[p.strip() for p in poll]for poll in poll_option]
        poll_option = [[p for p in poll if p] for poll in poll_option]
        poll_option = [{"choice": p[0], "result": p[1]} for p in poll_option]
        number_voter = int(re.sub('[^0-9]', '', soup.find("p", attrs={"class": "update-components-poll-summary__option-text"}).text))
        return  poll_option, number_voter

    def stop(self):
        self.__playwright.stop()

