import scrapy


class TennisItem(scrapy.Item):
    # --- Basis-Informationen ---
    name = scrapy.Field()               # Vollständiger Produkt-Name
    brand = scrapy.Field()              # Marke des Produkts
    category = scrapy.Field()           # Kategorie ('rackets', 'shoes', 'strings')
    gender = scrapy.Field()             # Damen, Herren, Unisex
    reference_variant = scrapy.Field()  # L2/L3, 39/43, 1.25 mm

    # --- Identifikator ---
    ean = scrapy.Field()                # Europäische Artikelnummer

    # --- Preis-Daten ---
    current_price = scrapy.Field()      # Der aktuell angezeigte Preis
    regular_price = scrapy.Field()      # gestrichener Preis
    msrp_price = scrapy.Field()         # UVP
    currency = scrapy.Field()           # Währung

    # --- Verfügbarkeit ---
    availability = scrapy.Field()       # Lagerstatus ('in_stock', 'out_of_stock')

    # --- Metadaten ---
    retailer = scrapy.Field()           # Daten-Herkunft ('Tennis-Point', 'Tennistown', 'Tennis-Heine')
    url = scrapy.Field()                # Link zum Produkt zur Validierung
    timestamp = scrapy.Field()          # Exakter Zeitpunkt des Crawls
