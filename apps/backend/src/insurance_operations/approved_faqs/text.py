def normalize_faq_question(value: str) -> str:
    characters = [
        character.casefold() if character.isalnum() else " " for character in value
    ]
    return " ".join("".join(characters).split())
