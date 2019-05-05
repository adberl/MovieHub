import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from ast import literal_eval
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.stem.snowball import SnowballStemmer
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import wordnet
from surprise import Reader, Dataset, SVD, evaluate
import warnings; warnings.simplefilter('ignore')
import pickle
import tkinter as tk

md = pd.read_csv('data/movies_metadata.csv')

md['genres'] = md['genres'].fillna('[]').apply(literal_eval).apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])

vote_counts = md[md['vote_count'].notnull()]['vote_count'].astype('int')
vote_averages = md[md['vote_average'].notnull()]['vote_average'].astype('int')
C = vote_averages.mean()

m = vote_counts.quantile(0.95)

md['year'] = pd.to_datetime(md['release_date'], errors='coerce').apply(lambda x: str(x).split('-')[0] if x != np.nan else np.nan)


s = md.apply(lambda x: pd.Series(x['genres']),axis=1).stack().reset_index(level=1, drop=True)
s.name = 'genre'
gen_md = md.drop('genres', axis=1).join(s)

s = md.apply(lambda x: pd.Series(x['genres']),axis=1).stack().reset_index(level=1, drop=True)
s.name = 'genre'
gen_md = md.drop('genres', axis=1).join(s)

links_small = pd.read_csv('data/links_small.csv') # dont
links_small = links_small[links_small['tmdbId'].notnull()]['tmdbId'].astype('int') # dont
md = md.drop([19730, 29503, 35587]) # dont
md['id'] = md['id'].astype('int') # dont
smd = md[md['id'].isin(links_small)] # dont
smd.shape # dont

smd['tagline'] = smd['tagline'].fillna('') # dont
smd['description'] = smd['overview'] + smd['tagline'] 
smd['description'] = smd['description'].fillna('') 

smd = smd.reset_index()
titles = smd['title']
indices = pd.Series(smd.index, index=smd['title'])

credits = pd.read_csv('data/credits.csv')
keywords = pd.read_csv('data/keywords.csv')

keywords['id'] = keywords['id'].astype('int')
credits['id'] = credits['id'].astype('int')
md['id'] = md['id'].astype('int')

md = md.merge(credits, on='id')
md = md.merge(keywords, on='id')

smd = md[md['id'].isin(links_small)]

smd['cast'] = smd['cast'].apply(literal_eval)
smd['crew'] = smd['crew'].apply(literal_eval)
smd['keywords'] = smd['keywords'].apply(literal_eval)
smd['cast_size'] = smd['cast'].apply(lambda x: len(x))
smd['crew_size'] = smd['crew'].apply(lambda x: len(x))

def get_director(x):
	for i in x:
		if i['job'] == 'Director':
			return i['name']
	return np.nan
	
smd['director'] = smd['crew'].apply(get_director)

smd['cast'] = smd['cast'].apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])
smd['cast'] = smd['cast'].apply(lambda x: x[:3] if len(x) >=3 else x)

smd['keywords'] = smd['keywords'].apply(lambda x: [i['name'] for i in x] if isinstance(x, list) else [])

smd['cast'] = smd['cast'].apply(lambda x: [str.lower(i.replace(" ", "")) for i in x])

smd['director'] = smd['director'].astype('str').apply(lambda x: str.lower(x.replace(" ", "")))
smd['director'] = smd['director'].apply(lambda x: [x,x, x])

s = smd.apply(lambda x: pd.Series(x['keywords']),axis=1).stack().reset_index(level=1, drop=True)
s.name = 'keyword'
s = s.value_counts()
s = s[s > 1]
stemmer = SnowballStemmer('english')

def filter_keywords(x):
	words = []
	for i in x:
		if i in s:
			words.append(i)
	return words

smd['keywords'] = smd['keywords'].apply(filter_keywords)
smd['keywords'] = smd['keywords'].apply(lambda x: [stemmer.stem(i) for i in x])
smd['keywords'] = smd['keywords'].apply(lambda x: [str.lower(i.replace(" ", "")) for i in x])

smd['soup'] = smd['keywords'] + smd['cast'] + smd['director'] + smd['genres']
smd['soup'] = smd['soup'].apply(lambda x: ' '.join(x))

count = CountVectorizer(analyzer='word',ngram_range=(1, 2),min_df=0, stop_words='english')
count_matrix = count.fit_transform(smd['soup'])

cosine_sim = cosine_similarity(count_matrix, count_matrix)

smd = smd.reset_index()
titles = smd['title']
indices = pd.Series(smd.index, index=smd['title'])

reader = Reader()

ratings = pd.read_csv('data/ratings_small.csv')

svd = SVD()


def convert_int(x):
	try:
		return int(x)
	except:
		return np.nan

id_map = pd.read_csv('data/links_small.csv')[['movieId', 'tmdbId']]
id_map['tmdbId'] = id_map['tmdbId'].apply(convert_int)
id_map.columns = ['movieId', 'id']
id_map = id_map.merge(smd[['title', 'id']], on='id').set_index('title')

indices_map = id_map.set_index('id')

#pickle.dump(svd, open('svd_file.dat', 'wb'))
#smd.to_csv(path_or_buf='smd_file.csv', index=False)
#indices.to_csv(path_or_buf='indices_file.csv', index=False)
#indices_map.to_csv(path_or_buf='indices_map.csv', index=False)

def hybrid(userId, title):
	idx = indices[title]
	
	sim_scores = list(enumerate(cosine_sim[int(idx)]))
	sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
	sim_scores = sim_scores[1:26]
	movie_indices = [i[0] for i in sim_scores]
	
	movies = smd.iloc[movie_indices][['title', 'vote_count', 'vote_average', 'year', 'id']]
	movies['est'] = movies['id'].apply(lambda x: svd.predict(userId, indices_map.loc[x]['movieId']).est)
	movies = movies.sort_values('est', ascending=False)
	return movies.head(10)

# ---------------------- gui starts here ---------------------------------

HEIGHT = 400
WIDTH = 800

root = tk.Tk()
root.title('MovieHub')
root.iconbitmap('favicon.ico')

list_movies = []
added_movies = tk.StringVar()
rec_movies = tk.StringVar()

def add_movie(movie, rate):
	if movie == '' or rate == '':
		return
	rate = max(min(int(rate), 5), 0)
	tmp = added_movies.get() + '○ ' + movie + ' (' + str(rate) + ')' '\n'
	list_movies.append([movie,float(rate)])
	added_movies.set(tmp)

def recommend_movies():

	mov_lst = []
	max = 0
	for a in list_movies:
		try:
			idx = indices[a[0]]
		except:
			continue
		if idx == None:
			continue
		if a[1] > max:
			max = a[1]
			mov_title = a[0]
		
		mov_lst.append([200000, idx, a[1], 10])
	
	df = pd.DataFrame(mov_lst, columns=['userId', 'movieId', 'rating', 'timestamp'])
	ratings1 = ratings.append(df, ignore_index=True)

	data = Dataset.load_from_df(ratings1[['userId', 'movieId', 'rating']], reader)
	data.split(n_folds=5)
	
	evaluate(svd, data, measures=['RMSE', 'MAE'])

	trainset = data.build_full_trainset()
	svd.train(trainset)
	
	recommended_movies = hybrid(200000, mov_title)['title']
	
	tmp = ''
	for m2 in recommended_movies:
		tmp = tmp + m2 + '\n'
	
	rec_movies.set(tmp)

canvas = tk.Canvas(root, height=HEIGHT, width=WIDTH)
canvas.pack()

#background_image = tk.PhotoImage(file='34428.png')
background_label = tk.Label(root, bg='#b6c1ff')#image=background_image)
background_label.place(relwidth=1, relheight=1)

frame = tk.Frame(root, bg='#ffb6c1', bd=4)
frame.place(relx=0.25, rely=0.05, relwidth=0.4, relheight=0.07, anchor='n')

entry = tk.Entry(frame, font=40) # MOVIE NAME ENTRY
entry.place(relwidth=0.5, relheight=1)

entry_rate = tk.Entry(frame, font=40) # MOVIE RATE ENTRY
entry_rate.place(relwidth=0.1, relx=0.55, relheight=1)

button = tk.Button(frame, text="Add", font=40, command=lambda: add_movie(entry.get(), entry_rate.get()))
button.place(relx=0.7, relheight=1, relwidth=0.3)

lower_frame = tk.Frame(root, bg='#ffb6c1', bd=4)
lower_frame.place(relx=0.25, rely=0.15, relwidth=0.4, relheight=0.8, anchor='n')

button = tk.Button(lower_frame, text="recommend", font=40, command=recommend_movies)
button.place(relx=0.5, rely=1, relheight=0.18, relwidth=1, anchor='s')

label = tk.Label(lower_frame, textvariable=added_movies, anchor='nw', justify='left')
label.place(relwidth=1, relheight=0.8)

right_frame = tk.Frame(root, bg='#ffb6c1', bd=4)
right_frame.place(relx=0.75, rely=0.05, relwidth=0.4, relheight=0.9, anchor='n')

label = tk.Label(right_frame, textvariable=rec_movies, anchor='nw', justify='left')
label.place(relwidth=1, relheight=1)

root.minsize(WIDTH, HEIGHT)
root.mainloop()