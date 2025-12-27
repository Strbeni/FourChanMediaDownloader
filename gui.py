import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import urllib.request
import urllib.error
import re
import os
import threading
import time
from PIL import Image, ImageTk
from io import BytesIO
import math

# Set theme and color
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ChanMediaScanner(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("4Chan Media Hub")
        self.geometry("1100x700")
        
        # Configure layout (2 columns: Sidebar, Main Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State
        self.download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
        if not os.path.exists(self.download_path):
            try:
                os.makedirs(self.download_path)
            except:
                self.download_path = os.getcwd()

        self.url_cache = {}  # URL -> list of media links
        self.image_cache = {} # URL -> key/image_data
        self.current_media = []
        self.visible_limit = 16 # Start with 4 rows of 4
        self.selected_urls = set()
        self.active_vars = {} # url -> BooleanVar for currently visible items
        
        # UI Setup
        self.create_sidebar()
        self.create_media_frame()
        self.create_settings_frame()

        # Start at Media Scanner
        self.select_frame("media")

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="4Chan Hub", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_media = ctk.CTkButton(self.sidebar_frame, text="Media Scanner", 
                                       command=lambda: self.select_frame("media"))
        self.btn_media.grid(row=1, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Settings", 
                                          command=lambda: self.select_frame("settings"))
        self.btn_settings.grid(row=2, column=0, padx=20, pady=10)

    def create_media_frame(self):
        self.media_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.media_frame.grid_columnconfigure(0, weight=1)
        self.media_frame.grid_rowconfigure(2, weight=1) # Preview expands

        # Input Section
        self.input_frame = ctk.CTkFrame(self.media_frame, fg_color="transparent")
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)  # Entry expands

        self.entry_url = ctk.CTkEntry(self.input_frame, placeholder_text="Enter 4Chan Thread URL...")
        self.entry_url.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")
        self.entry_url.bind('<Return>', lambda event: self.start_scan())

        self.btn_scan = ctk.CTkButton(self.input_frame, text="Scan Media", width=120, command=self.start_scan)
        self.btn_scan.grid(row=0, column=1, padx=0, pady=0)

        # Tools/Status Section
        self.tools_frame = ctk.CTkFrame(self.media_frame, fg_color="transparent")
        self.tools_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.lbl_status = ctk.CTkLabel(self.tools_frame, text="Ready to scan...", text_color="gray")
        self.lbl_status.pack(side="left")

        # Selection Tools
        self.btn_dl_sel = ctk.CTkButton(self.tools_frame, text="Download Selected", width=120, 
                                        fg_color="green", hover_color="darkgreen",
                                        command=self.download_selected)
        self.btn_dl_sel.pack(side="right", padx=(10, 0))

        self.btn_sel_none = ctk.CTkButton(self.tools_frame, text="Select None", width=80, 
                                          fg_color="gray", hover_color="gray30",
                                          command=self.select_none)
        self.btn_sel_none.pack(side="right", padx=5)

        self.btn_sel_all = ctk.CTkButton(self.tools_frame, text="Select All", width=80, 
                                         fg_color="gray", hover_color="gray30",
                                         command=self.select_all)
        self.btn_sel_all.pack(side="right", padx=5)


        # Preview Section (Scrollable Frame)
        self.preview_frame = ctk.CTkScrollableFrame(self.media_frame, label_text="Media Preview")
        self.preview_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        # Grid layout for images (4 columns)
        for i in range(4):
            self.preview_frame.grid_columnconfigure(i, weight=1)

        # Pagination Controls
        self.controls_frame = ctk.CTkFrame(self.media_frame, fg_color="transparent")
        self.controls_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        self.btn_show_more = ctk.CTkButton(self.controls_frame, text="Show More", width=120, command=self.show_more, state="disabled")
        self.btn_show_more.pack(side="left", padx=10)

        self.btn_show_all = ctk.CTkButton(self.controls_frame, text="Show All", width=120, command=self.show_all, state="disabled")
        self.btn_show_all.pack(side="right", padx=10)

    def create_settings_frame(self):
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        self.lbl_settings = ctk.CTkLabel(self.settings_frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_settings.pack(pady=20, padx=20, anchor="w")

        self.lbl_path = ctk.CTkLabel(self.settings_frame, text="Download Path:")
        self.lbl_path.pack(pady=(10, 5), padx=20, anchor="w")

        self.entry_path = ctk.CTkEntry(self.settings_frame, width=400)
        self.entry_path.insert(0, self.download_path)
        self.entry_path.pack(pady=5, padx=20, anchor="w")
        
        self.btn_browse = ctk.CTkButton(self.settings_frame, text="Browse Folder", command=self.choose_directory)
        self.btn_browse.pack(pady=10, padx=20, anchor="w")

    def select_frame(self, name):
        # Update button states
        self.btn_media.configure(fg_color=("gray75", "gray25") if name == "media" else "transparent")
        self.btn_settings.configure(fg_color=("gray75", "gray25") if name == "settings" else "transparent")

        # Show frame
        if name == "media":
            self.settings_frame.grid_forget()
            self.media_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.media_frame.grid_forget()
            self.settings_frame.grid(row=0, column=1, sticky="nsew")

    def choose_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.download_path = directory
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, directory)

    def start_scan(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid URL.")
            return

        self.lbl_status.configure(text="Scanning...", text_color="cyan")
        self.btn_scan.configure(state="disabled")
        
        # Reset View
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Run in thread
        threading.Thread(target=self.perform_scan, args=(url,), daemon=True).start()

    def perform_scan(self, url):
        # Check Cache
        if url in self.url_cache:
            self.current_media = self.url_cache[url]
            cached = True
        else:
            cached = False
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    html_code = response.read().decode('utf-8', errors='ignore')

                media_pattern = re.compile(r'<div class="fileText"[^>]*>.*?<a\s+[^>]*href=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL)
                matches = media_pattern.findall(html_code)
                
                # Normalize URLs
                full_urls = []
                for m in matches:
                    if m.startswith("//"):
                        full_urls.append("https:" + m)
                    elif m.startswith("http"):
                        full_urls.append(m)
                    else:
                        full_urls.append(m) 
                
                self.current_media = full_urls
                self.url_cache[url] = full_urls
            except Exception as e:
                self.after(0, lambda: self.show_error(str(e)))
                return

        self.after(0, lambda: self.scan_completed(cached))

    def show_error(self, msg):
        self.lbl_status.configure(text=f"Error: {msg}", text_color="red")
        self.btn_scan.configure(state="normal")
        messagebox.showerror("Error", msg)

    def scan_completed(self, cached):
        count = len(self.current_media)
        source = " (Cached)" if cached else ""
        self.lbl_status.configure(text=f"Found {count} media files{source}.", text_color="green")
        self.btn_scan.configure(state="normal")
        
        self.visible_limit = 16
        self.selected_urls.clear()
        self.update_preview_page()

    def update_preview_page(self):
        # Clear existing
        self.active_vars = {}
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        if not self.current_media:
            return

        visible_items = self.current_media[:self.visible_limit]
        
        # Update controls
        total_count = len(self.current_media)
        showing_count = len(visible_items)
        
        # Status update (showing X of Y)
        # self.lbl_status.configure(text=f"Showing {showing_count} of {total_count} files.")
        
        self.btn_show_more.configure(state="normal" if showing_count < total_count else "disabled")
        self.btn_show_all.configure(state="normal" if showing_count < total_count else "disabled")

        if not visible_items:
            ctk.CTkLabel(self.preview_frame, text="No media to display.").pack(pady=20)
            return

        # Load thumbnails
        threading.Thread(target=self.load_thumbnails, args=(visible_items,), daemon=True).start()

    def load_thumbnails(self, items):
        for index, url in enumerate(items):
            try:
                if url in self.image_cache:
                    ctk_image = self.image_cache[url]
                else:
                    base, ext = os.path.splitext(url)
                    thumb_url = base + "s.jpg"

                    headers = {'User-Agent': 'Mozilla/5.0'}
                    req = urllib.request.Request(thumb_url, headers=headers)
                    
                    with urllib.request.urlopen(req) as response:
                        data = response.read()
                    
                    img_data = BytesIO(data)
                    pil_image = Image.open(img_data)
                    pil_image.thumbnail((150, 150))
                    
                    ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=pil_image.size)
                    self.image_cache[url] = ctk_image
                
                # Pass to UI
                self.after(0, lambda u=url, i=ctk_image, n=index: self.add_preview_item(u, i, n))
                
                # Delay to prevent 429
                time.sleep(0.3)

            except Exception as e:
                # print(f"Failed to load thumb for {url}: {e}")
                self.after(0, lambda u=url, n=index: self.add_preview_item(u, None, n))

    def add_preview_item(self, url, ctk_img, index):
        if index == -1: return # Error case

        row = index // 4
        col = index % 4

        # Card Frame
        frame = ctk.CTkFrame(self.preview_frame, fg_color=("gray85", "gray20"))
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Inner Layout
        frame.grid_columnconfigure(0, weight=1)

        # Image
        if ctk_img:
            lbl_img = ctk.CTkLabel(frame, text="", image=ctk_img)
            lbl_img.grid(row=0, column=0, padx=5, pady=5)
        else:
            lbl_img = ctk.CTkLabel(frame, text="No Preview", width=100, height=100)
            lbl_img.grid(row=0, column=0, padx=5, pady=5)

        # Truncated Filename
        filename = url.split('/')[-1]
        display_name = (filename[:15] + '..') if len(filename) > 15 else filename
        ctk.CTkLabel(frame, text=display_name, font=ctk.CTkFont(size=11)).grid(row=1, column=0, pady=(0, 2))

        # Checkbox (No text)
        var_select = ctk.BooleanVar(value=url in self.selected_urls)
        self.active_vars[url] = var_select
        
        chk = ctk.CTkCheckBox(frame, text="", variable=var_select, width=20, height=20,
                              command=lambda u=url, v=var_select: self.toggle_selection(u, v))
        chk.grid(row=2, column=0, pady=2)

        # Download Button
        btn_dl = ctk.CTkButton(frame, text="Download", height=20, width=80, font=("Arial", 10),
                               command=lambda u=url: self.download_single_wrapper(u))
        btn_dl.grid(row=3, column=0, pady=(2, 10))

    def toggle_selection(self, url, var):
        if var.get():
            self.selected_urls.add(url)
        else:
            self.selected_urls.discard(url)

    def select_all(self):
        # Update set
        for url in self.current_media:
            self.selected_urls.add(url)
        # Update visible
        for url, search_var in self.active_vars.items():
            search_var.set(True)

    def select_none(self):
        self.selected_urls.clear()
        for url, search_var in self.active_vars.items():
            search_var.set(False)


    def download_selected(self):
        if not self.selected_urls:
            messagebox.showinfo("Info", "No files selected.")
            return
        
        urls = list(self.selected_urls)
        threading.Thread(target=self.download_bulk, args=(urls,), daemon=True).start()

    def download_single_wrapper(self, url):
         self.lbl_status.configure(text=f"Queueing download...", text_color="cyan")
         threading.Thread(target=self.download_with_retry, args=(url,), daemon=True).start()

    def download_bulk(self, urls):
        # Notify start
        self.lbl_status.configure(text=f"Starting download of {len(urls)} files.", text_color="cyan")
        
        success_count = 0
        for i, url in enumerate(urls):
            filename = url.split('/')[-1]
            self.lbl_status.configure(text=f"Downloading {filename} ({i+1}/{len(urls)})...", text_color="cyan")
            if self.download_with_retry(url):
                success_count += 1
            # Add delay
            time.sleep(1.5)
        
        self.lbl_status.configure(text=f"Completed. Downloaded {success_count} files.", text_color="green")

    def show_more(self):
        self.visible_limit += 16
        self.update_preview_page()

    def show_all(self):
        self.visible_limit = len(self.current_media)
        self.update_preview_page()

    def download_with_retry(self, url, retries=3):
        filename = url.split('/')[-1]
        path = os.path.join(self.download_path, filename)
        
        for attempt in range(retries):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as response:
                    data = response.read()
                
                with open(path, 'wb') as f:
                    f.write(data)
                
                print(f"Downloaded {filename}")
                return True
            except urllib.error.HTTPError as e:
                print(f"HTTP Error {e.code} for {filename}")
                if e.code == 429:
                    print(f"429 Too Many Requests for {filename}. Retrying in 2s...")
                    time.sleep(2 * (attempt + 1))
                else:
                    break
            except Exception as e:
                print(f"Error downloading {filename}: {e}")
                break
        return False


if __name__ == "__main__":
    app = ChanMediaScanner()
    app.mainloop()
