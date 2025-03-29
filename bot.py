import logging
import os
import re
import time
import subprocess
from collections.abc import Callable
from datetime import datetime, timedelta
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

        self.__page.get_by_label("Programmer un post").click()
        self.__page.get_by_role("textbox", name="Date").fill(date.strftime("%d/%m/%Y"))
        self.__page.get_by_label("Time").fill(f"{date.hour}:00")
        time.sleep(0.5)
        self.__page.get_by_role("button", name="Suivant").dblclick()
        self.__page.get_by_role("button", name="Programmer", exact=True).click()

    def create_poll(self, msg:str):
        self.__page.get_by_role("button", name="Plus").click()
        self.__page.get_by_label("Créer un sondage").click()
        self.__page.locator("#input-uid-ember180").fill(msg)

        for _ in range(3):
            self.__page.get_by_role("button", name="Ajouter une option").click()

        model_choice = ["Claude", "ChatGPT", "Mistral", "Deepseek", "Gemini"]

        for id, model in enumerate(model_choice):
            self.__page.locator(f"#poll-option-{id+1}").fill(model)
        self.__playwright.selectors.set_test_id_attribute("aria-labelledby")
        self.__page.get_by_test_id("polls-duration-label").select_option("1")
        self.__page.get_by_label("Terminé").click()


    def open_chromium(self):
        subprocess.Popen(
            " /Applications/Chromium.app/Contents/MacOS/Chromium --remote-debugging-port=1234 --user-data-dir=foo".split())
        time.sleep(0.5)
        chromium = self.__playwright.chromium
        browser = chromium.connect_over_cdp('http://127.0.0.1:1234')
        context = browser.new_context()
        self.__page = context.new_page()

    def authenticate_on_linkedin(self):
        self.__page.goto("https://www.linkedin.com/home")
        self.__page.get_by_role("link", name="\n          S’identifier\n      ", exact=True).click()
        self.__page.get_by_label("E-mail ou téléphone").fill(os.environ["LINKEDIN_USER"])
        self.__page.get_by_label("Mot de passe").fill(os.environ["LINKEDIN_PASSWORD"])
        self.__page.get_by_label("S’identifier", exact=True).click()

    def stop(self):
        self.__playwright.stop()


if __name__ == '__main__':
    bot = LinkedInBot()
    bot.open_chromium()
    bot.authenticate_on_linkedin()
    # bot.post("Ceci est un message généré automatiquement", date=datetime.today() + timedelta(hours=1))
    bot.create_poll("Test de sondage")
    print("Done")
    try:
        while True:
            pass
    finally:
        bot.stop()

