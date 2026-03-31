import logging
import logging.config
import datetime
import os
from requests.exceptions import RequestException, Timeout
import time
from dotenv import load_dotenv
import requests
from config import URL
from typing import Any, Optional

load_dotenv()

TOKEN = os.getenv("READWISE_TOKEN")
LOGS_DIR = os.getenv("LOGS_DIR")

class UserRequest:
    """

    """
    def __init__(self, url: str, token: str) -> None:
        self.location = None
        self.category = None
        self.updated_after = None
        self.url = url
        self.headers = {
            "Authorization": token,
        }
        self.parameters = {
            "location": self.location,
            "category": self.category,
            "updatedAfter": self.updated_after
        }

    def fetch_reader_document_list_api(self) -> None:
        '''
        Ask user for location, category, and updatedAfter date.
        :return:
        '''

        my_location = input("Please enter one of these locations: "
                            "\nNew "
                            "\nLater "
                            "\nArchive "
                            "\nFeed "
                            "\n").lower()
        valid_locations = ["new", "later", "archive", "feed"]
        while my_location not in valid_locations:
            print("Not a relevant input please try again.")
            my_location = input("Please enter one of these locations: "
                                "\nNew "
                                "\nLater "
                                "\nArchive "
                                "\nFeed "
                                "\n").lower()
        self.location = my_location

        my_category = input("Please enter one of these types: "
                            "\nArticle "
                            "\nEmail "
                            "\nRSS "
                            "\nHighlight "
                            "\nNote "
                            "\nPDF "
                            "\nEPub "
                            "\nTweet "
                            "\nVideo "
                            "\n").lower()
        valid_categories = ["article", "email", "rss", "highlight", "note", "pdf", "epub", "tweet", "video"]
        while my_category not in valid_categories:
            print("Not a relevant input please try again.")
            my_category = input("Please enter one of these types: "
                                "\nArticle "
                                "\nEmail "
                                "\nRSS "
                                "\nHighlight "
                                "\nNote "
                                "\nPDF "
                                "\nEPub "
                                "\nTweet "
                                "\nVideo "
                                "\n").lower()
        self.category = my_category

        days_back = int(input("Now search for articles that have had ANY changes i.e. highlights, notes, etc."
                              "\nHow far back (in days) do you want your search to be? You can skip this by typing zero: "))
        if days_back <= 0:
            self.updated_after = None
        elif days_back > 0:
            days_apart = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days_back)
            my_updated_after = days_apart.isoformat()
            self.updated_after = my_updated_after

        self.parameters["location"] = self.location
        self.parameters["category"] = self.category
        self.parameters["updatedAfter"] = self.updated_after


    def fetch_from_export_api(self,
                              updated_after: Optional[str] = None,
                              retries: int = 3,
                              backoff_factor: float = 1.5,
                              timeout: float = 10.0) -> list[dict[str, Any]]:
        """
        Fetches documents from the API, optionally filtering by date.
        """
        # If a date is provided, we add it to the self.parameters dictionary.
        if updated_after:
            self.parameters['updatedAfter'] = updated_after

        if 'pageCursor' in self.parameters:
            del self.parameters['pageCursor']

        all_documents = []
        data = None
        next_page_cursor = None
        while True:
            if next_page_cursor:
                self.parameters['pageCursor'] = next_page_cursor
            print("Making export api request with params " + str(self.parameters) + "...")

            logging.info("Requesting documents from %s with params: %s", self.url, self.parameters)
            for attempt in range(retries):
                try:
                    response = requests.get(
                        url=URL,
                        params=self.parameters,
                        headers={"Authorization": f"Token {TOKEN}"},
                        verify=True
                    )

                    # Check HTTP status code
                    if response.status_code == 200:
                        logging.info("Request succeeded with status 200.")
                        data = response.json()
                        break
                    elif 400 <= response.status_code < 500:
                        logging.warning("Client error (%s): %s", response.status_code, response.text)
                    elif 500 <= response.status_code < 600:
                        logging.error("Server error (%s): %s", response.status_code, response.text)
                    else:
                        logging.error("Unexpected status code %s: %s", response.status_code, response.text)

                        response.raise_for_status()
                        # Add the new results to our master list.
                        data = response.json()
                except Timeout:
                    print(f"Timeout on attempt {attempt + 1}/{retries}. Retrying...")
                except RequestException as e:
                    logging.exception("Request failed due to a network or HTTP error: %s", e)
                    print(f"Request failed: {e}. Retrying....")

                sleep_time = backoff_factor ** attempt
                print(f"Waiting {sleep_time:.1f}s before retrying...")
                time.sleep(sleep_time)
            else:
                raise RequestException(f"Failed to fetch {self.url} after {retries} retries.")

            all_documents.extend(data['results'])
            next_page_cursor = response.json().get('nextPageCursor')
            if not next_page_cursor:
                break

        return all_documents
