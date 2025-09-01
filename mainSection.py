# mainSection.py

import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk 
import os
import threading 
import time
import datetime
import pytz 

from konumBazli import WeatherAPI
from config import WEATHER_ICONS_DIR, DEFAULT_CITY, API_UNITS

class WeatherApp:
    def __init__(self, master):
        self.master = master
        master.title("Amistad Hava Durumu Uygulaması")
        master.geometry("1000x750") 
        master.resizable(False, False) 

        self.api = WeatherAPI() 
        self.current_city = tk.StringVar(value=DEFAULT_CITY)
        self.temp_unit = tk.StringVar(value=API_UNITS) 

        # Uygulama kapatıldığında çağrılacak protokolü ayarla
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.stop_threads = False # Thread'lerin durması için bayrak

        self._create_widgets() 
        self.fetch_weather_for_city(DEFAULT_CITY) 

    def _create_widgets(self):
        search_frame = tk.Frame(self.master, padx=10, pady=10)
        search_frame.pack(pady=10, fill="x")

        tk.Label(search_frame, text="Şehir Adı:").pack(side="left", padx=5)
        self.city_entry = tk.Entry(search_frame, textvariable=self.current_city, width=40)
        self.city_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.city_entry.bind("<Return>", self.on_search_button_click) 

        search_button = tk.Button(search_frame, text="Hava Durumunu Getir", command=self.on_search_button_click)
        search_button.pack(side="left", padx=5)

        self.celsius_radio = tk.Radiobutton(search_frame, text="°C", variable=self.temp_unit, value="metric", command=self._on_unit_change)
        self.celsius_radio.pack(side="left", padx=5)
        self.fahrenheit_radio = tk.Radiobutton(search_frame, text="°F", variable=self.temp_unit, value="imperial", command=self._on_unit_change)
        self.fahrenheit_radio.pack(side="left", padx=5)

        self.loading_label = tk.Label(self.master, text="Yükleniyor...", fg="blue")
        self.loading_label.pack(pady=5)
        self.loading_label.pack_forget() 

        main_weather_frame = tk.LabelFrame(self.master, text="Güncel Hava Durumu", padx=15, pady=15)
        main_weather_frame.pack(pady=10, padx=10, fill="x")

        self.city_display_label = tk.Label(main_weather_frame, text="Şehir: Yükleniyor...", font=("Helvetica", 20, "bold"))
        self.city_display_label.pack(pady=5)

        self.time_display_label = tk.Label(main_weather_frame, text="Yerel Saat: Yükleniyor...", font=("Helvetica", 12))
        self.time_display_label.pack(pady=2)

        self.temp_label = tk.Label(main_weather_frame, text="Sıcaklık: --°C", font=("Helvetica", 36, "bold"), fg="darkblue")
        self.temp_label.pack(pady=10)
        
        self.feels_like_label = tk.Label(main_weather_frame, text="Hissedilen: --°C", font=("Helvetica", 14))
        self.feels_like_label.pack(pady=2)

        self.description_label = tk.Label(main_weather_frame, text="Durum: ---", font=("Helvetica", 16))
        self.description_label.pack(pady=5)

        self.weather_icon_label = tk.Label(main_weather_frame)
        self.weather_icon_label.pack(pady=5)

        details_frame = tk.Frame(main_weather_frame)
        details_frame.pack(pady=10)

        self.humidity_label = tk.Label(details_frame, text="Nem: --%", font=("Helvetica", 12))
        self.humidity_label.grid(row=0, column=0, padx=10, pady=5)
        self.wind_label = tk.Label(details_frame, text="Rüzgar: -- m/s", font=("Helvetica", 12))
        self.wind_label.grid(row=0, column=1, padx=10, pady=5)
        self.pressure_label = tk.Label(details_frame, text="Basınç: -- hPa", font=("Helvetica", 12))
        self.pressure_label.grid(row=1, column=0, padx=10, pady=5)
        self.uvi_label = tk.Label(details_frame, text="UV İndeksi: --", font=("Helvetica", 12))
        self.uvi_label.grid(row=1, column=1, padx=10, pady=5)

        self.forecast_notebook = ttk.Notebook(self.master)
        self.forecast_notebook.pack(pady=10, padx=10, fill="both", expand=True)

        self.hourly_frame = tk.Frame(self.forecast_notebook)
        self.forecast_notebook.add(self.hourly_frame, text="Saatlik Tahmin")
        self.hourly_canvas = tk.Canvas(self.hourly_frame)
        self.hourly_canvas.pack(side="left", fill="both", expand=True)
        self.hourly_scrollbar = tk.Scrollbar(self.hourly_frame, orient="horizontal", command=self.hourly_canvas.xview)
        self.hourly_scrollbar.pack(side="bottom", fill="x")
        self.hourly_canvas.configure(xscrollcommand=self.hourly_scrollbar.set)
        self.hourly_canvas.bind('<Configure>', lambda e: self.hourly_canvas.configure(scrollregion = self.hourly_canvas.bbox("all")))
        self.hourly_inner_frame = tk.Frame(self.hourly_canvas)
        self.hourly_canvas.create_window((0,0), window=self.hourly_inner_frame, anchor="nw")

        self.daily_frame = tk.Frame(self.forecast_notebook)
        self.forecast_notebook.add(self.daily_frame, text="Günlük Tahmin")
        self.daily_canvas = tk.Canvas(self.daily_frame)
        self.daily_canvas.pack(side="left", fill="both", expand=True)
        self.daily_scrollbar = tk.Scrollbar(self.daily_frame, orient="horizontal", command=self.daily_canvas.xview)
        self.daily_scrollbar.pack(side="bottom", fill="x")
        self.daily_canvas.configure(xscrollcommand=self.daily_scrollbar.set)
        self.daily_canvas.bind('<Configure>', lambda e: self.daily_canvas.configure(scrollregion = self.daily_canvas.bbox("all")))
        self.daily_inner_frame = tk.Frame(self.daily_canvas)
        self.daily_canvas.create_window((0,0), window=self.daily_inner_frame, anchor="nw")


    def _on_unit_change(self):
        self.api.units = self.temp_unit.get() 
        self.fetch_weather_for_city(self.current_city.get()) 

    def on_search_button_click(self, event=None):
        city = self.city_entry.get().strip()
        if city:
            self.fetch_weather_for_city(city)
        else:
            messagebox.showwarning("Uyarı", "Lütfen bir şehir adı girin.")

    def fetch_weather_for_city(self, city_name):
        self.loading_label.pack(pady=5) 
        self.update_main_weather_display(
            city="Yükleniyor...",
            description="---",
            temp="--",
            feels_like="--",
            humidity="--",
            wind_speed="--",
            pressure="--",
            uvi="--",
            icon_code=None,  
            dt_utc=None,     
            timezone_offset=0 
        )
        self.clear_forecast_display() 

        # API çağrısını ayrı bir thread'de yap
        # Eğer thread zaten çalışıyorsa yeni bir tane başlatma
        # Bu, daha önce olan RuntimeError'ı çözmeye yardımcı olacak bir yaklaşımdır.
        if not hasattr(self, '_fetch_thread') or not self._fetch_thread.is_alive():
            self._fetch_thread = threading.Thread(target=self._fetch_and_update_gui, args=(city_name,))
            self._fetch_thread.start()
        else:
            # Mevcut thread bitene kadar bekle veya kullanıcıya bilgi ver
            print("Zaten bir hava durumu isteği işleniyor. Lütfen bekleyin.")


    def _fetch_and_update_gui(self, city_name):
        """
        API'den verileri çeker ve GUI'yi günceller. Ayrı bir thread'de çalışır.
        """
        # Thread'in GUI kapatıldığında durabilmesi için kontrol
        if self.stop_threads:
            return

        weather_data, error_message = self.api.get_weather_by_city(city_name)

        # GUI güncellemelerini ana thread'de yapmak için after metodunu kullan
        # Eğer master yoksa (uygulama kapatıldıysa) hata vermemek için kontrol et
        if self.master.winfo_exists():
            self.master.after(0, self._update_gui_with_weather_data, weather_data, error_message, city_name)
        else:
            print("GUI penceresi kapatıldığı için güncellemeler atlandı.")


    def _update_gui_with_weather_data(self, weather_data, error_message, requested_city_name):
        """
        Çekilen hava durumu verileriyle GUI'yi günceller. Ana thread'de çalışır.
        """
        # GUI'nin hala var olduğunu kontrol et
        if not self.master.winfo_exists():
            return

        self.loading_label.pack_forget() 

        if weather_data:
            current = weather_data['current']
            hourly = weather_data['hourly']
            daily = weather_data['daily']
            timezone_offset = weather_data['timezone_offset']
            
            # API'den gelen veriye göre şehir adını güncelle
            # OpenWeatherMap'in geocoding API'si `name` ve `country` döndürüyor.
            # get_coordinates() metodu bu bilgileri döndürmeli.
            lat, lon, geo_name, geo_country = self.api.get_coordinates(requested_city_name)
            display_city_name = geo_name or requested_city_name
            if geo_country:
                 display_city_name = f"{display_city_name}, {geo_country}"

            self.update_main_weather_display(
                city=display_city_name,
                description=current['weather'][0]['description'].capitalize(),
                temp=current['temp'],
                feels_like=current['feels_like'],
                humidity=current['humidity'],
                wind_speed=current['wind_speed'],
                pressure=current['pressure'],
                uvi=current['uvi'],
                icon_code=current['weather'][0]['icon'],
                dt_utc=current['dt'],
                timezone_offset=timezone_offset
            )
            self.update_hourly_forecast(hourly, timezone_offset)
            self.update_daily_forecast(daily, timezone_offset)
            self.current_city.set(requested_city_name) 
        else:
            messagebox.showerror("Hata", f"Hava durumu verileri çekilemedi:\n{error_message}\nLütfen API anahtarınızın doğru ve aktif olduğundan emin olun.")
            self.update_main_weather_display(
                city=f"{requested_city_name} (Bulunamadı)",
                description="---",
                temp="--",
                feels_like="--",
                humidity="--",
                wind_speed="--",
                pressure="--",
                uvi="--",
                icon_code=None,
                dt_utc=None,
                timezone_offset=0
            )
            self.clear_forecast_display()

    def update_main_weather_display(self, city, description, temp, feels_like, humidity, wind_speed, pressure, uvi, icon_code, dt_utc, timezone_offset):
        temp_suffix = "°C" if self.temp_unit.get() == "metric" else "°F"
        wind_suffix = "m/s" if self.temp_unit.get() == "metric" else "mph"

        self.city_display_label.config(text=f"Şehir: {city}")
        self.temp_label.config(text=f"Sıcaklık: {temp}{temp_suffix}")
        self.feels_like_label.config(text=f"Hissedilen: {feels_like}{temp_suffix}")
        self.description_label.config(text=f"Durum: {description}")
        self.humidity_label.config(text=f"Nem: {humidity}%")
        self.wind_label.config(text=f"Rüzgar: {wind_speed} {wind_suffix}")
        self.pressure_label.config(text=f"Basınç: {pressure} hPa")
        self.uvi_label.config(text=f"UV İndeksi: {uvi}")

        if dt_utc is not None and timezone_offset is not None:
            local_time = datetime.datetime.fromtimestamp(dt_utc + timezone_offset, tz=pytz.utc)
            self.time_display_label.config(text=f"Yerel Saat: {local_time.strftime('%H:%M - %Y-%m-%d')}")
        else:
            self.time_display_label.config(text="Yerel Saat: ---")

        self._load_weather_icon(icon_code)

    def _load_weather_icon(self, icon_code):
        if icon_code:
            icon_path = os.path.join(WEATHER_ICONS_DIR, f"{icon_code}@2x.png") 
            try:
                img = Image.open(icon_path)
                img = img.resize((100, 100), Image.Resampling.LANCZOS) 
                self.weather_icon = ImageTk.PhotoImage(img) 
                self.weather_icon_label.config(image=self.weather_icon)
                self.weather_icon_label.image = self.weather_icon 
            except FileNotFoundError:
                print(f"Uyarı: İkon dosyası bulunamadı: {icon_path}")
                self.weather_icon_label.config(image='') 
            except Exception as e:
                print(f"İkon yüklenirken hata: {e}")
                self.weather_icon_label.config(image='') 
        else:
            self.weather_icon_label.config(image='') 

    def update_hourly_forecast(self, hourly_data, timezone_offset):
        for widget in self.hourly_inner_frame.winfo_children():
            widget.destroy() 

        for i, hour in enumerate(hourly_data[:24]): 
            frame = tk.Frame(self.hourly_inner_frame, bd=1, relief="solid", padx=5, pady=5)
            frame.grid(row=0, column=i, padx=5, pady=5)

            hour_time = datetime.datetime.fromtimestamp(hour['dt'] + timezone_offset, tz=pytz.utc)
            tk.Label(frame, text=hour_time.strftime("%H:%M"), font=("Helvetica", 10, "bold")).pack()
            
            icon_code = hour['weather'][0]['icon']
            icon_path = os.path.join(WEATHER_ICONS_DIR, f"{icon_code}@2x.png")
            try:
                img = Image.open(icon_path)
                img = img.resize((50, 50), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                icon_label = tk.Label(frame, image=photo_img)
                icon_label.image = photo_img 
                icon_label.pack()
            except FileNotFoundError:
                tk.Label(frame, text="İkon Yok").pack()

            temp_suffix = "°C" if self.temp_unit.get() == "metric" else "°F"
            tk.Label(frame, text=f"{hour['temp']}{temp_suffix}", font=("Helvetica", 10)).pack()
            tk.Label(frame, text=hour['weather'][0]['description'].capitalize(), font=("Helvetica", 9), wraplength=80).pack()

        self.hourly_inner_frame.update_idletasks()
        self.hourly_canvas.config(scrollregion=self.hourly_canvas.bbox("all"))


    def update_daily_forecast(self, daily_data, timezone_offset):
        for widget in self.daily_inner_frame.winfo_children():
            widget.destroy() 

        for i, day in enumerate(daily_data[1:8]): 
            frame = tk.Frame(self.daily_inner_frame, bd=1, relief="solid", padx=5, pady=5)
            frame.grid(row=0, column=i, padx=5, pady=5)

            day_time = datetime.datetime.fromtimestamp(day['dt'] + timezone_offset, tz=pytz.utc)
            tk.Label(frame, text=day_time.strftime("%A"), font=("Helvetica", 10, "bold")).pack() 

            icon_code = day['weather'][0]['icon']
            icon_path = os.path.join(WEATHER_ICONS_DIR, f"{icon_code}@2x.png")
            try:
                img = Image.open(icon_path)
                img = img.resize((50, 50), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                icon_label = tk.Label(frame, image=photo_img)
                icon_label.image = photo_img 
                icon_label.pack()
            except FileNotFoundError:
                tk.Label(frame, text="İkon Yok").pack()
            
            temp_suffix = "°C" if self.temp_unit.get() == "metric" else "°F"
            tk.Label(frame, text=f"Max: {day['temp']['max']}{temp_suffix}", font=("Helvetica", 10)).pack()
            tk.Label(frame, text=f"Min: {day['temp']['min']}{temp_suffix}", font=("Helvetica", 10)).pack()
            tk.Label(frame, text=day['weather'][0]['description'].capitalize(), font=("Helvetica", 9), wraplength=80).pack()
        
        self.daily_inner_frame.update_idletasks()
        self.daily_canvas.config(scrollregion=self.daily_canvas.bbox("all"))

    def clear_forecast_display(self):
        for widget in self.hourly_inner_frame.winfo_children():
            widget.destroy()
        for widget in self.daily_inner_frame.winfo_children():
            widget.destroy()

    def on_closing(self):
        """Uygulama kapatıldığında kaynakları temizler ve thread'leri durdurur."""
        if messagebox.askokcancel("Çıkış", "Uygulamadan çıkmak istediğinizden emin misiniz?"):
            self.stop_threads = True # Thread'lerin durması için bayrağı ayarla
            # _fetch_thread'in bitmesini beklemek isteyebilirsiniz, ancak bu GUI'yi dondurabilir.
            # Genellikle, Tkinter'da after() ile çağrılan fonksiyonlar ana thread'de çalıştığı için
            # GUI kapanırken thread'in çağrısının hata vermemesini sağlamak daha önemlidir.
            # self.master.destroy() çağrısı bekleyen after() çağrılarını iptal eder.
            self.master.destroy() 


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()

