from scrapy import signals
from itemadapter import is_item, ItemAdapter
from scrapy.exceptions import CloseSpider
from urllib.parse import urlparse
class TennisAnalyticsSpiderMiddleware:

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
        
class TennisAnalyticsDownloaderMiddleware:

    def __init__(self):
        '''
        Initialisierung des domänenspezifischen Zählers für blockierte Anfragen
        und der Fehlergrenze.
        '''
        self.block_counter = {}
        self.max_blocks = 5

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        '''
        Analysiert den HTTP-Statuscode jeder Server-Antwort. Zählt 429-Antworten
        getrennt nach Domain und bricht das Scraping bei anhaltender Blockierung ab.
        '''
        # Überprüfung auf HTTP Status 429 (Zu viele Anfragen)
        if response.status == 429:
            # Extraktion der reinen Domain aus der Request-URL
            domain = urlparse(request.url).netloc

            # Initialisiert den Zähler für die Domain, falls noch kein Eintrag existiert
            self.block_counter.setdefault(domain, 0)
            # Fehlerzähler für die aktuelle Session inkrementieren
            self.block_counter[domain] += 1

            # Aktuellen Fehlerstand für die Log-Ausgabe isolieren
            counter = self.block_counter[domain]

            # System-Warnung mit exakter Fehleranzahl im Log protokollieren
            spider.logger.warning(
                f"429 erkannt! Fehlversuch {counter} von {self.max_blocks} bei {domain} für URL: {request.url}"
            )

            # Abbruch des Crawls bei Überschreiten der maximal zulässigen Anzahl an 429-Antworten
            if counter >= self.max_blocks:
                spider.logger.error(f"Sperre (429) auf {domain} dauerhaft aktiv! Schliesse Spider.")
                raise CloseSpider(f"Zu viele 429 Antworten bei {domain} (blockiert)")
        
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
