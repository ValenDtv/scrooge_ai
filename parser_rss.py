import requests
import time
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from dateutil.parser import parse
import traceback

class ParserRSS():
    
    
    def __init__(self, link):
        #self.start_link = 'https://finance.yahoo.com/news/rss'
        self.start_link = link
    
    
    def get_article_info(self, link):
        response = requests.get(link, headers={'User-Agent': UserAgent().chrome},
                            timeout=60)
        html = response.content
        article = BeautifulSoup(html,'html.parser')
        text = [p.text for p in article.find('div', attrs = {'class':'caas-body'}).findAll('p')]
        for i, line in enumerate(text[:3]):
            if len(line.split()) > 10 and 'By ' == line[:3]:
                text = text[i+1:]
        text = '\n'.join(text)
        return text
        
        
    def get_articles(self, start_date):
        response = requests.get(self.start_link, headers={'User-Agent': UserAgent().chrome},
                        timeout=60)
        xml = response.content
        soup = BeautifulSoup(xml, features='xml')
        articles = soup.findAll('item')

        start_date = parse(soup.find('pubDate').text).date()

        articles_data = []
        for article in articles:
            link = article.find('link').text
            if 'finance.yahoo' in link:
                try:
                    time.sleep(0.2)
                    text = self.get_article_info(link)
                    day = parse(article.find('pubDate').text).date()
                    dt = parse(article.find('pubDate').text)
                    title = article.find('title').text
                    articles_data.append({'link': link,
                                            'title': title,
                                            'day': day,
                                            'text': text,
                                            'datetime': dt})
                except Exception as e:
                        print(traceback.format_exc())
                        print(link)
        articles_data = sorted(articles_data, key=lambda x: x['datetime'], reverse=False)
        articles_data = [a for a in articles_data if a['day'] >= start_date and len(a['text'].split(' ')) <= 800]
        return articles_data





