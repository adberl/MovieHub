# get random movies, from each movie get random users that have a review
# for each user, get their reviews for movies
# for each movie reviewed, get their score and make a movie profile (get movies tags etc)
# construct a classifier for each user based on movies that they have watched and enjoyed.

# go to a user then the user's network, get its followers/following
# check if user you got doesnt exist in database + doesnt have more than 100 movies watched 
# first check movies watched due to efficiency

# DATABASE 1 - USER, MOVIE, RATING
# DATABASE 2 - MOVIE, TAGS
# 666

import urllib.request
import re
from bs4 import BeautifulSoup
import requests
import ujson
import gc

# class Dataget(object):

users = set()
movies = {}
user_struct = []

MAX_DEPTH = 2

with open("apikey.txt", 'r') as api_file:
	API_KEY = api_file.read()
	api_file.close()

#	def Dataget(MAX_DEPTH = 1):
#		self.MAX_DEPTH = MAX_DEPTH


def getRatingsLink(username_f: str) -> str:
	return 'https://letterboxd.com/' + username_f + '/films/ratings/page/'


def addAllRatings(start_username: str) -> set:

	# (movie, rating)	
	# (movie, tags)
	link = getRatingsLink(start_username)
	hasNext = True
	page = 1
	
	user_movies = set()
	
	while hasNext:

		r = urllib.request.urlopen(link + str(page) + '/').read()
		soup = BeautifulSoup(r, "html.parser")
		all_movies = soup.findAll('li', class_='poster-container')
		
		page += 1
		
		for movie in all_movies:
			
			film_link = movie.find('div')['data-film-slug']
			rating = int(movie.find('meta')['content'])

			if addTags(film_link) is None:
				continue
			user_movies.add((film_link, rating))

			# TAGS FOR MOVIES ARE ADDED HERE, WHEN ADDING A NEW MOVIE TO A USER

		if soup.find('a', class_='next') is None:
			hasNext = False

		if not(soup is None):
			soup.decompose()
			for a in all_movies:
				a.decompose()

	print("finished gathering ratings for user: ", start_username)
	return user_movies


def getFollowersLink(username_f:str) -> str:
	return 'https://letterboxd.com/' + username_f + '/followers/page/'


def addAllFollowers(start_username: str, depth: int):
	if depth > MAX_DEPTH:
		return
	link = getFollowersLink(start_username)
	hasNext = True
	page = 1
	
	while hasNext:

		r = urllib.request.urlopen(link + str(page) + '/').read()
		soup = BeautifulSoup(r, "html.parser")
		person_summary = soup.findAll('div', class_='person-summary')
		
		page += 1
		
		for person in person_summary:
			username_html = str(person.find('a', class_='name'))
			username = re.search('(?<=href="/).*(?=/">)', username_html).group(0)
			username_html = None
			gc.collect()
			users.add(username)
			# use a regex to find a string that starts with href="/ (dont capture it) 
			# and ends with \"> (also dont capture)
			# group(0) returns the first matched object

			if depth < MAX_DEPTH:
				addAllFollowers(username, depth+1)
		if soup.find('a', class_='next') is None:
			hasNext = False

		for a in person_summary:
			a.decompose()
		soup.decompose()
		gc.collect()
	print("done gathering followers: ", start_username)


def addTags(movie_url:str):

	if movie_url in movies:
		print('movie already exists: ', movie_url)
		return

	tags = set()
		
	r = urllib.request.urlopen('https://letterboxd.com' + movie_url).read()
	soup = BeautifulSoup(r, 'html.parser')
	tmdb_id = soup.find('body')['data-tmdb-id']

	r = requests.get('https://api.themoviedb.org/3/movie/' + tmdb_id + '/keywords?api_key=' + API_KEY).json()
	
	try:
		for keyword in r['keywords']:

			tags.add(keyword['name'])

			# try:
			# tags[keyword] += tags[keyword] + 1
			# except KeyError:
			# tags[keyword] = 1

	except KeyError:
		return None

	genres = soup.find('div', {'id': 'tab-genres'})
	if genres is None:
		return None
	genres = genres.find_all('a')	

	for genre in genres:
		tags.add(genre.contents[0])

# print(genre.contents[0])
# r = requests.get('https://api.themoviedb.org/3/movie/' + tmdb_id + '?api_key=' + API_KEY).json()
# for genre in r['genres']:
# print(genre['name'])

	movies[movie_url] = tags
	print("added movie tags for: ", movie_url)
	
	return True


def save_file():

	with open('data/users.json', 'w') as users_file:
		ujson.dump(users, users_file)
		users_file.close()

	with open('data/movies.json', 'w') as movies_file:
		ujson.dump(movies, movies_file)
		movies_file.close()

	# Writing the user's tags as CSV
	with open("data/data.csv", 'w') as csv_file:
		for i, j in user_struct:

			user_tags = set()
			for movie, rating in j:
				user_tags = user_tags.union(movies[movie])

			print(i, file=csv_file)
			for tag in user_tags:
				print(tag, end=',', file=csv_file)
		csv_file.close()




users.add('grantwilson999')
#addAllFollowers('grantwilson999', 1)
#save_file()

for user in users:
	print("constructing info for user:", user)
	user_struct.append((user, addAllRatings(user)))
#	save_file()
	print("movies: {}, users: {}".format(len(movies), len(users)))



"""
{ 'moviename' : set() -> pickled file }
moviename,file

"""
"""
with open('users.json', 'w') as users_file:
	json.dump(user_struct, users_file)
	users_file.close()

with open('movies.json', 'w') as movies_file:
	json.dump(movies, movies_file)
	movies_file.close()
	
"""

""""
#	print(user_tags, ',', i, file=csv_file)

#for tag in user_tags
#	print(tag, separator=',')
#	ptiny(user)
	
#with open("name_of_file.json", 'w') as some_variable:
#    json.dump(my_object, some_variable)
#    output_file.close()

#with open("name_of_file.json", 'r') as some_variable:	
#    my_object = json.load(some_variable)
#    database_in.close()	
	
#with open('filename', 'wb') as myfile:
#    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
#    wr.writerow(mylist)	
"""
