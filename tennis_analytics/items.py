import scrapy


class TennisItem(scrapy.Item):
    # --- METADATEN ---
    retailer = scrapy.Field()           # Daten-Herkunft ('Tennis-Point', 'Tennistown', 'Tennis-Heine')
    timestamp = scrapy.Field()          # Exakter Zeitpunkt des Crawls

    # --- BASIS-INFORMATIONEN ---
    category = scrapy.Field()           # Kategorie ('rackets', 'shoes', 'strings')
    gender = scrapy.Field()             # Damen, Herren, Unisex
    brand = scrapy.Field()              # Marke des Produkts
    name = scrapy.Field()               # Vollständiger Produkt-Name
    reference_variant = scrapy.Field()  # L2/L3, 39/43, 1.25 mm

    # --- IDENTIFIKATOR ---
    ean = scrapy.Field()                # Europäische Artikelnummer

    # --- PREIS-DATEN ---
    current_price = scrapy.Field()      # Der aktuell angezeigte Preis
    regular_price = scrapy.Field()      # gestrichener Preis
    msrp_price = scrapy.Field()         # UVP
    currency = scrapy.Field()           # Währung

    # --- VERFÜGBARKEIT ---
    availability = scrapy.Field()       # Lagerstatus ('in_stock', 'out_of_stock')

    # --- QUELLENNACHWEIS --- 
    url = scrapy.Field()                # Link zum Produkt zur Validierung