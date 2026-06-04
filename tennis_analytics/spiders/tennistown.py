import scrapy
from tennis_analytics.spiders.base_spider import BaseTennisSpider
from tennis_analytics.items import TennisItem

class TennistownSpider(BaseTennisSpider):

    name = 'tennistown'
    allowed_domains = ['tennistown.de']

    def start_requests(self):
        """
        1. SCHRITT: Initialisierung der Crawl-Requests.
        Definiert die Einstiegs-URLs für alle Zielkategorien und verankert 
        Kategorie sowie Geschlecht als feste Metadaten in der Request-Pipeline.
        """
        urls = [
            {
                'url': 'https://www.tennistown.de/index.php?cPath=786_21',
                'category': 'rackets',
                'gender': 'unisex'
            },
            {
                'url': 'https://www.tennistown.de/index.php?list=1&srsltid=AfmBOooLYOBhbpiFZJwjly3Ayf8IXwumalJff7M5-LYg5lNYWbIiO-hdwTU&cPath=786_515&tags=110',
                'category': 'shoes',
                'gender': 'women'
            },
            {
                'url': 'https://www.tennistown.de/index.php?list=1&srsltid=AfmBOooLYOBhbpiFZJwjly3Ayf8IXwumalJff7M5-LYg5lNYWbIiO-hdwTU&cPath=786_515&tags=109',
                'category': 'shoes',
                'gender': 'men'
            },
            {
                'url': 'https://www.tennistown.de/index.php?cPath=786_24',
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
        """
        2. SCHRITT: Verarbeitung der Produktübersichten.
        Extrahiert die Produktlinks der aktuellen Übersicht und steuert das 
        automatische Umblättern über die Folgeseiten.
        """
        self.logger.info(f'Produktübersicht geladen: {response.url}')

        # Kategorie und Geschlecht aus den übergebenen Metadaten extrahieren
        category = response.meta.get('category')
        gender = response.meta.get('gender')

        # Alle Produkt-Links auf der aktuellen Seite einsammeln
        product_links = response.css('section[aria-label="Produktliste"] a::attr(href)').getall()

        for link in product_links:
            # Relative URLs in absolute URLs umwandeln
            full_url = response.urljoin(link)
            
            # Produktseite aufrufen und Kategorie sowie Geschlecht mit Metadaten an 'parse_product' übergeben
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_product,
                meta={'category': category, 'gender': gender}
            )

        # Pagination im Shop über den "Weiter"-Button
        next_page_link = response.css('a.button_next::attr(href)').get()

        if next_page_link:
            full_next_page_url = response.urljoin(next_page_link)
            self.logger.info(f'Nächste Seite gefunden, blättere um: {full_next_page_url}')
            # Produktübersicht rekursiv aufrufen und Kategorie sowie Geschlecht für die Folgenseiten beibehalten
            yield scrapy.Request(
                url=full_next_page_url,
                callback=self.parse,
                meta={'category': category, 'gender': gender}
            )

    def parse_product(self, response):
        """
        3. SCHRITT: Extraktion der Produktdetails.
        Liest Name, Preise sowie EANs aus und prüft die Verfügbarkeit der
        gezielt ausgewählten Referenzgrößen.
        """
        self.logger.info(f'Produktseite geladen: {response.url}')

        # Kategorie und Geschlecht aus den übergebenen Metadaten extrahieren
        category = response.meta.get('category')
        gender = response.meta.get('gender', 'unisex')  # Standardwert 'unisex', falls nichts übergeben wurde

        # Name extrahieren
        name = response.css('h1#product-title::text').get()
        if name:
            name = name.strip()

        # Preise extrahieren
        current_price_raw = response.css('.products_details span.productSpecialPrice::text').get()
        regular_price_raw = response.css('.products_details span#pricefield s::text').get()
        msrp_price_raw = response.css('.products_details section#uvpfield::text').getall()

        # Falls kein Sonderpreis existiert, normalen Preis als aktuellen Preis setzen
        if not current_price_raw:
            current_price_raw = response.css('.products_details span#pricefield::text').get()
            regular_price_raw = None

        # Rohpreise bereinigen
        current_price = self.parse_price(current_price_raw)
        regular_price = self.parse_price(regular_price_raw)
        msrp_price_text = ''.join(msrp_price_raw) if msrp_price_raw else None
        msrp_price = self.parse_price(msrp_price_text)

        # --- MARKEN-FILTERUNG UND NORMALISIERUNG ---
        brand = None
        allowed_brands = self.allowed_brands.get(category, [])

        # Text-Normalisierung speziell für Tennistown (kswiss -> k-swiss)
        name_lower_normalized = name.lower() if name else ''
        if 'kswiss' in name_lower_normalized:
            name_lower_normalized = name_lower_normalized.replace('kswiss', 'k-swiss')

        # Überprüfen, ob eine der zu untersuchenden Marken im Produktnamen vorkommt
        for allowed_brand in allowed_brands:
            if name and allowed_brand in name_lower_normalized:
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
            if not name or self.required_racket_keyword not in name_lower_normalized:
                self.logger.info(f'Produkt ignoriert (Schläger ist nicht unbesaitet): {name}')
                return

        # --- SAITENLÄNGEN-FILTERUNG (Nur für Saiten)---
        # In der Kategorie 'strings' werden ausschließlich 200 Meter Saitenrollen erfasst
        if category == 'strings':
            # Überprüfung, ob keines der erlaubten Längen-Keywords im Namen vorkommt
            if not name or all(keyword not in name_lower_normalized for keyword in self.required_string_keywords):
                self.logger.info(f'Produkt ignoriert (Saitenlänge ist nicht korrekt): {name}')
                return

        # --- VARIANTENLOGIK: Verfügbarkeiten erfassen ---
        # Suche nach Varianten-Bezeichnungen und den dazugehörigen EANs
        spec_text_list = response.css('td.specName div.textNormal::text').getall()            
        ean_text_list = response.xpath(
            '//td[@class="specName"][div[@class="textNormal"]]'
            '/following-sibling::td[@class="col-right"]/text()'
        ).getall()

        found_variants = []

        # Paarung der Varianten mit EANs direkt über ihren Listen-Index
        for spec_text_raw, ean_text_raw in zip(spec_text_list, ean_text_list):
            spec_text = spec_text_raw.strip()
            ean_text = ean_text_raw.strip()

            # Zuweisung basierend auf den Kategorien
            if category == 'rackets':
                if spec_text.startswith('2'):
                    found_variants.append({'size': 'L2', 'ean': ean_text})
                elif spec_text.startswith('3'):
                    found_variants.append({'size': 'L3', 'ean': ean_text})
            
            elif category == 'shoes':
                if spec_text.startswith('39'):
                    found_variants.append({'size': 'EU 39', 'ean': ean_text})
                elif spec_text.startswith('43'):
                    found_variants.append({'size': 'EU 43', 'ean': ean_text})
            
            elif category == 'strings':
                if spec_text.startswith('1.25') or spec_text.startswith('1,25'):
                    found_variants.append({'size': '1.25 mm', 'ean': ean_text})

        # --- SEPARIERUNG IN EINZEL-ITEMS ---
        # Festlegen der standardmäßig erwarteten Zielvarianten pro Kategorie und Geschlecht
        target_variants = []

        if category == 'rackets':
            target_variants = self.target_racket_grip_sizes
        elif category == 'shoes':
            if gender == 'women':
                target_variants = self.target_women_shoe_sizes
            elif gender == 'men':
                target_variants = self.target_men_shoe_sizes
        elif category == 'strings':
            target_variants = self.target_string_thicknesses
        else:
            self.logger.info(f'Unbekannte Kategorie: {category}')
            return

        # Für jede erwartete Zielvariante wird ein separates Item erzeugt (yielden)
        for target_variant in target_variants:
            # Überprüfen, ob diese Zielvariante im Shop auf Lager ist; Abbruch nach erstem Treffer
            match = next((found_variant for found_variant in found_variants if found_variant['size'] == target_variant), None)
            
            if match:
                # Variante ist verfügbar: Status setzen und EAN zuweisen
                availability = 'in_stock'
                ean = match['ean']
            else:
                # Variante ist ausverkauft: Status setzen und EAN zunächst auf None setzen
                availability = 'out_of_stock'
                ean = None

            # Das finale Daten-Item für diese Referenzvariante generieren
            item = TennisItem(  
                retailer='Tennistown',
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


        