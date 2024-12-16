import re


def snake_to_title_case_with_acronyms(snake_str):
    # Split the string by underscores
    words = snake_str.split('_')

    # Process each word
    processed_words = []
    current_acronym = []

    for word in words:
        if word.isupper() and len(word) == 1:
            # Collect single uppercase letters for acronyms
            current_acronym.append(word)
        else:
            # If we have collected an acronym, add it to processed words
            if current_acronym:
                processed_words.append(''.join(current_acronym))
                current_acronym = []

            # Process the current word
            if word.isupper():
                processed_words.append(word)  # Keep all-uppercase words as is
            else:
                processed_words.append(word.capitalize())

    # Add any remaining acronym
    if current_acronym:
        processed_words.append(''.join(current_acronym))

    # Join the words with spaces
    return ' '.join(processed_words)
