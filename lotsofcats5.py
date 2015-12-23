from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from dbcatalog_setup5 import Category, Base, Item, User
 
engine = create_engine('postgresql://catalog:catalog@localhost:5432/catalog')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

#Users
user1 = User(name = "vikas", email="vikaskumar.ind@gmail.com")

session.add(user1)
session.commit()

user2 = User(name = "adam", email="adam@gmail.com")

session.add(user2)
session.commit()



#Menu for Soccer
cat1 = Category(name = "Soccer")

session.add(cat1)
session.commit()

Item1 = Item(title = "Jersey", description = "Team Jersey", category = cat1,user = user1)

session.add(Item1)
session.commit()


Item2 = Item(title = "Shinguards", description = "Shin protection", category = cat1,user = user1)

session.add(Item2)
session.commit()


#Menu for BasketBall
cat2 = Category(name = "Basketball")

session.add(cat2)
session.commit()

Item1 = Item(title = "ball", description = "basketball", category = cat2, user = user2)

session.add(Item1)
session.commit()


Item2 = Item(title = "Shoes", description = "basketball shoes", category = cat2,user=user2)

session.add(Item2)
session.commit()


print "added menu items!"
