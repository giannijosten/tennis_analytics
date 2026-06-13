BOT_NAME = "tennis_analytics"

SPIDER_MODULES = ["tennis_analytics.spiders"]
NEWSPIDER_MODULE = "tennis_analytics.spiders"

# Händlerfreundliches Crawling-Verhalten
ROBOTSTXT_OBEY = True

# Abwärtskompatibilität und Systemarchitektur
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# --- EXPORT-KONFIGURATION ---
# Garantiert eine einheitliche und logische Spaltenreihenfolge für alle CSV-Exporte
FEED_EXPORT_FIELDS = [
    'retailer',
    'timestamp',
    'category',
    'gender',
    'brand',
    'name',
    'reference_variant',
    'ean',
    'current_price',
    'regular_price',
    'msrp_price',
    'currency',
    'availability',
    'url'
]