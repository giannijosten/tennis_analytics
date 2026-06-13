import scrapy
import json
import re
from tennis_analytics.spiders.base_spider import BaseTennisSpider
from tennis_analytics.items import TennisItem

class TennisPointSpider(BaseTennisSpider):

    name = 'tennis_point'
    allowed_domains = ['tennis-point.de']

    # --- SICHERHEITS-KONFIGURATION (Shop-spezifisch) ---
    # Diese Einstellungen dienen der Tarnung und Server-Schonung, um Sperren zu vermeiden
    # Extrem defensive Einstellungen, um Anti-Bot-Systeme zu umgehen
    custom_settings = {
        'CONCURRENT_REQUESTS': 1,           # Limitiert gleichzeitige Anfragen auf 1
        'DOWNLOAD_DELAY': 5.5,                # Erzwingt eine Pause von 5 Sekunden zwischen einzelnen Anfragen
        'RANDOMIZE_DOWNLOAD_DELAY': True,   # Variiert die Pause zufällig (0.5x bis 1.5x), um menschliches Surfen zu simulieren
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'COOKIES_ENABLED': True            # Erlaubt Session-Cookies für authentischere Browser-Identifikation
    }

    def start_requests(self):
        '''
        1. SCHRITT: Initialisierung der Crawl-Requests.
        Definiert die Einstiegs-URLs für alle Zielkategorien und verankert 
        Kategorie sowie Geschlecht als feste Metadaten in der Request-Pipeline.
        '''
        urls = [
            {
                # Tennis-Point erlaubt das Filtern unbesaiteter Schläger direkt per URL-Parameter
                # Dadurch werden hunderte irrelevante Produktseiten gar nicht erst angefragt (Reduktion des Traffics zur Minimierung des Sperren-Risikos)
                'url': 'https://www.tennis-point.de/collections/tennisschlaeger?filter.v.m.rackets.type_100010=unbesaitet_100011',
                'category': 'rackets',
                'gender': 'unisex'
            },
            {
                'url': 'https://www.tennis-point.de/collections/tennisschuhe-damen',
                'category': 'shoes',
                'gender': 'women'
            },
            {
                'url': 'https://www.tennis-point.de/collections/tennisschuhe-herren',
                'category': 'shoes',
                'gender': 'men'
            },
            {
                'url': 'https://www.tennis-point.de/collections/tennissaiten-saitenrollen',
                'category': 'strings',
                'gender': 'unisex'
            }
        ]

        for entry in urls:
            # Produktübersicht aufrufen und Kategorie sowie Geschlecht mit Metadaten an 'parse' übergeben
            yield scrapy.Request(
                url=entry['url'],
                callback=self.parse,
                meta={'category': entry['category'], 'gender': entry['gender']}
            )

    def parse(self, response):
        '''
        2. SCHRITT: Verarbeitung der Produktübersichten.
        Extrahiert die Produktlinks der aktuellen Übersicht und steuert das 
        automatische Umblättern über die Folgeseiten.
        '''
        self.logger.info(f'Produktübersicht geladen: {response.url}')

        # --- INITIALISIERUNG DER METADATEN ---
        category = response.meta.get('category')
        gender = response.meta.get('gender')

        # --- EXTRAKTION DER PRODUKT-LINKS ---
        # Alle Produkt-Links auf der aktuellen Seite einsammeln
        product_links = response.css('#product-grid .tp-product-card__information > h3 > a.full-unstyled-link::attr(href)').getall()

        for link in product_links:
            # Relative URLs in absolute URLs umwandeln
            full_url = response.urljoin(link)
            
            # Produktseite aufrufen und Kategorie sowie Geschlecht mit Metadaten an 'parse_product' übergeben
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_product,
                meta={'category': category, 'gender': gender}
            )

        # --- PAGINATION (SEITENWECHSEL) ---
        # Link für den 'Weiter'-Button extrahieren
        next_page_link = response.css('a.tp-pagination__item--next::attr(href)').get()

        if next_page_link:
            full_next_page_url = response.urljoin(next_page_link)

            self.logger.info(f'Nächste Produktübersichtsseite gefunden, blättere um: {full_next_page_url}')

            # Produktübersicht rekursiv aufrufen und Kategorie sowie Geschlecht für die Folgenseiten beibehalten
            yield scrapy.Request(
                url=full_next_page_url,
                callback=self.parse,
                meta={'category': category, 'gender': gender}
            )

    def parse_product(self, response):
        '''
        3. SCHRITT: Extraktion der Produktdetails und Metadaten-Analyse.
        Liest Namen, Marke sowie reguläre Preise direkt aus dem HTML-Frontend aus, 
        filtert nach Spezifikation und extrahiert den ld+json-Datenblock. Führt 
        einen systematischen Abgleich der Kontrollvarianten durch, um EANs/GTINs
        sowie aktuelle Preise und Verfügbarkeiten aus den Metadaten zu isolieren.
        '''
        self.logger.info(f'Produktseite geladen: {response.url}')

        # --- EXTRAKTION DER BASIS-DATEN ---
        category = response.meta.get('category')
        gender = response.meta.get('gender', 'unisex')  # Standardwert 'unisex', falls nichts übergeben wurde

        # Brandnamen auslesen
        brand_raw = response.css('.product__info-wrapper p.product__text::text').get()

        # Produktnamen auslesen und bereinigen
        name = response.css('.product__title h1::text').get()
        if name:
            name = name.strip()

        # Produktname für die Filter-Logiken in Kleinbuchstaben umwandeln
        name_lower = name.lower() if name else ''

        # --- MARKEN-FILTERUNG ---
        brand = None
        allowed_brands = self.allowed_brands.get(category, [])

        # Brandnamen normalisieren
        brand_lower = brand_raw.lower().strip() if brand_raw else ''
        if 'kswiss' in brand_lower:
            brand_lower = brand_lower.replace('kswiss', 'k-swiss')

        # Überprüfen, ob die ausgelesene Marke zur Kontrollgruppe gehört
        for allowed_brand in allowed_brands:
            if allowed_brand in brand_lower:
                # Markennamen mit großen Anfangsbuchstaben speichern
                brand = allowed_brand.capitalize()

                # Sonderfall-Korrektur für die Schreibweise von K-Swiss
                if brand == 'K-swiss':
                    brand = 'K-Swiss'
                break

        # Produkt ignorieren, falls keine Marke der Kontrollgruppe matcht
        if not brand:
            self.logger.info(f'Produkt ignoriert (falsche Marke): {name}')
            return

        # --- BESAITUNGS-FILTERUNG (Nur für Schläger) ---
        # In der Kategorie 'rackets' werden ausschließlich unbesaitete Schläger erfasst
        if category == 'rackets':
            is_unbesaitet = False
            
            # Alle Feature-Items auf der Seite einsammeln
            feature_items = response.css('.tp-product-features__item')
            
            for item in feature_items:
                # Eintragsname und Ausprägung extrahieren
                title = item.css('.tp-product-features__item-title::text').get()
                description = item.css('.tp-product-features__item-description::text').get()
                
                # Suche nach Eintrag 'Schlägertyp' mit Ausprägung 'unbesaitet'
                if title and 'schlägertyp' in title.lower():
                    if description and self.required_racket_keyword in description.lower():
                        is_unbesaitet = True
                    break
            
            if not is_unbesaitet:
                self.logger.info(f'Produkt ignoriert (Schläger ist nicht unbesaitet): {name}')
                return

        # --- SAITENLÄNGEN-FILTERUNG (Nur für Saiten) ---
        # In der Kategorie 'strings' werden ausschließlich 200 Meter Saitenrollen erfasst
        if category == 'strings':
            # Überprüfung, ob keines der erlaubten Längen-Keywords im Namen vorkommt
            if not name or all(keyword not in name_lower for keyword in self.required_string_keywords):
                self.logger.info(f'Produkt ignoriert (Saitenlänge ist nicht korrekt): {name}')
                return

        # --- PREIS-EXTRAKTION UND BEREINIGUNG ---
        # Aktueller Preis wird über ld+json-Metadaten ausgelesen
        # Regulären Preis auslesen (variantenunabhängiger Wert) und bereinigen
        regular_price_raw = response.css('.product__info-wrapper span.tp-price-item--compare s::text').get()
        regular_price = self.parse_price(regular_price_raw)

        # Tennis-Point führt keinen separaten UVP-Listenpreis
        msrp_price = None

        # --- LD+JSON METADATEN-EXTRAKTION ---
        try:
            # Extrahieren des fünften Metadatenblocks aus dem HTML-Quelltext
            json_text_raw = response.css('script[type="application/ld+json"]::text').getall()[4]

            # Entfernt unzulässige, harte Steuerzeichen und Zeilenumbrüche aus dem Roh-JSON
            json_text = re.sub(r'[\x00-\x1F\x7F]', ' ', json_text_raw)
            product_data = json.loads(json_text)
        except (IndexError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f'Fehler beim Parsen des ld+json-Blocks auf {response.url}: {e}')
            return

        # --- ABGLEICH DER KONTROLLVARIANTEN MIT DEN SHOP-VARIANTEN ---
        # Festlegen der erwarteten Kontrollvarianten pro Kategorie und Geschlecht
        target_variants = []

        if category == 'rackets':
            target_variants = self.target_racket_grip_sizes
        elif category == 'shoes':
            if gender == 'women':
                target_variants = self.target_women_shoe_sizes_eu
            elif gender == 'men':
                target_variants = self.target_men_shoe_sizes_eu
        elif category == 'strings':
            target_variants = self.target_string_thicknesses
        else:
            self.logger.info(f'Unbekannte Kategorie: {category}')
            return

        # Extraktion der Varianten aus dem Metadatenblock
        found_variants = product_data.get('hasVariant', [])

        # Iteration über alle erwarteten Kontrollvarianten zur Extraktion der spezifischen Werte
        for target_variant in target_variants:
            # Abgleich der passenden Variante innerhalb des ld+json-Blocks
            variant_match = None

            for found_variant in found_variants:
                # Variantennamen auslesen und für den sicheren Abgleich normalisieren
                variant_name_raw = found_variant.get('name', '')
                variant_name_lower = variant_name_raw.lower() if variant_name_raw else ''
                
                # Kategorienabhängige Normalisierung und Zuordnung der Kontrollvariante zur passenden Shop-Variante
                if category == 'rackets':
                    # Extrahiert die reine Zahl der Griffgröße aus bspw. 'L2' -> '2'
                    grip_size_number = target_variant.replace('L', '')
                    # Überprüfen auf gesuchte Griffgröße am Namensende
                    if variant_name_lower.endswith(f' {grip_size_number}'):
                        variant_match = found_variant
                        break
                        
                elif category == 'shoes':
                    # Extrahiert die reine Zahl der Schuhgröße aus bspw. 'EU 43' -> '43'
                    shoe_size_number = target_variant.replace('EU ', '')
                    # Ersetzt ggf. Dezimalpunkt durch ein Komma für deutsches Format
                    shoe_size_number_normalized = shoe_size_number.replace('.', ',')
                    # Überprüfen auf gesuchte Schuhgröße am Namensende
                    if variant_name_lower.endswith(f' {shoe_size_number_normalized}'):
                        variant_match = found_variant
                        break
                        
                elif category == 'strings':
                    # Extrahiert die reine Zahl der Saitendicke aus '1.25 mm' -> '1.25'
                    string_thickness_number = target_variant.replace(' mm', '')
                    # Ersetzt den Dezimalpunkt durch ein Komma für deutsches Format
                    string_thickness_normalized = string_thickness_number.replace('.', ',')
                    # Überprüfen auf gesuchte Saitendicke am Namensende
                    if variant_name_lower.endswith(f' {string_thickness_normalized}'):
                        variant_match = found_variant
                        break

            # --- EXTRAKTION DER EAN/GTIN, DES AKTUELLEN PREISES UND DER VERFÜGBARKEIT ---
            if variant_match:
                # Objektdaten auslesen
                offer = variant_match.get('offers', {})

                # EAN/GTIN extrahieren
                ean = variant_match.get('gtin')
                if ean:
                    ean = str(ean).strip()

                # Aktuellen Preis auslesen und bereinigen
                current_price_raw = str(offer.get('price'))
                current_price = self.parse_price(current_price_raw)

                # Verfügbarkeit bestimmen
                availability_raw = offer.get('availability', '')
                if 'InStock' in availability_raw:
                    availability = 'in_stock'
                else:
                    availability = 'out_of_stock'

                # --- ITEM-GENERIERUNG (Nur wenn ein Match existiert) --- 
                # Das finale Daten-Item für diese Kontrollvariante generieren
                item = TennisItem(
                    retailer='Tennis-Point',
                    timestamp=self.get_timestamp(),
                    category=category,
                    gender=gender,
                    brand=brand,
                    name=name,
                    reference_variant=target_variant,
                    ean=ean,
                    current_price=current_price,
                    regular_price=regular_price,
                    msrp_price=msrp_price,
                    currency='€',
                    availability=availability,
                    url=response.url
                )

                self.logger.info(f'Erfolgreich erfasst ({target_variant} - {availability}): {name}')
                yield item
        