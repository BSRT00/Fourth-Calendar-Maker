import customtkinter as ctk
from ics import Calendar, Event
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time, sys, threading, shutil, requests, chromedriver_autoinstaller


# Optional: Set the appearance and theme for CustomTkinter
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Other themes: "dark-blue", "green"


class ScheduleFetcher:
    def __init__(self, headless=True):
        """
        Initialize the ScheduleFetcher class to manage login, schedule fetching, 
        and file creation for work schedules.
        """
        self.driver = None
        self.cookies = {}
        self.headless = headless

    def _initialize_driver(self):
        """
        Initialize the Chrome WebDriver with the given options.
        """
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")

        if self.headless:
            chrome_options.add_argument("--headless")

        # Automatically install chromedriver if not present
        chromedriver_autoinstaller.install()

        # Set up the Chrome driver
        self.driver = webdriver.Chrome(options=chrome_options)

    def login(self, username, password):
        """
        Log in to the website using the provided username and password.
        """
        try:
            self._initialize_driver()
            login_url = "https://secure.fourth.com/FMPLogin"
            self.driver.get(login_url)

            wait = WebDriverWait(self.driver, 10)
            username_field = wait.until(
                EC.presence_of_element_located((By.NAME, "j_id0:j_id2:j_id15:username"))
            )

            username_field.send_keys(username)
            password_field = self.driver.find_element(By.NAME, "j_id0:j_id2:j_id15:j_id24")
            password_field.send_keys(password)

            submit_button = self.driver.find_element(By.NAME, "j_id0:j_id2:j_id15:submit")
            submit_button.click()

            my_schedule_div = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[img[@class='app-logo-image' and @alt='My Schedule']]"
                ))
            )
            my_schedule_div.click()
            time.sleep(5)

            original_window = self.driver.current_window_handle
            for window in self.driver.window_handles:
                if window != original_window:
                    self.driver.switch_to.window(window)

            self.cookies = {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()}
            return True

        except Exception as e:
            print("An error occurred during login:", e)
            return False

    def fetch_raw_schedule(self, from_date, to_date):
        """
        Fetch the raw schedule data from the API using the given date range.
        """
        url = "https://api.fourth.com/api/myschedules/schedule"
        params = {
            "$orderby": "StartDateTime asc",
            "$top": 100,
            "fromDate": from_date,
            "toDate": to_date
        }
        headers = {
            "accept": "application/vnd.siren+json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "connection": "keep-alive",
            "content-type": "application/json",
            "referer": "https://api.fourth.com/myschedules/",
            "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Linux",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Linux; x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers, params=params, cookies=self.cookies)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            print("Error fetching schedule:", e)
            return None

    @staticmethod
    def parse_schedule(data):
        """
        Parse the raw schedule data and return a list of parsed schedule events.
        """
        schedule = []
        for entity in data.get("entities", []):
            properties = entity.get("properties", {})
            work_date = properties.get("workDate")
            start_time = properties.get("startDateTime")
            end_time = properties.get("endDateTime")
            location = properties.get("locationName")
            role = properties.get("roleName")

            work_date = datetime.fromisoformat(work_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime("%H:%M")
            end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00")).strftime("%H:%M")

            schedule.append({
                "date": work_date,
                "start": start_time,
                "end": end_time,
                "location": location,
                "role": role
            })
        return schedule

    def save_schedule_to_ics(self, schedule, file_name="work_schedule.ics"):
        """
        Save the parsed schedule as an ICS calendar file.
        """
        try:
            cal = Calendar()
            for shift in schedule:
                event = Event()
                event.name = f"{shift['role']} at {shift['location']}"
                event.begin = f"{shift['date']} {shift['start']}"
                event.end = f"{shift['date']} {shift['end']}"
                cal.events.add(event)

            with open(file_name, "w") as f:
                f.writelines(cal)
            return file_name

        except ImportError:
            print("\nInstall the `ics` module to save the schedule as a calendar file (`pip install ics`).")

    def close_driver(self):
        """
        Close the WebDriver instance.
        """
        if self.driver:
            self.driver.quit()


class App:
    def __init__(self, root):
        """
        Initialize the main application window and set up the login page.
        """
        self.root = root
        self.root.title("Fourth Calendar Maker")
        self.root.geometry("400x300")

        self.file_path = None
        self.fetcher = ScheduleFetcher(headless=True)
        
        self.initialize_login_page()

    def initialize_login_page(self):
        """
        Set up the login page widgets.
        """
        self.clear_widgets()

        ctk.CTkLabel(self.root, text="Email:").pack(pady=10)
        self.email_entry = ctk.CTkEntry(self.root, width=250)
        self.email_entry.pack()

        ctk.CTkLabel(self.root, text="Password:").pack(pady=10)
        self.password_entry = ctk.CTkEntry(self.root, width=250, show="*")
        self.password_entry.pack()

        self.login_button = ctk.CTkButton(self.root, text="Login", command=self.start_login)
        self.login_button.pack(pady=20)

    def start_login(self):
        """
        Start the login process in a separate thread.
        """
        email = self.email_entry.get()
        password = self.password_entry.get()

        if email and password:
            self.show_loading_page()
            threading.Thread(target=self.login, args=(email, password), daemon=True).start()
        else:
            messagebox.showwarning("Input Error", "Please enter both email and password.")

    def login(self, email, password):
        """
        Perform the login using the provided credentials.
        """
        success = self.fetcher.login(email, password)
        if success:
            self.fetch_schedule()
        else:
            messagebox.showerror("Login Error", "Login failed. Please check your credentials.")
            self.initialize_login_page()

    def show_loading_page(self):
        """
        Show the loading page with an animated progress message.
        """
        self.clear_widgets()

        # Create an empty label for spacing
        ctk.CTkLabel(self.root, text="").pack(pady=10)
        self.loading_label = ctk.CTkLabel(self.root, text="", font=("Arial", 12))
        self.loading_label.pack(pady=10)

        threading.Thread(target=self.animate_loading, daemon=True).start()

    def animate_loading(self):
        """
        Animate the loading process by updating the loading label text in a loop.
        """
        messages = ["Getting drivers ready", "Gathering timetable details", "Generating calendar", "Creating file"]
        progress_text = [".", "..", "...", "....", "....."]
        try:
            while True:
                for message in messages:
                    for dots in progress_text:
                        self.loading_label.configure(text=f"{message}{dots}")
                        self.root.update()
                        time.sleep(1.5)
        except Exception:
            pass

    def fetch_schedule(self):
        """
        Fetch the work schedule and save it to a file.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        date_in_a_year = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

        raw_data = self.fetcher.fetch_raw_schedule(today, date_in_a_year)
        
        if raw_data:
            schedule = self.fetcher.parse_schedule(raw_data)
            self.file_path = self.fetcher.save_schedule_to_ics(schedule, file_name="work_schedule.ics")
            self.root.after(0, self.initialize_download_page)
        else:
            messagebox.showerror("Error", "Failed to fetch schedule.")

    def initialize_download_page(self):
        """
        Set up the download page where the user can download the ICS file.
        """
        self.clear_widgets()

        ctk.CTkLabel(self.root, text="Calendar file ready for download:").pack(pady=10)
        ctk.CTkButton(self.root, text="Download File", command=self.download_file).pack(pady=20)

    def download_file(self):
        """
        Allow the user to download the ICS file to their selected directory.
        """
        if not self.file_path:
            messagebox.showerror("Error", "No file available for download.")
            return

        destination = filedialog.askdirectory()
        if destination:
            try:
                shutil.copy(self.file_path, destination)
                messagebox.showinfo("Success", "File downloaded successfully.")
                self.root.quit()
                sys.exit()
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")

    def clear_widgets(self):
        """
        Clear all widgets from the root window.
        """
        for widget in self.root.winfo_children():
            widget.destroy()


if __name__ == "__main__":
    # Create the main window using CustomTkinter's CTk
    root = ctk.CTk()
    app = App(root)
    root.mainloop()