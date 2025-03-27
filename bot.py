
from auth import AuthServer
import requests
import json

class LinkedInClient:

    def __init__(self, client_id, client_secret, urn, scope):

        self.__auth = AuthServer()
        self.__auth.authentication(client_id, client_secret, scope)
        self.__urn = urn
        pass

    def create_linkedin_draft_post(self, post_text):
        """
        Crée un post en brouillon sur LinkedIn

        :param access_token: Token d'authentification OAuth
        :param author_urn: URN (Unique Resource Name) de l'auteur
        :param post_text: Contenu du post
        :return: Réponse de l'API
        """
        url = "https://api.linkedin.com/v2/ugcPosts"

        headers = {
            'Authorization': f'Bearer {self.__auth.get_access_token()}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

        # Structure du corps de la requête pour un brouillon
        payload = {
            "author": self.__urn,
            "lifecycleState": "DRAFT",  # Changement clé ici : utilisation de DRAFT
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "CONNECTIONS"
            }
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        return response.json()

