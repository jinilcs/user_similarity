## User Similarity

This project is to find similar users based on user interests on different courses.
This consists of data preprocessing steps and the API code for RESTful endpoint to get similar users

### Dependencies

The below libraries are used to develop this project

- Flask==1.0.2
- matplotlib==2.2.3
- numpy==1.15.1
- pandas==0.23.4
- scikit-learn==0.19.2
- scipy==1.1.0

### Source code

git clone https://github.com/jinilcs/user_similarity.git

### Data Flow Diagram:
![alt text](dataflow.jpg "Data Flow")

#### Preprocessing: 
Preprocessing steps are available as Jupyter notebook (notebook/usersim.ipynb) and as a python script (usersim/preprocess.py)

During this step, different datasets are loaded, cleaned and applied required transformations.

#### Generate User Feature Vectors: 
Preprocessed data sets are merged to generate feature vectors for all the users.

#### Dimentionality Reduction:
User feature vectors are sparse and has a very large number of dimensions. So using SVD (Singular Value Decomposition), number of dimensions are reduced to make the user feature vector size small. And the result will be persisted to database.

#### Cosine Similarity:
Cosine Similarity function is used to find how similar the users are. This works best on huge sparse data on a positive space.  

#### RESTful API:

To call the API to find the similar users,

http://hostname/similarusers/<userhandle\> -- This will return a list of 10 users similar to the user handle
http://hostname/similarusers/<userhandle\>?numusers=100 -- This will return a list of 100 users similar to the user handle


This is deployed in AWS EC2 instance and currently available for use.

http://ec2-18-212-6-232.compute-1.amazonaws.com/similarusers/156 => Returns 10 similar users of user handle 156
http://ec2-18-212-6-232.compute-1.amazonaws.com/similarusers/156?numusers=200 => Returns 200 similar users of user handle 156

#### LRUCache:

This is included as part of API call. Recently accessed user handle responses will be cached. And least recently used will be removed from the cache. Implementation is available in usersim/cache.py

### Notes:

#### Similarity calculation:
Cosine similarity function has been used in this project to find the similar users. The data set becomes a huge sparse matrix after preprocessing. Cosine similarity works really good on big sparse dataset.

#### Big data recommendations:
Distributed file systems like HDFS for storage
Spark SQL and Dataframe to preprocess the data
Spark Mllib will be really good for machine learning models on big data stored in distributed file systems
Memory cache to reduce the latency of responses (LRUCache is implemented in this project)

#### Other data to collect:
The below set of data would be more useful to find the similar users
- User personal details (age, sex, location, occupation etc)
- Course ratings given by users
- User review comments on courses (for sentiment analysis)
