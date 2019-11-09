How to test:
Install python-scrapy: pip install python-scrapy or use your package manager to install python-scrapy in Linux.
Anaconda shell works well on Windows.
Install spoonacular API for python: pip install spoonacular
Developers: ipdb might be helpful for debugging, but it isn't used in the final code.

Run
    cd [this directory]/bon_spider
    scrapy crawl bon_spider_scrapy_spider

How to make a scrapy project:
https://www.linode.com/docs/development/python/use-scrapy-to-extract-data-from-html-tags/#create-scrapy-project

    Create a directory to hold your Scrapy project:

    mkdir ~/scrapy
    cd ~/scrapy
    scrapy startproject linkChecker

    Go to your new Scrapy project and create a spider. This guide uses a starting URL for scraping http://www.example.com. Adjust it to the web site you want to scrape.

    cd linkChecker
    scrapy genspider link_checker www.example.com

    This will create a file ~/scrapy/linkChecker/linkChecker/spiders/link_checker.py with a base spider.

        Note
        All path and commands in the below section are relative to the new scrapy project directory ~/scrapy/linkChecker.

Run Your SpiderPermalink

    Start your spider with:

    scrapy crawl

    The Spider registers itself in Scrapy with its name that is defined in the name attribute of your Spider class.

    Start the link_checker Spider:

    cd ~/scrapy/linkChecker
    scrapy crawl link_checker

    The newly created spider does nothing more than downloads the page www.example.com. We will now create the crawling logic.

