# Reference on how to make a Scrapy project

Credit given to Florent Houbart at Linode for giving us this awesome documentation: https://www.linode.com/docs/development/python/use-scrapy-to-extract-data-from-html-tags/#create-scrapy-project

GitHub: https://github.com/linode/docs/blob/master/docs/development/python/use-scrapy-to-extract-data-from-html-tags/index.md

## Licensing information

This document licensed under a CC BY-ND 4.0 license. This is an excerpt of the original document which is allowed under fair use. I use ... to separate parts of the document that I didn't use in the final project. As a result, I will keep the entire formatting the same (I will use the same Markdown formatting that Linode uses). (I used https://lumenlearning.zendesk.com/hc/en-us/articles/219255997-CC-BY-ND as a helpful reference)

The excerpts are shown below this line:
------

## Create Scrapy Project

...

1.  Create a directory to hold your Scrapy project:

        mkdir ~/scrapy
        cd ~/scrapy
        scrapy startproject linkChecker

2.  Go to your new Scrapy project and create a spider. This guide uses a starting URL for scraping `http://www.example.com`. Adjust it to the web site you want to scrape.

        cd linkChecker
        scrapy genspider link_checker www.example.com

    This will create a file `~/scrapy/linkChecker/linkChecker/spiders/link_checker.py` with a base spider.

    {{< note >}}
All path and commands in the below section are relative to the new scrapy project directory `~/scrapy/linkChecker`.
{{< /note >}}

## Run Your Spider

1.  Start your spider with:

        `scrapy crawl`

    The Spider registers itself in Scrapy with its name that is defined in the `name` attribute of your Spider class.

2.  Start the `link_checker` Spider:

        cd ~/scrapy/linkChecker
        scrapy crawl link_checker

    The newly created spider does nothing more than downloads the page `www.example.com`. We will now create the crawling logic.
