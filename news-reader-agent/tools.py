from crewai.tools import tool


@tool
def count_letters(sentence: str):
    # doc str - CrewAI's function definition
    """
    This function is to count the amount of letters in a sentence.
    The input is a 'sentence' string.
    The ouput is a number
    """
    return len(sentence)
