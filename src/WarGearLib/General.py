from xml.dom.minidom import parse, Document
import random
import re
from PIL import Image
from math import floor, ceil, sqrt
import string
import ImageFont, ImageDraw
from sys import exc_info
import traceback

'''
:module: WGLib
:platform: Unix, Windows
:synopsis: The WGLib module gives access to the WGMap base class as well as more specialized children.  These classes are used to create, load, modify & save War Gear Maps (XML & PNG files).

.. moduleauthor:: Ozyman



@todo: Need to finish wrapping up method groups that do the same thing 
with different arguments. i.e. add a single method that uses try/except 
to figure out what specific method to call.
           also make the sub methods private.  see deleteTerritory().
           (or maybe the by ID one should be public?)

@todo make documentation look better
      http://packages.python.org/an_example_pypi_project/sphinx.html

'''


class WGMap(object):
  """
  load, save, store and access a WarGear map
  The map state is represented internally by an XML DOM.

  """

  def __init__(self):
    """Constructor"""
    self.DOM = None

    
  def saveMapToFile(self, filePath, printStats=True):
    """
    Save the XML.

    Args:
      filePath (str): 

    >>> saveMapToFile(//SERVER/path/to/map/MapName.xml)    
    """
    if(printStats):
      self.printStatistics()
    fileHandle = open(filePath,'w')
    #print "DOM: ",self.DOM.toxml()
    fileHandle.write(self.DOM.toxml())
    fileHandle.close()

  def loadMapFromFile(self, filePath):
    """
    Loads the state of a map from an XML document.

    Args:
    filePath (str):

    """
    fileHandle = open(filePath)    
    self.DOM = parse(fileHandle)    

  def printDOM(self):
    """Print the DOM to stdout in XML format."""
    print self.DOM.toxml()

  def createBoard(self, boardName, versionMaj="1", versionMin="0", minPlayers="2",
                  maxPlayers="16", 
                  availablePlayers="2,3,4,5,7,8,9,10,12,13,14,15,16", 
                  gameplayType="Turn Based"):
    '''
    Add a <board> element to the DOM.

    note: all arguments are strings
    note: some problems?  Better to create a new board on wargear.net, export the XML, and use
    loadMapFromFile()
    
    '''
    #self.DOM = Document()
    newWGXMLElement = self.DOM.createElement("WarGearXML")
    self.DOM.appendChild(newWGXMLElement)

    newBoardElement = self.DOM.createElement("board")
    newBoardElement.setAttribute("boardname",str(boardName))
    newBoardElement.setAttribute("version_major",str(versionMaj))
    newBoardElement.setAttribute("version_minor",str(versionMin))
    newBoardElement.setAttribute("min_players",str(minPlayers))
    newBoardElement.setAttribute("max_players",str(maxPlayers))
    newBoardElement.setAttribute("available_players",str(availablePlayers))
    newBoardElement.setAttribute("gameplay_type",str(gameplayType))

    newWGXMLElement.appendChild(newBoardElement)
  
  # todo, check getNeighbors() to take into account one-way borders
  def checkOneTerritoryCanReachAll(self, territoryID=None):
    '''
    Test if the specified territory can reach all other territories.
    
    Args:
    territoryID (int): The territory ID for testing.  
    If no territory ID is given, the first territory in the DOM is used.

    '''
    # initial setup 
    self.printDOM()
    if territoryID == None:
      territoryID = self.DOM.getElementsByTagName("territory")[0].getAttribute("tid")
    #print "territoryID",territoryID
    territoriesReached = set(territoryID)
    #print "territoriesReached",territoriesReached
    territoriesToCheck = set() #territories that have neighbors we may not have looked at yet

    # account for neighbors of first territory
    territoriesToCheck |= self.getNeighborIDsFromID(territoryID)

    #print "territoriesToCheck", territoriesToCheck
    while len(territoriesToCheck) > 0:
      # get a territory to check/reach
      territoryID = territoriesToCheck.pop()
      #print "looking at",territoryID
      # find all of it's neighbors
      neighbors = self.getNeighborIDsFromID(territoryID)
      #print "neighbors", neighbors
      # add any newly available territories
      territoriesToCheck |= (neighbors - territoriesReached)
      #print "territoriesToCheck", territoriesToCheck
      
      territoriesReached.add(territoryID)
   
    # get a set of all the territory ID
    allTerritories = set()
    for territory in  self.DOM.getElementsByTagName("territory"):
      allTerritories.add(territory.getAttribute("tid"))

    #print "allTerritories",allTerritories
    #print "territoriesReached",territoriesReached
    territoriesMissed = allTerritories - territoriesReached
    if len(territoriesMissed) == 0:
      return True
    else:
      print "all territories:", self.getTerritoryNameFromID(allTerritories)
      print "territories reached:",self.getTerritoryNameFromID(territoriesReached)
      print "territories missed: ", self.getTerritoryNameFromID(allTerritories - territoriesReached)
      
      return False
  
  
  def setAllSoleContinentTerritoriesToNeutral(self,neutralBase=3):
    '''
    Find all continents that only have one member, and set that member to neutral
    Unit count is equal to the total continent bonus + neutralBase
    '''
    # <territory id="1360487" tid="229" boardid="1213" name="T20" xpos="553" ypos="543" max_units="0" 
    # scenario_type="Neutral" scenario_seat="0" scenario_units="5" /> 
    # <rules ... initial_setup="Scenario based" 
    #self.printDOM()
    territoryIDAndValue = {}
    for continent in self.DOM.getElementsByTagName("continent"):
      #print continent.getAttribute("members")
      if (len(continent.getAttribute("members").split(',')) == 1):
        territoryIDAndValue[continent.getAttribute("members")] = territoryIDAndValue.get(continent.getAttribute("members"),0)+int(continent.getAttribute("bonus"))
        #print "adding",continent.getAttribute("members")
    
    for tid in territoryIDAndValue.keys():
      territoryElement = self.getTerritoryElement(tid)
      territoryElement.setAttribute("scenario_type","Neutral")
      territoryElement.setAttribute("scenario_units",str(int(neutralBase)+territoryIDAndValue[tid]))
    
    
    self.DOM.getElementsByTagName("rules")[0].setAttribute("initial_setup","Scenario based")
  
  def addCollectorContinents(self, IDSet, individualBonus = "1", pairBonus="1" ):
    
    individualBonus = str(individualBonus)
    pairBonus = str(pairBonus)
    
    IDSet2 = set(IDSet)
    for a in IDSet:
      print "adding",a,IDSet2
      IDSet2.remove(a)
      aName = self.getTerritoryNameFromID(a)
      self.addContinent(aName,set(a),individualBonus)
      for b in IDSet2:
        abName = str(a)+ "_" + str(b)        
        self.addContinent(abName,set([a,b]),pairBonus)
        
    
  
  def hordify(self, bonus="1", continentNameSuffix="", 
              baseRegex=".*", neighborRegex=".*",verificationMode=False):
    '''
    Add continents in a "hordes" style.  For all territories that match baseRegex, a continent is created
    whose members are the original territory and all of the neighbors who match neighborRegex.  

    Args:
      bonus (int): The number of units a player will get for controlling this continent
      continentNameSuffix (str): This is added to the base territory name to get the continent name
      baseRegex (str): Only territorires that match this regex will have continents added.
      neighborRegex (str): Only neighbors that match this regex will be members of the new continents.
      verificationMode (bool): Verifies continent was added succesfully (for testing).
    '''
    
    # visit every territory
    territoryElementList = self.DOM.getElementsByTagName("territory")
    for territoryElement in territoryElementList:
      territoryName = territoryElement.getAttribute("name")
      hordesTerritoryName = territoryName + continentNameSuffix
      #print "comparing: ",baseRegex,territoryName
      if (None == re.search(baseRegex,territoryName)):
        #print "no match"
        continue
      # collect the neighbors & self
      neighborElementSet = self.getNeighbors(territoryElement, "either",neighborRegex)
      neighborElementSet.add(territoryElement)
      if (verificationMode):
        continentElement = self.getContinentFromMembers(neighborElementSet)
        if (None != continentElement):
          print "Hordify Continent:",hordesTerritoryName,"found:",continentElement
        else:
          print "Hordify Continent:",hordesTerritoryName,"MISSING!"
      else:  
        # add the continent
        self.addContinentFromElements(hordesTerritoryName, neighborElementSet, bonus)
      

  # what is the smallest continent that this territory is a member of.
  def getMinContinentSize(self, territoryName):
    """
    Find the smallest continent that territoryName is a member of.

    Args:
      territoryName (str): The territory name to look for.
    """
    minCS = 999999  #ugly hack
    tid = self.getTerritoryIDFromName(territoryName)
    for continent in self.DOM.getElementsByTagName("continent"):
      if tid in continent.getAttribute("members").split(','):
        size = len(continent.getAttribute("members").split(','))
        if (size < minCS):
          minCS = size
    return minCS

  '''
  def getMinContinentSize(self):
    minCS = len(self.DOM.getElementsByTagName("continent").getAttribute("members").split(','))
    for continent in self.DOM.getElementsByTagName("continent"):
      size = len(continent.getAttribute("members").split(','))
      if (size < minCS):
        minCS = size
    return minCS

  def maxContinentSize(self):
    maxCS = 0
    for continent in self.DOM.getElementsByTagName("continent"):
      size = len(continent.getAttribute("members").split(','))
      if (size > maxCS):
        maxCS = size
    return maxCS
  '''

  def getTerritoryIDsFromNameRegex(self, territoryNameRegex):
    '''
    Given a territory name regex return a list of all of the IDs that match
    
    Args:
      territoryNameRegex (str): The name to look for.    
    '''
    returnSet = set()
    for territoryElement in self.DOM.getElementsByTagName("territory"):
      territoryName = territoryElement.getAttribute("name")
      print "comparing",territoryNameRegex,territoryName
      if (None != re.search(territoryNameRegex,territoryName)):
        returnSet.add(territoryElement.getAttribute("tid"))
    #print "found no match for", territoryName
    return returnSet
        


  def getTerritoryIDFromName(self, territoryName):
    '''
    Given a territory name find the ID for that territory (or None if not found)
    Args:
      territoryName (str): The name to look for.

    '''
    for territory in self.DOM.getElementsByTagName("territory"):      
      if (territory.getAttribute("name") == territoryName):
        #print "found a match",territory.getAttribute("name"),territoryName,"with id",territory.getAttribute("tid")
        return territory.getAttribute("tid")
    #print "found no match for", territoryName
    return False 
        
  
  def getTerritoryNameFromID(self, territoryID):
    '''
    Given a territory ID find the name for that territory (or None if not found)
    
    Args:
      territoryName (str): The name to look for.

    '''
    names = []
    for tid in territoryID:
      #print "searching <territory>s for",tid
      for territory in self.DOM.getElementsByTagName("territory"):
        if (territory.getAttribute("tid") == tid):
          names.append(territory.getAttribute("name"))
      names.append(None)
      
    return names
  
  def getAllTerritoriesWithinNBorders(self,territoryID,nBorders,direction="to"):
    
    tid = int(territoryID)
    print"gatwnb called with",tid, nBorders
    borderDepth = 0
    allTerritoriesInReach = set()
    allTerritoriesInReach.add(tid)
    while(borderDepth < nBorders):
      allTerritoriesAddition = set()
      for tirID in allTerritoriesInReach:
        tb = self.getBorderTerritoryIDsByTerritoryID(tirID,direction)
        #print "for",tirID,"found borders:",tb        
        allTerritoriesAddition |= set(tb)
      allTerritoriesInReach |= allTerritoriesAddition
      borderDepth = borderDepth + 1 
   
    #print "atir",allTerritoriesInReach
    allTerritoriesInReach.discard(tid)
    print "returning", allTerritoriesInReach
    return allTerritoriesInReach
 
  def getATerritoryWithNBorders(self,nBorders):
    
    for territory in self.DOM.getElementsByTagName("territory"):
      if (len(self.getTerritoryBordersByElement(territory)) == nBorders):
        return territory
      
    return None
    
  
  def getBorderElementsByTerritoryID(self, territoryID,direction="either"):
    ''' 
    Get a collection of borders for this territory.
    Args:
      Identifier: territory ID 
    '''
    borders = self.DOM.getElementsByTagName("border")
    tid = str(territoryID)
    tb = []
    for border in borders:
      if (direction == "either" or direction == "to"):
        if ((tid == border.getAttribute("fromid")) or (tid == border.getAttribute("toid") and border.getAttribute("direction") == "Two-way")):
          tb.append(border)
      if (direction == "either" or direction == "from"):          
        if ((tid == border.getAttribute("toid")) or (tid == border.getAttribute("fromid") and border.getAttribute("direction") == "Two-way")):
          tb.append(border)
    return tb
  
  def getBorderTerritoryIDsByTerritoryID(self, territoryID, direction="either"):
    
    ''' 
    Get a collection of borders for this territory.
    Args:
      territoryID: territory ID
      direction: "either","to", or "from"
      
    '''
    borders = self.DOM.getElementsByTagName("border")
    tid = str(territoryID)
    tb = []
    for border in borders:
      if (direction == "either" or direction == "to" ):
        if (tid == border.getAttribute("fromid")):
          tb.append(int(border.getAttribute("toid")))
        if (tid == border.getAttribute("toid") and border.getAttribute("direction") == "Two-way"):
           tb.append(int(border.getAttribute("fromid")))         
      if (direction == "either" or direction == "from" ):          
        if (tid == border.getAttribute("toid")):
          tb.append(int(border.getAttribute("fromid")))  
        if (tid == border.getAttribute("fromid") and border.getAttribute("direction") == "Two-way"):
          tb.append(int(border.getAttribute("toid")))
    return tb

  def getTerritoryBordersByElement(self, territoryElement):
    ''' 
    Get a collection of borders for this territory.
    Args:
      Identifier: territoryElement
    '''
    tid = territoryElement.getAttribute("tid")
    return self.getBorderElementsByTerritoryID(tid)

  def getTerritoryElement(self, identifier):
    ''' 
    Get the territory Element based upon a name or territory ID.
    Args:
      Identifier: can be a Name or territory ID 
    '''
    #print "getTerritoryElement called with identity: ",identifier
    
    try:
      ID = int(identifier)
      #got a territory ID
      #print "getting territory element by ID",identifier
      return self.__getTerritoryElementByID(ID)

    except:
      #print "caught error:", exc_info()[0]
      #traceback.print_exc()
      # 
      # must be a name
      #print "getting territory element by name",identifier
      return self.__getTerritoryElementByName(identifier)
 
        
  def __getTerritoryElementByName(self, name):
    for territory in self.DOM.getElementsByTagName("territory"):
      if territory.getAttribute("name") == name:
        return territory
    return None

  def __getTerritoryElementByID(self, tid):
    for territory in self.DOM.getElementsByTagName("territory"):
      #print "comparing",territory.getAttribute("tid"), tid
      if int(territory.getAttribute("tid")) == int(tid):
        return territory
    return None
    

  def getNeighbors(self, territoryElement, direction="either", neighborRegex=".*"):
    '''
    Get a list of the IDs of the neighbors of a territory that match the neigborRegex.
    
    Args:
      territoryElement (DOMElement): The territory to find neighbors for.
      direction (string): valid values: "to", "from", or "either"
      neigborRegex (str): neigbors that do not match this are not added to the list.
    '''
    print "finding neighbors for",territoryElement.getAttribute("name")
    territoryID = territoryElement.getAttribute("tid")
    return self.getNeighborsFromID(territoryID,direction, neighborRegex)

  def getNeighborIDsFromID(self, territoryID, direction="either", neighborRegex=".*"):
    '''
    Given territoryID return all IDs of all other territories that share a border with it.
    
    Args:
      territoryID (int): The ID for which neighbors are found.
      direction (int): A string describing the type of neighbor to find.  Valid values::
        "to"
        "from"
        "either"
      nieghborRegex (str): Only include neighbors in the returned set if their name matches this regex.

    .. warning::
      direction is not working(?)

    '''
    neighborIDs = set()
    for neighbor in self.getNeighborsFromID(territoryID, direction, neighborRegex):
      neighborIDs.add(neighbor.getAttribute("tid"))

    return neighborIDs


  # todo: check that direction works.  We are not looking at 'one-way' vs. 'two-way'
  def getNeighborsFromID(self, territoryID, direction="either", neighborRegex=".*"):
    '''
    Given territoryID return all IDs of all other territories that share a border with it.
    
    Args:
      territoryID (int): The ID for which neighbors are found.
      direction (int): A string describing the type of neighbor to find.  Valid values::
        "to"
        "from"
        "either"
      nieghborRegex (str): Only include neighbors in the returned set if their name matches this regex.

    .. warning::
      direction is currently ignored

    '''
    print "finding neighbors for", territoryID, "with direction",direction
    neighbors = set()
    for border in self.DOM.getElementsByTagName("border"):
      print "border",border
      if territoryID == border.getAttribute("fromid"):
        print "looking for t:",border.getAttribute("toid")
        neighbor = self.getTerritoryElement(border.getAttribute("toid"))
        print "comparing:",neighborRegex,neighbor.getAttribute("name"),re.search(neighborRegex,neighbor.getAttribute("name"))
        if ((direction == "either" or direction == "from") and None != re.search(neighborRegex,neighbor.getAttribute("name"))):
          neighbors.add(neighbor)
          print "adding",neighbor
      if territoryID == border.getAttribute("toid"):
        print "looking for f:",border.getAttribute("fromid")
        neighbor = self.getTerritoryElement(border.getAttribute("fromid"))
        print "comparing:",neighborRegex,neighbor.getAttribute("name"),re.search(neighborRegex,neighbor.getAttribute("name"))
        if ((direction == "either" or direction == "to") and None != re.search(neighborRegex,neighbor.getAttribute("name"))):
          neighbors.add(neighbor)
          print "adding",neighbor
    print "found neighbors",neighbors
    return neighbors

  # todo: cache this?
  
  def getBorderCount(self, territoryID):
    '''
    returns the # of borders that a territory identified by territoryID has
    '''
    borderCount = 0
    for borderElement in self.DOM.getElementsByTagName("border"):
      if borderElement.getAttribute("toid") == territoryID:
        borderCount += 1
      if borderElement.getAttribute("fromid") == territoryID:
        borderCount += 1

    return borderCount

     
  
  def getBorderCounts(self, direction="Two-way"):
    '''
    Returns: 
      dictionary w/ key=territoryName & value=count of their borders
    
    Args:
      direction (int): A string describing the type of neighbor to find.  Valid values::
        "to"
        "from"
        "either"

    .. warning::
      direction is currently ignored
    '''

    borderCounts = {}
    for territoryElement in self.DOM.getElementsByTagName("territory"):
      territoryName = territoryElement.getAttribute("name")
      territoryID = territoryElement.getAttribute("tid")

      borderCounts[territoryName] = 0

      for borderElement in self.DOM.getElementsByTagName("border"):
        if borderElement.getAttribute("toid") == territoryID:
          borderCounts[territoryName] += 1
        if borderElement.getAttribute("fromid") == territoryID:
          borderCounts[territoryName] += 1

    return borderCounts


  def getMostBorderedTerritory(self, direction="Two-way"):
    '''
    Returns: 
      territoryName with the most borders & number of borders
    
    Args:
      direction (int): A string describing the type of neighbor to find.  Valid values::
        "to"
        "from"
        "either"

    .. note::
      In the case of a tie, one of the winners will be returned arbitrarily
    .. warning::
      direction is currently ignored
    '''
    # count up the borders
    borderCounts = self.getBorderCounts(direction)
    # find the max
    returnName = ""
    maxBorders = 0
    for BName,BCount in borderCounts.iteritems():
      if BCount > maxBorders:
        returnName = BName
        maxBorders = BCount

    return returnName, maxBorders

  def getLargestBonusContinent(self):
    '''
    Returns: 
      continentName with the largest bonus & that bonus
    
    .. note::
      In the case of a tie, one of the winners will be returned arbitrarily
    '''
    
    maxBonus = int(self.DOM.getElementsByTagName("continent")[0].getAttribute("bonus"))
    returnName = self.DOM.getElementsByTagName("continent")[0].getAttribute("name")
    for continentElement in self.DOM.getElementsByTagName("continent"):
      bonus = int(continentElement.getAttribute("bonus"))
      if (bonus > maxBonus):
        maxBonus = bonus
        returnName = continentElement.getAttribute("name")

    return returnName,maxBonus

  def getContinentMembersFromName(self,continentName):
    for continentElement in self.DOM.getElementsByTagName("continent"):
      if continentElement.getAttribute("name") == continentName:
        return continentElement.getAttribute("members")
       
    return None

  def getContinentFromMembers(self,neighborElementList):
    '''
    Args:
      neigbhorElementList (list): A list of neighbor elements to compare against.
    
    Returns:
      The first continentElement that has the same neighbors as the neighborElementList (or None)
    '''
    territoryIDSet = set(neighborElementList)

    for continentElement in self.DOM.getElementsByTagName("continent"):
      if set(continentElement.getAttribute("members")) == territoryIDSet:
        return continentElement
    return None

  def getContinentsWithTerritory(self, territoryID):
    '''
    Args:
      territoryID (int): A territory ID to look for.
    
    Returns:
      A set of all continentElements that have territoryID as a member. 
    '''
    continentSet = set()
    for continent in self.DOM.getElementsByTagName("continent"):
      if territoryID in continent.getAttribute("members").split(','):
        continentSet.add(continent)

    return continentSet

  def setBoardName(self, boardName):
    '''
    Sets the "boardname" attribute of the "board" element.
    '''
    self.DOM.getElementsByTagName("board")[0].setAttribute("boardname",str(boardName))

  def setNumAttacks(self, numAttacks):
    '''
    Sets the 'num_attacks' attribute of the 'rules' element.  numAttacks should be a number or 'Unlimited'
    '''
    self.DOM.getElementsByTagName("rules")[0].setAttribute("num_attacks",str(numAttacks))
    
  def setNumFortifies(self, numFortifies):
    '''
    Sets the 'num_fortifies' attribute of the 'rules' element.  numFortifies should be a number or 'Unlimited'
    '''
    self.DOM.getElementsByTagName("rules")[0].setAttribute("num_fortifies",str(numFortifies))
    

  def setEliminationBonus(self, bonus):
    '''
    Sets the 'elimination_bonus' attribute of the 'rules' element.  maxCabonusrds should be a number
    '''
    self.DOM.getElementsByTagName("rules")[0].setAttribute("elimination_bonus",str(bonus))
    
  def setMaxCards(self, maxCards):
    '''
    Sets the 'card_max_accrual' attribute of the 'rules' element.  maxCards should be a number or 'Unlimited'
    '''
    self.DOM.getElementsByTagName("rules")[0].setAttribute("card_max_accrual",str(maxCards))

def addBordersToSet(fromID, toIDs, direction='Two-way', 
                type = "Default", ftattackmod = "0",
                ftdefendmod="0", tfattackmod="0",
                tfdefendmod="0", ftattackmin="0",
                ftdefendmin="0", tfattackmin="0", 
                tfdefendmin="0"):
  for toID in toIDs:
    addBorder(fromID,toID,direction, type, ftattackmod,
                ftdefendmod, tfattackmod, tfdefendmod, ftattackmin,
                ftdefendmin, tfattackmin,tfdefendmin) 
         
     
  def addBorders(self,fromRegex,toRegex, direction = "Two-way", 
                type = "Default", ftattackmod = "0",
                ftdefendmod="0", tfattackmod="0",
                tfdefendmod="0", ftattackmin="0",
                ftdefendmin="0", tfattackmin="0", 
                tfdefendmin="0"):
    '''
    Adds borders between every country that matches the fromRegex to every country that matches the toRegex.
    '''
    
    for fromElement in self.DOM.getElementsByTagName("territory"):
      print "comparing: ",fromRegex,fromElement.getAttribute("name")
      if (None != re.search(fromRegex,fromElement.getAttribute("name"))):
        for toElement in self.DOM.getElementsByTagName("territory"):
          if (None != re.search(toRegex,toElement.getAttribute("name"))):
            print"found a match from:", fromElement.getAttribute("name"),"to:", toElement.getAttribute("name")
            self.addBorder(fromElement.getAttribute("tid"),toElement.getAttribute("tid"), \
                            direction, type, ftattackmod, ftdefendmod, tfattackmod, \
                            tfdefendmod, ftattackmin, ftdefendmin, tfattackmin, tfdefendmin )      
  
  def addBorder(self, fromIdentifier, toIdentifier, direction="Two-way", type = "Default", ftattackmod = "0",
                ftdefendmod="0", tfattackmod="0",
                tfdefendmod="0", ftattackmin="0",
                ftdefendmin="0", tfattackmin="0", 
                tfdefendmin="0"):
    ''' 
    Adds borders based upon names or territory IDs.
    Arguments correspond to attributes of the new border element.
    
    Args:
      from/to Identifiers: can be a Name or territory ID, but both must be the same 
      
    .. note::
       a "borders" element is created if it does not already exist
       
    .. warning::
      If your territory names are integers, they will get treated as tid attributes, so don't do this!!

    '''
    #print "add border called with identity: ",fromIdentifier,toIdentifier
    
    try:
      fromID = int(fromIdentifier)
      toID = int(toIdentifier)
      #got a territory ID
      #print "getting territory element by ID",fromIdentifier,toIdentifier
      return self.__addBorderByID(fromID,toID,direction, type, ftattackmod,
                ftdefendmod, tfattackmod,
                tfdefendmod, ftattackmin,
                ftdefendmin, tfattackmin, 
                tfdefendmin)

    except:
      #print "caught error:", exc_info()[0]
      #traceback.print_exc()

      # must be a name
      #print "adding borders by name",fromIdentifier,toIdentifier
      return self.__addBorderByName(fromIdentifier,toIdentifier,direction, type, ftattackmod,
                ftdefendmod, tfattackmod,
                tfdefendmod, ftattackmin,
                ftdefendmin, tfattackmin, 
                tfdefendmin)
    
  def __addBorderByName(self, fromName, toName, direction = "Two-way", 
                type = "Default", ftattackmod = "0",
                ftdefendmod="0", tfattackmod="0",
                tfdefendmod="0", ftattackmin="0",
                ftdefendmin="0", tfattackmin="0", 
                tfdefendmin="0"):
      #print "name - adding border from ",fromName,toName
      fromID = self.getTerritoryIDFromName(fromName)
      toID = self.getTerritoryIDFromName(toName)
      
      #print "attempting to add a border between",fromID,toID
      if fromID != False and toID != False :
        #print "adding border between",fromID,toID
        return self.__addBorderByID(fromID, toID, direction, type, ftattackmod,
                ftdefendmod, tfattackmod,
                tfdefendmod, ftattackmin,
                ftdefendmin, tfattackmin, 
                tfdefendmin)

    
  def __addBorderByID(self, fromid, toid, direction = "Two-way", 
                type = "Default", ftattackmod = "0",
                ftdefendmod="0", tfattackmod="0",
                tfdefendmod="0", ftattackmin="0",
                ftdefendmin="0", tfattackmin="0", 
                tfdefendmin="0"):
    '''
    Adds a border.  Arguments correspond to attributes of the new border element.

    .. note::
       a "borders" element is created if it does not already exist
    '''
    #print "ID - adding border from ",fromid,toid
    
    if (self.doTheyBorder(fromid, toid)):
      return False

    newBorderElement = self.DOM.createElement("border")
    newBorderElement.setAttribute("fromid",str(fromid))
    newBorderElement.setAttribute("toid",str(toid))
    newBorderElement.setAttribute("direction",str(direction))
    newBorderElement.setAttribute("type",str(type))
    newBorderElement.setAttribute("ftattackmod",str(ftattackmod))
    newBorderElement.setAttribute("ftdefendmod",str(ftdefendmod))
    newBorderElement.setAttribute("tfattackmod",str(tfattackmod))
    newBorderElement.setAttribute("ftdefendmod",str(ftdefendmod))
    newBorderElement.setAttribute("ftattackmin",str(ftattackmin))
    newBorderElement.setAttribute("ftdefendmin",str(ftdefendmin))
    newBorderElement.setAttribute("tfattackmin",str(tfattackmin))
    newBorderElement.setAttribute("tfdefendmin",str(tfdefendmin))

    bordersElements = self.DOM.getElementsByTagName("borders")
    #print bordersElements
    if (bordersElements == None or len(bordersElements) == 0):
      bordersElement = self.DOM.createElement("borders")
      bordersElement.appendChild(newBorderElement)
      self.DOM.getElementsByTagName("WarGearXML")[0].appendChild(bordersElement)
    else:
      bordersElements[0].appendChild(newBorderElement)


  def addTerritory(self, name, xpos, ypos, maxUnits = ""):
    '''
    Adds a territory.  Arguments correspond to attributes of the new territory element.

    .. note::
       a "territories" element is created if it does not already exist
    '''
    
    #import pdb; pdb.set_trace()

    #print "adding territory",name,xpos,ypos
    # get max tid (or 0) & start at one greater
    maxTID = 0
    for territory in self.DOM.getElementsByTagName("territory"):
      if (maxTID <1+ int(territory.getAttribute("tid"))):
        maxTID = 1+int(territory.getAttribute("tid"))

    newTerritoryElement = self.DOM.createElement("territory")
    newTerritoryElement.setAttribute("name",str(name))
    newTerritoryElement.setAttribute("xpos",str(xpos))
    newTerritoryElement.setAttribute("ypos",str(ypos))
    newTerritoryElement.setAttribute("max_units",str(maxUnits))
    newTerritoryElement.setAttribute("tid",str(maxTID))

    territoriesElements = self.DOM.getElementsByTagName("territories")
    if (territoriesElements == None or territoriesElements.length == 0):
      territoriesElement = self.DOM.createElement("territories")
      wge = self.DOM.getElementsByTagName("WarGearXML")[0]
      wge.appendChild(territoriesElement)
      territoriesElement.appendChild(newTerritoryElement)

    else:
      territoriesElements[0].appendChild(newTerritoryElement)

  def addContinentFromElements(self, continentName, territoryElementList, bonus=1):
    '''
    Adds a continent.  Arguments correspond to attributes of the new continent element.

    .. note::
       a "continents" element is created if it does not already exist
    '''
    print "addContinentFromElements:", continentName, territoryElementList, bonus
    territoryIDList = []
    for territoryElement in territoryElementList:
      territoryIDList.append(territoryElement.getAttribute("tid"))
    territoryIDsString = ",".join(territoryIDList)
    self.addContinent(continentName,territoryIDsString, bonus)

  def addContinent(self, continentName, memberIDsString, bonus=1):
    '''
    Adds a continent.  Arguments correspond to attributes of the new continent element.

    .. note::
       a "continents" element is created if it does not already exist
    '''
    print "Adding Continent",continentName, memberIDsString, bonus
    newContinentElement = self.DOM.createElement("continent")
    newContinentElement.setAttribute("boardid",str(
        self.DOM.getElementsByTagName("board")[0].getAttribute("boardid")))
    newContinentElement.setAttribute("name",str(continentName))
    newContinentElement.setAttribute("bonus",str(bonus))
    newContinentElement.setAttribute("members",str(memberIDsString))

    continentsElements = self.DOM.getElementsByTagName("continents")
#    print "adding continent",str(newContinentElement)
    if (continentsElements == None or len(continentsElements) == 0):
      continentsElement = self.DOM.createElement("continents")
      continentsElement.appendChild(newContinentElement)
      self.DOM.getElementsByTagName("WarGearXML")[0].appendChild(continentsElement)
    else:
      continentsElements[0].appendChild(newContinentElement)


       
  def printBorderDistributionTable(self):
    '''
    Prints a table to show how many territories there are with N borders.
    '''
    print "Distribution  of  Borders"
    print "-------------------------"
    print "# Borders | # Territories"

    maxBName, maxB = self.getMostBorderedTerritory()
    for ixBorder in range(0,maxB+1):
      print repr(ixBorder).rjust(8),' |',repr(self.countTerritoriesWithBorders(ixBorder)).rjust(6)



  def printContinentBonusDistributionTable(self):
    '''
    Prints a table to show how many continents there are with a bonus of N.
    '''
    print "Distribution of Continent Bonuses"
    print "---------------------------------"
    print "  Bonus |  # of Continents"
    maxBName, maxB = self.getLargestBonusContinent()
    for ixBonus in range(0,maxB+1):
      print repr(ixBonus).rjust(6),' |',repr(self.countContinentsWithBonus(ixBonus)).rjust(6)
          
  def printStatistics(self):
    '''
    Print some statistics about a map.
    '''
    print "Map Name:",self.DOM.getElementsByTagName("board")[0].getAttribute("boardname")
    print "# of Territories:",len(self.DOM.getElementsByTagName("territory"))
    print "# of Continents:",len(self.DOM.getElementsByTagName("continent"))
    print "# of Borders:",len(self.DOM.getElementsByTagName("border"))
    print "Total Continent Bonus",self.calculateTotalContinentBonus()
    print "Total Territory Bonus",self.calculateTotalTerritoryBonus()
    print "Total Bonus",self.calculateTotalBoardBonus()
    print ""
    self.printBorderDistributionTable()
    print ""
    #self.printContinentBonusDistributionTable()

 
  def calculateTotalContinentBonus(self):
    ''' calculateTotalContinentBonus '''
    total = 0
    for continentElement in self.DOM.getElementsByTagName("continent"):
      total += int(continentElement.getAttribute("bonus"))
    return total

  # todo: check that return value is rounding correctly
  def calculateTotalTerritoryBonus(self):
    ''' calculateTotalTerritoryBonus '''
    territoryCount = len(self.DOM.getElementsByTagName("territory"))
    return territoryCount / int(self.DOM.getElementsByTagName("rules")[0].getAttribute("bonus_per_x_territories"))



  def calculateTotalBoardBonus(self):
    ''' calculateTotalBoardBonus '''
    return self.calculateTotalContinentBonus() + self.calculateTotalTerritoryBonus()


  '''  Never finished this.  Instead it would be useful to have functions that calculate graph properties like:
  * http://en.wikipedia.org/wiki/Centrality
  ** http://en.wikipedia.org/wiki/Betweenness_Centrality
  ** http://en.wikipedia.org/wiki/Degree_%28graph_theory%29
  * http://en.wikipedia.org/l/Menger's_theorem
  * http://en.wikipedia.org/wiki/Clustering_coefficient
  * http://en.wikipedia.org/wiki/Cheeger_constant_%28graph_theory%29
  
     
  def calculateChokePoints(self):
    
    # for every territory alculate
    
    # iterate over every territory
    territories = self.DOM.getElementsByTagName("territory")
    for chokepointTerritory in territories:
      for sourceTerritory in territories:
        for destTerritory in territories:
          
        shortestDistance = self.findShortestDistance(sourceTerritory,destTerritory)
        shortestDistanceAvoiding =  self.findShortestDistance(sourceTerritory,destTerritory,chokepointTerritory)
  '''        


  # count how many territories have numBorders
  def countTerritoriesWithBorders(self, numBorders, direction="Two-way"):
    '''  '''
    borderCounts = self.getBorderCounts(direction)
    count = 0;
    for BName,BCount in borderCounts.iteritems():
      if (BCount == numBorders):
        count += 1

    return count;

  # count how many continents have numBonus
  def countContinentsWithBonus(self, numBonus):
    ''' '''
    count = 0;
    for continentElement in self.DOM.getElementsByTagName("continent"):
      #print "continent",continentElement.getAttribute("name")
      #print "bonus",continentElement.getAttribute("bonus")
      if (int(continentElement.getAttribute("bonus")) == numBonus):
        #print "found one with bonus=",numBonus
        count += 1

    return count;

  def doTheyBorder(self, ID1, ID2):
    '''
    Return true if the territories identified by ID1 & ID2 share a border.  False otherwise
    '''
    #print "checking for border:",ID1,ID2
    for borderElement in self.DOM.getElementsByTagName("border"):
      fromID = borderElement.getAttribute("fromid")
      toID =  borderElement.getAttribute("toid")
      if (fromID == ID1 and toID == ID2):
        #print "border found",ID1,ID2
        return True
      if (fromID == ID2 and toID == ID1):
       # print "border found",ID1,ID2
        return True
      
    #print "border not found"
    return False
    
    




  def deleteTerritory(self, identifier):
    ''' 
    Delete a territory.
    
    Args:
      identifier can be a Name or ID 
    '''
    #print "deleting territory",identifier
    try:
      ID = int(identifier)
      #got a identifier ID
      return self.__deleteTerritoryByID(ID)  

    except:
      # must be a name
      return self.__deleteTerritoryByName(identifier)
  
  
  def __deleteTerritoryByName(self, territoryName):
    for territory in self.DOM.getElementsByTagName("territory"):
      if (territory.getAttribute("name") == territoryName):
        return self.__deleteTerritoryByID(territory.getAttribute("tid"))
    return False

  def __deleteTerritoryByID(self, territoryID):
    ''' 
     deletes a territory from the XML, includes relevant borders, 
     and removes itself from continents

     returns false if the territoryID was not found, true otherwise
    '''

    # delete the territory element from the DOM
    found = False
    for territoryElement in self.DOM.getElementsByTagName("territory"):
      if (territoryElement.getAttribute("tid") == territoryID):
        found = True
        territoryElement.parentNode.removeChild(territoryElement)
        territoryElement.unlink()
   
    if not found:
      return False
    # todo: move this to a function
    # find borders that include this territoryID, and remove them
    for borderElement in self.DOM.getElementsByTagName("border"):
      if (borderElement.getAttribute("fromid") == territoryID or 
        borderElement.getAttribute("toid") == territoryID):
        borderElement.parentNode.removeChild(borderElement)
        borderElement.unlink()

    # todo: move this to a function
    # remove this territoryID from all continent member lists
    # remove the continent if there are no longer any territories in it.
    for continentElement in self.DOM.getElementsByTagName("continent"):
      memberList = set()
      #print territoryID,"c:",continentElement.getAttribute("name")," m:",continentElement.getAttribute("members")
      for memberID in continentElement.getAttribute("members").split(','):
        #print "for",continentElement.getAttribute("name"),"looking at",memberID
        #print territoryID,memberID
        if memberID != territoryID:
          memberList.add(memberID)
      memberListString = ",".join(memberList)
      continentElement.setAttribute("members",str(memberListString))
      
      if (len(memberList) == 0):
        continentElement.parentNode.removeChild(continentElement)
        continentElement.unlink()
        
      
    return True

  def deleteEmptyContinents(self):
    '''
    Find all continents with no members
    '''
    continentsElement = self.DOM.getElementsByTagName("continents")[0]
    for continentElement in self.DOM.getElementsByTagName("continent"):
      if (len(continentElement.getAttribute("members")) == 0):
        continentsElement.removeChild(continentElement)
        continentElement.unlink()        

  def deleteBorder(self,id1,id2):
    bordersElement = self.DOM.getElementsByTagName("borders")[0]
    for borderElement in self.DOM.getElementsByTagName("border"):
      if (borderElement.getAttribute("fromid") == id1 and borderElement.getAttribute("toid") == id2) or (borderElement.getAttribute("fromid") == id2 and borderElement.getAttribute("toid") == id1):
        bordersElement.removeChild(borderElement)
        borderElement.unlink()
    

  def deleteAllBorders(self):
    bordersElement = self.DOM.getElementsByTagName("borders")[0]
    for borderElement in self.DOM.getElementsByTagName("border"):
      bordersElement.removeChild(borderElement)
      borderElement.unlink()
      
    WarGearXMLElement = self.DOM.getElementsByTagName("WarGearXML")[0]
    WarGearXMLElement.removeChild(bordersElement)

  def deleteAllTerritories(self):
    territoriesElement = self.DOM.getElementsByTagName("territories")[0]
    for territoryElement in self.DOM.getElementsByTagName("territory"):
      territoriesElement.removeChild(territoryElement)
      territoryElement.unlink()
    
    WarGearXMLElement = self.DOM.getElementsByTagName("WarGearXML")[0]
    WarGearXMLElement.removeChild(territoriesElement)

  def deleteAllContinents(self):
    continentsElements = self.DOM.getElementsByTagName("continents")
    if len(continentsElements) == 0:
      return
    continentsElement = continentsElements[0]
    for continentElement in self.DOM.getElementsByTagName("continent"):
      continentsElement.removeChild(continentElement)
      continentElement.unlink()
    
    WarGearXMLElement = self.DOM.getElementsByTagName("WarGearXML")[0]
    WarGearXMLElement.removeChild(continentsElement)

class HexGridWGMap(WGMap):
  """Just a stub """
  pass

class SquareGridWGMap(WGMap):
  """Extends :class:WGMap class for maps on a rectangular grid"""
  
  def __init__(self):
    """Constructor"""
    self.rows = 0
    self.cols = 0
    self.doWrap = True

  def wrapR(self,r):
    if (not self.doWrap):
      return r
    if r < 0:
      r = self.wrapR(r+self.rows)
    if r >= self.rows:
      r = self.wrapR(r-self.rows)
    return r
    
  def wrapC(self,c):
    if (not self.doWrap):
      return c
    if c < 0:
      c = self.wrapC(c+self.cols)
    if c >= self.cols:
      c = self.wrapC(c-self.cols)
    return c

  def wrapRC(self,(r,c)):    
    return (self.wrapR(r),self.wrapC(c))
   
  def connectSeperateGroups(self,territoryID = None):
    
    done = False
    while not done:
      done = self.connectTwoGroups(territoryID)
    
    
    
  def connectTwoGroups(self,territoryID = None):
    '''
    Find territory groups that are not connected, and join them up.
    Assumes territories adjacent on the map can share a border.
    '''
    # initial setup 
    if territoryID == None:
      territoryID = self.DOM.getElementsByTagName("territory")[0].getAttribute("tid")
    #print "territoryID",territoryID
    territoriesReached = set(territoryID)
    #print "territoriesReached",territoriesReached
    territoriesToCheck = set() #territories that have neighbors we may not have looked at yet

    # account for neighbors of first territory
    territoriesToCheck |= self.getNeighborIDsFromID(territoryID)

    #print "territoriesToCheck", territoriesToCheck
    while len(territoriesToCheck) > 0:
      # get a territory to check/reach
      territoryID = territoriesToCheck.pop()
      #print "looking at",territoryID
      # find all of it's neighbors
      neighbors = self.getNeighborIDsFromID(territoryID)
      #print "neighbors", neighbors
      # add any newly available territories
      territoriesToCheck |= (neighbors - territoriesReached)
      #print "territoriesToCheck", territoriesToCheck
      
      territoriesReached.add(territoryID)
   
    # get a set of all the territory ID
    allTerritories = set()
    for territory in  self.DOM.getElementsByTagName("territory"):
      allTerritories.add(territory.getAttribute("tid"))

    #print "allTerritories",allTerritories
    #print "territoriesReached",territoriesReached
    
    territoriesMissed = allTerritories - territoriesReached
    #self.printDOM()
    #print "territoriesMissed",territoriesMissed     
    if len(territoriesMissed) == 0:
      return True
    else:
      #import pdb; pdb.set_trace()
      #print "connecting two groups of territories"
      for t1 in territoriesMissed:
        for t2 in territoriesReached:
          (r1,c1) = self.getRC(self.getTerritoryElement(t1))     
          (r2,c2) = self.getRC(self.getTerritoryElement(t2))
          #print "comparing",t1,t2,r1,c1,r2,c2
          if abs(r1-r2)+abs(c1-c2) < 2: #found a neighbor (no diagonals)
            #pdb.set_trace()
            self.addBorder(t1,t2)
            return False
            
      #return False  #give up!          
      #print "all territories:", self.getTerritoryNameFromID(allTerritories)
      #print "territories reached:",self.getTerritoryNameFromID(territoriesReached)
      #print "territories missed: ", self.getTerritoryNameFromID(allTerritories - territoriesReached)
      #return self.connectSeperateGroups(territoryID)

    raise StandardError #we should never get here  
    #return False
  
  
  def createTerritories(self, xOrigin=10, yOrigin=10, xOffset=20, yOffset=20):
    '''
    Args:
      rows,cols (int): The number of rows/columns of territories. 
      xOrigin,yOrigin (int): The position of the upper left grid box.  
      xOffset,yOffset (int): The width of the grid boxes.
    '''
    xpos = xOrigin
    for col in range(self.cols):
      ypos = yOrigin
      for row in range(self.rows):
        territoryName = self.getTerritoryName(row,col)
        self.addTerritory(territoryName, str(xpos), str(ypos))
        ypos += yOffset
      xpos += xOffset
 
  def createBlockContinents(self, bonus):
    ''' 
    Creates continents of every 2x2 block.
    
    Args:
      self.rows,self.cols (int): The number of rows/columns of territories. 
 
    '''
    for uly in range(self.rows-1):
      for ulx in range(self.cols-1):
        territoryElements = []
        # contintent name is name of UL territory
        #print "gridname", self.getTerritoryName(uly,ulx)
        territoryElement = self.getTerritoryElement( 
            self.getTerritoryName(uly,ulx))
        #print "territoryElement",territoryElement
        territoryElements.append( territoryElement)
        territoryElements.append( self.getTerritoryElement( 
            self.getTerritoryName(uly+1,ulx)))
        territoryElements.append( self.getTerritoryElement( 
            self.getTerritoryName(uly,ulx+1)))
        territoryElements.append( self.getTerritoryElement( 
            self.getTerritoryName(uly+1,ulx+1)))
        
        self.addContinentFromElements(self.getTerritoryName(uly,ulx),territoryElements, bonus)

  def getTerritoryName(self, row, col):
    '''
    Calculate the territory name from arguments
    '''
    return str(self.wrapR(row)) + "." + str(self.wrapC(col))
    #return str(row) + "." + str(col)

  def getRC(self, territoryElement):
    
    territoryName = territoryElement.getAttribute("name")
    return  map(int, territoryName.split("."))

  def getTerritoryElement(self, territoryIdentifier):
    
    #print "MazeWGMap.getTerritoryElement() called with",territoryIdentifier
    
    # if this is a string, we want to make sure python doesn't
    # treat it as a tuple
    if isinstance(territoryIdentifier, basestring):
      return WGMap.getTerritoryElement(self,territoryIdentifier)

    try:
      (r,c) = territoryIdentifier
      return WGMap.getTerritoryElement(self,self.getTerritoryName(r,c))
    
    except:
      #print "caught error:", exc_info()[0]
      #traceback.print_exc()

      # must be a name
      #print "getting territory element by name",identifier
      return WGMap.getTerritoryElement(self,territoryIdentifier)
    
  def addOneWayBordersFromBaseTerritoryID(self,baseID,RC,range=1,attackBonus=0,defenseBonus=0):
    '''
    RC - row column of source of borders
    '''
    for currentRange in range(range):
      pass
    #self.addBorder(baseID, toID, "One-way", type = "Default", attackBonus.str(),
    #            defenseBonus.str())
    
    
  def addBorders(self, ULRC, LRRC):
    '''
    ULRC - Upper Left Row Column
    LRRC - Lower Right Row Column
    '''
    (ULR, ULC) = ULRC
    (LRR, LRC) = LRRC
    
    for row in range(ULR,LRR):
      for col in range(ULC,LRC):
        self.addBorder((row,col),(row+1,col))
        self.addBorder((row,col),(row,col+1))
        

  def addBorder(self, fromRC, toRC):
    
    #print "SquareGridWGMap.addBorder():", fromRC,toRC
    
    # if this is a string, we want to make sure python doesn't
    # treat it as a tuple
    if isinstance(fromRC, basestring):
      return WGMap.addBorder(self,fromRC, toRC)
    
    try:
      (fromR, fromC) = fromRC
      (toR,toC) = toRC
      return WGMap.addBorder(self,self.getTerritoryName(fromR,fromC),self.getTerritoryName(toR,toC))
    
    except:
      #print "caught error:", exc_info()[0]
      #traceback.print_exc()

      # must be a name
      #print "getting territory element by name",identifier
      return WGMap.addBorder(self,fromRC, toRC)

  def doTheyBorder(self, fromRC, toRC):
    
    
    # if this is a string, we want to make sure we don't think
    # it is our r,c tuple
    if isinstance(fromRC, basestring):
      return WGMap.doTheyBorder(self, fromRC, toRC)
    
    try:
      (fromR, fromC) = fromRC
      (toR,toC) = toRC
      toID = self.getTerritoryIDFromName(self.getTerritoryName(toR,toC))
      fromID = self.getTerritoryIDFromName(self.getTerritoryName(fromR,fromC))
      return WGMap.doTheyBorder(self,fromID,toID)
    
    except:
      #print "caught error:", exc_info()[0]
      #traceback.print_exc()

      # must be a name
      #print "getting territory element by name",identifier
      return WGMap.doTheyBorder(self,fromRC, toRC)
    
    

  def addBorderToCoordinate(self, fromID,toRow,toCol):
    '''
    Add a border between fromID and the continent at toRow,toCol 
    '''
    if (toRow >= 0 and toCol >= 0 and toRow < self.rows and toCol < self.cols):
      toTerritoryName = self.getTerritoryName(toRow,toCol)
      toID = self.getTerritoryIDFromName(toTerritoryName)
      self.addBorder(fromID, toID)
      
# todo: this is not finished
  def addSquareBorders(self):
    '''Adds borders for a grid created by createTerritories.  All arguments are ints. (incomplete)
    
       .. warning::
       This function does not work yet.

    '''

    if (self.DOM.getElementsByTagName("borders") == None):
      newBordersElement = self.DOM.createElement("borders")
      self.DOM.getElemntsByTagName("board")[0].appendChild(newBordersElement)
      
    for row in range(self.rows):
      for col in range(self.cols):
        newBorderElement = self.DOM.createElement("border")
        # todo: need to calculate name
        #newBorderElement.setAttribute("name",str(name))

        territoryName = str(row) + "." + str(col)
        fromID = self.getTerritoryIDFromName(territoryName)
        if (row > 0):
          toName = str(row-1) + "." + str(col)
          toID = self.getTerritoryIDFromName(toName)
          
          #finish this.

class MazeWGMap(SquareGridWGMap):
  """
  Extends the SquareGridWGMap.
  Creates a 'maze map' in which players
  gain bonuses for completing a row or column
  """
  
  
  def __init__(self):
    """Constructor"""
    super(MazeWGMap,self).__init__()

    self.setDefaultParameters()
    

  def setDefaultParameters(self):
    self.branchingFactor = .3  #Fraction of growth points that will branch
    self.connectionRejection = .8  # % chance a connection from a growth point to a territory w/borders will be retried
    self.chanceToDeadEnd = .4 #Fraction of times a connection from gp to territory w/borders will dead end vs. joining up (assuming !connectionRejected)
  
  
  def setOpenParameters(self):
    self.branchingFactor = .4  #Fraction of growth points that will branch
    self.connectionRejection = .8  # % chance a connection from a growth point to a territory w/borders will be retried
    self.chanceToDeadEnd = .33 #Fraction of times a connection from gp to territory w/borders will dead end vs. joining up (assuming !connectionRejected)
  
  def setWideOpenParameters(self):
    self.branchingFactor = .6  #Fraction of growth points that will branch
    self.connectionRejection = .7  # % chance a connection from a growth point to a territory w/borders will be retried
    self.chanceToDeadEnd = .25 #Fraction of times a connection from gp to territory w/borders will dead end vs. joining up (assuming !connectionRejected)
  
  def setTightParameters(self):
    self.branchingFactor = .2  #Fraction of growth points that will branch
    self.connectionRejection = .92  # % chance a connection from a growth point to a territory w/borders will be retried
    self.chanceToDeadEnd = .6 #Fraction of times a connection from gp to territory w/borders will dead end vs. joining up (assuming !connectionRejected)
   
  def setTighterParameters(self):
    self.branchingFactor = .15  #Fraction of growth points that will branch
    self.connectionRejection = .94  # % chance a connection from a growth point to a territory w/borders will be retried
    self.chanceToDeadEnd = .7 #Fraction of times a connection from gp to territory w/borders will dead end vs. joining up (assuming !connectionRejected)
    
  
  def cleanupFourSquares(self):
    
    for r in range(self.rows):
      for c in range(self.cols):
        ulID = self.getTerritoryIDFromName(self.getTerritoryName(r,c))
        blID = self.getTerritoryIDFromName(self.getTerritoryName(r+1,c))
        urID = self.getTerritoryIDFromName(self.getTerritoryName(r,c+1))
        lrID = self.getTerritoryIDFromName(self.getTerritoryName(r+1,c+1))
        
        if self.doTheyBorder(ulID,blID) and self.doTheyBorder(ulID,urID) and self.doTheyBorder(lrID,urID) and self.doTheyBorder(lrID,blID):
          #print "cleaning up a 4-square at",r,c
          #pick a random border to remove.
          rnd = random.random()
          if rnd < .25:
            self.deleteBorder(ulID,blID)        
          elif rnd < .5:
            self.deleteBorder(ulID,urID)          
          elif rnd < .75:
            self.deleteBorder(lrID,urID)          
          else:
            self.deleteBorder(lrID,blID)          
 
  def addContinents(self,valueFunction=None):
    
    def divideByTwo(n):
      return n/2
    
    if valueFunction == None:
      valueFunction = divideByTwo
      
      
    colContinents = 0
    for r in range(self.rows):
      for c in range(self.cols):        
        centerID = self.getTerritoryIDFromName(self.getTerritoryName(r,c))
        aboveID =  self.getTerritoryIDFromName(self.getTerritoryName(r-1,c))
        # if there a border above, we have done this column continent already      
        if(not self.doTheyBorder(centerID,aboveID)):
          #print "starting a column at ",centerID,r,c
          membersList = str(centerID)        
          rBelow=r+1
          prevBelowID = centerID
          belowID = self.getTerritoryIDFromName(self.getTerritoryName(rBelow,c))
          contLength = 1
          # Find the extent of the column          
          while self.doTheyBorder(belowID,prevBelowID):
            #print "continuing a column at ",belowID,rBelow,c 
            membersList += ","  + belowID
            contLength += 1
            rBelow += 1
            prevBelowID = belowID
            belowID = self.getTerritoryIDFromName(self.getTerritoryName(rBelow,c))
          
          if (contLength > 1):
            self.addContinent("Column "+str(colContinents),membersList,valueFunction(contLength))
            colContinents += 1
          
    rowContinents = 0
    for r in range(self.rows):
      for c in range(self.cols):        
        centerID = self.getTerritoryIDFromName(self.getTerritoryName(r,c))
        leftID =  self.getTerritoryIDFromName(self.getTerritoryName(r,c-1))
        # if there a border above, we have done this column continent already      
        if(not self.doTheyBorder(centerID,leftID)):
          membersList = str(centerID)        
          cRight=c+1
          prevRightID = centerID
          rightID = self.getTerritoryIDFromName(self.getTerritoryName(r,cRight))
          contLength = 1
          # Find the extent of the column          
          while self.doTheyBorder(rightID,prevRightID):
            membersList += ","  + rightID
            contLength += 1
            cRight += 1
            prevRightID = rightID
            rightID = self.getTerritoryIDFromName(self.getTerritoryName(r,cRight))
          
          if (contLength > 1):
            self.addContinent("Row "+str(rowContinents),membersList,valueFunction(contLength))
            rowContinents += 1
       
            
                                
  
  
  def createMazeGame(self,filePath,rowHeight=40,colWidth=40):
    '''Be sure to set the board name by hand'''
    
    xOrigin = colWidth/2
    yOrigin = rowHeight/2
    
    #print "Maze (" + str(self.rows) + "x" + str(self.cols) + ")"#+str(placeKnightFunc)
    print filePath
    self.deleteAllBorders()
    self.deleteAllTerritories()
    self.deleteAllContinents()

    #self.setBoardName("Knight's Tour (" + str(rows) + "x" + str(cols) + ")")
    
    self.createTerritories(xOrigin, yOrigin, rowHeight, colWidth)   
    self.fillWithRandomWalk()
    
    
    returnValue = self.connectSeperateGroups()
    self.cleanupFourSquares()
    
    self.addContinents()
    self.setNumFortifies(int(ceil(sqrt(self.rows*self.cols))))
    self.setEliminationBonus(int(ceil(sqrt(self.rows*self.cols))))
    self.setMaxCards(2+int(ceil(sqrt(sqrt(self.rows*self.cols)))))
    
    self.createPNG(filePath, rowHeight, colWidth)


    self.saveMapToFile(filePath + ".xml")
    
    bc = self.getBorderCounts()
    for BName,BCount in bc.iteritems():
      if BCount > 4:
        print BName,"has",BCount,"borders!!"

    return returnValue
  
  

  # @todo: change putpixel to the  faster way
  def createPNG(self, filePath, rowHeight, colWidth):
    '''
    Creates a PNG of a maze with walls
    '''
    im = Image.new("RGB", ( self.cols*colWidth,self.rows*rowHeight), "white")
    #print "create new RGB image:", self.cols*colWidth,self.rows*rowHeight
    # @todo: these should all be rowHeight

    wallHalfWidth=2
    
    def safePutPixel(xy,rgb):
      (x,y) = xy
      (r,g,b) = rgb
      if (x < 0 or x >= self.cols*colWidth):
        return
      if (y < 0 or y >= self.rows*rowHeight):
        return
      im.putpixel(xy, rgb)
      
    
    def drawRightWall(fromR, fromC):
      if (fromC == self.cols-1):
        whw = wallHalfWidth*2
      else:
        whw = wallHalfWidth
      for y in range(fromR*rowHeight-wallHalfWidth,(fromR+1)*rowHeight+wallHalfWidth+1):
        for x in range((fromC+1)*colWidth-whw,(fromC+1)*colWidth+whw+1):
          safePutPixel((x,y), (0,0,0))
    
    def drawBottomWall(fromR, fromC):
      if (fromR == self.rows-1):
        whw = wallHalfWidth*2
      else:
        whw = wallHalfWidth
      for x in range(fromC*colWidth-wallHalfWidth,(fromC+1)*colWidth+wallHalfWidth+1):
        for y in range((fromR+1)*rowHeight-whw,(fromR+1)*rowHeight+whw+1):
          safePutPixel((x,y), (0,0,0))

    def drawLeftWall(fromR, fromC):
      if (fromC == 0):
        whw = wallHalfWidth*2-1
      else:
        whw = wallHalfWidth
        
      for y in range(fromR*rowHeight-wallHalfWidth,(fromR+1)*rowHeight+wallHalfWidth+1):
        for x in range((fromC)*colWidth-whw,(fromC)*colWidth+whw+1):
          safePutPixel((x,y), (0,0,0))
    
    def drawTopWall(fromR, fromC):
      if (fromR == 0):
        whw = wallHalfWidth*2-1
      else:
        whw = wallHalfWidth
      for x in range(fromC*colWidth-wallHalfWidth,(fromC+1)*colWidth+wallHalfWidth+1):
        for y in range((fromR)*rowHeight-whw,(fromR)*rowHeight+whw+1):
          safePutPixel((x,y), (0,0,0))

    def drawEdgeBorders():
      for y in range(self.rows*rowHeight):
        x = 0
        safePutPixel((x, y), (128, 128, 128))
        x = self.cols*colWidth-1
        safePutPixel((x, y), (128, 128, 128))
      for x in range(self.cols*colWidth):
        y = 0
        safePutPixel((x, y), (128, 128, 128))
        y = self.rows*rowHeight-1
        safePutPixel((x, y), (128, 128, 128))
        
      
        
    #draw in grey lines between each square for continent borders. 
    for col in range(self.cols):      
      for y in range(self.rows*rowHeight):
        row = floor(y/rowHeight)
        x = col*colWidth
        #print x,y
        #print im.getpixel((x,y))
        #print "putpixel",x,y
        if (col != 0):     
          safePutPixel((x, y), (128, 128, 128))
        
    for row in range(self.rows):      
      for x in range(self.cols*colWidth):
        col = floor(x/colWidth)
        y = row*rowHeight
        #print x,y
        #print im.getpixel((x,y))
        #print "putpixel",x,y
        if (row != 0):
          safePutPixel((x, y), (128, 128, 128))
        
    drawEdgeBorders()     


    # fill in strong borders on top 
    for c in range(self.cols):
      topID = self.getTerritoryIDFromName(self.getTerritoryName(0,c))
      bottomID = self.getTerritoryIDFromName(self.getTerritoryName(self.rows-1,c))
      if(not self.doTheyBorder(topID,bottomID)):
        #print "border between",self.getTerritoryName(r,c),self.getTerritoryName(r+1,c)
        drawTopWall(0,c)
      
    # & left sides
    for r in range(self.rows):
      leftID = self.getTerritoryIDFromName(self.getTerritoryName(r,0))
      rightID = self.getTerritoryIDFromName(self.getTerritoryName(r,self.cols-1))
      if(not self.doTheyBorder(leftID,rightID)):
        #print "border between",self.getTerritoryName(r,c),self.getTerritoryName(r+1,c)
        drawLeftWall(r,0)
      
    
    # draw the rest of the walls
    for r in range(self.rows):
      for c in range(self.cols):
        centerID = self.getTerritoryIDFromName(self.getTerritoryName(r,c))
        rightID =  self.getTerritoryIDFromName(self.getTerritoryName(r,c+1))
        bottomID =  self.getTerritoryIDFromName(self.getTerritoryName(r+1,c))
        if(not self.doTheyBorder(centerID,rightID)):
          #print "border between",self.getTerritoryName(r,c),self.getTerritoryName(r,c+1)        
          drawRightWall(r,c)
        if(not self.doTheyBorder(centerID,bottomID)):
          #print "border between",self.getTerritoryName(r,c),self.getTerritoryName(r+1,c)
          drawBottomWall(r,c)
          
          
      
         
         
        

    # add some text  
    #draw = ImageDraw.Draw(im)
    # use a truetype font
    #font = ImageFont.truetype("//BHO/data/wargear development/scripts/nayla.ttf", 15)

    #draw.text((10, 25), "TESETING world TSETING", font=font)



    im.save(filePath + ".png")

  def fillWithRandomWalk(self):
    
    self.addRandomWalk()
    while(self.countTerritoriesWithBorders(0) > 0):
      self.addRandomWalk(-2,-2)

  def addRandomWalk(self,r=-1,c=-1):
    """
    adds a maze starting at r,c
    if r & c are -2, a territory with no borders is found (if it exists), and the random walk is started there.
    otherwise if r or c is negative, they are set to the middle of the map.
    
    todo: This seems to hang on a rare occasion (recursion to infinity).  What is happening?  Does it get stuck in a corner somehow?
           Also a problem, it can get called with no r,c more than once, and we start again at the same place...
           
           Also somehow (maybe related to above), I am seeing the same border created multiple times.  
            The example I saw had 4 copies of the border from tid: 0 to tid: 1.  
    """

    # set r & c to a zero-border territory    
    if r == -2 and c == -2:
      startingTerritory = self.getATerritoryWithNBorders(0)
      (r,c) = self.getRC(startingTerritory)
      r = int(r)
      c = int(c)
      #print "found a new starting spot at",r,c 
    
    
    if (r < 0 or c < 0):
      r = self.rows/2
      c = self.cols/2
    
    
    pointsReached = set()
    growthPoints = set()
    
    growthPoints.add((r, c))
    
    def attemptTerritoryAdd(rTo,cTo):
      rTo = self.wrapR(rTo)
      cTo = self.wrapC(cTo)
      toTerritory = self.getTerritoryElement((rTo, cTo))
      fromTerritory = self.getTerritoryElement((rFrom,cFrom))
      fromBorders = self.getBorderCount(fromTerritory.getAttribute("tid"))
      
      #print "attempting",rFrom,cFrom,rTo,cTo
      if (toTerritory != None):
        toBorders = self.getBorderCount(toTerritory.getAttribute("tid"))
        #print "target has borders:",toBorders
        if (toBorders > 0):
          if random.random() < self.connectionRejection:
            growthPoints.add((rFrom,cFrom))  #add this point back again for another try
          else:             
            if  random.random() > self.chanceToDeadEnd:
              if False == self.addBorder((rFrom, cFrom),(rTo, cTo)): #border already existed
                if fromBorders < 3:
                  growthPoints.add((rFrom,cFrom))
        else:
          self.addBorder((rFrom, cFrom),(rTo, cTo))
          growthPoints.add((rTo,cTo))
          if random.random() < self.branchingFactor:
              growthPoints.add((rFrom,cFrom))
      else:
        growthPoints.add((rFrom,cFrom))
                      
    
    while(len(growthPoints) > 0):      
      (rFrom, cFrom) = growthPoints.pop()
      #print "growing at",rFrom,cFrom
      rnd = random.random()
      if rnd < .25:
        attemptTerritoryAdd(rFrom, cFrom-1)          
      elif rnd < .5:
        attemptTerritoryAdd(rFrom,cFrom+1)
      elif rnd < .75:
        attemptTerritoryAdd(rFrom+1,cFrom)
      else:
        attemptTerritoryAdd(rFrom-1, cFrom)
          
      
      


class KnightWGMap(SquareGridWGMap):
  """
  Extends the SquareGridWGMap.
  Creates a 'chessboard map' in which players
  gain bonuses for 4-squares & borders are connected
  like a knight moves in chess.
  """
  def addBorders(self):
    '''
    Adds borders as a knight could attack for a grid created 
    by :func:`SquareGridWGMap.createTerritories.
    
    Args are both ints.
    '''
    if self.DOM.getElementsByTagName("borders") == None:
      newBordersElement = self.DOM.createElement("borders")
      self.DOM.getElementsByTagName("board")[0].appendChild(newBordersElement)
      

    for row in range(self.rows):
      for col in range(self.cols):
        # skip half the squares since borders are two way
        if (row+col)%2 == 0:
          continue          
        fromTerritoryName = str(row) + "." + str(col)
        fromID = self.getTerritoryIDFromName(fromTerritoryName)
        self.addBorderToCoordinate(fromID,row-2,col-1)
        self.addBorderToCoordinate(fromID,row-2,col+1)
        self.addBorderToCoordinate(fromID,row-1,col-2)
        self.addBorderToCoordinate(fromID,row-1,col+2)
        self.addBorderToCoordinate(fromID,row+1,col-2)
        self.addBorderToCoordinate(fromID,row+2,col-1)
        self.addBorderToCoordinate(fromID,row+1,col+2)
        self.addBorderToCoordinate(fromID,row+2,col+1)

  def createFunctionGame(self,filePath,placeKnightFunc,rowHeight=40,colWidth=40,):
    
    '''Be sure to set the board name by hand'''
    
    xOrigin = colWidth/2
    yOrigin = rowHeight/2
    
    #print "Creating Function Knight's Tour:",filePath,rows,cols,rowHeight,colWidth,xOrigin,yOrigin
    print "Knight's Tour (" + str(self.rows) + "x" + str(self.cols) + ")"#+str(placeKnightFunc)
    
    self.deleteAllBorders()
    self.deleteAllTerritories()
    self.deleteAllContinents()

    #self.setBoardName("Knight's Tour (" + str(rows) + "x" + str(cols) + ")")
    
    self.createTerritories(xOrigin, yOrigin, rowHeight, colWidth)   
    self.addBorders()
    self.createBlockContinents(1)

    print "Deleting Territories",
    territoriesDeleted = []
    
    for r in range(self.rows):
      for c in range(self.cols):
        if(placeKnightFunc(r,c)):
          self.deleteTerritory(self.getTerritoryName(r,c))
          territoriesDeleted.append([r, c])
    
    self.setNumAttacks(int(ceil(sqrt(self.rows*self.cols))))
    self.setNumFortifies(int(ceil(sqrt(sqrt(self.rows*self.cols)))))
    self.setAllSoleContinentTerritoriesToNeutral()

    self.createPNG(filePath, rowHeight, colWidth, 
                             xOrigin, yOrigin, territoriesDeleted)

    self.saveMapToFile(filePath + ".xml")
    if (self.checkOneTerritoryCanReachAll() == False):
          return False

    return True
 
  def placeRandomVerticalStripes(self,r,c):
    if(c%5 == 3):
      return (random.random() < .3)        
    if(c%5 == 4):
      return (random.random() < .5)
    
    if(c%5 == 0):
        return True;
    if(c%5 == 1):
      if (random.random() < .5):
        return True;
    if(c%5 == 2):
      if (random.random() < .3):
        return True;

 
  def placeRandomSnake(self,r,c):
    if(c%8 == 0) or (c%8 == 7):
      if (r < self.rows-2):
        return random.random() < .85
    if(c%8 ==1) or (c%8 == 6):
      if (r < self.rows-2):
        return random.random() < .15

    if(c%8 == 3) or (c%8 == 4):
      if (r > 1):
        return random.random() < .85
    if(c%8 ==2) or (c%8 == 5):
      if (r > 1):
        return random.random() < .15
      
    return False
 
  def placeGrid(self,r,c):
    
    rFlag = False
    cFlag = False
    if (r%3 == 0):
      rFlag = True
    if (c%3 == 0):
      cFlag = True
    
    if (rFlag and cFlag):
      return False
    
    if (rFlag or cFlag):
      return True
    
    return False
  
  def placeCells(self,r,c):
    
    inCell = True
    
    # edges
    if(c==0 or c == self.cols-1 or r==0 or r == self.rows-1):
      inCell = False
    
    # dividing rows
#    if( r == self.rows/2-1 or r == self.rows/2):
    if( r == self.rows/3-1 or r == self.rows/3 or r == 2*self.rows/3-1 or r == 2*self.rows/3):
      inCell = False
    
    # dividing cols
    if( c % 5 == 0 or c % 5 == 4):
      inCell = False
      
  
    if (inCell):
      return random.random() < .1
    else:
      return random.random() < .9
    

  def placeKnightsSpots(self,r,c):
    '''
     012345678
    0 
    1 x  x  x  
    2
    3 x  x  x
    4
    5 x  x  x
    6
    7 x  x  x
    8
    
    '''
    if (r%3==1 and c%3 == 1):
      return True
    else:
      return False
    
     
    

  def createCellsGame(self,filePath,rowHeight=40,colWidth=40):
    
    xOrigin = colWidth/2
    yOrigin = rowHeight/2
    
    print "Creating Cells Knight's Tour:",filePath,self.rows,self.cols,rowHeight,colWidth,xOrigin,yOrigin
    self.deleteAllBorders()
    self.deleteAllTerritories()
    self.deleteAllContinents()

    self.setBoardName("Knight's Tour Cells" + str(self.rows) + "x" + str(self.cols))
    
    if (self.rows%5 != 0 ):
      return -1;
    
    self.createTerritories(xOrigin, yOrigin, rowHeight, colWidth)   
    self.addBorders()
    self.createBlockContinents(1)

    print "Deleting Territories",
    territoriesDeleted = [] 
    
    
    #Set knights on all edges.    
    for r in range(self.rows):
      c=0
      self.deleteTerritory(self.getTerritoryName(r,c))
      territoriesDeleted.append([r, c])
      #print r,c," ",

      c = self.cols-1
      self.deleteTerritory(self.getTerritoryName(r,c))
      territoriesDeleted.append([r, c])
      #print r,c," ",
   
    for c in range(self.cols):
      r=0
      self.deleteTerritory(self.getTerritoryName(r,c))
      territoriesDeleted.append([r, c])
      #print r,c," ",
      r = self.rows-1
      self.deleteTerritory(self.getTerritoryName(r,c))
      territoriesDeleted.append([r, c])
      #print r,c," ",

    
    
    # Draw two cols of knights at 4,5,9,10,14,15,...
    # with one open spot on the top half & one in the bottom half.
    for c in range(4,self.cols,5):
      print ""  
      rSkip = random.randint(1, self.rows/2-2) 
      for r in range(1,self.rows/2-1):
        if r != rSkip:
          #print r,c," ",
          self.deleteTerritory(self.getTerritoryName(r,c))
          territoriesDeleted.append([r, c])
          
      rSkip = random.randint(self.rows/2+1, self.rows-2)
      for r in range(self.rows/2+1,self.rows-1):        
        if r != rSkip:
          #print r,c," ",
          self.deleteTerritory(self.getTerritoryName(r,c))
          territoriesDeleted.append([r, c])
      
      c=c+1
      rSkip = random.randint(1, self.rows/2-2)
      for r in range(1,self.rows/2-1):
        if r != rSkip:
          self.deleteTerritory(self.getTerritoryName(r,c))
          territoriesDeleted.append([r, c])
          
      rSkip = random.randint(self.rows/2+1, self.rows-2)
      for r in range(self.rows/2+1,self.rows-1):
        if r != rSkip:
          self.deleteTerritory(self.getTerritoryName(r,c))
          territoriesDeleted.append([r, c])
      
    
    # Draw two rows of knights halfway through the board
    # with 90% coverage.
    r = self.rows/2-1;
    for c in range(self.cols):
      if (random.random() < 0.9):
        self.deleteTerritory(self.getTerritoryName(r,c))
        territoriesDeleted.append([r, c])
        
    r = self.rows/2;
    for c in range(self.cols):
      if (random.random() < 0.9):
        self.deleteTerritory(self.getTerritoryName(r,c))
        territoriesDeleted.append([r, c])

    self.deleteEmptyContinents()
    self.setAllSoleContinentTerritoriesToNeutral()
    self.setNumAttacks(int(ceil(sqrt(self.rows*self.cols))))
    self.setNumFortifies(int(ceil(sqrt(sqrt(self.rows*self.cols)))))

    self.createPNG(filePath, self.rows, self.cols, rowHeight, colWidth, 
                             xOrigin, yOrigin, territoriesDeleted)

    self.saveMapToFile(filePath + ".xml")
    if (self.checkOneTerritoryCanReachAll() == False):
          return False

    return True
 
    

  def createRandomGame(self, filePath, rowHeight=40, colWidth=40,
                           percentDeadSquares=.4, xOrigin=-1, yOrigin=-1):
    '''
    returns True if a board was created, False if board creation failed.
    '''
    if xOrigin < 0:
      xOrigin = colWidth/2
    if yOrigin < 0:
      yOrigin = rowHeight/2
    
    print "Creating Random Knight's Tour:",filePath,self.rows,self.cols,rowHeight,colWidth,percentDeadSquares,xOrigin,yOrigin
    
    self.setBoardName("Knight's Tour " + str(self.rows) + "x" + str(self.cols))


    self.deleteAllBorders()
    self.deleteAllTerritories()
    self.deleteAllContinents()
    
    #self.printDOM()

    self.createTerritories(xOrigin, yOrigin, rowHeight, colWidth)   
    self.addBorders()
    self.createBlockContinents(1)

    print "Deleting Territories",
    territoriesToDelete = floor(percentDeadSquares*self.rows*self.cols)
    territoriesDeleted = [] 
    while(territoriesToDelete > 0):
      # todo: Can we sort territories in some way to make good boards more likely?
      # 
      row = random.randint(0, self.rows-1)
      col = random.randint(0, self.cols-1)
      # don't use this square if it is one of the two that 
      # attack a corner square
      if ((row == 1 and col == 2) or
          (row == 2 and col == 1) or
          (row == self.rows-2 and col == self.cols-3) or
          (row == self.rows-3 and col == self.cols-2) or
          (row == 1 and col == self.cols-3) or
          (row == 2 and col == self.cols-2) or
          (row == self.rows-2 and col == 2) or
          (row == self.rows-3 and col == 1)):
        #print "skipping",row,col
        continue

      # Also don't use this square if it would create a continent with only
      # one territory in it.
      if self.getMinContinentSize(self.getTerritoryName(row,col)) <= 2:
        continue

      if (self.deleteTerritory(self.getTerritoryName(row,col))):
        territoriesToDelete -= 1
        territoriesDeleted.append([row, col])
      #print ".",
    #self.printDOM()
    if (self.checkOneTerritoryCanReachAll() == False):
          return False

    self.setNumAttacks(int(ceil(sqrt(self.rows*self.cols))))
    self.setNumFortifies(int(ceil(sqrt(sqrt(self.rows*self.cols)))))

    self.createPNG(filePath, rowHeight, colWidth, 
                             xOrigin, yOrigin, territoriesDeleted)

    self.saveMapToFile(filePath + ".xml")

    return True
  
  # @todo: territoriesDeleted needs to be handled
  # @todo: change putpixel to the  faster way
  def createPNG(self, filePath, rowHeight, colWidth, 
                          xOrigin, yOrigin, territoriesDeleted):
    '''
    Creates a PNG of a chessboard w/knights in dead squares..
    '''
    im = Image.new("RGB", ( self.cols*colWidth,self.rows*rowHeight), "white")
    #print "create new RGB image:", self.cols*colWidth,self.rows*rowHeight
    # @todo: these should all be rowHeight
    borderSize = 3; #borders are actually twice this. todo:
    for x in range(self.cols*colWidth):
      for y in range(self.rows*rowHeight):
        row = floor(y/rowHeight)
        col = floor(x/colWidth)
        #print x,y
        #print im.getpixel((x,y))
        #print "putpixel",x,y
        if ((row+col) % 2 == 0): #black square
          if (x - col*colWidth) >=  borderSize and (y - row*rowHeight) >= borderSize and ((col+1)*colWidth - x) >  borderSize and ((row+1)*rowHeight - y) > borderSize:
            im.putpixel((x,y), (1, 1, 1)) #off color centers
          else:
            im.putpixel((x, y), (0, 0, 0)) 
        else: #white square 
          if (x - col*colWidth) >= borderSize and (y - row*rowHeight) >= borderSize and ((col+1)*colWidth - x) >  borderSize and ((row+1)*rowHeight - y) > borderSize:
            im.putpixel((x,y), (245, 254, 254)) #off color centers
          else:
            im.putpixel((x, y), (255, 255, 255)) 


    #paste in the knight icons to the deleted territories
    for territory in territoriesDeleted:
      (delr, delc) = territory
      px = delc*colWidth
      py = delr*rowHeight
      if ((delr+delc) % 2 == 0): #black square
        im.paste(self.whiteKnightImage, (px+borderSize, py+borderSize)) 
      else:
        im.paste(self.blackKnightImage, (px+borderSize, py+borderSize)) 


    # add some text  
    #draw = ImageDraw.Draw(im)
    # use a truetype font
    #font = ImageFont.truetype("//BHO/data/wargear development/scripts/nayla.ttf", 15)

    #draw.text((10, 25), "TESETING world TSETING", font=font)



    im.save(filePath + ".png")


  # todo: maybe create knights tour config object
  def setKnightIcons(self, wkpath, bkpath):
    ''' 
    setter
    TODO: It would be great if rowHeight & colWidth were class members (instance variables), and were set 
      by the width/height of these images.
    '''
    self.whiteKnightImage = Image.open(wkpath)
    self.blackKnightImage = Image.open(bkpath)
 
def hordifySuperMetgear2():
  wgmap = WGMap()
  wgmap.loadMapFromFile('//DISKSTATION/data/wargear development/Super Metgear/Super Metgear - 5. Upper Levels.xml')
  wgmap.hordify()
  wgmap.saveMapToFile('//DISKSTATION/data/wargear development/Super Metgear/Super MetgearHordes - 5. Upper Levels.xml')
  
#    
def hordifySuperMetgear():
  wgmap = WGMap()
#  wgmap.loadMapFromFile('//BHO/data/wargear development/Super Metgear/Super_Metgear.xml')
#  print "Statistics before Hordify\n"
#  wgmap.printStatistics()
#  wgmap.hordify()
#  print "\n\nStatistics after Hordify\n"
#  wgmap.saveMapToFile('//BHO/data/wargear development/Super Metgear/Super_MetgearHordes.xml')


  for name in ["2. Crateria","3. Tourain","4. Brinstar","5. Wrecked Ship","6. Maridia","7. Norfair"]:
    wgmap.loadMapFromFile('//DISKSTATION/data/wargear development/Super Metgear/Super Metgear - ' + name + '.xml')
    wgmap.hordify()
    wgmap.saveMapToFile('//DISKSTATION/data/wargear development/Super Metgear/Super MetgearHordes - ' + name + '.xml')


def hordifyPangaea():
  wgmap = WGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/pangaea/Pangaea - Land&C.xml')
  print "Statistics before Hordify\n"
  wgmap.printStatistics()
  wgmap.hordify(1,"","Ocean.*","Ocean")
  print "\n\nStatistics after Hordify\n"
  wgmap.saveMapToFile('//BHO/data/wargear development/pangaea/Pangaea - Land&CHordes.xml')

def testHordify():
  ''' Testing - Hordify '''
  wgmap = WGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/scripts/KnightsTour8x8.xml')
  print "Statistics before Hordify\n"
  wgmap.printStatistics()
  wgmap.hordify(2,"_h",r"new",r"new",True)
  wgmap.hordify(2,"_h",r"new",r"new")
  print "\n\nStatistics after Hordify\n"
  wgmap.hordify(2,"_h",r"new",r"new",True)
  
  
  wgmap.saveMapToFile('//BHO/data/wargear development/scripts/SimpleBoardHordes.xml')

def testMazeMap():
  wgmap = MazeWGMap()
  
  wgmap.rows = 16
  wgmap.cols = 16

  wgmap.loadMapFromFile('//BHO/data/wargear development/Maze/Random Mazes.xml')
  wgmap.createMazeGame('//BHO/data/wargear development/Maze/MazeTest1')

def createHugeMazeMaps():
  wgmap = MazeWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Maze/Random Mazes.xml')
  
  size = 30
    
  wgmap.rows = size
  wgmap.cols = size
  extension = "C"
  file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
  wgmap.createMazeGame(file,25,25)
    
  wgmap.setWideOpenParameters()
  extension = "A"    
  file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
  wgmap.createMazeGame(file,25,25)

  wgmap.setOpenParameters()
  extension = "B"    
  file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
  wgmap.createMazeGame(file,25,25)
    
  wgmap.setTightParameters()
  extension = "D"    
  file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
  wgmap.createMazeGame(file,25,25)

  wgmap.setTighterParameters()
  extension = "E"    
  file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
  wgmap.createMazeGame(file,25,25)
  

def createMazeMaps():
  wgmap = MazeWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Maze/Random Mazes.xml')
  
  for size in range(8,21,4):
    
    if (size <= 12):
      territoryWidth = 40
    elif (size > 16):
      territoryWidth = 30
    else:
      territoryWidth = 35
    
    wgmap.rows = size
    wgmap.cols = size
    extension = "C"
    file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
    wgmap.createMazeGame(file,territoryWidth,territoryWidth)
      
    wgmap.setWideOpenParameters()
    extension = "A"    
    file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
    wgmap.createMazeGame(file,territoryWidth,territoryWidth)
  
    wgmap.setOpenParameters()
    extension = "B"    
    file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
    wgmap.createMazeGame(file,territoryWidth,territoryWidth)
      
    wgmap.setTightParameters()
    extension = "D"    
    file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
    wgmap.createMazeGame(file,territoryWidth,territoryWidth)
  
    wgmap.setTighterParameters()
    extension = "E"    
    file = '//BHO/data/wargear development/Maze/RandomMaze'+str(wgmap.rows) + 'x' + str(wgmap.cols) + extension
    wgmap.createMazeGame(file,territoryWidth,territoryWidth)
    
def createRandomKnightTour():
  ''' Create a Knight Tour's map '''
  wgmap = KnightWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Knights Tour/Knights Tour NxN - 10^2 - Random.xml')
  wgmap.setKnightIcons('//BHO/data/wargear development/Knights Tour/WhiteKnightIcon34.png',
                       '//BHO/data/wargear development/Knights Tour/BlackKnightIcon34.png')

  wgmap.rows = 10
  wgmap.cols = 10

  if (wgmap.createRandomGame(
      "//BHO/data/wargear development/Knights Tour/KnightsTour")):
    print "succesfully created a map :^)"
  else:
    print "map creation failed. :^( "
    
def createCellsKnightTour():
  ''' Create a Knight Tour's map '''
  wgmap = KnightWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Knights Tour/Knights Tour NxN - 20^2 - Cells.xml')
  wgmap.setKnightIcons('//BHO/data/wargear development/Knights Tour/WhiteKnightIcon34.png',
                       '//BHO/data/wargear development/Knights Tour/BlackKnightIcon34.png')

  
  if (wgmap.createCellsGame(
      "//BHO/data/wargear development/Knights Tour/KnightsTour")):
    print "succesfully created a map :^)"
  else:
    print "map creation failed. :^( "

def createVerticalStripesKnightsTour():
  ''' Create a Knight Tour's map '''
  wgmap = KnightWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Knights Tour/Knights Tour NxN - 15^2 - Stripes.xml')
  wgmap.setKnightIcons('//BHO/data/wargear development/Knights Tour/WhiteKnightIcon34.png',
                       '//BHO/data/wargear development/Knights Tour/BlackKnightIcon34.png')

  wgmap.rows = 20
  wgmap.cols = 20
  numAttempts = 0
  while (numAttempts < 20):
    if (wgmap.createFunctionGame(
                                 "//BHO/data/wargear development/Knights Tour/KnightsTour",wgmap.placeRandomVerticalStripes)):
      print "succesfully created a map :^) after", numAttempts+1,"attempts"
      break
    else:
      print "map creation failed. :^( ----  ATTEMPT: ",numAttempts+1
    numAttempts+=1


def createSnakesGame():
  ''' Create a Knight Tour's map '''
  wgmap = KnightWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Knights Tour/Knights Tour NxN - 20^2 - Random Snake.xml')
  wgmap.setKnightIcons('//BHO/data/wargear development/Knights Tour/WhiteKnightIcon34.png',
                       '//BHO/data/wargear development/Knights Tour/BlackKnightIcon34.png')

  wgmap.rows = 20
  wgmap.cols = 20

  numAttempts = 0
  while (numAttempts < 20):
    if (wgmap.createFunctionGame(
                                 "//BHO/data/wargear development/Knights Tour/KnightsTour",wgmap.placeRandomSnake)):
      print "succesfully created a map :^) after", numAttempts+1,"attempts"
      break
    else:
      print "map creation failed. :^( ----  ATTEMPT: ",numAttempts+1
    numAttempts+=1

def createFunctionCellGame():
  ''' Create a Knight Tour's map '''
  wgmap = KnightWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Knights Tour/Knights Tour NxN - 20^2 - Cells.xml')
  wgmap.setKnightIcons('//BHO/data/wargear development/Knights Tour/WhiteKnightIcon34.png',
                       '//BHO/data/wargear development/Knights Tour/BlackKnightIcon34.png')

  wgmap.rows = 21
  wgmap.cols = 20

  numAttempts = 0
  while (numAttempts < 30):
    if (wgmap.createFunctionGame(
                                 "//BHO/data/wargear development/Knights Tour/KnightsTour",wgmap.placeCells)):
      print "succesfully created a map :^) after", numAttempts+1,"attempts"
      break
    else:
      print "map creation failed. :^( ----  ATTEMPT: ",numAttempts+1
    numAttempts+=1

def createGridGame():
  ''' Create a Knight Tour's map '''
  wgmap = KnightWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Knights Tour/Knights Tour NxN - 12x12 - Grid.xml')
  wgmap.setKnightIcons('//BHO/data/wargear development/Knights Tour/WhiteKnightIcon34.png',
                       '//BHO/data/wargear development/Knights Tour/BlackKnightIcon34.png')

  wgmap.rows = 13
  wgmap.cols = 13

  numAttempts = 0
  while (numAttempts < 1):
    if (wgmap.createFunctionGame(
                                 "//BHO/data/wargear development/Knights Tour/KnightsTour",wgmap.placeGrid)):
      print "succesfully created a map :^) after", numAttempts+1,"attempts"
      break
    else:
      print "map creation failed. :^( ----  ATTEMPT: ",numAttempts+1
    numAttempts+=1

def addDnDGridTerritories():
  wgmap = SquareGridWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Dungeons & Dragons/Dungeons & Dragons.xml')
  wgmap.rows = 24
  wgmap.cols = 41
  wgmap.doWrap = False
  ULCR = (0,0)
  LRCR = (24,41)
  wgmap.createTerritories(1*25+25/2,7*25+25/2,25,25)
  wgmap.addBorders(ULCR,LRCR)
  wgmap.saveMapToFile('//BHO/data/wargear development/Dungeons & Dragons/Dungeons & Dragons.out.xml')

def addDnDPCBorders():
  wgmap = SquareGridWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Dungeons & Dragons/Dungeons & Dragons.xml')
  wgmap.rows = 24
  wgmap.cols = 41
  wgmap.doWrap = False
  
  mage1ID = wgmap.getTerritoryIDFromName("Mage 1")
  mage2ID = wgmap.getTerritoryIDFromName("Mage 2")
  mage3ID = wgmap.getTerritoryIDFromName("Mage 3")
  mage4ID = wgmap.getTerritoryIDFromName("Mage 4")
  mage5ID = wgmap.getTerritoryIDFromName("Mage 5")
  
  fighter1ID = wgmap.getTerritoryIDFromName("Fighter 1")
  fighter2ID = wgmap.getTerritoryIDFromName("Fighter 2")
  fighter3ID = wgmap.getTerritoryIDFromName("Fighter 3")
  fighter4ID = wgmap.getTerritoryIDFromName("Fighter 4")
  fighter5ID = wgmap.getTerritoryIDFromName("Fighter 5")
  
  cleric1ID = wgmap.getTerritoryIDFromName("Cleric 1")
  cleric2ID = wgmap.getTerritoryIDFromName("Cleric 2")
  cleric3ID = wgmap.getTerritoryIDFromName("Cleric 3")
  cleric4ID = wgmap.getTerritoryIDFromName("Cleric 4")
  cleric5ID = wgmap.getTerritoryIDFromName("Cleric 5")
  
  rogue1ID = wgmap.getTerritoryIDFromName("Rogue 1")
  rogue2ID = wgmap.getTerritoryIDFromName("Rogue 2")
  rogue3ID = wgmap.getTerritoryIDFromName("Rogue 3")
  rogue4ID = wgmap.getTerritoryIDFromName("Rogue 4")
  rogue5ID = wgmap.getTerritoryIDFromName("Rogue 5")
  
  # do level 1s by hand to boot strap the process.
#  mage1Neighbors = wgmap.getAllTerritoriesWithinNBorders(mage1ID, 2)
#  for mage1NID in mage1Neighbors:
#    WGMap.addBorder(self,mage1ID,mage1NID,"One-way","Default","0")
    
  mage1Neighbors = wgmap.getAllTerritoriesWithinNBorders(mage1ID, 4)
  for mage1NID in mage1Neighbors:
    WGMap.addBorder(wgmap,mage2ID,mage1NID,"One-way","Default","1")
    
  mage1Neighbors = wgmap.getAllTerritoriesWithinNBorders(mage1ID, 6)
  for mage1NID in mage1Neighbors:
    WGMap.addBorder(wgmap,mage3ID,mage1NID,"One-way","Default","2")
    
  mage1Neighbors = wgmap.getAllTerritoriesWithinNBorders(mage1ID, 8)
  for mage1NID in mage1Neighbors:
    WGMap.addBorder(wgmap,mage4ID,mage1NID,"One-way","Default","4")
    
  mage1Neighbors = wgmap.getAllTerritoriesWithinNBorders(mage1ID, 10)
  for mage1NID in mage1Neighbors:
    WGMap.addBorder(wgmap,mage5ID,mage1NID,"One-way","Default","8")
    
    
  
#  fighter1Neighbors = wgmap.getAllTerritoriesWithinNBorders(fighter1ID, 1)
#  for fighter1NID in fighter1Neighbors:
#    WGMap.addBorder(self,fighter1ID,fighter1NID,"One-way","Default","2")
    
  fighter1Neighbors = wgmap.getAllTerritoriesWithinNBorders(fighter1ID, 2)
  for fighter1NID in fighter1Neighbors:
    WGMap.addBorder(wgmap,fighter2ID,fighter1NID,"One-way","Default","4")
    
  fighter1Neighbors = wgmap.getAllTerritoriesWithinNBorders(fighter1ID, 3)
  for fighter1NID in fighter1Neighbors:
    WGMap.addBorder(wgmap,fighter3ID,fighter1NID,"One-way","Default","6")
    
  fighter1Neighbors = wgmap.getAllTerritoriesWithinNBorders(fighter1ID, 4)
  for fighter1NID in fighter1Neighbors:
    WGMap.addBorder(wgmap,fighter4ID,fighter1NID,"One-way","Default","8")
    
  fighter1Neighbors = wgmap.getAllTerritoriesWithinNBorders(fighter1ID, 5)
  for fighter1NID in fighter1Neighbors:
    WGMap.addBorder(wgmap,fighter5ID,fighter1NID,"One-way","Default","10")
    
#  cleric1Neighbors = wgmap.getAllTerritoriesWithinNBorders(cleric1ID, 1)
#  for cleric1NID in cleric1Neighbors:
#    WGMap.addBorder(self,cleric1ID,cleric1NID,"One-way","Default","1")
    
  cleric1Neighbors = wgmap.getAllTerritoriesWithinNBorders(cleric1ID, 2)
  for cleric1NID in cleric1Neighbors:
    WGMap.addBorder(wgmap,cleric2ID,cleric1NID,"One-way","Default","2")
    
  cleric1Neighbors = wgmap.getAllTerritoriesWithinNBorders(cleric1ID, 3)
  for cleric1NID in cleric1Neighbors:
    WGMap.addBorder(wgmap,cleric3ID,cleric1NID,"One-way","Default","3")
    
  cleric1Neighbors = wgmap.getAllTerritoriesWithinNBorders(cleric1ID, 4)
  for cleric1NID in cleric1Neighbors:
    WGMap.addBorder(wgmap,cleric4ID,cleric1NID,"One-way","Default","4")
    
  cleric1Neighbors = wgmap.getAllTerritoriesWithinNBorders(cleric1ID, 5)
  for cleric1NID in cleric1Neighbors:
    WGMap.addBorder(wgmap,cleric5ID,cleric1NID,"One-way","Default","5")
    
#  rogue1Neighbors = wgmap.getAllTerritoriesWithinNBorders(rogue1ID, 3)
#  for rogue1NID in rogue1Neighbors:
#    WGMap.addBorder(self,rogue1ID,rogue1NID,"One-way","Default","1")
   
  rogue1Neighbors = wgmap.getAllTerritoriesWithinNBorders(rogue1ID, 4)
  for rogue1NID in rogue1Neighbors:
    WGMap.addBorder(wgmap,rogue2ID,rogue1NID,"One-way","Default","2")
   
  rogue1Neighbors = wgmap.getAllTerritoriesWithinNBorders(rogue1ID, 5)
  for rogue1NID in rogue1Neighbors:
    WGMap.addBorder(wgmap,rogue3ID,rogue1NID,"One-way","Default","3")
   
  rogue1Neighbors = wgmap.getAllTerritoriesWithinNBorders(rogue1ID, 6)
  for rogue1NID in rogue1Neighbors:
    WGMap.addBorder(wgmap,rogue4ID,rogue1NID,"One-way","Default","4")
   
  rogue1Neighbors = wgmap.getAllTerritoriesWithinNBorders(rogue1ID, 7)
  for rogue1NID in rogue1Neighbors:
    WGMap.addBorder(wgmap,rogue5ID,rogue1NID,"One-way","Default","5")
   
  wgmap.saveMapToFile('//BHO/data/wargear development/Dungeons & Dragons/Dungeons & Dragons.out.xml',False)


def addDnDRodContinents():
  wgmap = SquareGridWGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Dungeons & Dragons/Dungeons & Dragons(5).xml')
  
  rodIDs = wgmap.getTerritoryIDsFromNameRegex("Rod")
  print "ROD IDs",rodIDs
  wgmap.addCollectorContinents(rodIDs,3,3)
  wgmap.saveMapToFile('//BHO/data/wargear development/Dungeons & Dragons/Dungeons & Dragons(5).out.xml',False)
  

def addQbertViewTerritories():
  wgmap = WGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/qbert/qbert.xml')
  wgmap.addBorders("Disk","^[1234567890]*$","One-way","View Only")
  wgmap.saveMapToFile('//BHO/data/wargear development/qbert/qbertOut.xml')

def addBackForMoreDiceContinents():
  
  wgmap = WGMap()
  wgmap.loadMapFromFile('//BHO/data/wargear development/Back For More/Back For More.xml')
  
  diceTerritoryNames = ["2x","4x","8x","16x","32x","64x"]
  diceMultipliers = [1,3,7,15,31,63]
  
  diceTerritoryIDs = []
  for dtn in diceTerritoryNames:
    diceTerritoryIDs.append(wgmap.getTerritoryIDFromName(dtn))
    
  checkerContinents = wgmap.DOM.getElementsByTagName("continent") 
  for checkerContinent in checkerContinents:
    checkerName = checkerContinent.getAttribute("name")
    checkerID = wgmap.getContinentMembersFromName(checkerName)
    print "Adding dice continents for",checkerName,checkerID
    checkerValue = int(checkerContinent.getAttribute("bonus"))
    
    # add single dice continents
    for diceName,diceID,diceMultiplier in zip(diceTerritoryNames,diceTerritoryIDs,diceMultipliers):
      continentName = checkerName + "_" + diceName
      continentMembers = str(diceID) +  "," + str(checkerID)      
      wgmap.addContinent(continentName,continentMembers,diceMultiplier*checkerValue) 
  
    # add two dice continents
    for d1 in range(6):
      for d2 in range(d1):
        d1Name = diceTerritoryNames[d1]
        d1Multiplier = diceMultipliers[d1]
        d1ID = wgmap.getTerritoryIDFromName(d1Name)
        
        d2Name = diceTerritoryNames[d2]
        d2Multiplier = diceMultipliers[d2]
        d2ID = wgmap.getTerritoryIDFromName(d2Name)
        
        continentName = checkerName + "_" + d1Name + "_" + d2Name
        continentMembers = str(d1ID) +  "," + str(d2ID) + "," + str(checkerID)
        continentValue = -1 * min(d1Multiplier,d2Multiplier)*checkerValue      
        wgmap.addContinent(continentName,continentMembers,continentValue) 
  
    # add three dice continents
    for d1 in range(6):
      for d2 in range(d1):
        for d3 in range(d2):
          d1Name = diceTerritoryNames[d1]
          d1Multiplier = diceMultipliers[d1]
          d1ID = wgmap.getTerritoryIDFromName(d1Name)
        
          d2Name = diceTerritoryNames[d2]
          d2Multiplier = diceMultipliers[d2]
          d2ID = wgmap.getTerritoryIDFromName(d2Name)
        
          d3Name = diceTerritoryNames[d3]
          d3Multiplier = diceMultipliers[d3]
          d3ID = wgmap.getTerritoryIDFromName(d3Name)
        
          continentName = checkerName + "_" + d1Name + "_" + d2Name + "_" + d3Name
          continentMembers = str(d1ID) +  "," + str(d2ID) +  "," + str(d3ID) + "," + str(checkerID)
          continentValue = min(d1Multiplier,d2Multiplier,d3Multiplier)*checkerValue      
          wgmap.addContinent(continentName,continentMembers,continentValue) 
  
    # add four dice continents
    for d1 in range(6):
      for d2 in range(d1):
        for d3 in range(d2):
          for d4 in range(d3):
            d1Name = diceTerritoryNames[d1]
            d1Multiplier = diceMultipliers[d1]
            d1ID = wgmap.getTerritoryIDFromName(d1Name)
          
            d2Name = diceTerritoryNames[d2]
            d2Multiplier = diceMultipliers[d2]
            d2ID = wgmap.getTerritoryIDFromName(d2Name)
          
            d3Name = diceTerritoryNames[d3]
            d3Multiplier = diceMultipliers[d3]
            d3ID = wgmap.getTerritoryIDFromName(d3Name)
          
            d4Name = diceTerritoryNames[d4]
            d4Multiplier = diceMultipliers[d4]
            d4ID = wgmap.getTerritoryIDFromName(d4Name)
          
            continentName = checkerName + "_" + d1Name + "_" + d2Name + "_" + d3Name + "_" + d4Name
            continentMembers = str(d1ID) +  "," + str(d2ID) +  "," + str(d3ID) + "," + str(d4ID) + "," + str(checkerID)
            continentValue =-1 *  min(d1Multiplier,d2Multiplier,d3Multiplier,d4Multiplier)*checkerValue      
            wgmap.addContinent(continentName,continentMembers,continentValue) 
  
    # add five dice continents
    for d1 in range(6):
      for d2 in range(d1):
        for d3 in range(d2):
          for d4 in range(d3):
            for d5 in range(d4):
              d1Name = diceTerritoryNames[d1]
              d1Multiplier = diceMultipliers[d1]
              d1ID = wgmap.getTerritoryIDFromName(d1Name)
            
              d2Name = diceTerritoryNames[d2]
              d2Multiplier = diceMultipliers[d2]
              d2ID = wgmap.getTerritoryIDFromName(d2Name)
            
              d3Name = diceTerritoryNames[d3]
              d3Multiplier = diceMultipliers[d3]
              d3ID = wgmap.getTerritoryIDFromName(d3Name)
            
              d4Name = diceTerritoryNames[d4]
              d4Multiplier = diceMultipliers[d4]
              d4ID = wgmap.getTerritoryIDFromName(d4Name)
            
              d5Name = diceTerritoryNames[d5]
              d5Multiplier = diceMultipliers[d5]
              d5ID = wgmap.getTerritoryIDFromName(d5Name)
            
              continentName = checkerName + "_" + d1Name + "_" + d2Name + "_" + d3Name + "_" + d4Name+ "_" + d5Name
              continentMembers = str(d1ID) +  "," + str(d2ID) +  "," + str(d3ID) + "," + str(d4ID) + "," + str(d5ID) + "," + str(checkerID)
              continentValue = min(d1Multiplier,d2Multiplier,d3Multiplier,d4Multiplier,d5Multiplier)*checkerValue      
              wgmap.addContinent(continentName,continentMembers,continentValue) 
  
    # kind of silly to go through all this for one continent, but eh.
    # add six dice continents
    for d1 in range(6):
      for d2 in range(d1):
        for d3 in range(d2):
          for d4 in range(d3):
            for d5 in range(d4):
              for d6 in range(d5):
                d1Name = diceTerritoryNames[d1]
                d1Multiplier = diceMultipliers[d1]
                d1ID = wgmap.getTerritoryIDFromName(d1Name)
              
                d2Name = diceTerritoryNames[d2]
                d2Multiplier = diceMultipliers[d2]
                d2ID = wgmap.getTerritoryIDFromName(d2Name)
              
                d3Name = diceTerritoryNames[d3]
                d3Multiplier = diceMultipliers[d3]
                d3ID = wgmap.getTerritoryIDFromName(d3Name)
              
                d4Name = diceTerritoryNames[d4]
                d4Multiplier = diceMultipliers[d4]
                d4ID = wgmap.getTerritoryIDFromName(d4Name)
              
                d5Name = diceTerritoryNames[d5]
                d5Multiplier = diceMultipliers[d5]
                d5ID = wgmap.getTerritoryIDFromName(d5Name)
              
                d6Name = diceTerritoryNames[d6]
                d6Multiplier = diceMultipliers[d6]
                d6ID = wgmap.getTerritoryIDFromName(d6Name)
              
                continentName = checkerName + "_" + d1Name + "_" + d2Name + "_" + d3Name + "_" + d4Name + "_" + d5Name + "_" + d6Name
                continentMembers = str(d1ID) +  "," + str(d2ID) +  "," + str(d3ID) + "," + str(d4ID) + "," + str(d5ID) + "," + str(d6ID) + "," + str(checkerID)
                continentValue = -1 *min(d1Multiplier,d2Multiplier,d3Multiplier,d4Multiplier,d5Multiplier,d6Multiplier)*checkerValue      
                wgmap.addContinent(continentName,continentMembers,continentValue) 
     

  
  
  
  wgmap.saveMapToFile('//BHO/data/wargear development/Back For More/Back For More - Out.xml')

if __name__ == '__main__':
#   print 'Hello World'
    #createRandomKnightTour()
    #addQbertViewTerritories()
    #createCellsKnightTour();
    #createVerticalStripesKnightsTour()
    #createSnakesGame()
    #createGridGame()
    #createFunctionCellGame()
    #testMazeMap()
    #createMazeMaps()
    #createHugeMazeMaps()
    #addBackForMoreDiceContinents()
    #hordifySuperMetgear()
    #hordifySuperMetgear2()           
    #hordifyPangaea()
    #addDnDGridTerritories()
    #addDnDPCBorders()
    #addDnDRodContinents()
    print "test"