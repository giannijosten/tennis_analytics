import scrapy
from tennis_analytics.spiders.base_spider import BaseTennisSpider
from tennis_analytics.items import TennisItem

class TennisHeineSpider(BaseTennisSpider):

    name = 'tennis_heine'
    allowed_domains = ['tennis-heine.de']

    # --- SPEZIFIKATIONS-KONFIGURATION (Shop-spezifisch) ---
    # Tennis-Heine deklariert unbesaitete Schläger nicht; Filterung stattdessen über den Ausschluss
    excluded_racket_keyword = 'besaitet'
    # Tennis-Heine deklariert Schuhe in UK-Größen
    target_women_shoe_sizes_uk = ['UK 6']
    target_men_shoe_sizes_uk = ['UK 9']

    def start_requests(self):
        '''
        1. SCHRITT: Initialisierung der Crawl-Requests.
        Definiert die Einstiegs-URLs für alle Zielkategorien und verankert 
        Kategorie sowie Geschlecht als feste Metadaten in der Request-Pipeline.
        '''
        urls = [
            {
                'url': 'https://www.tennis-heine.de/tennisschlaeger/?p=1',
                'category': 'rackets',
                'gender': 'unisex'
            },
            {
                'url': 'https://www.tennis-heine.de/tennisschuhe/?p=1&o=1&n=12&f=6',
                'category': 'shoes',
                'gender': 'women'
            },
            {
                'url': 'https://www.tennis-heine.de/tennisschuhe/?p=1&o=1&n=12&f=5',
                'category': 'shoes',
                'gender': 'men'
            },
            {
                'url': 'https://www.tennis-heine.de/zubehoer/saiten/?p=1',
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
        Nachladen weiterer Produkte durch die Erhöhung des Seitenparameters.
        '''
        self.logger.info(f'Produktübersicht geladen: {response.url}')

        # Kategorie und Geschlecht aus den übergebenen Metadaten extrahieren
        category = response.meta.get('category')
        gender = response.meta.get('gender')

        # Alle Produkt-Links auf der aktuellen Seite einsammeln
        product_links = response.css('a.product--title::attr(href)').getall()

        for link in product_links:
            # Relative URLs in absolute URLs umwandeln
            full_url = response.urljoin(link)
            
            # Produktseite aufrufen und Kategorie sowie Geschlecht mit Metadaten an 'parse_product' übergeben
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_product,
                meta={'category': category, 'gender': gender}
            )

        # Pagination im Shop über URL-Parameter 'p'; Inkrementierung bis keine Ergebnisse mehr vorhanden sind
        # Ungültige Seitenzahlen führen zu HTTP 404 und beenden den Crawl automatisch
        if product_links and '?p=' in response.url:
            # Extrahiert den Seitenparameter (Wert hinter '?p=' bis zum nächsten '&' oder zum URL-Ende)
            current_page_number = int(response.url.split('?p=')[-1].split('&')[0])
            next_page_number = current_page_number + 1

            # Ersetzt den Seitenparameter in der URL, restliche Query-Parameter bleiben erhalten
            current_page_param = f'?p={current_page_number}'
            next_page_param = f'?p={next_page_number}'
            full_next_page_url = response.url.replace(current_page_param, next_page_param)

            self.logger.info(f'Nächste Produktübersichtsseite generiert, rufe URL auf: {full_next_page_url}')

            # Produktübersicht rekursiv aufrufen und Kategorie sowie Geschlecht für die Folgenseiten beibehalten
            yield scrapy.Request(
                url=full_next_page_url,
                callback=self.parse,
                meta={'category': category, 'gender': gender}
            )

    def parse_product(self, response):
        '''
        3. SCHRITT: Extraktion der Produkt-Basisdaten.
        Liest Name, filtert nach Marke/Spezifikation und erzeugt für jede
        Zielvariante eine spezifische AJAX-Anfrage.
        '''
        self.logger.info(f'Produktseite geladen: {response.url}')

        # Kategorie und Geschlecht aus den übergebenen Metadaten extrahieren
        category = response.meta.get('category')
        gender = response.meta.get('gender', 'unisex')  # Standardwert 'unisex', falls nichts übergeben wurde

        # Name extrahieren
        name = response.css('h1.product--title::text').get()
        if name:
            name = name.strip()

        # --- MARKEN-FILTERUNG ---
        brand = None
        allowed_brands = self.allowed_brands.get(category, [])

        # Produktname in Kleinbuchstaben umwandeln
        name_lower = name.lower() if name else ''

        # Überprüfen, ob eine der zu untersuchenden Marken im Produktnamen vorkommt
        for allowed_brand in allowed_brands:
            if name and allowed_brand in name_lower:
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
            if not name or self.excluded_racket_keyword in name_lower:
                self.logger.info(f'Produkt ignoriert (Schläger ist nicht unbesaitet): {name}')
                return

        # --- SAITENLÄNGEN-FILTERUNG (Nur für Saiten)---
        # In der Kategorie 'strings' werden ausschließlich 200 Meter Saitenrollen erfasst
        if category == 'strings':
            # Überprüfung, ob keines der erlaubten Längen-Keywords im Namen vorkommt
            if not name or all(keyword not in name_lower for keyword in self.required_string_keywords):
                self.logger.info(f'Produkt ignoriert (Saitenlänge ist nicht korrekt): {name}')
                return

        # --- VARIANTEN-ERZEUGUNG MIT AJAX ---
        # Festlegen der standardmäßig erwarteten Zielvarianten pro Kategorie und Geschlecht
        target_variants = []
        shoe_size_mapping = {}

        if category == 'rackets':
            target_variants = self.target_racket_grip_sizes
        elif category == 'shoes':
            if gender == 'women':
                shoe_size_mapping = {size_uk: size_eu for size_uk, size_eu in zip(self.target_women_shoe_sizes_uk, self.target_women_shoe_sizes_eu)}
            elif gender == 'men':
                shoe_size_mapping = {size_uk: size_eu for size_uk, size_eu in zip(self.target_men_shoe_sizes_uk, self.target_men_shoe_sizes_eu)}
            # Zielvarianten entsprechen den UK-Keys des Mappings
            target_variants = list(shoe_size_mapping.keys())
        elif category == 'strings':
            target_variants = self.target_string_thicknesses
        else:
            self.logger.info(f'Unbekannte Kategorie: {category}')
            return

        # Alle Variantenoptionen (Radio-Buttons) auf der Produktseite ermitteln
        options = response.css('.variant--group .variant--option')

        for option in options:
            variant_text = option.css('label::text').get()
            if variant_text:
                variant_text = variant_text.strip()

            # Überprüfen, ob die Auswahlmöglichkeit zu einer der gesuchten Kontrollgrößen passt
            if variant_text in target_variants:
                # Interne ID-Parameter der jeweiligen Variante extrahieren
                group_name = option.css('input::attr(name)').get()    # z.B. 'group[3]'
                group_value = option.css('input::attr(value)').get()  # z.B. '121'

                # AJAX-URL mit Varianten-Parametern generieren
                separator = '&' if '?' in response.url else '?'
                ajax_url = f'{response.url}{separator}{group_name}={group_value}&template=ajax'

                # UK-Schuhgrößen in EU-Schuhgrößen übersetzen (greift bei Schlägern/Saiten mangels Mapping auf den Originalwert zurück)
                mapped_variant_text = shoe_size_mapping.get(variant_text, variant_text)

                # Dynamischer Log-Text: Zeigt die Übersetzung nur an, wenn tatsächlich ein Mapping stattgefunden hat (nur bei Schuhen)
                log_suffix = f' (gespeichert als {mapped_variant_text})' if variant_text != mapped_variant_text else ''
                self.logger.info(f'Sende AJAX-Request für Variante {variant_text}{log_suffix}: {ajax_url}')

                # Variantenparameter an die Produkt-URL anhängen, um das AJAX-Fragment der gewählten Variante abzurufen
                yield scrapy.Request(
                    url=ajax_url,
                    callback=self.parse_product_variant,
                    meta={
                        'category': category,
                        'gender': gender,
                        'brand': brand,
                        'name': name,
                        'reference_variant': mapped_variant_text,
                        'url': response.url  # Produkt-URL für das Item behalten
                    }
                )

    def parse_product_variant(self, response):
        '''
        4. SCHRITT: Verarbeitung des AJAX-Fragments.
        Liest Preise und den Verfügbarkeitsstatus aus dem isolierten
        HTML-Fragment der Variante aus.
        '''
        # Basisdaten aus den übergebenen Metadaten extrahieren
        category = response.meta['category']
        gender = response.meta['gender']
        brand = response.meta['brand']
        name = response.meta['name']
        reference_variant = response.meta['reference_variant']
        url = response.meta['url']

        # Da Tennis-Heine keine EAN bereitstellt, bleibt dieses Feld konsequent leer
        ean = None

        # Preise extrahieren
        current_price_raw = response.css('.product--buybox meta[itemprop="price"]::attr(content)').get()
        regular_price_raw = response.css('.product--buybox span.price--line-through::text').get()
        msrp_price_raw = response.xpath(
            '//td[contains(@class, "product--properties-label") and contains(text(), "UVP:")]'
            '/following-sibling::td[contains(@class, "product--properties-value")]/text()'
        ).get()

        # Rohpreise bereinigen
        current_price = self.parse_price(current_price_raw)
        regular_price = self.parse_price(regular_price_raw)
        msrp_price = self.parse_price(msrp_price_raw)

        # Verfügbarkeit über Status-Icon bestimmen; Existiert die CSS-Klasse 'delivery--status-not-available', gilt die Variante als nicht verfügbar
        is_not_available = response.css('i.delivery--status-not-available')
        if is_not_available:
            availability = 'out_of_stock'
        else:
            availability = 'in_stock'

        # Das finale Daten-Item für diese Referenzvariante generieren
        item = TennisItem(  
            retailer='Tennis-Heine',
            timestamp=self.get_timestamp(),
            category=category,
            gender=gender,
            brand=brand,
            name=name,
            reference_variant=reference_variant,  
            ean=ean,
            current_price=current_price,
            regular_price=regular_price,
            msrp_price=msrp_price,
            currency='€',  
            availability=availability,  
            url=url
        )

        self.logger.info(f'Erfolgreich erfasst ({reference_variant} - {availability}): {name}')
        yield item