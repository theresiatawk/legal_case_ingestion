import scrapy


class CaseItem(scrapy.Item):
    identifier = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    date = scrapy.Field()
    body = scrapy.Field()
    detail_url = scrapy.Field()
    partition_date = scrapy.Field()
    doc_url = scrapy.Field()
    file_type = scrapy.Field()  #html, pdf, doc, docx
    raw_content = scrapy.Field()  #bytes consumed and dropped by the storage pipeline never saved in Mongo
    file_hash = scrapy.Field()
    file_path = scrapy.Field()
