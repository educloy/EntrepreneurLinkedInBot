import re


def create_mapping(style_type):
    """
    Crée un dictionnaire de mapping pour différents styles de formatage
    """
    if style_type == 'bold':
        # Mappings pour le texte en gras (A-Z, a-z, 0-9)
        uppercase_mapping = {chr(i): chr(i + 119743) for i in range(65, 91)}  # A-Z -> 𝐀-𝐙
        lowercase_mapping = {chr(i): chr(i + 119737) for i in range(97, 123)}  # a-z -> 𝐚-𝐳
        numbers_mapping = {
            '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒',
            '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
        }
        return {**uppercase_mapping, **lowercase_mapping, **numbers_mapping}

    elif style_type == 'italic':
        # Mappings pour le texte en italique (A-Z, a-z)
        uppercase_mapping = {chr(i): chr(i + 119795) for i in range(65, 91)}  # A-Z -> 𝐴-𝑍
        lowercase_mapping = {chr(i): chr(i + 119789) for i in range(97, 123)}  # a-z -> 𝑎-𝑧
        return {**uppercase_mapping, **lowercase_mapping}

    elif style_type == 'bold_italic':
        # Mappings pour le texte en gras et italique (A-Z, a-z)
        uppercase_mapping = {chr(i): chr(i + 119847) for i in range(65, 91)}  # A-Z -> 𝑨-𝒁
        lowercase_mapping = {chr(i): chr(i + 119841) for i in range(97, 123)}  # a-z -> 𝒂-𝒛
        return {**uppercase_mapping, **lowercase_mapping}

    elif style_type == 'monospace':
        # Mappings pour le texte monospace (A-Z, a-z, 0-9)
        uppercase_mapping = {chr(i): chr(i + 120263) for i in range(65, 91)}  # A-Z -> 𝙰-𝚉
        lowercase_mapping = {chr(i): chr(i + 120257) for i in range(97, 123)}  # a-z -> 𝚊-𝚣
        numbers_mapping = {
            '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺',
            '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿'
        }
        return {**uppercase_mapping, **lowercase_mapping, **numbers_mapping}

    elif style_type == 'strikethrough':
        # Pour le texte barré, on utilisera un caractère spécial combinant
        return {'STRIKETHROUGH': '\u0336'}

    return {}


def apply_style(text, mapping):
    """
    Applique un style spécifique au texte
    """
    if 'STRIKETHROUGH' in mapping:
        # Cas spécial pour le texte barré
        return ''.join(c + mapping['STRIKETHROUGH'] for c in text)

    result = ""
    for char in text:
        # Si le caractère est dans le mapping, utiliser la version stylisée
        # Sinon, le garder tel quel
        result += mapping.get(char, char)

    return result


def convert_markdown_to_unicode(markdown_text):
    """
    Convertit la syntaxe Markdown en texte stylisé Unicode
    """
    # Créer une copie du texte pour travailler
    result = markdown_text

    # Créer les mappings de style
    bold_mapping = create_mapping('bold')
    italic_mapping = create_mapping('italic')
    bold_italic_mapping = create_mapping('bold_italic')
    monospace_mapping = create_mapping('monospace')
    strikethrough_mapping = create_mapping('strikethrough')

    # Fonction auxiliaire pour remplacer les correspondances en toute sécurité
    def replace_matches(pattern, mapping):
        matches = []

        # Collecter toutes les correspondances
        for match in re.finditer(pattern, result):
            matches.append({
                'full_match': match.group(0),
                'inner_text': match.group(1),
                'start': match.start(),
                'end': match.end()
            })

        # Remplacer les correspondances dans l'ordre inverse pour éviter les problèmes de décalage
        # avec la modification de la chaîne
        for match in reversed(matches):
            styled_text = apply_style(match['inner_text'], mapping)
            result_list = list(result)
            result_list[match['start']:match['end']] = styled_text
            nonlocal result
            result = ''.join(result_list)

    # Traiter les styles dans un ordre spécifique pour gérer correctement l'imbrication
    # Ordre: gras+italique, gras, italique, code, barré

    # 1. Traiter le gras et italique (***texte***)
    replace_matches(r'\*\*\*(.*?)\*\*\*', bold_italic_mapping)

    # 2. Traiter le gras (**texte**)
    replace_matches(r'\*\*(.*?)\*\*', bold_mapping)

    # 3. Traiter l'italique (*texte*)
    replace_matches(r'\*(.*?)\*', italic_mapping)

    # 4. Traiter le monospace/code (`texte`)
    replace_matches(r'`(.*?)`', monospace_mapping)

    # 5. Traiter le texte barré (~~texte~~)
    replace_matches(r'~~(.*?)~~', strikethrough_mapping)

    return result


class MarkdownFormatter:
    """
    Classe pour formater du texte Markdown en texte Unicode stylisé
    """

    @staticmethod
    def format(text):
        """
        Formate le texte Markdown en Unicode
        """
        return convert_markdown_to_unicode(text)

    @staticmethod
    def bold(text):
        """
        Convertit le texte en gras Unicode
        """
        return apply_style(text, create_mapping('bold'))

    @staticmethod
    def italic(text):
        """
        Convertit le texte en italique Unicode
        """
        return apply_style(text, create_mapping('italic'))

    @staticmethod
    def bold_italic(text):
        """
        Convertit le texte en gras et italique Unicode
        """
        return apply_style(text, create_mapping('bold_italic'))

    @staticmethod
    def monospace(text):
        """
        Convertit le texte en monospace Unicode
        """
        return apply_style(text, create_mapping('monospace'))

    @staticmethod
    def strikethrough(text):
        """
        Convertit le texte en barré Unicode
        """
        return apply_style(text, create_mapping('strikethrough'))