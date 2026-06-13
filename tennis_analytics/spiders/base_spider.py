import scrapy
from datetime import datetime
import re

class BaseTennisSpider(scrapy.Spider):
    # Diese Klasse hat keinen 'name'; Scrapy ignoriert sie beim Crawlen

    # --- SICHERHEITS-KONFIGURATION ---
    # Diese Einstellungen dienen der Tarnung und Server-Schonung, um Sperren zu vermeiden
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,   # Limitiert gleichzeitige Anfragen auf 8 (Standard ist 16)
        'DOWNLOAD_DELAY': 0.5,      # Erzwingt eine Pause von 0,5 Sekunden zwischen einzelnen Anfragen (Simulation menschlichen Klickens)
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    # --- MARKEN-KONFIGURATION ---
    # Diese Marken werden einheitlich für alle Shops untersucht
    allowed_brands = {
        'rackets': ['dunlop', 'head', 'wilson', 'yonex'],
        'shoes': ['head', 'k-swiss', 'wilson'],
        'strings': ['luxilon', 'solinco', 'head', 'wilson', 'yonex']
    }

    # --- SPEZIFIKATIONS-KONFIGURATION ---
    # Diese Kriterien werden einheitlich für alle Shops untersucht

    # Produkt-Filter: Bestimmen, ob das gesamte Produkt relevant ist (Abbruch bei Nicht-Treffer)
    required_racket_keyword = 'unbesaitet'
    required_string_keywords = ['200m', '200 m']

    # Varianten-Filter: Definieren die exakten Kontrollgrößen, die als separate Zeilen extrahiert werden
    target_racket_grip_sizes = ['L2', 'L3']
    target_women_shoe_sizes_eu = ['EU 39']
    target_men_shoe_sizes_eu = ['EU 43']
    target_string_thicknesses = ['1.25 mm']

    def parse_price(self, price_string):
        '''
        Reinigt Preis-Strings und wandelt sie im DE- und US-Format sicher
        in einen Float (nur Dezimalpunkt zulässig) um.
        '''
        if not price_string:
            return None
        
        # Säubern von Währungszeichen und Leerzeichen
        temp_price = re.sub(r'[^\d.,]', '', price_string.strip())
        
        if not temp_price:
            return None

        # Es existieren Punkt und Komma (z.B. 1.250,00 oder 1,250.00)
        if '.' in temp_price and ',' in temp_price:
            # Überprüfen, welches Zeichen weiter hinten im String steht
            if temp_price.rfind('.') > temp_price.rfind(','):
                # Der Punkt ist weiter hinten -> US-Format (z.B. 1,250.00)
                temp_price = temp_price.replace(',', '')
            else:
                # Das Komma ist weiter hinten -> DE-Format (z.B. 1.250,00)
                temp_price = temp_price.replace('.', '').replace(',', '.')
        
        # Es existiert nur ein Komma (z.B. 125,00 oder 1250,00)
        elif ',' in temp_price:
            temp_price = temp_price.replace(',', '.')
            
        # Es existiert nur ein Punkt (z.B. 125.00 oder 1250.00)
        elif '.' in temp_price:
            pass         

        # Versucht die Umwandlung in Float; Verhindert Scraper-Abstürze bei ungültigen Preisdaten
        try:
            return float(temp_price)                         
        except ValueError:
            return None
        
    def get_timestamp(self):
        '''
        Erstellt einen einheitlichen Zeitstempel für die Zeitreihenanalyse.
        '''
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')