import psycopg2
import psycopg2.extras
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd


def fetch_data_from_postgres(dbname: str, user: str, password: str) -> pd.DataFrame:
    """
    Connects to Postgres and pulls the article table into a DataFrame.
    """
    conn = None
    try:
        conn = psycopg2.connect(dbname=dbname,
                                user=user,
                                password=password)

        query = "SELECT title, url, summary, time_saved, date_saved FROM readwise_articles"
        df = pd.read_sql(query, conn)
        df.rename(columns={
            "title": "Title", "url": "Url", "summary": "Summary",
            "time_saved": "Time Saved", "date_saved": "Date Saved"
        }, inplace=True)

        return df

    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()  # Return empty DF on failure
    finally:
        if conn: conn.close()

def append_new_rows_postgres(dataframe: pd.DataFrame, dbname: str, user: str, password: str) -> None:
    """
    Inserts NEW rows into Postgres.
    If a row with the same URL exists, it does nothing (skips it).
    """
    conn = None
    try:
        conn = psycopg2.connect(dbname=dbname,
                                user=user,
                                password=password)
        cur = conn.cursor()

        # SQL: Try to insert, but do nothing if the URL already exists.
        sql_query = """
            INSERT INTO readwise_articles (title, url, summary, time_saved, date_saved)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        """

        data_tuples = list(zip(
            dataframe['Title'],
            dataframe['Url'],
            dataframe['Summary'],
            dataframe['Time Saved'],
            dataframe['Date Saved']
        ))

        psycopg2.extras.execute_batch(cur, sql_query, data_tuples)
        conn.commit()
        print(f"Batch insert complete. (Duplicates were skipped).")

    except Exception as e:
        print(f"Postgres Insert Failed: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

def append_new_rows_snowflake(df: pd.DataFrame, user: str, password: str, account: str, warehouse: str) -> None:
    """
    Appends ONLY new rows to Snowflake.
    It compares the 'Url' in your dataframe with the 'URL' in the database.
    If the URL is missing from the DB, it inserts the row.
    """
    con = None
    try:
        # Authenticates via HTTPS
        con = snowflake.connector.connect(user=user,
                                           password=password,
                                           account=account,
                                           warehouse=warehouse,
                                          database="READWISE_ARTICLES",
                                          schema="PUBLIC",
                                          autocommit=True)


        df.columns = [c.strip().replace(" ", "_").upper() for c in df.columns]
        write_pandas(
            con,
            df,
            "TEMP_NEW_DATA",
            auto_create_table=True,
            table_type="TEMPORARY"
        )

        merge_sql = """
            MERGE INTO READWISE_ARTICLES.PUBLIC.READWISE_ARTICLES t
            USING TEMP_NEW_DATA s
            ON t.URL = s.URL
            WHEN NOT MATCHED THEN
                INSERT (TITLE, URL, SUMMARY, TIME_SAVED, DATE_SAVED)
                VALUES (s.TITLE, s.URL, s.SUMMARY, s.TIME_SAVED, s.DATE_SAVED)
        """
        # Submits a job to the cloud queue
        con.cursor().execute(merge_sql)
        print("Snowflake Append Complete (New rows added).")

    except Exception as e:
        print(f"Snowflake Append Failed: {e}")
    finally:
        if con: con.close()
