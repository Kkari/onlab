import psycopg2
import string
import numpy as np
import pandas as pd
import sys

from bs4 import BeautifulSoup
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.tokenize import WordPunctTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import Normalizer
from sklearn.decomposition import TruncatedSVD

reload(sys)
sys.setdefaultencoding("utf-8")

class Challenge:
    def __init__(self, id, name, summary, description):
        self.id = id
        self.name = name
        self.description = BeautifulSoup(description, 'lxml').get_text(separator=u' ')
        self.summary = summary
        self.recommendedReadings = []
        self.skills = []

        #pandas dataframe for the computed cosine similarity matrix
        self.similarity_dataframe = []

    def getSkills(self):
        return self.skills

    def addSkills(self, skills):
        self.skills = skills

    def addRecommendedReadings(self, rr):
        self.recommendedReadings = rr

    def getConcatenatedContent(self):
        return u"""%s %s %s %s %s""" % (self.name, self.description, self.summary, " ".join(self.skills), " ".join(self.recommendedReadings))


class Parser:
    def filterSkillsForChallenge(self, challenge, skills):
       # print 'Filtering for' + challenge.id
        c_skills = [skill[1] for skill in skills if skill[0] == challenge.id]
        return c_skills

    def createChallenge(self, row):
        return Challenge(row[0], row[1], row[2], row[3])

    def getChallengeData(self):

        print 'Connecting to the database...\n'
        #Set up the database connection
        conn = psycopg2.connect("dbname='kkari' user='kkari' host='localhost' password='agusztus'")
        cur = conn.cursor()
        cur.execute("Select id_, name, summary, description from challenges;")

        #fetch challenge data
        raw_challenges = cur.fetchall();
        challenges = [self.createChallenge(row) for row in raw_challenges]

        #fetch tag data for the challenges
        cur.execute(
            "Select c.id_, s.name from challenges c join challenge_skills cs on cs.challenge_id = c.id_ join skills s on s.id_ = cs.skill_id;")
        raw_skills = cur.fetchall();

        [challenge.addSkills(self.filterSkillsForChallenge(challenge, raw_skills)) for challenge in challenges]

        #fetch the name of the recommended readings for the challenges
        cur.execute(
            "Select c.id_, r.name from challenges c join recommendations r on r.recommender_id = c.id_;")
        raw_skills = cur.fetchall();

        [challenge.addRecommendedReadings(self.filterSkillsForChallenge(challenge, raw_skills)) for challenge in challenges]

        return challenges

    def computeSimilarities(self, challenges):

        challenge_dict = {}
        skills_dict = {}

        print 'Preprocessing challenges...\n'
        for challenge in challenges:
            wpt = WordPunctTokenizer()
            tokenized = wpt.tokenize(challenge.getConcatenatedContent())

            no_punc = [word for word in tokenized if word not in string.punctuation]
            tokenized_lower = [word.lower() for word in no_punc if word not in string.punctuation]
            filtered = [word for word in tokenized_lower if word not in stopwords.words('english')]

            wl = WordNetLemmatizer()
            text_stemmed = [wl.lemmatize(word) for word in filtered]

            challenge_dict[challenge.name] = ' '.join(text_stemmed).lower()
            skills_dict[challenge.name] = ' '.join(challenge.getSkills()).lower()

        tfidf = TfidfVectorizer()
        tfs_concat = tfidf.fit_transform(challenge_dict.values())

        lsa = TruncatedSVD(3, algorithm='arpack')

        dtm_concat_lsa = lsa.fit_transform(tfs_concat)
        dtm_concat_lsa = Normalizer(copy=False).fit_transform(dtm_concat_lsa)
        

        
        #dtm_concat_lsa = Normalizer(copy=False).fit_transform(tfs)
        #all vectors are normalized, so we only have to multiply them to acquire the cosine similarity
        if skills_dict:
            tfs_skills = tfidf.fit_transform(skills_dict.values())
            dtm_skills_lsa = lsa.fit_transform(tfs_skills)
            dtm_skills_lsa = Normalizer(copy=False).fit_transform(dtm_skills_lsa)

            skillCosineSimilarity = np.asarray(np.asmatrix(dtm_skills_lsa) * np.asmatrix(dtm_skills_lsa).T)
            concatCosineSimilarity = np.asarray(np.asmatrix(dtm_concat_lsa) * np.asmatrix(dtm_concat_lsa).T)
            cos_similarity = 0.5 * skillCosineSimilarity + 0.5 * concatCosineSimilarity
        else:
            cos_similarity = np.asarray(np.asmatrix(dtm_concat_lsa) * np.asmatrix(dtm_concat_lsa).T)

        self.similarity_dataframe = pd.DataFrame(cos_similarity, index=challenge_dict.keys(), columns=challenge_dict.keys())
        return self.similarity_dataframe


class ContentBasedRecommender:

    def __init__(self, challenges, similarities):
        self.challenges = challenges
        self.similarities = similarities

    def findChallengeByName(self, name):
        for challenge in self.challenges:
            if (challenge.name == name):
                return challenge
        raise Exception('No such challenge')

    def recommendForChallenge(self, challengeName):
        challengeSims = self.similarities[challengeName].sort_values(ascending=0)

    #    recommendations = pd.DataFrame(columns=[challengeName])
    #   counter = 0
        if len(self.findChallengeByName(challengeName).skills) != 0:
            recommendations = challengeSims[challengeSims.between(0.75, 0.99999999)]
        else:
            recommendations = challengeSims[challengeSims.between(0.3, 0.49999999)]

        if len(recommendations) != 0:
            recommendations = recommendations.sample(min(len(recommendations), 3))

        return recommendations
