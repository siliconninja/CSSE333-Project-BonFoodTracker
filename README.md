# CSSE333-Project-BonFoodTracker
Track food information and your favorite foods at the Bon. A Databases project using Python, MS SQL, and Java.

It uses the Spoonacular API to get cuisine and food picture information, and Scrapy to do web scraping.

# Where is everything?
The frontend application code is stored in the `frontend` folder.

The web scraper script is stored in the `scrapy` folder.

The backend scripts are stored in the `scrapy/bon_spider/bon_spider/spiders/bon_spider_scrapy_spider_Create_db_Ver.py` file, as part of this project was to put the import process into 1 file.

The DB maintenance scripts are stored in the `sql_maintenance_scripts` folder.

Some useful project information including ER diagrams and the relational schema are stored in the `db_schema` folder.

# Important Usage Notes
To run this project, you will need an MS SQL Server (at least 2017) and allow ODBC connections. You can provision one on Azure: https://azure.microsoft.com/en-us/services/sql-database/. It has not been tested on earlier versions of SQL Server.

1. Replace `server.com` in the code with the address to your instance of MS SQL Server (either IP address or domain name).
2. The `master_access_username` and `bon19` users both have to be created on your instance of SQL Server by a database admin. The web scraper/import script will NOT create these for you.
3. Also, the `master_access_username` user MUST have access to creating databases, but not users, for maximum security.
4. After you have completed these steps, to run the web scraper script, go to `readme.txt` in the `scrapy` folder and follow the instructions.
