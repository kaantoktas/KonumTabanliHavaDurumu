import requests
import json
import time 
from config import OPENWEATHER_API_KEY, OPENWEATHER_BASE_URL, OPENWEATHER_GEOCODING_URL, API_LANG, API_UNITS

class WeatherAPI:
    def __init__(self, api_key=OPENWEATHER_API_KEY, base_url=OPENWEATHER_BASE_URL, geocoding_url=OPENWEATHER_GEOCODING_URL, lang=API_LANG, units=API_UNITS):
        self.api_key = api_key
        self.base_url = base_url
        self.geocoding_url = geocoding_url
        self.lang = lang
        self.units = units

    def _fetch_data_with_retry(self, url, params=None, max_retries=5, initial_delay=1):
        """
        Bir URL'den veriyi başarısızlık durumunda üstel geri çekilme ile çeker.
        """
        if params is None:
            params = {}
        params['appid'] = self.api_key
        
        for i in range(max_retries):
            try:
                response = requests.get(url, params=params)
                response.raise_for_status() 
                return response.json()
            except requests.exceptions.RequestException as e:
                if i < max_retries - 1:
                    delay = initial_delay * (2 ** i)
                    print(f"Hava durumu isteği başarısız oldu ({e}). {delay} saniye sonra tekrar deniyorum...")
                    time.sleep(delay)
                else:
                    print(f"Maksimum deneme sayısı aşıldı. Hava durumu isteği başarısız oldu: {e}")
                    return None

    def get_coordinates(self, city_name):
        """
        Şehir adından enlem ve boylam koordinatlarını alır.
        """
        url = f"{self.geocoding_url}/direct"
        params = {
            "q": city_name,
            "limit": 1 
        }
        data = self._fetch_data_with_retry(url, params)
        
        if data and len(data) > 0:
            return data[0]['lat'], data[0]['lon'], data[0].get('name'), data[0].get('country')
        return None, None, None, None

    def get_weather_data(self, lat, lon):
        """
        Verilen enlem ve boylam için güncel hava durumu ve tahmini (saatlik/günlük) verilerini çeker.
        """
        url = f"{self.base_url}/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,alerts", 
            "units": self.units,         
            "lang": self.lang           
        }
        data = self._fetch_data_with_retry(url, params)
        return data

    def get_weather_by_city(self, city_name):
        """
        Şehir adına göre tüm hava durumu verilerini (koordinatlar, güncel, saatlik, günlük) alır.
        """
        lat, lon, name, country = self.get_coordinates(city_name)
        if lat is None or lon is None:
            return None, "Geçersiz şehir adı veya koordinatlar bulunamadı."
        
        weather_data = self.get_weather_data(lat, lon)
        if weather_data is None:
            return None, "Hava durumu verileri çekilemedi."
        
        return weather_data, None 

if __name__ == "__main__":
    api = WeatherAPI()
    
    test_city = "Ankara"
    print(f"'{test_city}' için hava durumu verileri çekiliyor...")
    weather_data, error_message = api.get_weather_by_city(test_city)

    if weather_data:
        print("\n--- Güncel Hava Durumu ---")
        current = weather_data['current']
        print(f"Sıcaklık: {current['temp']}°C (Hissedilen: {current['feels_like']}°C)")
        print(f"Durum: {current['weather'][0]['description'].capitalize()}")
        print(f"Nem: {current['humidity']}%")
        print(f"Rüzgar Hızı: {current['wind_speed']} m/s")
        print(f"Basınç: {current['pressure']} hPa")
        print(f"UV İndeksi: {current['uvi']}")

        print("\n--- Saatlik Tahmin (İlk 3 saat) ---")
        for i, hourly in enumerate(weather_data['hourly'][:3]):
            print(f"Saat: {time.strftime('%H:%M', time.gmtime(hourly['dt'] + weather_data['timezone_offset']))}, Sıcaklık: {hourly['temp']}°C, Durum: {hourly['weather'][0]['description'].capitalize()}")

        print("\n--- Günlük Tahmin (İlk 3 gün) ---")
        for i, daily in enumerate(weather_data['daily'][:3]):
            print(f"Gün: {time.strftime('%Y-%m-%d', time.gmtime(daily['dt'] + weather_data['timezone_offset']))}, Min: {daily['temp']['min']}°C, Max: {daily['temp']['max']}°C, Durum: {daily['weather'][0]['description'].capitalize()}")
    else:
        print(f"Hata: {error_message}")

    test_city_invalid = "GeçersizŞehirAdıBurada"
    print(f"\n'{test_city_invalid}' için hava durumu verileri çekiliyor...")
    weather_data, error_message = api.get_weather_by_city(test_city_invalid)
    if weather_data:
        print("Hata: Geçersiz şehir adı için veri geldi (bu olmamalıydı).")
    else:
        print(f"Beklenen Hata: {error_message}")
