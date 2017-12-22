# Zigate Python Plugin
#
# Author: zaraki673
#

"""
<plugin key="Zigate" name="Zigate plugin" author="zaraki673" version="1.0.7" wikilink="http://www.domoticz.com/wiki/plugins/zigate.html" externallink="https://www.zigate.fr/">
	<params>
		<param field="Mode1" label="Type" width="75px">
			<options>
				<option label="USB" value="USB" default="true" />
				<option label="Wifi" value="Wifi"/>
			</options>
		</param>
		<param field="Address" label="IP" width="150px" required="true" default="0.0.0.0"/>
		<param field="Port" label="Port" width="150px" required="true" default="9999"/>
		<param field="SerialPort" label="Serial Port" width="150px" required="true" default="/dev/ttyUSB0"/>
		<param field="Mode6" label="Debug" width="75px">
			<options>
				<option label="True" value="Debug"/>
				<option label="False" value="Normal"  default="true" />
			</options>
		</param>
	</params>
</plugin>
"""

import Domoticz
import binascii
import time

class BasePlugin:
	enabled = False

	def __init__(self):
		self.ListOfDevices = {}  # {DevicesAddresse : { status : status_de_detection, data : {ep list ou autres en fonctions du status}}, DevicesAddresse : ...}
		return

	def onStart(self):
		Domoticz.Log("onStart called")
		global ReqRcv
		global ZigateConn
		if Parameters["Mode6"] == "Debug":
			Domoticz.Debugging(1)
			DumpConfigToLog()
			#Domoticz.Log("Debugger started, use 'telnet 0.0.0.0 4444' to connect")
			#import rpdb
			#rpdb.set_trace()
		if Parameters["Mode1"] == "USB":
			ZigateConn = Domoticz.Connection(Name="ZiGate", Transport="Serial", Protocol="None", Address=Parameters["SerialPort"], Baud=115200)
			ZigateConn.Connect()
		if Parameters["Mode1"] == "Wifi":
			ZigateConn = Domoticz.Connection(Name="Zigate", Transport="TCP/IP", Protocol="None ", Address=Parameters["Address"], Port=Parameters["Port"])
			ZigateConn.Connect()
		ReqRcv=''
		for x in Devices : # initialise listeofdevices avec les devices en bases domoticz
			ID = Devices[x].ID
			Type = Devices[x].Type
			Subtype = Devices[x].Subtype
			Switchtype= Devices[x].Switchtype
			self.ListOfDevices[ID]['status']="inDB"
			self.ListOfDevices[ID]['Type']=Type
			self.ListOfDevices[ID]['Subtype']=Subtype
			self.ListOfDevices[ID]['Switchtype']=Switchtype

	def onStop(self):
		Domoticz.Log("onStop called")

	def onConnect(self, Connection, Status, Description):
		Domoticz.Log("onConnect called")
		global isConnected
		if (Status == 0):
			isConnected = True
			Domoticz.Log("Connected successfully")
			ZigateConf()
		else:
			Domoticz.Log("Failed to connect ("+str(Status)+")")
			Domoticz.Debug("Failed to connect ("+str(Status)+") with error: "+Description)
		return True

	def onMessage(self, Connection, Data):
		Domoticz.Log("onMessage called")
		global Tmprcv
		global ReqRcv
		Tmprcv=binascii.hexlify(Data).decode('utf-8')
		if Tmprcv.find('03') != -1 and len(ReqRcv+Tmprcv[:Tmprcv.find('03')+2])%2==0 :### fin de messages detecter dans Data
			ReqRcv+=Tmprcv[:Tmprcv.find('03')+2] #
			try :
				if ReqRcv.find("0301") == -1 : #verifie si pas deux messages coller ensemble
					ZigateDecode(self, ReqRcv) #demande de decodage de la trame recu
					ReqRcv=Tmprcv[Tmprcv.find('03')+2:]  # traite la suite du tampon
				else : 
					ZigateDecode(self, ReqRcv[:ReqRcv.find("0301")+2])
					ZigateDecode(self, ReqRcv[ReqRcv.find("0301")+2:])
					ReqRcv=Tmprcv[Tmprcv.find('03')+2:]
			except :
				Domoticz.Debug("onMessage - effacement de la trame suite a une erreur de decodage : " + ReqRcv)
				ReqRcv = Tmprcv[Tmprcv.find('03')+2:]  # efface le tampon en cas d erreur
		else : # while end of data is receive
			ReqRcv+=Tmprcv
		return

	def onCommand(self, Unit, Command, Level, Hue):
		Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

	def onDisconnect(self, Connection):
		Domoticz.Log("onDisconnect called")

	def onHeartbeat(self):
		#Domoticz.Log("onHeartbeat called")
		Domoticz.Debug("ListOfDevices : " + str(self.ListOfDevices))
		for key in self.ListOfDevices :
			status=self.ListOfDevices[key]['status']
			if status=="004d" :
				sendZigateCmd("0045","0002", str(key))    # Envoi une demande Active Endpoint request
				self.ListOfDevices[key]['status']="0045"
		
		
			if RIA==10 and status != "inDB" :
				#creer le device ds domoticz en se basant sur le clusterID
				IsCreated=False
				x=0
				nbrdevices=0
				for x in Devices:
					#Domoticz.Debug("ZigateRead - MsgType 8102 - reception heartbeat (0000) - MsgAttrID (0005) - Type de Device : " + Type + " read Devices id : " + x )
					#DOptions = Devices[x].Options
					if Devices[x].DeviceID == str(key) : #and DOptions['devices_type'] == str(Type) and DOptions['Ep'] == str(MsgSrcEp) :
						IsCreated = True
						Domoticz.Debug("Devices already exist. Unit=" + str(x))
					if IsCreated == False :
						nbrdevices=x
				if IsCreated == False :
					nbrdevices=nbrdevices+1
					Domoticz.Debug("HearBeat - creating device " )
					CreateDomoDevice(self, nbrdevices, key)
		#ResetDevice("lumi.sensor_motion.aq2")
		#ResetDevice("lumi.sensor_motion")
		if (ZigateConn.Connected() != True):
			ZigateConn.Connect()
		return True


global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

def onStop():
	global _plugin
	_plugin.onStop()

def onConnect(Connection, Status, Description):
	global _plugin
	_plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
	global _plugin
	_plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
	global _plugin
	_plugin.onDisconnect(Connection)

def onHeartbeat():
	global _plugin
	_plugin.onHeartbeat()

	# Generic helper functions
def DumpConfigToLog():
	for x in Parameters:
		if Parameters[x] != "":
			Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
	Domoticz.Debug("Device count: " + str(len(Devices)))
	for x in Devices:
		Domoticz.Debug("Device:		   " + str(x) + " - " + str(Devices[x]))
		Domoticz.Debug("Device ID:	   '" + str(Devices[x].ID) + "'")
		Domoticz.Debug("Device Name:	 '" + Devices[x].Name + "'")
		Domoticz.Debug("Device nValue:	" + str(Devices[x].nValue))
		Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
		Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
		Domoticz.Debug("Device options: " + str(Devices[x].options))
	return


def ZigateConf():

	################### ZiGate - set channel 11 ##################
	sendZigateCmd("0021","0004", "00000800")

	################### ZiGate - Set Type COORDINATOR#################
	sendZigateCmd("0023","0001","00")
	
	################### ZiGate - start network##################
	sendZigateCmd("0024","0000","")

	################### ZiGate - discover mode 255sec ##################
	sendZigateCmd("0049","0004","FFFCFE00")

def ZigateDecode(self, Data):  # supprime le transcodage
	Domoticz.Debug("ZigateDecode - decodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			if Outtmp == "02" :
				Transcode=True
			else :
				if Transcode == True:
					Transcode = False
					if Outtmp[0]=="1" :
						Out+="0"
					else :
						Out+="1"
					Out+=Outtmp[1]
					#Out+=str(int(str(Outtmp)) - 10)
				else :
					Out+=Outtmp
			Outtmp=""
	ZigateRead(self, Out)

def ZigateEncode(Data):  # ajoute le transcodage
	Domoticz.Debug("ZigateDecode - Encodind data : " + Data)
	Out=""
	Outtmp=""
	Transcode = False
	for c in Data :
		Outtmp+=c
		if len(Outtmp)==2 :
			if Outtmp[0] == "1" :
				if Outtmp[1] == "0" :
					Outtmp="0200"
					Out+=Outtmp
				else :
					Out+=Outtmp
			elif Outtmp[0] == "0" :
				Out+="021" + Outtmp[1]
			else :
				Out+=Outtmp
			Outtmp=""
	Domoticz.Debug("Transcode in : " + str(Data) + "  / out :" + str(Out) )
	return Out

def sendZigateCmd(cmd,length,datas) :
	if datas =="" :
		checksumCmd=getChecksum(cmd,length,"0")
		if len(checksumCmd)==1 :
			strchecksum="0" + str(checksumCmd)
		else :
			strchecksum=checksumCmd
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(strchecksum) + "03" 
	else :
		checksumCmd=getChecksum(cmd,length,datas)
		if len(checksumCmd)==1 :
			strchecksum="0" + str(checksumCmd)
		else :
			strchecksum=checksumCmd
		lineinput="01" + str(ZigateEncode(cmd)) + str(ZigateEncode(length)) + str(strchecksum) + str(ZigateEncode(datas)) + "03"   
	Domoticz.Debug("sendZigateCmd - Comand send : " + str(lineinput))
	if Parameters["Mode1"] == "USB":
		ZigateConn.Send(bytes.fromhex(str(lineinput)))	
	if Parameters["Mode1"] == "Wifi":
		ZigateConn.Send(bytes.fromhex(str(lineinput))+bytes("\r\n",'utf-8'))

def ZigateRead(self, Data):
	Domoticz.Debug("ZigateRead - decoded data : " + Data)
	MsgType=Data[2:6]
	MsgData=Data[12:len(Data)-4]
	MsgRSSI=Data[len(Data)-4:len(Data)-2]
	MsgLength=Data[6:10]
	MsgCRC=Data[10:12]
	Domoticz.Debug("ZigateRead - Message Type : " + MsgType + ", Data : " + MsgData + ", RSSI : " + MsgRSSI + ", Length : " + MsgLength + ", Checksum : " + MsgCRC)

	if str(MsgType)=="004d":  # Device announce
		Domoticz.Debug("ZigateRead - MsgType 004d - Reception Device announce ")
		Decode004d(self, MsgData)
		return
		
	elif str(MsgType)=="00d1":  #
		Domoticz.Debug("ZigateRead - MsgType 00d1 - Reception Touchlink status : " + Data)
		return
		
	elif str(MsgType)=="8000":  # Status
		Domoticz.Debug("ZigateRead - MsgType 8000 - reception status ")
		Decode8000(self, MsgData)
		return

	elif str(MsgType)=="8001":  # Log
		Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level ")
		Decode8001(self, MsgData)
		return

	elif str(MsgType)=="8002":  #
		Domoticz.Debug("ZigateRead - MsgType 8002 - Reception Data indication : " + Data)
		return

	elif str(MsgType)=="8003":  #
		Domoticz.Debug("ZigateRead - MsgType 8003 - Reception Liste des cluster de l'objet : " + Data)
		return

	elif str(MsgType)=="8004":  #
		Domoticz.Debug("ZigateRead - MsgType 8004 - Reception Liste des attributs de l'objet : " + Data)
		return
		
	elif str(MsgType)=="8005":  #
		Domoticz.Debug("ZigateRead - MsgType 8005 - Reception Liste des commandes de l'objet : " + Data)
		return

	elif str(MsgType)=="8006":  #
		Domoticz.Debug("ZigateRead - MsgType 8006 - Reception Non factory new restart : " + Data)$
		return

	elif str(MsgType)=="8007":  #
		Domoticz.Debug("ZigateRead - MsgType 8007 - Reception Factory new restart : " + Data)
		return

	elif str(MsgType)=="8010":  # Version
		Domoticz.Debug("ZigateRead - MsgType 8010 - Reception Version list : " + Data)
		Decode8010(self, MsgData)
		return

	elif str(MsgType)=="8014":  #
		Domoticz.Debug("ZigateRead - MsgType 8014 - Reception Permit join status response : " + Data)
		return
		
	elif str(MsgType)=="8024":  #
		Domoticz.Debug("ZigateRead - MsgType 8024 - Reception Network joined /formed : " + Data)
		return

	elif str(MsgType)=="8028":  #
		Domoticz.Debug("ZigateRead - MsgType 8028 - Reception Authenticate response : " + Data)
		return

	elif str(MsgType)=="8029":  #
		Domoticz.Debug("ZigateRead - MsgType 8029 - Reception Out of band commissioning data response : " + Data)
		return

	elif str(MsgType)=="802b":  #
		Domoticz.Debug("ZigateRead - MsgType 802b - Reception User descriptor notify : " + Data)
		return

	elif str(MsgType)=="802c":  #
		Domoticz.Debug("ZigateRead - MsgType 802c - Reception User descriptor response : " + Data)
		return

	elif str(MsgType)=="8030":  #
		Domoticz.Debug("ZigateRead - MsgType 8030 - Reception Bind response : " + Data)
		return

	elif str(MsgType)=="8031":  #
		Domoticz.Debug("ZigateRead - MsgType 8031 - Reception Unbind response : " + Data)
		return

	elif str(MsgType)=="8034":  #
		Domoticz.Debug("ZigateRead - MsgType 8034 - Reception Coplex Descriptor response : " + Data)
		return

	elif str(MsgType)=="8040":  #
		Domoticz.Debug("ZigateRead - MsgType 8040 - Reception Network address response : " + Data)
		return

	elif str(MsgType)=="8041":  #
		Domoticz.Debug("ZigateRead - MsgType 8041 - Reception IEEE address response : " + Data)
		return

	elif str(MsgType)=="8042":  #
		Domoticz.Debug("ZigateRead - MsgType 8042 - Reception Node descriptor response : " + Data)
		return

	elif str(MsgType)=="8043":  # Simple Descriptor Response
		Domoticz.Debug("ZigateRead - MsgType 8043 - Reception Simple descriptor response " + Data)
		Decode8043(self, MsgData)
		return

	elif str(MsgType)=="8044":  #
		Domoticz.Debug("ZigateRead - MsgType 8044 - Reception Power descriptor response : " + Data)
		return

	elif str(MsgType)=="8045":  # Active Endpoints Response
		Domoticz.Debug("ZigateRead - MsgType 8045 - Reception Active endpoint response : " + Data)
		Decode8045(self, MsgData)
		return

	elif str(MsgType)=="8046":  #
		Domoticz.Debug("ZigateRead - MsgType 8046 - Reception Match descriptor response : " + Data)
		return

	elif str(MsgType)=="8047":  #
		Domoticz.Debug("ZigateRead - MsgType 8047 - Reception Management leave response : " + Data)
		return

	elif str(MsgType)=="8048":  #
		Domoticz.Debug("ZigateRead - MsgType 8048 - Reception Leave indication : " + Data)
		return

	elif str(MsgType)=="804a":  #
		Domoticz.Debug("ZigateRead - MsgType 804a - Reception Management Network Update response : " + Data)
		return

	elif str(MsgType)=="804b":  #
		Domoticz.Debug("ZigateRead - MsgType 804b - Reception System server discovery response : " + Data)
		return

	elif str(MsgType)=="804e":  #
		Domoticz.Debug("ZigateRead - MsgType 804e - Reception Management LQI response : " + Data)
		return

	elif str(MsgType)=="8060":  #
		Domoticz.Debug("ZigateRead - MsgType 8060 - Reception Add group response : " + Data)
		return

	elif str(MsgType)=="8061":  #
		Domoticz.Debug("ZigateRead - MsgType 8061 - Reception Viex group response : " + Data)
		return

	elif str(MsgType)=="8062":  #
		Domoticz.Debug("ZigateRead - MsgType 8062 - Reception Get group Membership response : " + Data)
		return

	elif str(MsgType)=="8063":  #
		Domoticz.Debug("ZigateRead - MsgType 8063 - Reception Remove group response : " + Data)
		return

	elif str(MsgType)=="80a0":  #
		Domoticz.Debug("ZigateRead - MsgType 80a0 - Reception View scene response : " + Data)
		return

	elif str(MsgType)=="80a1":  #
		Domoticz.Debug("ZigateRead - MsgType 80a1 - Reception Add scene response : " + Data)
		return

	elif str(MsgType)=="80a2":  #
		Domoticz.Debug("ZigateRead - MsgType 80a2 - Reception Remove scene response : " + Data)
		return

	elif str(MsgType)=="80a3":  #
		Domoticz.Debug("ZigateRead - MsgType 80a3 - Reception Remove all scene response : " + Data)
		return

	elif str(MsgType)=="80a4":  #
		Domoticz.Debug("ZigateRead - MsgType 80a4 - Reception Store scene response : " + Data)
		return

	elif str(MsgType)=="80a6":  #
		Domoticz.Debug("ZigateRead - MsgType 80a6 - Reception Scene membership response : " + Data)
		return

	elif str(MsgType)=="8100":  #
		Domoticz.Debug("ZigateRead - MsgType 8100 - Reception Real individual attribute response : " + Data)
		return

	elif str(MsgType)=="8101":  # Default Response
		Domoticz.Debug("ZigateRead - MsgType 8101 - Default Response")
		Decode8101(self, MsgData)
		return

	elif str(MsgType)=="8102":  # Report Individual Attribute response
		Domoticz.Debug("ZigateRead - MsgType 8102 - Report Individual Attribute response")	
		Decode8102(self, MsgData)
		return
		
	elif str(MsgType)=="8110":  #
		Domoticz.Debug("ZigateRead - MsgType 8110 - Reception Write attribute response : " + Data)
		return

	elif str(MsgType)=="8120":  #
		Domoticz.Debug("ZigateRead - MsgType 8120 - Reception Configure reporting response : " + Data)
		return

	elif str(MsgType)=="8140":  #
		Domoticz.Debug("ZigateRead - MsgType 8140 - Reception Attribute discovery response : " + Data)
		return

	elif str(MsgType)=="8401":  # Reception Zone status change notification
		Domoticz.Debug("ZigateRead - MsgType 8401 - Reception Zone status change notification : " + Data)
		Decode8401(self, MsgData)
		return

	elif str(MsgType)=="8701":  # 
		Domoticz.Debug("ZigateRead - MsgType 8701 - Reception Router discovery confirm : " + Data)
		return

	elif str(MsgType)=="8702":  # APS Data Confirm Fail
		Domoticz.Debug("ZigateRead - MsgType 8702 -  Reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)
		Decode8702(self, MsgData)
		return

	else: # unknow or not dev function
		Domoticz.Debug("ZigateRead - Unknow Message Type " + MsgType)
		return

def Decode004d(self, MsgData) : # Reception Device announce
	MsgSrcAddr=MsgData[0:4]
	MsgIEEE=MsgData[4:20]
	MsgMacCapa=MsgData[20:22]
	Domoticz.Debug("Decode004d - Reception Device announce : Source :" + MsgSrcAddr + ", IEEE : "+ MsgIEEE + ", Mac capa : " + MsgMacCapa)
	# tester si le device existe deja dans la base domoticz
	if DeviceExist(self, MsgSrcAddr)==False :
		self.ListOfDevices[MsgSrcAddr]['data']['MacCapa']=MsgMacCapa

def Decode8000(self, MsgData) : # Reception status
	MsgDataLenght=MsgData[0:4]
	MsgDataStatus=MsgData[4:6]
	if MsgDataStatus=="00" :
		MsgDataStatus="Success"
	elif MsgDataStatus=="01" :
		MsgDataStatus="Incorrect Parameters"
	elif MsgDataStatus=="02" :
		MsgDataStatus="Unhandled Command"
	elif MsgDataStatus=="03" :
		MsgDataStatus="Command Failed"
	elif MsgDataStatus=="04" :
		MsgDataStatus="Busy"
	elif MsgDataStatus=="05" :
		MsgDataStatus="Stack Already Started"
	else :
		MsgDataStatus="ZigBee Error Code "+ MsgDataStatus
	MsgDataSQN=MsgData[6:8]
	if int(MsgDataLenght,16) > 2 :
		MsgDataMessage=MsgData[8:len(MsgData)]
	else :
		MsgDataMessage=""
	Domoticz.Debug("Decode8000 - Reception status : " + MsgDataStatus + ", SQN : " + MsgDataSQN + ", Message : " + MsgDataMessage)

def Decode8001(self, MsgData) : # Reception log Level
	MsgLogLvl=MsgData[0:2]
	MsgDataMessage=MsgData[2:len(MsgData)]
	Domoticz.Debug("ZigateRead - MsgType 8001 - Reception log Level 0x: " + MsgLogLvl + "Message : " + MsgDataMessage)

def Decode8010(self,MsgData) : # Reception Version list
	MsgDataApp=MsgData[0:4]
	MsgDataSDK=MsgData[4:8]
	Domoticz.Debug("Decode8010 - Reception Version list : " + MsgData)
	
def Decode8043(self, MsgData) : # Reception Simple descriptor response
	MsgDataSQN=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgDataShAddr=MsgData[4:8]
	MsgDataLenght=MsgData[8:10]
		# if int(MsgDataLenght,16)>0 :
			# MsgDataEp=MsgData[8:10]
	Domoticz.Debug("Decode8043 - Reception Simple descriptor response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", Lenght " + MsgDataLenght)

def Decode8045(self, MsgData) : # Reception Active endpoint response
	MsgDataSQN=MsgData[0:2]
	MsgDataStatus=MsgData[2:4]
	MsgDataShAddr=MsgData[4:8]
	MsgDataEpCount=MsgData[8:10]
	MsgDataEPlist=MsgData[10:len(MsgData)]
	Domoticz.Debug("Decode8045 - Reception Active endpoint response : SQN : " + MsgDataSQN + ", Status " + MsgDataStatus + ", short Addr " + MsgDataShAddr + ", EP count " + MsgDataEpCount + ", Ep list " + MsgDataEPlist)
	OutEPlist=""
	if DeviceExist(self, MsgSrcAddr)==False :
		if self.ListOfDevices[MsgDataShAddr]['status']="0045" :
			self.ListOfDevices[MsgDataShAddr]['status']="8045"
			for i in MsgDataEPlist :
				OutEPlist+=i
				if len(OutEPlist)==2 :
					self.ListOfDevices[MsgDataShAddr]['data'][OutEPlist]={}
					OutEPlist=""
	
def Decode8101(self, MsgData) :  # Default Response
	MsgDataSQN=MsgData[0:2]
	MsgDataEp=MsgData[2:4]
	MsgClusterId=MsgData[4:8]
	MsgDataCommand=MsgData[8:10]
	MsgDataStatus=MsgData[10:12]
	Domoticz.Debug("Decode8101 - reception Default response : SQN : " + MsgDataSQN + ", EP : " + MsgDataEp + ", Cluster ID : " + MsgClusterId + " , Command : " + MsgDataCommand+ ", Status : " + MsgDataStatus)

def Decode8102(self, MsgData) :  # Report Individual Attribute response
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]
	Domoticz.Debug("Decode8102 - reception data : " + MsgClusterData + " ClusterID : " + MsgClusterId + " Attribut ID : " + MsgAttrID + " Src Addr : " + MsgSrcAddr + " Scr Ep: " + MsgSrcEp)	
	ReadCluster(self, MsgData) 


def Decode8702(self, MsgData) : # Reception APS Data confirm fail
	MsgDataStatus=MsgData[0:2]
	MsgDataSrcEp=MsgData[2:4]
	MsgDataDestEp=MsgData[4:6]
	MsgDataDestMode=MsgData[6:8]
	MsgDataDestAddr=MsgData[8:12]
	MsgDataSQN=MsgData[12:14]
	Domoticz.Debug("Decode 8702 - Reception APS Data confirm fail : Status : " + MsgDataStatus + ", Source Ep : " + MsgDataSrcEp + ", Destination Ep : " + MsgDataDestEp + ", Destination Mode : " + MsgDataDestMode + ", Destination Address : " + MsgDataDestAddr + ", SQN : " + MsgDataSQN)

def Decode8401(self, MsgData) : # Reception Zone status change notification
	Domoticz.Debug("Decode8401 - Reception Zone status change notification : " + MsgData)
	MsgSrcAddr=MsgData[10:14]
	MsgSrcEp=MsgData[2:4]
	MsgClusterData=MsgData[16:18]
		
def CreateDomoDevice(nbrdevices,Addr,Ep,Type) :
	DeviceID=Addr #int(Addr,16)
	Domoticz.Debug("CreateDomoDevice - Device ID : " + str(DeviceID) + " Device EP : " + str(Ep) + " Type : " + str(Type) )
	if Type=="lumi.weather" :  # Detecteur temp/hum/baro xiaomi (v2)
		typename="Temp+Hum+Baro"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Temp+Hum"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+1, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Temperature"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+2, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Humidity"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+3, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Barometer"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+4, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_ht" : # Detecteur temp/humi xiaomi (v1)
		typename="Temp+Hum"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Temperature"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+1, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Humidity"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+2, TypeName=typename, Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_magnet.aq2" or Type=="lumi.sensor_magnet": # capteur ouverture/fermeture xiaomi  (v1 et v2)
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=2 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_motion" :  # detecteur de presence (v1) xiaomi
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=8 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()

	if Type=="lumi.sensor_switch.aq2" or Type=="lumi.sensor_switch"  :  # petit inter rond ou carre xiaomi (v1)
		typename="Switch"		
		Options = {"LevelActions": "||||", "LevelNames": "Off|1 Click|2 Clicks|3 Clicks|4 Clicks", "LevelOffHidden": "true", "SelectorStyle": "0","EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}
		Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_switch.aq2" + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
		
	if Type=="lumi.sensor_86sw2"  :  #inter sans fils 2 touches 86sw2 xiaomi
		typename="Switch"		
		Options = {"LevelActions": "|||", "LevelNames": "Off|Left Click|Right Click|Both Click", "LevelOffHidden": "true", "SelectorStyle": "0","EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}
		Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_86sw2" + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
		
	if Type=="lumi.sensor_smoke" :  # detecteur de fumee (v1) xiaomi
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=5 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()

	if Type=="lumi.sensor_motion.aq2" :  # Lux sensors + detecteur xiaomi v2
		typename="Lux"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=246, Subtype=1 , Switchtype=0 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices+1, Type=244, Subtype=73 , Switchtype=8 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()

	if Type=="lumi.sensor_86sw1":  # inter sans fils 1 touche 86sw1 xiaomi
		typename="Switch"
		Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, Type=244, Subtype=73 , Switchtype=9 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		
	if Type=="lumi.sensor_cube" :  # Xiaomi Magic Cube
		#typename="Text"
		#Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_cube-text" + " - " + str(DeviceID), Unit=nbrdevices, Type=243, Subtype=19 , Switchtype=0 , Options={"EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}).Create()
		typename="Switch"		
		Options = {"LevelActions": "||||||||", "LevelNames": "Off|Shake|Slide|90°|Clockwise|Tap|Move|Free Fall|Anti Clockwise|180°", "LevelOffHidden": "true", "SelectorStyle": "0","EP":str(Ep), "devices_type": str(Type), "typename":str(typename)}
		Domoticz.Device(DeviceID=str(DeviceID),Name="lumi.sensor_cube" + " - " + str(DeviceID), Unit=nbrdevices+1, Type=244, Subtype=62 , Switchtype=18, Options = Options).Create()
		
def MajDomoDevice(self,Addr,Ep,Type,value) :
	Domoticz.Debug("MajDomoDevice - Device ID : " + str(Addr) + " - Device EP : " + str(Ep) + " - Type : " + str(Type)  + " - Value : " + str(value) )
	x=0
	nbrdevices=1
	DeviceID=Addr #int(Addr,16)
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID) : 
			DOptions = Devices[x].Options
			DType=DOptions['devices_type']
			Dtypename=DOptions['typename']
			if DType=="lumi.weather" : #temp+hum+baro xiaomi
				if Type==Dtypename=="Temperature" :  # temperature
					#Devices[x].Update(nValue = 0,sValue = str(value))	
					UpdateDevice(x,0,str(value))				
				if Type==Dtypename=="Humidity" :   # humidite
					#Devices[x].Update(nValue = int(value), sValue = "0")	
					UpdateDevice(x,int(value),"0")				
				if Type==Dtypename=="Barometer" :  # barometre
					CurrentnValue=Devices[x].nValue
					CurrentsValue=Devices[x].sValue
					Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
					SplitData=CurrentsValue.split(";")
					valueBaro='%s;%s' % (value,SplitData[0])
					#Devices[x].Update(nValue = 0,sValue = str(valueBaro))	
					UpdateDevice(x,0,str(valueBaro))				
				if Dtypename=="Temp+Hum+Baro" :
					if Type=="Temperature" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s;%s;%s'	% (str(value) ,  SplitData[1] , SplitData[2] , SplitData[3] , SplitData[4])
						Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))		
						UpdateDevice(x,0,str(NewSvalue))									
					if Type=="Humidity" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2] , SplitData[3] , SplitData[4])
						Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))		
						UpdateDevice(x,0,str(NewSvalue))									
					if Type=="Barometer" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice baro CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s;%s;%s'	% (SplitData[0], SplitData[1] , SplitData[2] , str(value) , SplitData[3])
						Domoticz.Debug("MajDomoDevice bar NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))		
						UpdateDevice(x,0,str(NewSvalue))									
				if Dtypename=="Temp+Hum" : #temp+hum xiaomi
					if Type=="Temperature" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
						Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))			
						UpdateDevice(x,0,str(NewSvalue))								
					if Type=="Humidity" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
						Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))	
						UpdateDevice(x,0,str(NewSvalue))				
	
			if DType=="lumi.sensor_ht" :
				if Type==Dtypename=="Temperature" :
					#Devices[x].Update(nValue = 0,sValue = str(value))
					UpdateDevice(x,0,str(value))
				if Type==Dtypename=="Humidity" :
					#Devices[x].Update(nValue = int(value), sValue = "0")
					UpdateDevice(x,int(value),"0")
				#if Dtypename=="Temp+Hum" :
					#Domoticz.Device(DeviceID=str(DeviceID),Name=str(typename) + " - " + str(DeviceID), Unit=nbrdevices, TypeName=typename, options={"EP":Ep, "devices_type": str(Type), "typename":str(typename)}).Create()				
				if Dtypename=="Temp+Hum" :
					if Type=="Temperature" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice temp CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (str(value), SplitData[1] , SplitData[2])
						Domoticz.Debug("MajDomoDevice temp NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))		
						UpdateDevice(x,0,str(NewSvalue))				
					if Type=="Humidity" :
						CurrentnValue=Devices[x].nValue
						CurrentsValue=Devices[x].sValue
						Domoticz.Debug("MajDomoDevice hum CurrentsValue : " + CurrentsValue)
						SplitData=CurrentsValue.split(";")
						NewSvalue='%s;%s;%s'	% (SplitData[0], str(value) , SplitData[2])
						Domoticz.Debug("MajDomoDevice hum NewSvalue : " + NewSvalue)
						#Devices[x].Update(nValue = 0,sValue = str(NewSvalue))
						UpdateDevice(x,0,str(NewSvalue))		

			if DType=="lumi.sensor_magnet.aq2" or DType=="lumi.sensor_magnet" :  # detecteur ouverture/fermeture Xiaomi
				if Type==Dtypename :
					if value == "01" :
						state="Open"
					elif value == "00" :
						state="Closed"
					#Devices[x].Update(nValue = int(value),sValue = str(state))
					UpdateDevice(x,int(value),str(state))
				

			if DType=="lumi.sensor_86sw1" or DType=="lumi.sensor_smoke" or DType=="lumi.sensor_motion" :  # detecteur de presence / interrupteur / detecteur de fumée
				if Type==Dtypename=="Switch" :
					if value == "01" :
						state="On"
					elif value == "00" :
						state="Off"
					#Devices[x].Update(nValue = int(value),sValue = str(state))
					UpdateDevice(x,int(value),str(state))
					
					
			if DType=="lumi.sensor_switch" or DType=="lumi.sensor_switch.aq2"  :  # interrupteur xiaomi rond et carre
				if Type==Dtypename :
					if Type=="Switch" :
						if value == "01" :
							state="10"
						elif value == "02" :
							state="20"
						elif value == "03" :
							state="30"
						elif value == "04" :
							state="40"
						#Devices[x].Update(nValue = int(value),sValue = str(state))
						UpdateDevice(x,int(value),str(state))
						
						
			if DType=="lumi.sensor_86sw2"   :  # inter 2 touches xiaomi 86sw2
				if Type==Dtypename :
					if Type=="Switch" :
						if Ep == "01" :
							if value == "01" :
								state="10"
								data="01"
						elif Ep == "02" :
							if value == "01" :
								state="20"
								data="02"
						elif Ep == "03" :
							if value == "01" :
								state="30"
								data="03"
						#Devices[x].Update(nValue = int(data),sValue = str(state))
						UpdateDevice(x,int(data),str(state))
						
						
						
			if DType=="lumi.sensor_cube"   :  # Xiaomi Magic Cube
				if Type==Dtypename :
					if Type=="Switch" :
						if Ep == "02" :
							if value == "0000" : #shake
								state="10"
								data="01"
						
							elif value == "0204" or value == "0200" or value == "0203" or value == "0201" or value == "0202" or value == "0205": #tap
								state="50"
								data="05"
							
							elif value == "0103" or value == "0100" or value == "0104" or value == "0101" or value == "0102" or value == "0105": #Slide
								state="20"
								data="02"
							
							elif value == "0003" : #Free Fall
								state="70"
								data="07"
								
							elif value >= "0004" and value <= "0059": #90°
								state="30"
								data="03"
								
							elif value >= "0060" : #180°
								state="90"
								data="09"
					# elif Type=="Switch" : #rotation
						# elif MsgClusterId=="000c":
							# if Ep == "03" :
								# if value == "40404040" or value=="41414141" or value=="42424242" or value=="43434343" : #clockwise
								  # state="40"
								  # data="04"
						
							# # elif value == "0204" or value == "0200": #tap
								# # state="50"
								# # data="05"
								
							#Devices[x].Update(nValue = int(data),sValue = str(state))
							UpdateDevice(x,int(data),str(state))

			if DType=="lumi.sensor_motion.aq2":  # detecteur de luminosite
				if Type==Dtypename :
					if Type=="Lux" :
						#Devices[x].Update(nValue = 0 ,sValue = str(value))
						UpdateDevice(x,0,str(value))
				elif Type==Dtypename :
					if Type=="Switch" :
						if value == "01" :
							state="On"
						elif value == "00" :
							state="Off"
						Devices[x].Update(nValue = int(value),sValue = str(state))
			
def ResetDevice(Type) :
	x=0
	for x in Devices: 
		try :
			LUpdate=Devices[x].LastUpdate
			LUpdate=time.mktime(time.strptime(LUpdate,"%Y-%m-%d %H:%M:%S"))
			current = time.time()
			DOptions = Devices[x].Options
			DType=DOptions['devices_type']
			Dtypename=DOptions['typename']
			if (current-LUpdate)> 30 :
				if DType==Type :
					if Dtypename=="Switch":
						value = "00"
						state="Off"
						#Devices[x].Update(nValue = int(value),sValue = str(state))
						UpdateDevice(x,int(value),str(state))	
		except :
			return
			
def DeviceExist(self, Addr) :
	#check in ListOfDevices
	try :
		status=self.ListOfDevices[Addr]['status']
		return True
	except :  # devices inconnu ds listofdevices et ds db
		self.ListOfDevices[MsgSrcAddr]={}
		self.ListOfDevices[MsgSrcAddr]['status']="004d"
		self.ListOfDevices[MsgSrcAddr]['Heartbeat']="0"
		self.ListOfDevices[MsgSrcAddr]['RIA']="0"
		self.ListOfDevices[MsgSrcAddr]['Battery']={}
		self.ListOfDevices[MsgSrcAddr]['Model']={}
		self.ListOfDevices[MsgSrcAddr]['Data']={}
		return False

def getChecksum(msgtype,length,datas) :
	temp = 0 ^ int(msgtype[0:2],16) 
	temp ^= int(msgtype[2:4],16) 
	temp ^= int(length[0:2],16) 
	temp ^= int(length[2:4],16)
	for i in range(0,len(datas),2) :
		temp ^= int(datas[i:i+2],16)
		chk=hex(temp)
	Domoticz.Debug("getChecksum - Checksum : " + str(chk))
	return chk[2:4]


def UpdateBattery(DeviceID,BatteryLvl):
	x=0
	found=False
	for x in Devices:
		if Devices[x].DeviceID == str(DeviceID):
			found==True
			Domoticz.Log("Devices exist in DB. Unit=" + str(x))
			CurrentnValue=Devices[x].nValue
			Domoticz.Log("CurrentnValue = " + str(CurrentnValue))
			CurrentsValue=Devices[x].sValue
			Domoticz.Log("CurrentsValue = " + str(CurrentsValue))
			Domoticz.Log("BatteryLvl = " + str(BatteryLvl))
			Devices[x].Update(nValue = int(CurrentnValue),sValue = str(CurrentsValue), BatteryLevel = BatteryLvl )
	if found==False :
		self.ListOfDevices[DeviceID]['status']="004d"
		self.ListOfDevices[DeviceID]['Battery']=BatteryLvl
		
		
	#####################################################################################################################

def UpdateDevice(Unit, nValue, sValue):
	# Make sure that the Domoticz device still exists (they can be deleted) before updating it 
	if (Unit in Devices):
		if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
			Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
			Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
	return		

def ReadCluster(self, MsgData):
	MsgSQN=MsgData[0:2]
	MsgSrcAddr=MsgData[2:6]
	MsgSrcEp=MsgData[6:8]
	MsgClusterId=MsgData[8:12]
	MsgAttrID=MsgData[12:16]
	MsgAttType=MsgData[16:20]
	MsgAttSize=MsgData[20:24]
	MsgClusterData=MsgData[24:len(MsgData)]
	if DeviceExist(self, MsgSrcAddr)==False :
		self.ListOfDevices[MsgSrcAddr]['data'][MsgSrcEp]={}
		self.ListOfDevices[MsgSrcAddr]['data'][MsgSrcEp][MsgClusterId]={}

	else :
		self.ListOfDevices[MsgSrcAddr]['RIA']=self.ListOfDevices[MsgSrcAddr]['RIA']+1


	if MsgClusterId=="0000" :  # (General: Basic)
		if MsgAttrID=="ff01" :  # xiaomi battery lvl
			MsgBattery=MsgClusterData[4:8]
			try :
				ValueBattery='%s%s' % (str(MsgBattery[2:4]),str(MsgBattery[0:2]))
				ValueBattery=round(int(ValueBattery,16)/10/3)
				Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - MsgAttrID=ff01 - reception batteryLVL : " + str(ValueBattery) + " pour le device addr : " +  MsgSrcAddr)
				if self.ListOfDevices[MsgSrcAddr]['status']=="inDB":
					self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
					UpdateBattery(MsgSrcAddr,ValueBattery)
				else :
					self.ListOfDevices[MsgSrcAddr]['Battery']=ValueBattery
			except :
				Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - MsgAttrID=ff01 - reception batteryLVL : erreur de lecture pour le device addr : " +  MsgSrcAddr)
		elif MsgAttrID=="0005" :  # Model info Xiaomi
			Type=binascii.unhexlify(MsgClusterData).decode('utf-8')
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - MsgAttrID=0005 - reception Model de Device : " + Type)
			self.ListOfDevices[MsgSrcAddr]['data']['Model']=Type
			if self.ListOfDevices[MsgSrcAddr]['status']!="inDB":
				CheckType(self, MsgSrcAddr)
		else :
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0000 - reception heartbeat - Message attribut inconnu : " + MsgData)
	
	elif MsgClusterId=="0006" :  # (General: On/Off) xiaomi
		MajDomoDevice(self, MsgSrcAddr, MsgSrcEp, "Switch", MsgClusterData)
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0006 - reception General: On/Off : " + str(MsgClusterData) )
	
	elif MsgClusterId=="0402" :  # (Measurement: Temperature) xiaomi
		MsgValue=Data[len(Data)-8:len(Data)-4]
		MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Temperature",round(int(MsgValue,16)/100,1))
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0402 - reception temp : " + str(int(MsgValue,16)/100) )
				
	elif MsgClusterId=="0403" :  # (Measurement: Pression atmospherique) xiaomi   ### a corriger/modifier http://zigate.fr/xiaomi-capteur-temperature-humidite-et-pression-atmospherique-clusters/
		if str(Data[28:32])=="0028":
			MsgValue=Data[len(Data)-6:len(Data)-4] ##bug !!!!!!!!!!!!!!!!
			#MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgValue,8))
			#Domoticz.Debug("ReadCluster (8102) - ClusterId=0403 - reception atm : " + str(int(MsgValue,8)) )
			
		if str(Data[26:32])=="000029":
			MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgValue,16),1))
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0403 - reception atm : " + str(round(int(MsgValue,16)/100,1)))
			
		if str(Data[26:32])=="100029":
			MsgValue=Data[len(Data)-8:len(Data)-4]
			MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Barometer",round(int(MsgValue,16)/10,1))
			Domoticz.Debug("ReadCluster (8102) - ClusterId=0403 - reception atm : " + str(round(int(MsgValue,16)/10,1)))

	elif MsgClusterId=="0405" :  # (Measurement: Humidity) xiaomi
		MsgValue=Data[len(Data)-8:len(Data)-4]
		MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Humidity",round(int(MsgValue,16)/100,1))
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0405 - reception hum : " + str(int(MsgValue,16)/100) )

	elif MsgClusterId=="0406" :  # (Measurement: Occupancy Sensing) xiaomi
		MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Occupancy",MsgClusterData)
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0406 - reception Occupancy Sensor : " + str(MsgClusterData) )

	elif MsgClusterId=="0400" :  # (Measurement: LUX) xiaomi
		MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"Lux",str(int(MsgClusterData,16) ))
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0400 - reception LUX Sensor : " + str(MsgClusterData) )
		
	elif MsgClusterId=="0012" :  # Magic Cube Xiaomi
		MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"XiaomiSwitch",MsgClusterData)
		Domoticz.Debug("ReadCluster (8102) - ClusterId=0012 - reception Xiaomi Magic Cube Value : " + str(MsgClusterData) )
		
	elif MsgClusterId=="000c" :  # Magic Cube Xiaomi rotation
		MajDomoDevice(self, MsgSrcAddr,MsgSrcEp,"XiaomiVertRot",MsgClusterData)
		Domoticz.Debug("ReadCluster (8102) - ClusterId=000c - reception Xiaomi Magic Cube Value Vert Rot : " + str(MsgClusterData) )
		
	else :
		Domoticz.Debug("ReadCluster (8102) - Error/unknow Cluster Message : " + MsgClusterId)

def CheckType(self, MsgSrcAddr) :
	Domoticz.Debug("CheckType of device : " + MsgSrcAddr)
	x=0
	found=False
	for x in Devices:
		if Devices[x].DeviceID == str(MsgSrcAddr) :
			found=True
	
	if found==false :
		#check type with domoticz device type then add or del then re add device
		self.ListOfDevices[MsgSrcAddr]['status']="inDB"
		
