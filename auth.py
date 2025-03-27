from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser, requests, secrets, urllib.parse
from urllib.error import HTTPError

from http import HTTPStatus

import threading, logging, time, json, os
from datetime import datetime, timedelta
from random import randint

DEFAULT_ADDRESS = "0.0.0.0"
DEFAULT_PORT = 8000
REDIRECT_URI_AUTH = f"http://localhost:{DEFAULT_PORT}/auth/linkedin/callback"
DEFAULT_TIMEOUT = 600
ACCESS_TOKEN_FILE = ".access_token"

code_dict = {}


class WebRequestHandler(BaseHTTPRequestHandler):
    """
    Web server to be used as a callback for the OAuth2 protocol
    """

    def do_GET(self):
        """
        When a get request is send to the callback server, store the code in a dictionary to ask for an access token
        :return: HTTP code 200
        """
        logging.info(f'client:  {self.client_address}')
        logging.info(f'command: {self.command}')
        logging.info(f'path:    {self.path}')

        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)

        if url.path == "/auth/linkedin/callback":
            logging.info('Callback!')
            logging.debug(query)
            if 'state' in query and 'code' in query:
                logging.info("Code provided!")
                state = query['state'][0]
                code_dict[state] = query['code'][0]
            else:
                logging.error("No state provided")

        self.send_response(HTTPStatus.OK)


class AuthServer():
    """
    Authentication class, it creates, asks and stores all information needed to be authenticated by the Twitch API.
    It contains all tools to communicate with the Twitch API.
    """

    def __init__(self,
                 address=DEFAULT_ADDRESS,
                 port=DEFAULT_PORT,
                 start=False):
        """
        :param address: ip address of the host
        :param port: port of the host
        :param start: True if the user wants to automatically start the callback server
        """

        self.address = address
        self.port = port
        self._client_id = None
        self.__client_secret = None
        self.__credentials = None
        self.__token_file_path = None

        if start is True:
            self.start()

    def __http_thread(self):
        """
        Start a thread with the callback server
        """
        self.server = HTTPServer(('', self.port), WebRequestHandler)
        logging.info(f'Serving on {self.server.server_address}')

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        logging.info('Exiting HTTP thread')

    def start(self):
        """
        Start the callback server
        """
        self.thread = threading.Thread(target=self.__http_thread)
        self.thread.start()

    def stop(self):
        """
        Stop the callback server
        """
        logging.info('Stopping server')
        self.server.shutdown()

        logging.info('Join thread')
        self.thread.join()
        self.server.server_close()
        logging.info('Server stopped!')

    def create_access_token(self, client_id: str, client_secret: str, scope: list[str],
                         redirect_uri: str = REDIRECT_URI_AUTH,
                         timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Retrieves access token via Twitch's OAuth2 protocol
        :param client_id: id of the client twitch application
        :param client_secret: secret of the client twitch application
        :param scope: token rights list
        :param redirect_uri: Uri of the callback server
        :param timeout
        """

        code = None
        linkedin_code_url = "https://www.linkedin.com/oauth/v2/authorization"
        linkedin_token_url = "https://www.linkedin.com/oauth/v2/accessToken"

        # builds the url to request the Twitch API authentication code
        state_length = randint(16, 32)
        state = secrets.token_urlsafe(state_length)
        code_auth_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scope),
            "state": state
        }

        code_auth_params_str = urllib.parse.urlencode(code_auth_params)
        logging.debug(code_auth_params_str)

        # Request the authentication code
        r = requests.get(f"{linkedin_code_url}?{code_auth_params_str}")

        if r.status_code != 200:
            logging.error(r.content)
            raise HTTPError("Failed to call the Authorization end point! Verify the Client ID of your "
                            "application!")

        # Open a logging page
        logging.debug("Authentification URL: " + r.url)
        webbrowser.open_new(r.url)

        logging.info("Retrieving access_token from redirect_uri..")

        # Start the callback the server to receive the authentication code
        self.start()

        start = time.time()

        try:
            while time.time() - start < timeout:
                if state in code_dict:
                    code = code_dict[state]
                    code_dict.pop(state)
                    break
                time.sleep(1)

            if code is None:
                logging.error("code not recovered..")
                raise TimeoutError("Fail to provide authorization code! Verify the redirect URI "
                                   "(if not default value)!")
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

        # Use the authentication code to request the access token
        # Builds url to request access token from Twitch API
        token_auth_params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }

        token_auth_params_str = urllib.parse.urlencode(token_auth_params)

        logging.debug(token_auth_params_str)

        # Request the access token
        r = requests.post(f"{linkedin_token_url}", data=token_auth_params,
                          headers={"Content-Type": "application/x-www-form-urlencoded"})

        if r.status_code != 200:
            logging.error(r.content)
            raise HTTPError("Fail to provide access token! Verify the Client secret of your "
                            "application!")

        data = r.json()
        access_token = data["access_token"]
        # The expiry date is today's date + 60 days
        expire_date = (datetime.now() + timedelta(seconds=data["expires_in"]) - timedelta(days=7)).strftime('%d/%m/%Y')
        logging.info('access_token received!')

        logging.debug(f"OAuth token: {access_token}")

        self.__credentials = {"access_token": access_token, "expire_date": expire_date,
                              "scope": scope}
        with open(self.__token_file_path, "w") as f:
            json.dump(self.__credentials, f)


    def authentication(self, client_id: str, client_secret: str, scope: list[str],
                       token_file_path: str = ACCESS_TOKEN_FILE, timeout: int = DEFAULT_TIMEOUT,
                       redirect_uri: str = REDIRECT_URI_AUTH):
        """
        Set authentication header and authenticate with Twitch to create access token as needed
        :param client_id: id of the client twitch application
        :param client_secret: secret of the client twitch application
        :param token_file_path: path of the file where access token is stored
        :param scope: token rights list
        :param redirect_uri: Uri of the callback server
        """
        self._client_id = client_id
        self.__client_secret = client_secret
        self.__token_file_path = token_file_path

        if not os.path.exists(self.__token_file_path):
            self.create_access_token(client_id=client_id, client_secret=client_secret, scope=scope,
                                  redirect_uri=redirect_uri, timeout=timeout)
        else:
            with open(self.__token_file_path, "r") as f:
                self.__credentials = json.load(f)

            if sorted(scope) != sorted(self.__credentials["scope"]):
                os.remove(self.__token_file_path)
                self.authentication(client_id, client_secret, scope, self.__token_file_path, timeout, redirect_uri)

    def get_access_token(self):
        return self.__credentials.get("access_token", None)


