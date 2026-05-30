import scrapy
from datetime import datetime
import re

class BaseTennisSpider(scrapy.Spider):
    # Diese Klasse hat keinen 'name'; Scrapy ignoriert sie beim Crawlen

    # --- SICHERHEITS-KONFIGURATION ---
    # Diese Einstellungen dienen der Tarnung und Server-Schonung, um Sperren zu vermeiden
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,   # Limitiert gleichzeitige Anfragen auf 2 (Standard ist 16)
        'DOWNLOAD_DELAY': 1.5,      # Erzwingt eine Pause von 1,5 Sekunden zwischen einzelnen Anfragen (Simulation menschlichen Klickens)
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
    required_racket_keyword = 'unbesaitet'
    required_string_keywords = ['200m', '200 m']

    def parse_price(self, price_string):
        """Reinigt Preis-Strings und wandelt sie in einen Float um."""
        if not price_string:
            return None
        
        temp_price = price_string.replace('.', '')              # Entfernt Tausender-Punkte (z.B. 1.299,00 -> 1299,00)
        temp_price = re.sub(r'[^\d,]', '', temp_price)          # Entfernt alles außer Zahlen und dem Dezimal-Komma
        cleaned_price = temp_price.replace(',', '.')            # Ersetzt deutsches Komma durch Punkt für Python-Float

        try:
            return float(cleaned_price)                         # Versucht die Umwandlung in Float; verhindert Scraper-Abstürze bei ungültigen Preisdaten
        except ValueError:
            return None
        
    def get_timestamp(self):
        """Erstellt einen einheitlichen Zeitstempel für die Zeitreihenanalyse."""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    #def get_user_agent(self):
    #    """Gibt einen festen User-Agent zurück, damit der Scraper als regulärer Browser erkannt wird."""
    #    # HINWEIS: Spätere Rotation bei Bedarf hier ergänzen
    #    return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

