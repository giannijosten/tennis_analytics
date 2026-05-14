# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TennisItem(scrapy.Item):
    # --- Basis-Informationen ---
    name = scrapy.Field()           # Vollständiger Produkt-Name
    brand = scrapy.Field()          # Marke des Produkts
    category = scrapy.Field()       # Schläger, Schuhe, Saite
    gender = scrapy.Field()         # Damen, Herren, Unisex
    reference_size = scrapy.Field() # L2/L3 (Schläger), 39/43 (Schuhe), 1.25 mm (Saiten)

    # --- Identifikatoren ---
    sku = scrapy.Field()            # Händlerspezifische Artikelnummer
    ean = scrapy.Field()            # Europäische Artikelnummer

    # --- Preis-Daten ---
    price_current = scrapy.Field()  # Der aktuell angezeigte Preis
    price_regular = scrapy.Field()  # UVP oder gestrichener Preis
    currency = scrapy.Field()       # Währung

    # --- Verfügbarkeit ---
    availability = scrapy.Field()   # "in_stock" oder "out_of_stock"
    stock_level = scrapy.Field()    # Der exakte Lagerbestand, falls verfügbar (z.B. 3)

    # --- Metadaten ---
    retailer = scrapy.Field()       # Daten-Herkunft (Tennis-Point, Tennistown, Tennis-Heine)
    url = scrapy.Field()            # Link zum Produkt zur Validierung
    timestamp = scrapy.Field()      # Exakter Zeitpunkt des Crawls
