# de-densification-2

Courses are subject to change and are classified in different ways. The scraper is a student-created tool. The Spectator’s Data Visualization team did their best to filter classes faithfully based on information provided by the University. Because of these potential errors, these results might not be replicable. Find our data, code, and methodology here.

## <b>The data:<b>

Per University communications about departments subject to de-densification, we filtered classes to only include classes offered by the Faculty of Arts and Sciences and the School of Engineering and Applied Science. Classes without a start or stop time listed were excluded. Classes with variations and abbreviations on the words “laboratory,” “recitation,” and “discussion” in their names were excluded, in accordance with how the University measured departments meeting the 40 percent de-densification cap. All course data was scraped from the Columbia directory of classes on April 22nd.  Generative artificial intelligence tools were utilized in the creation of the web-scraping algorithm.

'desenificationgfx.ipynb' cleans raw course data and finds all the classes in session during 30-minute increments for every day of the week.

'desenificationgfx (1).ipynb' cleans raw course data and sorts classes into time buckets based on class times. 

'desenificationgfx (1).ipynb' cleans raw course data and finds the percent of classes in each department starting from 10 am-2 pm (exclusive).

## <b>The scraper:<b>
'new_scraper.py' scrapes the CU Directory of Classes and Vergil to retrieve course data. It scrapes the CU Directory of Classes for the department code. Our scraper manually adds the department codes for departments in the Faculty of Arts and Sciences and the School of Engineering and Applied Science. The scraper can be run by editing the year and semester when running 'scrape_courses()'. This follows the key '<yearsemester> (spring - 1, summer - 2, fall - 3)'

