READ ME - 

Prequisites - 

1. Make sure that you have vagrant setup on your computer. 
2. The vagrant environment should have python,sqlalchemy,flask and sqlite installed. 
3. Please make sure you have the version 0.9 of Flask (pip install flask==0.9).
This will be required to avoid the oauth serializable error.


2. Download the zip file into a folder under the vagrant folder.
3. Start vagrant giving the command vagrant up
4. Open command prompt and execute vagrant ssh command and then cd to the folder where the files are unzipped


Running the program - 

1. Give the following command in shell - python dbcatalog_setup5.py
This will create the required database schema in the sqlite db - catalogAppDB2.db


2. Next type the command python lotsofcats5.py. This will create some data for the tables for categories and items.


3. Then type the command python application.py. 
This will start the catalog application.

4. Go to the following link to access the catalog application - 

localhost:5000

5. The login functionality is implement with Google+. So the application will allow login with a 
google+ credentials. The client_secrets.json is included and needs to be in the same folder as the application.py.
It has the required parameters for the connected app.
