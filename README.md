# Bearing  
#### Video Demo:  https://youtu.be/pdFlYQo2TzA  
#### Description: Bearing is a free application and our goal is to help you to learn a new language and maximize your learning process with flash cards that can be reviewed anytime you want. Flash cards can also be used for learning or recall anything you want, bearing it in your mind.  
#### Project link: https://bearing.pythonanywhere.com  

## Files walkthrough
**static**: Contains all files used for styling the pages and add images to the application. "css" directory contains the CSS files and the "images" directory contains every used image.  
**templates**: Contains all html files used in the website. In the html, I have been through a lot of javascript, including jQuery library and AJAX method for performing requests to my back end server.  
**.gitignore**: Simply ignore the .env fie, which contains all environmental variables.  
**README.md**: It is this file.  
**app.py**: It is main file of the application and it is all structured and organized in this files, it uses a lot of the Flask library for structuring the site and rendering every template. It is also using, among others libraries, sqlite3 for performing SQL queries in my database.  
**bearing.db**: It is the SQLite database which contains 3 tables: users, cards and examples. It stores data about the user, the cards owned by each user and the examples for each card.  
**helpers.py**:  
**requirements.txt**:  


## How to acess it  
#### web version  
• go to https://bearing.pythonanywhere.com.  
• enjoy it.  
  
#### local version  
• Clone the repository: git clone https://github.com/opedroporto/finalproject.  
• Once you are in its directory, edit the app.py and you should need to make some changes in the following lines:  
• 16, 17, 54.  
• Edit these lines in order for them to fit your directories paths.  
• You should also define values to variables set in .env file.  
• Install the requirements: pip install -r requirements.txt  
• Execute: flask run  
• If you need some support, you can contact me via this e-mail address: portopdr@gmail.com  
  
I've been testing my application lately and it is running properly locally but my web app is running into some bugs, so I'm sorry for it and I hope can fix it soon.  
