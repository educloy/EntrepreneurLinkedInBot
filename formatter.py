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


def convert_markdown_to_unicode(text):
    """
    Convertit la syntaxe Markdown en texte stylisé Unicode
    """
    # Créer les mappings de style
    bold_mapping = create_mapping('bold')
    italic_mapping = create_mapping('italic')
    bold_italic_mapping = create_mapping('bold_italic')
    monospace_mapping = create_mapping('monospace')
    strikethrough_mapping = create_mapping('strikethrough')

    # Fonction qui recherche et remplace tous les motifs d'un type spécifique
    def process_patterns(pattern_re, mapping):
        nonlocal text

        # Trouver tous les motifs
        matches = list(pattern_re.finditer(text))

        # Traiter les correspondances de la fin vers le début pour éviter les décalages
        for match in reversed(matches):
            full_match = match.group(0)
            content = match.group(1)

            # Appliquer le style au contenu
            styled_content = apply_style(content, mapping)

            # Remplacer dans le texte original
            start, end = match.span()
            text = text[:start] + styled_content + text[end:]

    # Traiter les différents formats dans un ordre spécifique

    # 1. Bold & Italic (***text***)
    pattern_bold_italic = re.compile(r'\*\*\*(.*?)\*\*\*')
    process_patterns(pattern_bold_italic, bold_italic_mapping)

    # 2. Bold (**text**)
    pattern_bold = re.compile(r'\*\*(.*?)\*\*')
    process_patterns(pattern_bold, bold_mapping)

    # 3. Italic (*text*)
    pattern_italic = re.compile(r'\*(.*?)\*')
    process_patterns(pattern_italic, italic_mapping)

    # 4. Code (`text`)
    pattern_code = re.compile(r'`(.*?)`')
    process_patterns(pattern_code, monospace_mapping)

    # 5. Strikethrough (~~text~~)
    pattern_strikethrough = re.compile(r'~~(.*?)~~')
    process_patterns(pattern_strikethrough, strikethrough_mapping)

    return text


class MarkdownFormatter:
    @staticmethod
    def format(markdown_text):
        """
        Formate le texte Markdown en Unicode
        """
        return convert_markdown_to_unicode(markdown_text)

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