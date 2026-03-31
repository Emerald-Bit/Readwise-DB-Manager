import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pandas as pd
import datetime
import webbrowser
import back_end as backend

class ReadwiseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Readwise DB Manager")
        self.geometry("1000x700")

        self.apply_theme()

        self.df = pd.DataFrame()
        self.user_request = backend.UserRequest(backend.URL, backend.TOKEN)
        self.processor = None

        # Setup UI
        self.create_widgets()

        self.status("Connecting to Postgres...")
        threading.Thread(target=self.load_initial_data, daemon=True).start()

    def apply_theme(self):
        """Applies a dark blue-grey color scheme."""
        # Main Window Background
        bg_color = "#2c3e50"  # Dark Blue-Grey
        fg_color = "white"
        accent_color = "#e74c3c"  # Red/Orange

        self.configure(bg=bg_color)

        # Configure the Style for ttk widgets
        style = ttk.Style()
        style.theme_use('clam')
        # General Labels
        style.configure("TLabel", background=bg_color, foreground=fg_color)

        # LabelFrames (The boxes around controls)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)

        # Buttons
        style.configure("TButton", background=accent_color, foreground="white", borderwidth=0)
        style.map('TButton', background=[('active', '#c0392b')])  # Darker red on hover

        # Treeview (The Table)
        style.configure("Treeview",
                        background="#ecf0f1",  # Light grey table background
                        fieldbackground="#ecf0f1",
                        foreground="black",
                        rowheight=25)
        style.map('Treeview', background=[('selected', '#3498db')])  # Blue when row selected

        # Treeview Headings
        style.configure("Treeview.Heading", background="#95a5a6", foreground="black", relief="flat")


    def create_widgets(self):
        control_frame = ttk.LabelFrame(self, text="API Settings", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(control_frame, text="Location:").pack(side="left")
        self.combo_loc = ttk.Combobox(control_frame, values=["new", "later", "archive", "feed"], width=10)
        self.combo_loc.set("new")
        self.combo_loc.pack(side="left", padx=5)

        ttk.Label(control_frame, text="Category:").pack(side="left")
        self.combo_cat = ttk.Combobox(control_frame, values=["article", "tweet", "highlight", "note"], width=10)
        self.combo_cat.set("article")
        self.combo_cat.pack(side="left", padx=5)

        ttk.Label(control_frame, text="Days Back:").pack(side="left")
        self.entry_days = ttk.Entry(control_frame, width=5)
        self.entry_days.insert(0, "0")
        self.entry_days.pack(side="left", padx=5)

        self.btn_fetch = ttk.Button(control_frame, text="Fetch from API", command=self.start_fetch)
        self.btn_fetch.pack(side="left", padx=20)


        self.tree = ttk.Treeview(self, columns=("Title", "Url", "Summary", "Date"), show="headings")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Url", text="URL")
        self.tree.heading("Summary", text="Summary")
        self.tree.heading("Date", text="Date Saved")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree.bind("<Double-1>", self.on_double_click)

        action_frame = ttk.LabelFrame(self, text="Actions", padding=10)
        action_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(action_frame, text="Search:").pack(side="left")
        self.entry_search = ttk.Entry(action_frame, width=30)
        self.entry_search.pack(side="left", padx=5)

        ttk.Button(action_frame, text="Word Search", command=lambda: self.run_search("word")).pack(side="left")
        ttk.Button(action_frame, text="Fuzzy Search", command=lambda: self.run_search("fuzzy")).pack(side="left")
        ttk.Button(action_frame, text="Ask AI", command=self.run_ai).pack(side="left", padx=5)

        ttk.Button(action_frame, text="Save to DBs", command=self.save_to_dbs).pack(side="right")

        self.lbl_status = ttk.Label(self, text="Ready", relief="sunken")
        self.lbl_status.pack(fill="x")

    def status(self, msg):
        self.lbl_status.config(text=msg)

    def on_double_click(self, event):
        """Opens the URL of the selected row in the default browser."""
        try:
            item_id = self.tree.selection()[0]
            values = self.tree.item(item_id, "values")
            url = values[1]

            if url and (url.startswith("http") or url.startswith("www")):
                webbrowser.open(url)
                self.status(f"Opening: {url}")
            else:
                self.status("No valid URL found for this row.")
        except IndexError:
            pass

    def load_initial_data(self):
        try:
            self.df = backend.fetch_data_from_postgres(
                backend.PGRES_DB_NAME, backend.PGRES_DB_USER, backend.PGRES_DB_PASSWORD
            )
            self.processor = backend.RequestDataInteraction(self.df)
            self.after(0, self.refresh_table)
            self.after(0, lambda: self.status(f"Loaded {len(self.df)} rows."))
        except Exception as e:
            self.after(0, lambda: self.status(f"DB Error: {e}"))

    def start_fetch(self):
        self.status("Fetching...")
        # Get values from GUI
        loc = self.combo_loc.get()
        cat = self.combo_cat.get()
        try:
            days = int(self.entry_days.get())
        except:
            days = 0

        threading.Thread(target=self.run_fetch_logic, args=(loc, cat, days), daemon=True).start()

    def run_fetch_logic(self, loc, cat, days):
        try:
            updated_after = None
            if days > 0:
                days_apart = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days)
                updated_after = days_apart.isoformat()

            self.user_request.parameters = {
                "location": loc,
                "category": cat,
                "updatedAfter": updated_after
            }

            new_docs = self.user_request.fetch_from_export_api()

            if new_docs:
                self.df = self.processor.process_and_save_batch(new_docs)
                self.processor.dataframe = self.df
                msg = f"Fetched {len(new_docs)} new items."
                self.after(0, self.refresh_table)
            else:
                msg = "No new items found."

            self.after(0, lambda: self.status(msg))

        except Exception as e:
            print(e)
            self.after(0, lambda: self.status(f"Error: {e}"))

    def refresh_table(self, custom_df=None):
        for item in self.tree.get_children():
            self.tree.delete(item)

        target_df = custom_df if custom_df is not None else self.df
        if target_df.empty: return

        for _, row in target_df.iterrows():
            self.tree.insert("", "end", values=(
                row.get("Title", ""),
                row.get("Url", ""),
                str(row.get("Summary", ""))[:50] + "...",
                row.get("Date Saved", "")
            ))

    def run_search(self, mode):
        term = self.entry_search.get()
        if not term:
            self.refresh_table()
            return

        if mode == "word":
            res = self.df[self.df['Summary'].astype(str).str.contains(term, case=False, na=False)]
        else:
            from fuzzywuzzy import process, fuzz
            valid_df = self.df.dropna(subset=['Summary'])
            unique_strings = valid_df['Summary'].astype(str).unique()
            matches = process.extract(term, unique_strings, limit=None, scorer=fuzz.partial_ratio)
            close_matches = [m[0] for m in matches if m[1] >= 80]
            res = self.df[self.df['Summary'].isin(close_matches)]

        self.refresh_table(res)

    def run_ai(self):
        query = self.entry_search.get()
        if not query: return

        def ai_thread():
            self.status("AI Thinking...")
            df_slice = self.df.head(20)
            data_dict = df_slice.to_dict(orient="records")

            response = backend.chat_gpt_response(query, data_dict)

            self.after(0, lambda: messagebox.showinfo("AI Response", response))
            self.after(0, lambda: self.status("Ready"))

        threading.Thread(target=ai_thread, daemon=True).start()

    def save_to_dbs(self):
        self.status("Saving to DBs...")
        try:
            backend.append_new_rows_postgres(
                self.df, backend.PGRES_DB_NAME, backend.PGRES_DB_USER, backend.PGRES_DB_PASSWORD
            )
            backend.append_new_rows_snowflake(
                self.df, backend.SF_USERNAME, backend.SF_PASSWORD, backend.SF_ACCOUNT, backend.SF_WAREHOUSE
            )
            messagebox.showinfo("Success", "Saved to Postgres and Snowflake!")
            self.status("Ready")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status("Error Saving")


if __name__ == "__main__":
    app = ReadwiseApp()
    app.mainloop()
