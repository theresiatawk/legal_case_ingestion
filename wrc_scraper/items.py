import scrapy


class CaseItem(scrapy.Item):
    identifier = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    date = scrapy.Field()
    body = scrapy.Field()
    detail_url = scrapy.Field()
    partition_date = scrapy.Field()
