_F='work_schedule.ics'
_E='location'
_D='Error'
_C='date'
_B='%Y-%m-%d'
_A=True
import customtkinter as ctk
from ics import Calendar,Event
from tkinter import messagebox,filedialog
from datetime import datetime,timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time,sys,threading,shutil,requests,chromedriver_autoinstaller
ctk.set_appearance_mode('System')
ctk.set_default_color_theme('blue')
class ScheduleFetcher:
	def __init__(A,headless=_A):A.driver=None;A.cookies={};A.headless=headless
	def _initialize_driver(B):
		A=Options();A.add_argument('--disable-gpu');A.add_argument('--no-sandbox')
		if B.headless:A.add_argument('--headless')
		chromedriver_autoinstaller.install();B.driver=webdriver.Chrome(options=A)
	def login(A,username,password):
		try:
			A._initialize_driver();D='https://secure.fourth.com/FMPLogin';A.driver.get(D);B=WebDriverWait(A.driver,10);E=B.until(EC.presence_of_element_located((By.NAME,'j_id0:j_id2:j_id15:username')));E.send_keys(username);F=A.driver.find_element(By.NAME,'j_id0:j_id2:j_id15:j_id24');F.send_keys(password);G=A.driver.find_element(By.NAME,'j_id0:j_id2:j_id15:submit');G.click();H=B.until(EC.element_to_be_clickable((By.XPATH,"//div[img[@class='app-logo-image' and @alt='My Schedule']]")));H.click();time.sleep(5);I=A.driver.current_window_handle
			for C in A.driver.window_handles:
				if C!=I:A.driver.switch_to.window(C)
			A.cookies={A['name']:A['value']for A in A.driver.get_cookies()};return _A
		except Exception as J:print('An error occurred during login:',J);return False
	def fetch_raw_schedule(B,from_date,to_date):
		C='https://api.fourth.com/api/myschedules/schedule';D={'$orderby':'StartDateTime asc','$top':100,'fromDate':from_date,'toDate':to_date};E={'accept':'application/vnd.siren+json','accept-encoding':'gzip, deflate, br, zstd','accept-language':'en-GB,en-US;q=0.9,en;q=0.8','connection':'keep-alive','content-type':'application/json','referer':'https://api.fourth.com/myschedules/','sec-ch-ua':'"Chromium";v="131", "Not_A Brand";v="24"','sec-ch-ua-mobile':'?0','sec-ch-ua-platform':'Linux','sec-fetch-dest':'empty','sec-fetch-mode':'cors','sec-fetch-site':'same-origin','user-agent':'Mozilla/5.0 (Linux; x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'}
		try:A=requests.get(C,headers=E,params=D,cookies=B.cookies);A.raise_for_status();return A.json()
		except requests.RequestException as F:print('Error fetching schedule:',F);return
	@staticmethod
	def parse_schedule(data):
		H='%H:%M';F='+00:00';E='Z';G=[]
		for I in data.get('entities',[]):A=I.get('properties',{});B=A.get('workDate');C=A.get('startDateTime');D=A.get('endDateTime');J=A.get('locationName');K=A.get('roleName');B=datetime.fromisoformat(B.replace(E,F)).strftime(_B);C=datetime.fromisoformat(C.replace(E,F)).strftime(H);D=datetime.fromisoformat(D.replace(E,F)).strftime(H);G.append({_C:B,'start':C,'end':D,_E:J,'role':K})
		return G
	def save_schedule_to_ics(F,schedule,file_name=_F):
		C=file_name
		try:
			D=Calendar()
			for A in schedule:B=Event();B.name=f"{A['role']} at {A[_E]}";B.begin=f"{A[_C]} {A['start']}";B.end=f"{A[_C]} {A['end']}";D.events.add(B)
			with open(C,'w')as E:E.writelines(D)
			return C
		except ImportError:print('\nInstall the `ics` module to save the schedule as a calendar file (`pip install ics`).')
	def close_driver(A):
		if A.driver:A.driver.quit()
class App:
	def __init__(A,root):A.root=root;A.root.title('Fourth Calendar Maker');A.root.geometry('400x300');A.file_path=None;A.fetcher=ScheduleFetcher(headless=_A);A.initialize_login_page()
	def initialize_login_page(A):A.clear_widgets();ctk.CTkLabel(A.root,text='Email:').pack(pady=10);A.email_entry=ctk.CTkEntry(A.root,width=250);A.email_entry.pack();ctk.CTkLabel(A.root,text='Password:').pack(pady=10);A.password_entry=ctk.CTkEntry(A.root,width=250,show='*');A.password_entry.pack();A.login_button=ctk.CTkButton(A.root,text='Login',command=A.start_login);A.login_button.pack(pady=20)
	def start_login(A):
		B=A.email_entry.get();C=A.password_entry.get()
		if B and C:A.show_loading_page();threading.Thread(target=A.login,args=(B,C),daemon=_A).start()
		else:messagebox.showwarning('Input Error','Please enter both email and password.')
	def login(A,email,password):
		B=A.fetcher.login(email,password)
		if B:A.fetch_schedule()
		else:messagebox.showerror('Login Error','Login failed. Please check your credentials.');A.initialize_login_page()
	def show_loading_page(A):A.clear_widgets();ctk.CTkLabel(A.root,text='').pack(pady=10);A.loading_label=ctk.CTkLabel(A.root,text='',font=('Arial',12));A.loading_label.pack(pady=10);threading.Thread(target=A.animate_loading,daemon=_A).start()
	def animate_loading(A):
		B=['Getting drivers ready','Gathering timetable details','Generating calendar','Creating file'];C=['.','..','...','....','.....']
		try:
			while _A:
				for D in B:
					for E in C:A.loading_label.configure(text=f"{D}{E}");A.root.update();time.sleep(1.5)
		except Exception:pass
	def fetch_schedule(A):
		C=datetime.now().strftime(_B);D=(datetime.now()+timedelta(days=365)).strftime(_B);B=A.fetcher.fetch_raw_schedule(C,D)
		if B:E=A.fetcher.parse_schedule(B);A.file_path=A.fetcher.save_schedule_to_ics(E,file_name=_F);A.root.after(0,A.initialize_download_page)
		else:messagebox.showerror(_D,'Failed to fetch schedule.')
	def initialize_download_page(A):A.clear_widgets();ctk.CTkLabel(A.root,text='Calendar file ready for download:').pack(pady=10);ctk.CTkButton(A.root,text='Download File',command=A.download_file).pack(pady=20)
	def download_file(A):
		if not A.file_path:messagebox.showerror(_D,'No file available for download.');return
		B=filedialog.askdirectory()
		if B:
			try:shutil.copy(A.file_path,B);messagebox.showinfo('Success','File downloaded successfully.');A.root.quit();sys.exit()
			except Exception as C:messagebox.showerror(_D,f"An error occurred: {C}")
	def clear_widgets(A):
		for B in A.root.winfo_children():B.destroy()
if __name__=='__main__':root=ctk.CTk();app=App(root);root.mainloop()