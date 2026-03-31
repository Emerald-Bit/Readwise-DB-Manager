import os
import sys
import requests
from requests.exceptions import RequestException, Timeout
import time
import datetime

import pandas as pd
from request_data_interaction import RequestDataInteraction
from user_request import UserRequest
from database import fetch_data_from_postgres, append_new_rows_postgres, append_new_rows_snowflake

import logging
import logging.config
from fuzzywuzzy import process, fuzz
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

client = OpenAI()

URL = "https://readwise.io/api/v3/list/"
TOKEN = os.getenv("READWISE_TOKEN")
LOGS_DIR = os.getenv("LOGS_DIR")
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_ACCOUNT = os.getenv("SF_ACCOUNT")
SF_WAREHOUSE = os.getenv("SF_WAREHOUSE")
PGRES_DB_NAME = os.getenv("PGRES_DB_NAME")
PGRES_DB_USER = os.getenv("PGRES_DB_USER")
PGRES_DB_PASSWORD = os.getenv("PGRES_DB_PASSWORD")
# ======================================================================================================================
def word_specific_search_method(df: pd.DataFrame) -> None:
    '''
    Search text for an exact word match, then print the results.
    :return:
    '''
    search_term_case_insensitive = str(input("Please enter a search term: ")).lower()
    result_df_case_insensitive = df[df['Summary'].str.contains(search_term_case_insensitive, case=False, na=False)]
    for i in range(len(result_df_case_insensitive)):
        print(result_df_case_insensitive["Title"].values[i],
            result_df_case_insensitive["Url"].values[i])

def fuzzy_search_method(search_term_fuzzy: str, min_score: int = 80) -> None:
    '''
    Perform a fuzzy search and print the results.
    :param search_term_fuzzy:
    :param min_score:
    :return:
    '''
    column_to_search = "Summary"
    unique_strings = df[column_to_search].unique()
    fuzzy_matches = process.extract(search_term_fuzzy, unique_strings, limit=None, scorer=fuzz.partial_ratio)
    close_matches = [match[0] for match in fuzzy_matches if match[1] >= min_score]
    result_df_fuzzy = df[df[column_to_search].isin(close_matches)]

    for i in range(len(result_df_fuzzy)):
        print(result_df_fuzzy["Title"].values[i],
            result_df_fuzzy["Url"].values[i])

    print(f"\n--- Fuzzy Match for '{search_term_fuzzy}' (score >= {min_score}) in 'Summary' column ---")

def chat_gpt_response(llm_query: str, readwise_text: list[dict[str, str]]) -> str:
    '''
    Sends a query to Chat GPT 4.1 and returns a formatted response.
    :param llm_query:
    :param obsidian_text:
    :return:
    '''

    response = client.responses.create(
        model="gpt-4.1-mini",
        instructions=f"I have input a dictionary (python) that contains information relating to articles saved from "
                     f"readwise. They are arranged as title, article, summary, time article was saved, date article was"
                     f" saved. "
                     f"I need you to analyse this, then answer the following query with the titles and related urls, "
                     f"with a small amount of text under each article explaining why you selected it: {str(llm_query)}."
                     f"If there are none, just say N/A. I do not"
                     "want any pleasantries, or any other text accompanied with your output.",
        input=f"{readwise_text}",
    )
    llm_response = response.output_text

    print(llm_response)
    return llm_response

def user_questions(df: pd.DataFrame, number_of_found_documents: int) -> None:
    """

    :return:
    """
    search_method_choice = input(
        f"You've found {number_of_found_documents} documents! \nHow do you want to search your "
        f"results? "
        f"\nWord? "
        f"\nFuzzy? "
        f"\nAI? "
        f"\n").lower()
    if search_method_choice == "word":
        word_specific_search_method()
    elif search_method_choice == "fuzzy":
        word_selected = input("Please select your search word").lower()
        score_selected = int(input("Please select your min fuzzy score (80 is a good start)"))
        fuzzy_search_method(word_selected, min_score=score_selected)
    elif search_method_choice == "ai":
        df_as_a_dict = df.to_dict(orient="records")
        print(df_as_a_dict)
        the_ask = str(input("What do you want to know about the collection of articles? "))
        chat_gpt_response(llm_query=the_ask, readwise_text=df_as_a_dict)
    else:
        print("You did not select a valid choice.")
# ======================================================================================================================
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
"formatters": {
    "minimal": {
        "format": "%(asctime)s %(message)s",
        "datefmt": "%d-%m-%Y %H:%M:%S",
    },
    "detailed": {
        "format": "%(levelname)s %(asctime)s [%(name)s:%(filename)s:%(funcName)s:%(lineno)d]\n%(message)s\n",
        "datefmt": "%d-%m-%Y %H:%M:%S",
    },
},
"handlers": {
    # These messages will appear in the "console" after runs, like print messages.
    "console": {
        "class": "logging.StreamHandler",
        "stream": sys.stdout,
        "formatter": "minimal",
        "level": logging.DEBUG,
    },
    "info": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": Path(LOGS_DIR, "info.log"),
        "maxBytes": 10485760,  # 1 MB
        "backupCount": 10,
        "formatter": "detailed",
        "level": logging.INFO,
    },
    "error": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": Path(LOGS_DIR, "error.log"),
        "maxBytes": 10485760,  # 1 MB
        "backupCount": 10,
        "formatter": "detailed",
        "level": logging.ERROR,
    },
},
"root": {
    "handlers": ["console", "info", "error"],
    "level": logging.INFO,
    "propagate": True,
    },
}
logging.config.dictConfig(logging_config)

logger = logging.getLogger()

if __name__ == "__main__":
    df = fetch_data_from_postgres(PGRES_DB_NAME, PGRES_DB_USER, PGRES_DB_PASSWORD)

    processor = RequestDataInteraction(df)

    processor.dataframe = df
    user_request = UserRequest(url=URL, token=TOKEN)

    app_on = True

    while app_on:
        user_request.fetch_reader_document_list_api()
        response_data = user_request.fetch_from_export_api()
        number_of_found_documents = len(response_data)
        print(f"Number of documents found: {number_of_found_documents}")

        df = processor.process_and_save_batch(response_data)
        processor.dataframe = df

        questions_on = True
        while questions_on:
            user_questions()
            continue_questions = input("Do you want to ask another question? \nYes/No").lower()
            if continue_questions == "yes" or continue_questions == "y":
                pass
            elif continue_questions == "no" or continue_questions == "n":
                questions_on = False
            else:
                print("Please submit a valid answer.")
        app_choice = input("Do you want change the parameters of your search query?").lower()
        if app_choice == "yes" or app_choice == "y":
            pass
        else:
            app_on = False

    append_new_rows_postgres(df, dbname=PGRES_DB_NAME, user=PGRES_DB_USER, password=PGRES_DB_PASSWORD)
    append_new_rows_snowflake(df, user=SF_USERNAME, password=SF_PASSWORD, account=SF_ACCOUNT, warehouse= SF_WAREHOUSE)
