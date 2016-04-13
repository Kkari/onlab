# -*- coding: utf-8 -*-
import sys
import csv

from ContentBasedRecommender import Parser, ContentBasedRecommender
from PyQt4 import QtCore, QtGui
from gui import Ui_RecommenderValidator


class challengeRatingEvaluationData:
  def __init__(self, viewedName):
    self.viewed = viewedName
    self.rated = {}

  def getEvaluationData(self):
    return self.rated;

  def updateEvaluationData(self, name, fits):
    self.rated[name] = str(fits)

class StartQT4(QtGui.QMainWindow):
  def __init__(self, parent=None):
    
    QtGui.QWidget.__init__(self, parent)
    self.ui = Ui_RecommenderValidator()
    self.ui.setupUi(self)
    # set the widths of the columns
    self.connect(self.ui.challengeList, QtCore.SIGNAL("itemClicked(QTreeWidgetItem*, int)"), self.selectChallenge)
    self.connect(self.ui.recommendedList, QtCore.SIGNAL("itemClicked(QTreeWidgetItem*, int)"), self.clickedRecommendedItem)
    self.connect(self.ui.allSimilarities, QtCore.SIGNAL("itemClicked(QTreeWidgetItem*, int)"), self.selectRecommendedChallenge)
    self.connect(self.ui.saveRating_button, QtCore.SIGNAL('clicked()'), self.saveRatings)
    self.ui.recommendedList.setColumnWidth(0,150)
    self.ui.recommendedList.setColumnWidth(1,150)
    self.ui.allSimilarities.setColumnWidth(0, 150)
    self.ui.allSimilarities.setColumnWidth(1, 150)

    p = Parser()

    self.challenges = p.getChallengeData()
    self.similarities = p.computeSimilarities(self.challenges)

    self.cb = ContentBasedRecommender(self.challenges, self.similarities)
    self.evalDataForChallenges = {}
    self.viewedChallenge = ''

    for challenge in self.challenges:
      a = QtGui.QTreeWidgetItem(self.ui.challengeList)
      a.setText(0, challenge.name)

  def saveRatings(self):

    with open('ratingEval.csv', 'w') as csvfile:
      ratingWriter = csv.writer(csvfile, delimiter=',')
      for chName, ratingData in self.evalDataForChallenges.iteritems():
        for recName, fits in ratingData.getEvaluationData().iteritems():
          if fits == 'yes':
            ratingWriter.writerow([chName, recName, '1'])
          else:
            ratingWriter.writerow([chName, recName, '0'])

    print 'Ratings saved.'


  def clickedRecommendedItem(self, item, column):
    if column == 0:
      self.selectRecommendedChallenge(item, column)
    elif column == 1:
      self.rateRecommendation(item, column)

  def rateRecommendation(self, item, column):
    if column != 1:
      return

    if item.text(1) == '-':
      item.setText(1, 'yes')
    elif item.text(1) == 'yes':
      item.setText(1, 'no')
    elif item.text(1) == 'no':
      item.setText(1, '-')

    if self.viewedChallenge not in self.evalDataForChallenges:
      self.evalDataForChallenges[self.viewedChallenge] = challengeRatingEvaluationData(
                                                              self.viewedChallenge,
                                                              item.text(0),
                                                              item.text(1))
    self.evalDataForChallenges[self.viewedChallenge].updateEvaluationData(item.text(0), item.text(1))

  def findChallengeByName(self, name):
    for challenge in self.challenges:
      if (challenge.name == name):
        return challenge
    raise Exception('No such challenge')

  def selectRecommendedChallenge(self, item, column):
    #get challenge details
    challenge = self.findChallengeByName(item.text(0))
    text = 'Skills:\n\n' + ', '.join(challenge.skills) + \
                '\n\n\nSummary:\n\n' + challenge.summary + \
                '\n\n\nDescription:\n\n' + challenge.description + \
                '\n\n\nRecommended readings: \n\n' + '\n'.join(challenge.recommendedReadings)
    self.ui.recommendedDescription.setText(text)

  def selectChallenge(self, item, column):
    self.viewedChallenge = str(item.text(0))

    #get challenge details
    challenge = self.findChallengeByName(item.text(column))
    text = 'Skills:\n\n' + ', '.join(challenge.skills) + \
                '\n\n\nSummary:\n\n' + challenge.summary + \
                '\n\n\nDescription:\n\n' + challenge.description + \
                '\n\n\nRecommended readings: \n\n' + '\n'.join(challenge.recommendedReadings)
    self.ui.challengeDescription.setText(text)

    #set the similarity list
    self.ui.allSimilarities.clear()
    orderedCol = self.similarities[challenge.name].sort_values(ascending=0)
    for name, value in orderedCol.iteritems():
      # name = orderedCol.index[i];
      a = QtGui.QTreeWidgetItem(self.ui.allSimilarities)
      a.setText(0, name)
      a.setText(1, "%.4f" % value)

    #get the recommendations

    recommendations = self.cb.recommendForChallenge(challenge.name)
    self.ui.recommendedList.clear()

    for name, similarity in recommendations.iteritems():
      a = QtGui.QTreeWidgetItem(self.ui.recommendedList)
      a.setText(0, name)

      if self.viewedChallenge in self.evalDataForChallenges:
        if QtCore.QString(name) in self.evalDataForChallenges[self.viewedChallenge].getEvaluationData():
          a.setText(1, self.evalDataForChallenges[self.viewedChallenge].getEvaluationData()[QtCore.QString(name)])
        else:
          a.setText(1, '-')
      else:
        a.setText(1, '-')

if __name__ == "__main__":
  app = QtGui.QApplication(sys.argv)
  myapp = StartQT4()
  myapp.show()
  sys.exit(app.exec_())
