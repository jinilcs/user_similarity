import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import sqlite3
from sklearn.externals import joblib
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import collections


def load_data():
	"""
	Loads data from the csv files and writes to sqlite database for later use
	"""
	scores = pd.read_csv('../data/user_assessment_scores.csv')
	views = pd.read_csv('../data/user_course_views.csv')
	tags = pd.read_csv('../data/course_tags.csv')
	interests = pd.read_csv('../data/user_interests.csv')

	db_file = '../db/usersim.sqlite'
	try:
		engine = sqlite3.connect(db_file, timeout=10)
		scores.to_sql('scores', engine, if_exists='replace', index=False, index_label='user_handle')
		views.to_sql('views', engine, if_exists='replace', index=False, index_label='user_handle')
		tags.to_sql('tags', engine, if_exists='replace', index=False, index_label='course_id')
		interests.to_sql('interests', engine, if_exists='replace', index=False, index_label='user_handle')
	except:
		print('Error occured while inserting into database')
	finally:
		if engine:
			engine.close()
	return scores, views, tags, interests

def expand_scores(row):
    tags = row['assessment_tag']
    decays = row['user_assessment_decay']
    for tag, decay in zip(tags,decays):
        row[tag] = decay
    return row

def preprocess_scores(scores):
	"""
	Process the scores dataframe
	"""
	scores['user_assessment_date'] = pd.to_datetime(scores['user_assessment_date'])
	scores['user_assessment_age'] = pd.to_datetime(scores['user_assessment_date'].max() + pd.DateOffset(1)) - scores['user_assessment_date']

	#converting Date to days
	scores['user_assessment_age'] = scores['user_assessment_age'].apply(lambda x: x.days)

	#Decay factor
	scores['user_assessment_decay'] = 1/(scores['user_assessment_age']//30 + 1)

	scores['user_assessment_decay'] = scores['user_assessment_score'] * scores['user_assessment_decay']
	scores_decay_scaler = MinMaxScaler()
	scores['user_assessment_decay'] = scores_decay_scaler.fit_transform(scores['user_assessment_decay'].values.reshape(-1,1))
	scores.drop(['user_assessment_date', 'user_assessment_score', 'user_assessment_age'], axis=1, inplace=True)
	scores_tags = scores.groupby(by='user_handle')['assessment_tag'].apply(list).reset_index()
	scores_decay = scores.groupby(by='user_handle')['user_assessment_decay'].apply(list).reset_index()
	scores_final = pd.merge(scores_tags, scores_decay, on='user_handle')

	scores_final = scores_final.apply(expand_scores, axis=1)
	scores_final.fillna(value=0, inplace=True)
	scores_final.drop(['assessment_tag', 'user_assessment_decay'], axis=1, inplace=True)
	return scores_final

def expand_views_record(row):
    course_ids = row['course_id']
    view_stregths = row['view_stregth']
    tags = row['course_tags']
    
    tag_strengths = collections.defaultdict(list)
    for course, strength, ctags in zip(course_ids, view_stregths, tags):
        row[course] = strength
        for tag in ctags:
            tag_strengths[tag].append(strength)

    for tag, values in tag_strengths.items():
        row[tag] = np.max(values)

    return row

def preprocess_views_tags(views, tags):
	"""
	Process the views and tags dataframe
	"""
	max_val = views['view_time_seconds'].quantile(0.995)
	views['view_time_seconds'] = np.clip(views['view_time_seconds'], 0 , max_val)

	#Finding view strength using a decay factor based on view date
	views['view_date'] = pd.to_datetime(views['view_date'])
	views['view_age'] = pd.to_datetime(views['view_date'].max() + pd.DateOffset(1)) - views['view_date']
	views['view_age'] = views['view_age'].apply(lambda x: x.days)
	views['view_decay'] = 1/(views['view_age']//30 + 1)
	views['view_stregth'] = views['view_time_seconds'] * views['view_decay']
	#Log Transformation for normal distribution from skewed distribution
	views['view_stregth'] = np.log2(views['view_stregth']+3)
	views_strength_scaler = MinMaxScaler()
	views['view_stregth'] = views_strength_scaler.fit_transform(views['view_stregth'].values.reshape(-1,1))
	views.drop(['view_date', 'view_time_seconds', 'view_age', 'view_decay' ], axis=1, inplace=True)
	views = views.groupby(by=['user_handle', 'course_id']).max()['view_stregth'].reset_index()

	#Removing missing data
	tags.dropna(inplace=True)

	#Grouping tags for each course id
	tags = tags.groupby(by='course_id')['course_tags'].apply(set).reset_index()

	views = pd.merge(views, tags, on='course_id')
	views = views.sort_values(by=['user_handle', 'view_stregth'])
	views_course = views.groupby(by='user_handle')['course_id'].apply(list).reset_index()
	views_strength = views.groupby(by='user_handle')['view_stregth'].apply(list).reset_index()
	views_tags= views.groupby(by='user_handle')['course_tags'].apply(list).reset_index()
	views_df = pd.merge(views_course, views_strength, on='user_handle')
	views_df = pd.merge(views_df, views_tags, on='user_handle')
	views_final = views_df.apply(expand_views_record, axis=1)
	views_final.fillna(value=0, inplace=True)
	views_final.drop(['course_id','view_stregth','course_tags'], axis=1, inplace=True)
	return views_final


def expand_interests(row):
    tags = row['interest_tag']
    decays = row['interest_decay']
    
    for tag, decay in zip(tags, decays):
        row[tag] = decay
        
    return row


def preprocess_interests(interests):
	"""
	Process the interests dataframe
	"""
	interests['date_followed']= pd.to_datetime(interests['date_followed'])
	interests['interest_age'] = pd.to_datetime(interests['date_followed'].max() + pd.DateOffset(1)) - interests['date_followed']
	interests['interest_age'] = interests['interest_age'].apply(lambda x: x.days)
	interests['interest_decay'] = (1/interests['interest_age']//30 + 1)

	interests.drop(['date_followed','interest_age'], axis=1, inplace=True)

	interests_tag = interests.groupby(by='user_handle')['interest_tag'].apply(list).reset_index()
	interests_decay = interests.groupby(by='user_handle')['interest_decay'].apply(list).reset_index()
	interests = pd.merge(interests_tag, interests_decay, on='user_handle')

	interests_final = interests.apply(expand_interests, axis=1)
	interests_final.fillna(value=0, axis=1, inplace=True)
	interests_final.drop(['interest_tag', 'interest_decay'], axis=1, inplace=True)
	return interests_final


def generate_feature_vectors(scores_final, views_final, interests_final):
	"""
	Generate sparse feauture vectors for all users from preprocessed dataframes
	"""
	users = pd.merge(scores_final, views_final, how='outer', on='user_handle')
	users = pd.merge(users, interests_final, how='outer', on='user_handle')
	users.fillna(value=0, inplace=True)
	users.set_index('user_handle', inplace=True)
	return users

def reduce_dimentions(users):
	"""
	Dimentionality reduction using SVD. TruncatedSVD is used since data is sparse
	300 features can retain 80% of informaion from the data
	"""
	svd = TruncatedSVD(n_components=300, n_iter=10, random_state=42)
	svd.fit(users)
	users_svd = svd.transform(users)
	users_svd = pd.DataFrame(users_svd, index=users.index)
	return users_svd

def insert_to_database(users_svd):
	"""
	Writes the user feature vector into database for later use
	RESTful API to find the similar users will use this feature vector from database
	"""
	db_file = '../db/usersim.sqlite'
	try:
		engine = sqlite3.connect(db_file, timeout=10)
		users_svd.to_sql('users', engine, if_exists='replace', index=True)
	except:
		print('Error occured while inserting to database')
	finally:
		engine.close()

if __name__ == "__main__":

	print('Loading the file to dataframe and database')
	scores, views, tags, interests = load_data()

	print('Processing scores')
	scores_final = preprocess_scores(scores)

	print('Processing views and tags')
	views_final = preprocess_views_tags(views, tags)

	print('Processing interests')
	interests_final = preprocess_interests(interests)

	print('Generating user feature vectors')
	users = generate_feature_vectors(scores_final, views_final, interests_final)

	print('Reducing dimensions')
	users_svd = reduce_dimentions(users)

	print('writing to database')
	insert_to_database(users_svd)

	print('Preprocessing completed successfully')

