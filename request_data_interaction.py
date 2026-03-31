import pandas as pd
import datetime as datetime

class RequestDataInteraction:
    """

    """
    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.time_to_convert = None

    def convert_time_date(self, input_date: str) -> tuple[str, str]:
        '''
        Convert ISO datetime to UK date and time strings.
        :param input_date:
        :return:
        '''
        input_date = input_date.split("T")
        date = input_date[0]
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
        date = date.strftime("%d/%m/%Y")
        time_to_convert = input_date[1].split(".")[0]
        return date, time_to_convert

    def process_and_save_batch(self, documents: list[dict]) -> pd.DataFrame:
        """
        Takes a list of raw documents, processes them all in memory,
        and writes them to the CSV in a single operation.
        """
        temp_data_storage = []
        for doc in documents:
            raw_date = doc["saved_at"]
            uk_date, uk_time = self.convert_time_date(raw_date)

            temp_data_storage.append({
                "Title": doc["title"],
                "Url": doc["url"],
                "Summary": doc["summary"],
                "Time Saved": uk_time,
                "Date Saved": uk_date
            })

        new_data_df = pd.DataFrame(temp_data_storage)
        new_data_df['Date Saved'] = pd.to_datetime(new_data_df['Date Saved'], dayfirst=True, errors="coerce")

        # Removing Timezone info (make "Naive") to prevent Database errors
        if not new_data_df.empty and new_data_df['Date Saved'].dt.tz is not None:
            new_data_df['Date Saved'] = new_data_df['Date Saved'].dt.tz_convert(None)

        combined_df = pd.concat([self.dataframe, new_data_df])

        print(f"Successfully saved {len(new_data_df)} new records.")
        return combined_df
