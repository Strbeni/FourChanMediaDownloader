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
        self.current_media = []
        self.current_page = 0
        self.items_per_page = 15 # Grid view needs more items (3 rows of 5)
        self.selected_urls = set()
        
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
        # Grid layout for images (5 columns)
        for i in range(5):
            self.preview_frame.grid_columnconfigure(i, weight=1)

        # Pagination Controls
        self.controls_frame = ctk.CTkFrame(self.media_frame, fg_color="transparent")
        self.controls_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        self.btn_prev = ctk.CTkButton(self.controls_frame, text="<< Previous", width=100, command=self.prev_page, state="disabled")
        self.btn_prev.pack(side="left")
        
        self.lbl_page = ctk.CTkLabel(self.controls_frame, text="Page 0 of 0", text_color="gray")
        self.lbl_page.pack(side="left", padx=20, expand=True)

        self.btn_next = ctk.CTkButton(self.controls_frame, text="Next >>", width=100, command=self.next_page, state="disabled")
        self.btn_next.pack(side="right")

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
        
        self.current_page = 0
        self.selected_urls.clear()
        self.update_preview_page()

    def update_preview_page(self):
        # Clear existing
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        if not self.current_media:
            return

        total_pages = math.ceil(len(self.current_media) / self.items_per_page)
        
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.current_media[start_idx:end_idx]

        # Update controls
        self.lbl_page.configure(text=f"Page {self.current_page + 1} of {total_pages}")
        self.btn_prev.configure(state="normal" if self.current_page > 0 else "disabled")
        self.btn_next.configure(state="normal" if end_idx < len(self.current_media) else "disabled")

        if not page_items:
            ctk.CTkLabel(self.preview_frame, text="No media to display.").pack(pady=20)
            return

        # Load thumbnails
        threading.Thread(target=self.load_thumbnails, args=(page_items,), daemon=True).start()

    def load_thumbnails(self, items):
        for index, url in enumerate(items):
            try:
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
                
                # Pass to UI
                self.after(0, lambda u=url, i=ctk_image, n=index: self.add_preview_item(u, i, n))
                
                # Delay to prevent 429
                time.sleep(0.3)

            except Exception as e:
                # print(f"Failed to load thumb for {url}: {e}")
                self.after(0, lambda u=url, n=index: self.add_preview_item(u, None, n))

    def add_preview_item(self, url, ctk_img, index):
        if index == -1: return # Error case

        row = index // 5
        col = index % 5

        # Card Frame
        frame = ctk.CTkFrame(self.preview_frame, fg_color=("gray85", "gray20"))
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # Image
        if ctk_img:
            lbl_img = ctk.CTkLabel(frame, text="", image=ctk_img)
            lbl_img.pack(padx=5, pady=5)
        else:
            lbl_img = ctk.CTkLabel(frame, text="No Preview", width=100, height=100)
            lbl_img.pack(padx=5, pady=5)

        # Truncated Filename
        filename = url.split('/')[-1]
        display_name = (filename[:15] + '..') if len(filename) > 15 else filename
        ctk.CTkLabel(frame, text=display_name, font=ctk.CTkFont(size=11)).pack()

        # Checkbox
        var_select = ctk.BooleanVar(value=url in self.selected_urls)
        chk = ctk.CTkCheckBox(frame, text="Select", variable=var_select, width=60, height=20,
                              command=lambda u=url, v=var_select: self.toggle_selection(u, v))
        chk.pack(pady=2)

        # Download Button
        btn_dl = ctk.CTkButton(frame, text="Download", height=20, width=80, font=("Arial", 10),
                               command=lambda u=url: self.download_single_wrapper(u))
        btn_dl.pack(pady=(2, 5))

    def toggle_selection(self, url, var):
        if var.get():
            self.selected_urls.add(url)
        else:
            self.selected_urls.discard(url)

    def select_all(self):
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        items = self.current_media[start_idx:end_idx]
        for url in items:
            self.selected_urls.add(url)
        self.update_preview_page() # Refresh UI to show checked

    def select_none(self):
        self.selected_urls.clear()
        self.update_preview_page()

    def download_selected(self):
        if not self.selected_urls:
            messagebox.showinfo("Info", "No files selected.")
            return
        
        urls = list(self.selected_urls)
        threading.Thread(target=self.download_bulk, args=(urls,), daemon=True).start()

    def download_single_wrapper(self, url):
         messagebox.showinfo("Download", f"Starting download...")
         threading.Thread(target=self.download_with_retry, args=(url,), daemon=True).start()

    def download_bulk(self, urls):
        # Notify start
        self.after(0, lambda: messagebox.showinfo("Download", f"Starting background download of {len(urls)} files."))
        
        success_count = 0
        for url in urls:
            if self.download_with_retry(url):
                success_count += 1
            # Add delay between bulk downloads to avoid 429
            time.sleep(1.5)
        
        self.after(0, lambda c=success_count: messagebox.showinfo("Completed", f"Downloaded {c} files."))

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

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_preview_page()

    def next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.current_media):
            self.current_page += 1
            self.update_preview_page()

if __name__ == "__main__":
    app = ChanMediaScanner()
    app.mainloop()
