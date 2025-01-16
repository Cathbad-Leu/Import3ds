#!BPY

#""" Registration info for Blender menus:
#Name: '3DS'
#Blender: 232
#Group: 'Import'
#Tip: 'import to 3DS (.3ds) format.'
#"""

bl_info = {
	"name": "Import 3ds",
	"description": "addon to import 3ds files",
	"author": "Federico B.",
	"version": (0, 0, 1),
	"blender": (2, 8, 1),
	"location": "Import",
	"warning": "This addon is still in development.",
	"wiki_url": "",
	"category": "Object" }
	

#//////////////////////////////////// IMPORT3DS /////////////////////////////////*
#/////
#/////	SCRIPT: IMPORT3DS.PY
#/////	VERSION: 1.0
#/////	
#/////	AUTHOR:	Federico B. 
#/////	
#/////	Thanks to GameTutorials.com
#/////	Thanks to Reevan Mckay for his scritp full of usefull info.
#/////	Thanks to Blender.it and his comunity for support and help 
#/////
#/////	REQUIRMENTS:	Python full istallation (www.python.org) and Blender
#/////
#/////	DONE:			The Script now import 3d mesh, material, textures and textures coords, 
#/////					light and camera supp and keyframes. The standard out is logged in a file blende_out.txt
#/////					in the current model dir. 
#/////
#//////////////////////////////////// IMPORT3DS /////////////////////////////////*

import array
import struct
import sys

import bpy
#import Blender
#from Blender import NMesh, Material, Texture, Scene, Lamp, Image
#from Blender.Draw import *
#from Blender.BGL import *

import math
from math import sin, cos, sqrt
from math import cos, acos, sin, asin
from math import pi as PI

import exceptions
from exceptions import *

import string
from string import *

#>------ Primary CChunk, at the beginning of each file
PRIMARY 	=		long("0x4D4D",16)

#>------ Main CChunks
OBJECTINFO	=		long("0x3D3D",16)		#This gives the version of the mesh and is found right before the material and object information
VERSION		=		long("0x0002",16)		#This gives the version of the .3ds file
EDITKEYFRAME=		long("0xB000",16)		#This is the header for all of the key frame info

#>------ sub defines of OBJECTINFO
MATERIAL =			long("0xAFFF",16)		#This stored the texture info
OBJECT 	 =			long("0x4000",16)		#This stores the Faces, vertices, etc...

#>------ sub defines of MATERIAL
MATERIAL_NAME 	 =	long("0xA000",16)		# This holds the material name
MATERIAL_AMBIENT =	long("0xA010",16)		# Ambient color of the object/material
MATERIAL_DIFFUSE =	long("0xA020",16)		# This holds the color of the object/material
MATERIAL_SPECULAR=	long("0xA030",16)		# SPecular color of the object/material
MATERIAL_SHINESS =	long("0xA040",16)		# ??
MATERIAL_TRANSPARENCY	=	long("0xA050",16)	# Transparency value of material
MATERIAL_MAP 	 		=	long("0xA200",16)	# This is a header for a new material

#>------ sub defines of MATERIAL_MAP
MATERIAL_MAP_SPECULAR	=	long("0xA204",16)	# This is a header for a new specular map
MATERIAL_MAP_OPACITY	=	long("0xA210",16)	# This is a header for a new opacity map
MATERIAL_MAP_BUMP		=	long("0xA230",16)	# This is a header for a new bump map
MATERIAL_MAP_FILE 		=	long("0xA300",16)	# This holds the file name of the texture

#>------ sub defines of OBJECT
OBJECT_MESH  	  =	long("0x4100",16)		# This lets us know that we are reading a new object
OBJECT_LIGHT 	  =	long("0x4600",16)		# This lets un know we are reading a light object
OBJECT_CAMERA	  =	long("0x4700",16)		# This lets un know we are reading a camera object

#>------ sub defines of OBJECT_CAMERA
OBJECT_CAMERA_RANGES =	long("0x4720",16)		# The camera range values

#>------ sub defines of OBJECT_MESH
OBJECT_MESH_VERTICES =	long("0x4110",16)		# The objects vertices
OBJECT_MESH_FACES 	 =	long("0x4120",16)		# The objects faces
OBJECT_MESH_MATERIAL =	long("0x4130",16)		# This is found if the object has a material, either texture map or color
OBJECT_MESH_UV 		 =	long("0x4140",16)		# The UV texture coordinates
OBJECT_MESH_MATRIX =	long("0x4160",16)		# The Object Matrix

#>------ sub defines of EDIT_KEYFRAME
KEYFRAME				=	long("0xB000",16)	# This lets us know that we are reading in a keyframe
KEYFRAME_MESH_INFO		=	long("0xB002",16)
KEYFRAME_OBJECT_NAME	=	long("0xB010",16)
KEYFRAME_START_AND_END	=	long("0xB008",16)
PIVOT					=	long("0xB013",16)
POSITION_TRACK_TAG		=	long("0xB020",16)
ROTATION_TRACK_TAG		=	long("0xB021",16)
SCALE_TRACK_TAG			=	long("0xB022",16)


#//////////////////////////////////// C3DMODEL /////////////////////////////////*
#/////
#/////	This class holds the data of an intere model
#/////
#//////////////////////////////////// C3DMODEL /////////////////////////////////*
class C3DModel(object):
	numOfObjects 	= 0		# The number of objects in the model
	numOfMaterials 	= 0		# The number of materials for the model
	numOfLights		= 0
	numOfCameras	= 0
	pMaterials		= []	# The list of material information (Textures and colors)
	pObjects		= []	# The object list for our model
	pLights			= []
	pCameras		= []
	
	numberOfFrames	= 0	# The number of frames of animation this model (at least 1)
	
#//////////////////////////////////// C3DOBJECT /////////////////////////////////*
#/////
#/////	This class holds the data of a part of a model
#/////
#//////////////////////////////////// C3DOBJECT /////////////////////////////////*  
class C3DObject(object):
	numOfVerts	= 0			# The number of verts in the model
	numOfFaces	= 0			# The number of faces in the model
	numTexVertex= 0			# The number of texture coordinates
	materialID	= []		# The textures ID to use, which is the index into our texture array
	bHasTexture	= False		# This is TRUE if there is a texture map for this object
	strName		= ""		# The name of the object
	pVerts		= []		# The object's vertices
	pTexVerts	= []		# The texture's UV coordinates
	pFaces 		= []		# The faces information of the object
	objMatrix	= []		# Our object matrix is a 4 rows x 3 cols
	
	positionFrames = 0		# The number of key frames for the position
	rotationFrames = 0		# The number of key frames for the rotations
	scaleFrames		= 0		# The number of key frames for the scaling

	vPivot = []				# The object pivot point (The local axis it rotates around)

	vRotDegree = []
	vPosition 	= []			# The object's current position list (vectors list)
	vRotation 	= []			# The object's current rotation list  (vectors list)	
	vScale		= []			# The object's current scale list (vectors list)
	
#//////////////////////////////////// CINDICES /////////////////////////////////*
#/////
#/////	This class holds the indeces of a face
#/////
#//////////////////////////////////// CINDICES /////////////////////////////////*  
class CIndices(object):
	a	= 0
	b	= 0
	c	= 0
	bVisible = 0	# This will hold point1, 2, and 3 index's into the vertex array plus a visible flag
	
#//////////////////////////////////// CFACE /////////////////////////////////*
#/////
#/////	This class colde the data of a face
#/////
#//////////////////////////////////// CFACE /////////////////////////////////*  
class CFace(object):
	vertIndex	= CIndices()	# indicies for the verts that make up this triangle
	coordIndex	= CIndices()	# indicies for the tex coords to texture this face
	
#//////////////////////////////////// CMATERIALINFO /////////////////////////////////*
#/////
#/////	This class holds materilas and texture info
#/////
#//////////////////////////////////// CMATERIALINFO /////////////////////////////////*  
class CMaterialInfo(object):
	strName		=	""		# The texture name
	strFile		=	""		# The texture file name (If this is set it's a texture map)
	color		=	[]		# The color of the object (R, G, B)
	ambient		=	[]		# The ambient color
	specular	=	[]		# The speculat color
	numOfFaces	=	0			# number of Faces covered by the material
	pFaces		=	[]		# Array of Faces covered by the material
	alpha		= 	0		   # Our material could have an alpha channel
	
#//////////////////////////////////// CLIGHT /////////////////////////////////*
#/////
#/////	This class holds materilas and texture info
#/////
#//////////////////////////////////// CLIGHT /////////////////////////////////*  
class CLight(object):	
	position	=	[]
	color		=	[]
	
#//////////////////////////////////// CCAMERA /////////////////////////////////*
#/////
#/////	This class holds camera info
#/////
#//////////////////////////////////// CCAMERA /////////////////////////////////*  
class CCamera(object):	
	Position	=	[]
	Target		=	[]
	Angle		=	0.0
	Focus		=	0.0
	near		=	0.0
	far			=	0.0

#//////////////////////////////////// CCHUNK /////////////////////////////////*
#/////
#/////	This class is the basic unit of 3ds subdivision
#/////
#//////////////////////////////////// CCHUNK /////////////////////////////////*  
class CChunk(object):
	ID 			= 0		# The CChunk's ID
	length 		= 0		# The length of the CChunk
	bytesRead 	= 0		# The amount of bytes read within that CChunk

#//////////////////////////////////// CLOAD3DS /////////////////////////////////*
#/////
#/////	#This class load 3ds info and construct a 3d model from it
#/////
#//////////////////////////////////// CLOAD3DS /////////////////////////////////*  
class CLoad3ds(object): 

	#///////////////////////////////// __INIT__ \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	Constructor of the class
	#/////
	#///////////////////////////////// __INIT__ \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def __init__(self):
		
		self.m_FilePointer = []
		
		self.currentChunk	= CChunk()
		self.tempChunk 	= CChunk()
		
		self.m_CurrentObject	= C3DObject()
	
	#///////////////////////////////// FREAD \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function emulate C++ fread
	#/////
	#///////////////////////////////// FREAD \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def fread( self, Type, Size, Count ):
		value = []
		try:
			value = ( struct.unpack( "%s%s" % (Count,Type), self.m_FilePointer.read(Size)))
		except IOError:
			print("IO Error, failed to read the next byte in the stream.")
		return Size * Count, value[0]
	
	#///////////////////////////////// SKIP \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function permit to skip some bytes
	#/////
	#///////////////////////////////// SKIP \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def skip(self, n):
	
		try:
			self.m_FilePointer.read(n)
		except IOError:
			print("IO Error, failed to read the next byte in the stream.")			
		return n
		
	#///////////////////////////////// IMPORT3DS \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	Main function of the class, open file and import the 3ds into our 
	#/////	C3DModel class
	#/////
	#///////////////////////////////// IMPORT3DS \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def Import3DS( self, pModel, strFileName ):
	
		self.currentChunk = CChunk()
		# Open the 3DS file
		try:
			self.m_FilePointer = open(strFileName, "rb")
		except IOError:
			# Make sure we have a valid file pointer (we found the file)
			print("Unable to find the file %s!" % (strFileName))
			return 
			
		# Once we have the file open, we need to read the very first data chunk
		# to see if it's a 3DS file.  That way we don't read an invalid file.
		# If it is a 3DS file, then the first chunk ID will be equal to PRIMARY (some hex num)
		
		# Read the first chuck of the file to see if it's a 3DS file
		self.ReadChunk(self.currentChunk)
		
		# Make sure this is a 3DS file
		if (self.currentChunk.ID != PRIMARY):
			print("Unable to load PRIMARY chuck from file: %s!" % (strFileName))
			print( "%s" % self.currentChunk.ID)
			return 
			
		# Now we actually start reading in the data.  ProcessNextChunk() is recursive
		# Begin loading objects, by calling this recursive function
		self.ProcessNextChunk(pModel, self.currentChunk)
	
		# Clean up after everything
		self.CleanUp()
		return 
		
	#///////////////////////////////// CLEAN UP \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function cleans up our allocated memory and closes the file
	#/////
	#///////////////////////////////// CLEAN UP \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def CleanUp( self ):
	
		self.m_FilePointer.close()		# Close the current file pointer
	
	#/////////////////////////// PROCESS NEXT CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads the main sections of the .3DS file, then dives 
	#/////	deeper with recursion
	#/////
	#/////////////////////////// PROCESS NEXT CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ProcessNextChunk( self, pModel, pPreviousChunk ):
	
		print( "CHUNK <--")
		
		self.currentChunk = CChunk()		# The current chunk to load
		version	 = 0						# This will hold the file version
    	
		# Below we check our chunk ID each time we read a new chunk.  Then, if
		# we want to extract the information from that chunk, we do so.
		# If we don't want a chunk, we just read past it.  
    	
		# Continue to read the sub chunks until we have reached the length.
		# After we read ANYTHING we add the bytes read to the chunk and then check
		# check against the length.
		while pPreviousChunk.bytesRead < pPreviousChunk.length:
		
			# Read next Chunk
			self.ReadChunk(self.currentChunk)
    	
			# Check the chunk ID
			if self.currentChunk.ID == VERSION:	# This holds the version of the file				
				# If the file was made in 3D Studio Max, this chunk has an int that 
				# holds the file version.  Since there might be new additions to the 3DS file
				# format in 4.0, we give a warning to that problem.
				# However, if the file wasn't made by 3D Studio Max, we don't 100% what the
				# version length will be so we'll simply ignore the value
    			# Read the file version and add the bytes read to our bytesRead variable
				value = self.fread("H", 2, 1)
				self.currentChunk.bytesRead += value[0]
				version = value[1]
				print( "VERSION %s, file version %s" % (VERSION,version))
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)
				# If the file version is over 3, give a warning that there could be a problem
				if  (version > int("0x03",16)):
					print( "This 3DS file is over version 3 so it may load incorrectly")
    	
			elif self.currentChunk.ID == OBJECTINFO:	# This holds the version of the mesh
				# This chunk holds the version of the mesh.  It is also the head of the MATERIAL
				# and OBJECT chunks.  From here on we start reading in the material and object info.    	
				# Read the next chunk
				self.ReadChunk(self.tempChunk)    	
				# Get the version of the mesh
				value = self.fread("H", 2, 1)
				self.tempChunk.bytesRead += value[0]
				version = value[1]
				print( "OBJECTINFO %s, mesh version %s" % (OBJECTINFO,version))
				# skip some trash
				self.tempChunk.bytesRead += self.skip(self.tempChunk.length - self.tempChunk.bytesRead)
				# Increase the bytesRead by the bytes read from the last chunk
				self.currentChunk.bytesRead += self.tempChunk.bytesRead
				# Go to the next chunk, which is the object has a texture, it should be MATERIAL, then OBJECT.
				self.ProcessNextChunk(pModel, self.currentChunk)

			elif self.currentChunk.ID == MATERIAL:				# This holds the material information			 			
				# This chunk is the header for the material info chunks				
				# Increase the number of materials
				pModel.numOfMaterials += 1
				print( "MATERIAL (num: %s)" % pModel.numOfMaterials)	
				# This is used to add to our material list
				newTexture = CMaterialInfo()				
				# Add a empty texture structure to our texture list.
				pModel.pMaterials.append(newTexture)    	
				# Proceed to the material loading function
				self.ProcessNextMaterialChunk(pModel, self.currentChunk)
    	
			elif self.currentChunk.ID == OBJECT:	# This holds the name of the object being read
				print( "OBJECT"	)		
				# This chunk is the header for the object info chunks.  It also
				# holds the name of the object.    	
				# Increase the object count
				pModel.numOfObjects += 1
				# A new object to add to our object list
				newObject = C3DObject() 
				# Get the name of the object and store it, then add the read bytes to our byte counter.
				value = self.GetString()
				self.currentChunk.bytesRead += value[0]
				newObject.strName = value[1]
				# Add a new CObject node to our list of objects (like a link list)
				pModel.pObjects.append(newObject)				
				print( "OBJECT %s, object name -%s-" % (OBJECT,value[1]))				
				# Now proceed to read in the rest of the object information
				self.ProcessNextObjectChunk(pModel, newObject, self.currentChunk)
		
			elif self.currentChunk.ID == EDITKEYFRAME:			
				print("EDITKEYFRAME")		
				# This is where we starting to read in all the key frame information.
				# This is read in at the END of the file.  It stores all the animation data.
				# Recurse further to read in all the animation data
				self.ProcessNextKeyFrameChunk(pModel, self.currentChunk)
			
			else : 			
				print("CHUNK ELSE at %s " % self.m_FilePointer.tell())
				# If we didn't care about a chunk, then we get here.  We still need
				# to read past the unknown or ignored chunk and add the bytes read to the byte counter.
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)
				
			# Add the bytes read from the last chunk to the previous chunk passed in.
			pPreviousChunk.bytesRead += self.currentChunk.bytesRead
			
		# Free the current CChunk and set it back to the previous CChunk (since it started that way)
		self.currentChunk = pPreviousChunk

	#///////////////////////////////// PROCESS NEXT OBJECT CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function handles all the information about the objects in the file
	#/////
	#///////////////////////////////// PROCESS NEXT OBJECT CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ProcessNextObjectChunk(self, pModel, pObject, pPreviousChunk):
	
		print("--> OBJECT CHUNK  <--")
		
		# The current object chunk to work with
		self.currentChunk = CChunk()
	
		# Continue to read these chunks until we read the end of this sub chunk
		while pPreviousChunk.bytesRead < pPreviousChunk.length:
		
			# Read the next chunk
			self.ReadChunk(self.currentChunk)
			
			# Check which chunk we just read
			if self.currentChunk.ID == OBJECT_MESH:			# This lets us know that we are reading a new mesh object
				print( "--> OBJECT_MESH")
				# Read all the infgormations about the mesh
				self.ProcessNextMeshChunk( pModel, pObject, self.currentChunk)	
												
			elif self.currentChunk.ID == OBJECT_LIGHT:
				print( "--> OBJECT_LIGHT")
				# Increase the light count
				pModel.numOfLights += 1
				newLight = CLight() 				
				self.ReadLight(newLight, self.currentChunk)							
				pModel.pLights.append(newLight)
				
			elif self.currentChunk.ID == OBJECT_CAMERA:
				print( "--> OBJECT_CAMERA")
				pModel.numOfCameras += 1
				newCamera = CCamera()				
				pModel.pCameras.append(newCamera)				
				self.ReadCamera(newCamera, self.currentChunk)
				
			elif self.currentChunk.ID == OBJECT_CAMERA_RANGES:				
				print( "--> OBJECT_CAMERA_RANGES")
				self.ReadCameraRanges(pModel, self.currentChunk)
				
			else:  
				print( "--> OBJECTCHUNK ELSE at %s " % self.m_FilePointer.tell())
				# Read past the ignored or unknown chunks
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)
				
			# Add the bytes read from the last chunk to the previous chunk passed in.
			pPreviousChunk.bytesRead += self.currentChunk.bytesRead
		
		# Free the current CChunk and set it back to the previous CChunk (since it started that way)
		self.currentChunk = pPreviousChunk
		
	#///////////////////////////////// PROCESS NEXT MESH CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function handles all the information about the mesh
	#/////
	#///////////////////////////////// PROCESS NEXT MESH CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ProcessNextMeshChunk(self, pModel, pObject, pPreviousChunk):

		print( "--> MESH CHUNK  <--")
				
		# The mesh current chunk to work with
		self.currentChunk = CChunk()				
				
		# Continue to read these chunks until we read the end of this sub chunk
		while pPreviousChunk.bytesRead < pPreviousChunk.length:
		
			# Read the next chunk
			self.ReadChunk(self.currentChunk)
									
			# We found a new object, so let's read in							
			if self.currentChunk.ID == OBJECT_MESH_VERTICES:		# This is the objects vertices
				print( "--> OBJECT_MESH_VERTICES")
				self.ReadVertices(pObject, self.currentChunk)
			
			elif self.currentChunk.ID == OBJECT_MESH_FACES:			# This is the objects face information
				print( "--> OBJECT_MESH_FACES")
				self.ReadVertexIndices(pObject, self.currentChunk)	
					
			elif self.currentChunk.ID == OBJECT_MESH_MATERIAL:		# This holds the material name that the object has				
				print( "--> OBJECT_MESH_MATERIAL")
				# This chunk holds the name of the material that the object has assigned to it.
				# This could either be just a color or a texture map.  This chunk also holds
				# the faces that the texture is assigned to (In the case that there is multiple
				# textures assigned to one object, or it just has a texture on a part of the object.
				# Since most of my game objects just have the texture around the whole object, and 
				# they aren't multitextured, I just want the material name.			
				# We now will read the name of the material assigned to this object
				self.ReadObjectMaterial(pModel, pObject, self.currentChunk)			
			
			elif self.currentChunk.ID == OBJECT_MESH_UV:				# This holds the UV texture coordinates for the object
				print( "--> OBJECT_MESH_UV")
				# This chunk holds all of the UV coordinates for our object.  Let's read them in.
				self.ReadUVCoordinates(pObject, self.currentChunk)

			elif self.currentChunk.ID == OBJECT_MESH_MATRIX:		# This holds the matricx for the object
				print( "--> OBJECT_MESH_MATRIX")
				# This chunk holds the matrix for our object.
				self.ReadMeshMatrix(pObject, self.currentChunk)
										
			else:  
				print( "--> OBJECTCHUNK ELSE at %s " % self.m_FilePointer.tell())
				# Read past the ignored or unknown chunks
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)
		
			# Add the bytes read from the last chunk to the previous chunk passed in.
			pPreviousChunk.bytesRead += self.currentChunk.bytesRead

		# Free the current CChunk and set it back to the previous CChunk (since it started that way)
		self.currentChunk = pPreviousChunk
		

	#///////////////////////////////// PROCESS NEXT MATERIAL CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function handles all the information about the material (Texture)
	#/////
	#///////////////////////////////// PROCESS NEXT MATERIAL CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ProcessNextMaterialChunk(self, pModel, pPreviousChunk):
	
		print( "--> MATERIAL CHUNK <--")
		
		# The current chunk to work with
		self.currentChunk = CChunk()
		
		# Continue to read these chunks until we read the end of this sub chunk
		while pPreviousChunk.bytesRead < pPreviousChunk.length:
		
			# Read the next chunk
			self.ReadChunk(self.currentChunk)
		
			# Check which chunk we just read in
			
			if self.currentChunk.ID == MATERIAL_NAME:		# This chunk holds the name of the material
				# Here we read in the material name
				value = self.GetString()
				self.currentChunk.bytesRead += value[0] 
				pModel.pMaterials[pModel.numOfMaterials - 1].strName = value[1] 
				print( "--> MATERIAL_NAME %s, material name %s" % (MATERIAL_NAME,value[1]))
			
			elif self.currentChunk.ID == MATERIAL_AMBIENT:			# This holds the R G B color of our object
				print( "--> MATERIAL_AMBIENT")
				self.ReadAmbientChunk( pModel, self.currentChunk)
				
			elif self.currentChunk.ID == MATERIAL_DIFFUSE:			# This holds the R G B color of our object			
				print( "--> MATERIAL_DIFFUSE")
				self.ReadColorChunk( pModel, self.currentChunk)
			
			elif self.currentChunk.ID == MATERIAL_SPECULAR:			# This holds the R G B color of our object
				print( "--> MATERIAL_SPECULAR")
				self.ReadSpecularChunk( pModel, self.currentChunk)
			
			elif self.currentChunk.ID == MATERIAL_SHINESS:
				# ---> todo
				print( "--> MATERIAL_SHINESS")
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)

			elif self.currentChunk.ID == MATERIAL_TRANSPARENCY :			
				print( "--> MATERIAL_TRANSPARENCY")
				# Proceed to read in the transparency information (alpha channel)
				self.ReadTransparencyChunk(pModel, self.currentChunk)				
							
			elif self.currentChunk.ID == MATERIAL_MAP :			
				print( "--> MATERIAL_MAP")
				# Proceed to read in the material information
				self.ProcessNextMaterialChunk(pModel, self.currentChunk)

			elif self.currentChunk.ID == MATERIAL_MAP_SPECULAR :			
				print( "--> MATERIAL_MAP_SPECULAR")
				# Proceed to read in the material information
				self.ProcessNextMaterialChunk(pModel, self.currentChunk)
	
			elif self.currentChunk.ID == MATERIAL_MAP_OPACITY :			
				print( "--> MATERIAL_MAP_OPACITY")
				# Proceed to read in the material information
				self.ProcessNextMaterialChunk(pModel, self.currentChunk)
	
			elif self.currentChunk.ID == MATERIAL_MAP_BUMP :			
				print( "--> MATERIAL_MAP_BUMP")
				# Proceed to read in the material information
				self.ProcessNextMaterialChunk(pModel, self.currentChunk)
					
			elif self.currentChunk.ID == MATERIAL_MAP_FILE:			# This stores the file name of the material				
				print( "--> MATERIAL_MAP_FILE")
				# Here we read in the material's file name
				value = self.GetString()
				self.currentChunk.bytesRead += value[0] 
				pModel.pMaterials[pModel.numOfMaterials - 1].strFile = value[1] 
				print( "--> MATERIAL_MAP_FILE %s, material file name %s" % (MATERIAL_MAP_FILE,value[1]))
				
			else:				
				print( "--> MATERIAL_ELSE at %s " % self.m_FilePointer.tell())
				# Read past the ignored or unknown chunks
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)
			
			# Add the bytes read from the last chunk to the previous chunk passed in.
			pPreviousChunk.bytesRead += self.currentChunk.bytesRead
			
		# Free the current chunk and set it back to the previous chunk (since it started that way)
		self.currentChunk = pPreviousChunk

	#///////////////////////////////// PROCESS NEXT KEYFRAME CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function handles all the information about the keyframes (animation data)
	#/////
	#///////////////////////////////// PROCESS NEXT KEYFRAME CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ProcessNextKeyFrameChunk(self, pModel, pPreviousChunk):

		print( "--> KEYFRAME CHUNK <--")
			
		# Allocate a new chunk to work with
		self.currentChunk = CChunk()

		# Continue to read these chunks until we read the end of this sub chunk
		while pPreviousChunk.bytesRead < pPreviousChunk.length :
	
			# Read the next chunk
			self.ReadChunk(self.currentChunk)

			# Check which chunk we just read
			if self.currentChunk.ID == KEYFRAME_MESH_INFO:		# This tells us there is a new object being described
				print( "--> KEYFRAME_MESH_INFO")
				# This tells us that we have another objects animation data to be read,
				# so let's use recursion again so we read the next chunk and not read past this.
				self.ProcessNextKeyFrameChunk(pModel, self.currentChunk)

			elif self.currentChunk.ID ==  KEYFRAME_OBJECT_NAME:	# This stores the current objects name
				print( "--> KEYFRAME_OBJECT_NAME")							
				# Get the name of the object that the animation data being read is about.		
				value = self.GetString()
				# This stores the name of the current object being described							
				self.currentChunk.bytesRead += value[0]
				strKeyFrameObject = value[1]
				# Now that we have the object that is being described, set the m_CurrentObject.
				# That way we have a pointer to the object in the model to store the anim data.
				self.SetCurrentObject(pModel, strKeyFrameObject)			
				# Read past 2 flags and heirarchy number (3 shorts - Not used by this loader).
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)

			elif self.currentChunk.ID ==  KEYFRAME_START_AND_END:	# This chunk stores the start and end frame	
				print( "--> KEYFRAME_START_AND_END")					
				# Read in the beginning frame and the end frame.  We just write over the
				# beginning frame because it is assumed that we will always start at the beginning (0)
				value  = self.fread("L",4,1)
				self.currentChunk.bytesRead += value[0] 
				pModel.numberOfFrames = value[1] 
				value  = self.fread("L",4,1)				
				self.currentChunk.bytesRead += value[0] 
				pModel.numberOfFrames = value[1] 
				print( "-->> NUM KEYFRAMES IS %s" % pModel.numberOfFrames)
				
			elif self.currentChunk.ID == PIVOT:		# This stores the pivot point of the object		
				print( "--> PIVOT")			
				# Here we read in 3 floats which are the (X, Y, Z) for the objects pivot point.
				# The pivot point is the local axis in which the object rotates around.  This is
				# By default (0, 0, 0), but may be changed manually in 3DS Max.
				self.m_CurrentObject.vPivot = []
				value  = self.fread("f",4,1)
				self.currentChunk.bytesRead += value[0] 	
				self.m_CurrentObject.vPivot.append(value[1])
				value  = self.fread("f",4,1)
				self.currentChunk.bytesRead += value[0] 	
				self.m_CurrentObject.vPivot.append(value[1])
				value  = self.fread("f",4,1)
				self.currentChunk.bytesRead += value[0] 	
				self.m_CurrentObject.vPivot.append(value[1])


			elif self.currentChunk.ID == POSITION_TRACK_TAG:		# This stores the translation position each frame
				print( "--> POSITION_TRACK_TAG")			
				# Now we want to read in the positions for each frame of the animation
				self.ReadKeyFramePositions(pModel, self.currentChunk)

			elif self.currentChunk.ID == ROTATION_TRACK_TAG:		# This stores the rotation values for each KEY frame			
				print( "--> ROTATION_TRACK_TAG")			
				# Now we want to read in the rotations for each KEY frame of the animation.
				# This doesn't store rotation values for each frame like scale and translation,
				# so we need to interpolate between each frame.
				self.ReadKeyFrameRotations(pModel, self.currentChunk)

			elif self.currentChunk.ID == SCALE_TRACK_TAG:			# This stores the scale values for each frame
				print( "--> SCALE_TRACK_TAG")			
				# Now we want to read in the scale value for each frame of the animation
				self.ReadKeyFrameScales(pModel, self.currentChunk)

			else:				
				print( "--> KEYFRAME_ELSE at %s " % self.m_FilePointer.tell())
				# Read past the ignored or unknown chunks
				self.currentChunk.bytesRead += self.skip(self.currentChunk.length - self.currentChunk.bytesRead)
			
			# Add the bytes read from the last chunk to the previous chunk passed in.
			pPreviousChunk.bytesRead += self.currentChunk.bytesRead
			
		# Free the current chunk and set it back to the previous chunk (since it started that way)
		self.currentChunk = pPreviousChunk

						
	#///////////////////////////////// READ CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in a chunk ID and it's length in bytes
	#/////
	#///////////////////////////////// READ CHUNK \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadChunk(self, pChunk):
	
		# This reads the chunk ID which is 2 bytes.
		# The chunk ID is like OBJECT or MATERIAL.  It tells what data is
		# able to be read in within the chunks section.  
		value = self.fread( "H", 2, 1 )
		pChunk.bytesRead = value[0] 	
		pChunk.ID = value[1] 
		
		# Then, we read the length of the chunk which is 4 bytes.
		# This is how we know how much to read in, or read past.
		value = self.fread( "L", 4, 1 )
		pChunk.bytesRead += value[0] 	
		pChunk.length = value[1] 
		
		
	#///////////////////////////////// GET STRING \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in a string of characters
	#/////
	#///////////////////////////////// GET STRING \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def GetString(self):
	
		string=""

		while (1):
			char=self.m_FilePointer.read(1)
			if (char=='\0'):
				return ( (len(string)+1), string)
			else:
				string=string+char

	#///////////////////////////////// READ LIGHT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the Light chunk
	#/////
	#///////////////////////////////// READ LIGHT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadLight(self, pLight, pChunk):
	
		print( "--> READLIGHT")
		
		pObject.vPosition = []
			
		# Read the Position for the light
		value = self.fread("f",4,1)
		pChunk.bytesRead += value[0] 
		pLight.position.append(value[1])
		value = self.fread("f",4,1)
		pChunk.bytesRead += value[0]  
		pLight.position.append(value[1])
		value = self.fread("f",4,1)
		pChunk.bytesRead += value[0] 
		pLight.position.append(value[1])
		
	#///////////////////////////////// READ COLOR \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the RGB color data
	#/////
	#///////////////////////////////// READ COLOR \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadColorChunk(self, pModel, pChunk):
	
		print( "--> READCOLORCHUNK"	)
		pModel.pMaterials[pModel.numOfMaterials - 1].color = []
		
		# Read the color chunk info
		self.ReadChunk(self.tempChunk)
		
		# Read in the R  color (3 bytes - 0 through 255)
		value = self.fread("B",1,1)	
		self.tempChunk.bytesRead += 1
		((pModel.pMaterials[pModel.numOfMaterials - 1]).color).append(value[1])	
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1
		((pModel.pMaterials[pModel.numOfMaterials - 1]).color).append(value[1])
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1
		((pModel.pMaterials[pModel.numOfMaterials - 1]).color).append(value[1])
		# Add the bytes read to our chunk
		pChunk.bytesRead += self.tempChunk.bytesRead;
		
	#///////////////////////////////// READ AMBIENT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the RGB color data
	#/////
	#///////////////////////////////// READ AMBIENT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadAmbientChunk(self, pModel, pChunk):

		print( "--> READAMBIENTCHUNK")		
		pModel.pMaterials[pModel.numOfMaterials - 1].ambient = []
				
		# Read the color chunk info
		self.ReadChunk(self.tempChunk)
	
		# Read in the R  color (3 bytes - 0 through 255)
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1
		((pModel.pMaterials[pModel.numOfMaterials - 1]).ambient).append(value[1])		
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1
		((pModel.pMaterials[pModel.numOfMaterials - 1]).ambient).append(value[1])
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1
		((pModel.pMaterials[pModel.numOfMaterials - 1]).ambient).append(value[1])
				
		# Add the bytes read to our chunk
		pChunk.bytesRead += self.tempChunk.bytesRead;
		
	#///////////////////////////////// READ SPECULAR \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the RGB color data
	#/////
	#///////////////////////////////// READ SPECULAR \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadSpecularChunk(self, pModel, pChunk):

		print( "--> READSPECULARCHUNK")		
		pModel.pMaterials[pModel.numOfMaterials - 1].specular = []
				
		# Read the color chunk info
		self.ReadChunk(self.tempChunk)
	
		# Read in the R  color (3 bytes - 0 through 255)
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1;
		((pModel.pMaterials[pModel.numOfMaterials - 1]).specular).append(value[1])
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1;
		((pModel.pMaterials[pModel.numOfMaterials - 1]).specular).append(value[1])
		value = self.fread("B",1,1)
		self.tempChunk.bytesRead += 1;
		((pModel.pMaterials[pModel.numOfMaterials - 1]).specular).append(value[1])
				
		# Add the bytes read to our chunk
		pChunk.bytesRead += self.tempChunk.bytesRead;

	#///////////////////////////////// READ TRANSPARENCY \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the alpha color data
	#/////
	#///////////////////////////////// READ TRANSPARENCY \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadTransparencyChunk(self, pModel, pChunk):
	
		print( "--> READTRANSPARENCYCHUNK")		
		
		# Read the color chunk info
		self.ReadChunk(self.tempChunk)
	
		# Read in the alpha  color 
		value = self.fread("H",2,1)
		self.tempChunk.bytesRead += value[0] 
		pModel.pMaterials[pModel.numOfMaterials - 1].alpha = value[1] 
				
		# Add the bytes read to our chunk
		pChunk.bytesRead += self.tempChunk.bytesRead;		
				
	#///////////////////////////////// READ CAMERA \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the camera data
	#/////
	#///////////////////////////////// READ CAMERA \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadCamera(self, pCamera, pChunk):

		print( "--> READCAMERA")
		pCamera.Position = []
		# camera x
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Position.append(value[1])
		# camera y
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0] 
		pCamera.Position.append(value[1])
		# camera z
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Position.append(value[1])
		
		pCamera.Target	= []	
		# tartget x
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Target.append(value[1])
		# target y
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Target.append(value[1])
		# target z
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Target.append(value[1])
		# bank angle
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Angle = value[1] 
		# focus
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		pCamera.Focus = value[1] 

	#///////////////////////////////// READ CAMERA RANGES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the camra ranges data
	#/////
	#///////////////////////////////// READ CAMERA RANGES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadCameraRanges(self,pModel, pChunk):
	
		print( "--> READCAMERARANGES")
		
		# camera near range
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0]  
		(pModel.pCameras[len(pModel.pCameras)-1]).near = value[1] 
		# camera far range
		value = self.fread("f", 4, 1)
		pChunk.bytesRead += value[0] 
		(pModel.pCameras[len(pModel.pCameras)-1]).far = value[1] 

		
	#///////////////////////////////// READ VERTEX INDECES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the indices for the vertex array
	#/////
	#///////////////////////////////// READ VERTEX INDECES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadVertexIndices(self, pObject, pPreviousChunk):
	
		print( "--> READVERTEXINDICES")
		
		# In order to read in the vertex indices for the object, we need to first
		# read in the number of them, then read them in.  Remember,
		# we only want 3 of the 4 values read in for each face.  The fourth is
		# a visibility flag for 3D Studio Max that doesn't mean anything to us.
	
		# Read in the number of faces that are in this object (int)
		value = self.fread("H",2,1)
		pPreviousChunk.bytesRead += value[0]
		pObject.numOfFaces = value[1]
		
		# Alloc enough memory for the faces and initialize the structure
		pObject.pFaces = []
	
		# Go through all of the faces in this object
		for i in xrange(pObject.numOfFaces):
			
			# Read the first vertice index for the current face 
			value = self.fread("H",2,1)
			pPreviousChunk.bytesRead += value[0]  
			a = value[1]
			
			# Read the second vertice index for the current face 
			value = self.fread("H",2,1)
			pPreviousChunk.bytesRead += value[0]  
			b = value[1]
			
			# Read the third vertice index for the current face 
			value = self.fread("H",2,1)
			pPreviousChunk.bytesRead += value[0]  
			c = value[1]
			
			# Visibility flag
			value = self.fread("H",2,1)
			pPreviousChunk.bytesRead += value[0]  
			bVisible = value[1]
			
			# Store the index in our face structure.
			indices = CIndices()
			indices.a = a;
			indices.b = b 
			indices.c = c 
			indices.bVisible = bVisible
			
			face = CFace()
			face.vertIndex = indices;
			
			pObject.pFaces.append(face)

	#///////////////////////////////// READ UV COORDINATES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the UV coordinates for the object
	#/////
	#///////////////////////////////// READ UV COORDINATES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadUVCoordinates(self, pObject, pPreviousChunk):
	
		print( "--> READUVCOORDINATES")
		
		# In order to read in the UV indices for the object, we need to first
		# read in the amount there are, then read them in.
	
		# Read in the number of UV coordinates there are (int)
		value = self.fread("H", 2, 1)
		pPreviousChunk.bytesRead += value[0]
		pObject.numTexVertex = value[1]
		
		# Allocate memory to hold the UV coordinates
		pObject.pTexVerts = []
	
		# Read in the texture coodinates (an array 2 float)
		
		for i in xrange(pObject.numTexVertex):
		
			value = self.fread("f", 4, 1)
			pPreviousChunk.bytesRead += value[0]  
			vert1 = value[1]
			
			value = self.fread("f", 4, 1)
			pPreviousChunk.bytesRead += value[0]  
			vert2 = value[1]
			
			TexVector = CVector2(vert1,vert2)
			pObject.pTexVerts.append( TexVector )
			
		
	#///////////////////////////////// READ VERTICES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the vertices for the object
	#/////
	#///////////////////////////////// READ VERTICES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadVertices(self, pObject, pPreviousChunk):

		print( "--> READVERTICES")
		# Like most chunks, before we read in the actual vertices, we need
		# to find out how many there are to read in.  Once we have that number
		# we then self.fread() them into our vertice array.
	
		# Read in the number of vertices (int)
		value = self.fread("H",2,1)
		pPreviousChunk.bytesRead += value[0]
		pObject.numOfVerts = value[1]
		
		pObject.pVerts = []
		
		for i in xrange(pObject.numOfVerts):

			# Read in the vertices
			value = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]  
			vert1 = value[1] 
			
			value = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]  
			vert2 = value[1] 
			
			value = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]  
			vert3 = value[1] 
						
			VertVector = CVector3(vert1,vert2,vert3)
			pObject.pVerts.append( VertVector )

						
	#///////////////////////////////// READ VERTICES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the vertices for the object
	#/////
	#///////////////////////////////// READ VERTICES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadMeshMatrix(self, pObject, pPreviousChunk):	
						
		print("--> READOBJECTMESHMATRIX")
		
		pObject.objMatrix = []
		
		# Read in the matrix 4x3 (it's an array of floats)
		for r in xrange(4):
			for c in xrange(3):
							
				val = self.fread("f",4,1)
				pPreviousChunk.bytesRead += val[0]  	
				# Add each num to our object matrix	
				pObject.objMatrix.append(val[1])

									
	#///////////////////////////////// READ OBJECT MATERIAL \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the material name assigned to the object and sets the materialID
	#/////
	#///////////////////////////////// READ OBJECT MATERIAL \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadObjectMaterial(self, pModel, pObject, pPreviousChunk):
	
		print("--> READOBJECTMATERIAL")
	
		strMaterial = ""	    # This is used to hold the objects material name
	
		# *What is a material?*  - A material is either the color or the texture map of the object.
		# It can also hold other information like the brightness, shine, etc... Stuff we don't
		# really care about.  We just want the color, or the texture map file name really.
	
		# Here we read the material name that is assigned to the current object.
		# strMaterial should now have a string of the material name, like "Material #2" etc..
		value = self.GetString()
		print( "--> %s " % value[1])
		pPreviousChunk.bytesRead += value[0]  
		strMaterial = value[1]
		
		
		nFaces = 0		#This is used to hold the number of faces for the material
		pFaces = []		#The array of faces
		
		# Look if our material is applied to some faces rather than the whole object
		value = self.fread("H",2,1)
		pPreviousChunk.bytesRead += value[0]  
		nFaces = value[1] 	
		
		if( nFaces > 0):
				
			# Loop nFaces times to read all the face indexes
			for i in xrange(nFaces):
				value = self.fread("H",2,1)
				pPreviousChunk.bytesRead += value[0] 		
				pFaces.append(value[1])
		else:
			nFaces = 0;	
		# Now that we have a material name, we need to go through all of the materials
		# and check the name against each material.  When we find a material in our material
		# list that matches this name we just read in, then we assign the materialID
		# of the object to that material index.  You will notice that we passed in the
		# model to this function.  This is because we need the number of textures.
		# Yes though, we could have just passed in the model and not the object too.
	
		pObject.materialID = []		
		
		# Go through all of the textures
		for i in range(pModel.numOfMaterials):
	
			# If the material we just read in matches the current texture name
			if strMaterial == pModel.pMaterials[i].strName:
	
				# Add to the material ids list of this object the current index 'i'
				pObject.materialID.append(i)
				
				# Assing to our material the numbers of faces is applied to and it's face array
				pModel.pMaterials[i].numOfFaces = nFaces;
				
				if( nFaces > 0): 
					# Add to the material a face array of face index
					pModel.pMaterials[i].pFaces = pFaces;
	
				# Now that we found the material, check if it's a texture map.
				# If the strFile has a string length of 1 and over it's a texture
				if len(pModel.pMaterials[i].strFile) > 0:
	
					# Set the object's flag to say it has a texture map to bind.
					pObject.bHasTexture = True;	
					
				break;
	
		# Read past the rest of the chunk since we don't care about shared vertices
		# You will notice we subtract the bytes already read in this chunk from the total length.
		pPreviousChunk.bytesRead += self.skip(pPreviousChunk.length - pPreviousChunk.bytesRead)

		
	#///////////////////////////////// SET CURRENT OBJECT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This sets the current model that animation is being read in for by it's name
	#/////
	#///////////////////////////////// SET CURRENT OBJECT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def SetCurrentObject(self, pModel, strObjectName):

		print( "--> SETCURRENTOBJECT")	
	
		# This function takes a model and name of an object inside of the model.
		# It then searches the objects in the model and finds that object that
		# has the name passed in.  We use this function after we have read in
		# all the model's data, except for the KEY FRAME data.  The key frame
		# data is last.  The key frame animation data stores the objects name
		# that the data is describing, so we need to get that address to
		# that object and then set the animation data being read in for it.

		# Make sure there was a valid object name passed in
		if(strObjectName == ''): 
	
			# Set the current object to NULL and return
			print( "ERROR: No object in model with given name! (SetCurrentObject) make one new")
			self.m_CurrentObject = C3DObject()
			return 
	
		else :
		 
			# Go through all of the models objects and match up the name passed in
			for object in pModel.pObjects :
		
				# Check if the current model being looked at has the same name as strObjectName
				if strObjectName == object.strName :
			
					# Get a pointer to the object with the name passed in.
					# This will be the object that the next animation data is describing
					print( "--> SETCURRENTOBJECT %s" % object.strName)					
					self.m_CurrentObject = object;
					return 
				
		# Give an error message (better to have an assert()
		print( "ERROR: No object in model with given name! (SetCurrentObject)")
		# Set the current object to NULL since we didn't find an object with that name
		self.m_CurrentObject = C3DObject()
					

	#///////////////////////////////// ROUND FLOAT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This rounds a float down to zero if it's smaller than 0.001 or -0.001
	#/////
	#///////////////////////////////// ROUND FLOAT \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def RoundFloat(self, number):

		# If the float passed in is a really small number, set it to zero
		if(number > 0.0 and number <  0.001 ):
			number = 0.0;
		if(number < 0.0 and number > -0.001 ):
			number = 0.0;

		# Return the float changed or unchanged
		return number;
					    		
		
	#///////////////////////////////// READ KEYFRAME POSITIONS \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the positions of the current object for every frame
	#/////
	#///////////////////////////////// READ KEYFRAME POSITIONS \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadKeyFramePositions(self, pModel, pPreviousChunk ):
	
		print( "--> READKEYFRAMEPOSITIONS")	
	
		frameNumber = 0
		# This function will read in each position for every frame that we need to
		# translate the object too.  Remember, this position is relative to the object's
		# pivot point.  The first 5 short's are ignored because we do not utilize
		# them in this tutorial.  they are flags, the node ID, tension, bias, strength
		# I believe.
		
		self.m_CurrentObject.vPosition = []		
		
		# Read past the ignored data
		pPreviousChunk.bytesRead += self.skip(10)
		# Here we read in the number of position frames this object has.
		# In other words, how many times the object moves to a new location
		value  = self.fread("h",2,1)
		pPreviousChunk.bytesRead += value[0] 	
		self.m_CurrentObject.positionFrames = value[1]		
		# Read past one more ignored short
		pPreviousChunk.bytesRead += self.skip(2)	
		# Now we need to go through ALL of the frames of animation and set
		# the position of the object for every frame.  Even if we only have one
		# or 50 position changes out of 100 frames, we will set the remaining to
		# the last position it moved too.
		for i in xrange(int(pModel.numberOfFrames)+1):	

			# If the current frame of animation hasn't gone over the position frames,
			# we want to read in the next position for the current frame.
			if (i < self.m_CurrentObject.positionFrames):
							
				# Read in the current frame number (not used ever, we just use i)
				value  = self.fread("h",2,1)
				pPreviousChunk.bytesRead += value[0] 	
				frameNumber = value[1]
						
				# Next we read past an unknown long
				pPreviousChunk.bytesRead += self.skip(4)
						
				# Here we read in 3 floats that store the (x, y, z) of the position.
				# Remember, CVector3 is 3 floats so it's the same thing as sizeof(float) * 3.
				value  = self.fread("f",4,1)
				pPreviousChunk.bytesRead += value[0] 	
				x = value[1] 
				value  = self.fread("f",4,1)
				pPreviousChunk.bytesRead += value[0] 	
				y = value[1] 
				value  = self.fread("f",4,1)
				pPreviousChunk.bytesRead += value[0] 	
				z = value[1] 	
				
				# Here we add a new CVector3 to our list of positions.  This will
				# store the current position for the current frame of animation 'i'.
				self.m_CurrentObject.vPosition.append(CVector3(x,y,z))														
			
			# Otherwise we just set the current frames position to the last position read in
			else:
				# Set the current frame's position to the last position read in.
				self.m_CurrentObject.vPosition.append(self.m_CurrentObject.vPosition[self.m_CurrentObject.positionFrames - 1])			

		# Now we need to go through and subtract the pivot point from each vertice.
		# 3DS files are saved with their vertices in world space PLUS their pivot point (bad).
		# You will notice we also subtract the current frame's position from each point.
		# We do this because 3DS files store the position of the pivot point for each frame.
		# We want the pivot point to start at zero
		for i in xrange(self.m_CurrentObject.numOfVerts):
		
			# Subtract the current frames position and pivtor point from each vertice to make it easier.
			self.m_CurrentObject.pVerts[i].x -= (self.m_CurrentObject.vPosition[0].x + self.m_CurrentObject.vPivot[0])
			self.m_CurrentObject.pVerts[i].y -= (self.m_CurrentObject.vPosition[0].y + self.m_CurrentObject.vPivot[1])
			self.m_CurrentObject.pVerts[i].z -= (self.m_CurrentObject.vPosition[0].z + self.m_CurrentObject.vPivot[2])
			

	#///////////////////////////////// READ KEYFRAME ROTATIONS \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the rotations of the current object for every key frame
	#/////
	#///////////////////////////////// READ KEYFRAME ROTATIONS \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadKeyFrameRotations(self, pModel, pPreviousChunk):
	
		print( "--> READKEYFRAMEROTATIONS")

		frameNumber = 0;
		rotationDegree = 0;
		vFrameNumber = []
		vRotDegree = []
		vRotation = []
		
		self.m_CurrentObject.vRotation = []
		self.m_CurrentObject.vRotDegree = []				
		
		# This function will read in each key frames rotation angle and rotation axis.
		# Remember, this rotation is relative to the object's pivot point.  The first 5 
		# short's are ignored because we do not utilize them in this tutorial.  They are 
		# flags, the node ID, tension, bias, and strength I believe.  Don't worry about 
		# them now, the next tutorial we will further explain it.

		# Read past the ignored data
		pPreviousChunk.bytesRead += self.skip(10)

		# Read in the number of rotation key frames for the animation.
		# Remember, unlike the scale and translation data, it does not store
		# the rotation degree and axis for every frame, only for every key frame.
		# That is why we need to interpolate below between each key frame.
		value  = self.fread("h",2,1)
		pPreviousChunk.bytesRead += value[0]	
		self.m_CurrentObject.rotationFrames = value[1]
	
		# Read past an ignored short
		pPreviousChunk.bytesRead += self.skip(2)
	
		# Now we need to go through ALL of the frames of animation and set
		# the rotation of the object for every frame.  We will need to interpolate
		# between key frames if there is more than 1 (there is always at least 1).
		for i in xrange(self.m_CurrentObject.rotationFrames):

			# Next we read in the frame number that the rotation takes place
			value  = self.fread("h",2,1)
			pPreviousChunk.bytesRead += value[0]
			frameNumber = value[1]
			vFrameNumber.append(frameNumber)	
			
			# Then we read past some unknown data
			pPreviousChunk.bytesRead += self.skip(4)
			
			# Read in the current rotation degree for this key frame.  We will
			# also inteprolate between this degree down below if needed.
			value  = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]	
			rotationDegree = value[1]
			vRotDegree.append(rotationDegree)
			
			# Convert the Degrees to degress (Degrees * (180 / PI) = degrees)
			rotationDegree = rotationDegree * (180.0 / 3.14159)
			
			# Here we read in the actual axis that the object will rotate around.
			# This will NOT need to be interpolated because the rotation degree is what matters.
			value  = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]
			x = value[1]
			value  = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]
			y = value[1]
			value  = self.fread("f",4,1)
			pPreviousChunk.bytesRead += value[0]
			z = value[1]
			
			# Because I was having problems before with really small numbers getting
			# set to scientific notation.
			# I just decided to round them down to 0 if they were too small.
			# This isn't ideal, but it seemed to work for me.
			x = self.RoundFloat(x)
			y = self.RoundFloat(y)
			z = self.RoundFloat(z)					
			
			# Here we add the frame number, a new CVector3 for axis and the degree to our list of rotations. 
			vRotation.append(CVector3(x,y,z))	

		self.m_CurrentObject.vRotation.append(vRotation[0])
		# Add the rotation degree for the first frame to our list.  If we did NO rotation
		# in our animation the rotation degree should be 0.
		self.m_CurrentObject.vRotDegree.append(vRotDegree[0])
		
		# Create a counter for the current rotation key we are on (Only used if rotKeys are > 1)
		currentKey = 1;

		# Go through all of the frames of animation plus 1 because it's zero based
		for i in xrange(1, pModel.numberOfFrames + 1): 
		
			self.m_CurrentObject.vRotation.append(CVector3(0.0,0.0,0.0))									
			self.m_CurrentObject.vRotDegree.append(0.0)
			
			# Check if the current key frame is less than or equal to the max key frames
			if(currentKey < self.m_CurrentObject.rotationFrames):
			
				# Get the current and previous key frame number, along with the rotation degree.
				# This just makes it easier code to work with, especially since you can't
				# debug vectors easily because they are operator overloaded.
				currentFrame = vFrameNumber[currentKey] 
				previousFrame = vFrameNumber[currentKey - 1] 
				degree = vRotDegree[currentKey] 
	
				# Interpolate the rotation degrees between the current and last key frame.
				# Basically, this sickningly simple algorithm is just getting how many
				# frames are between the last and current keyframe (currentFrame - previousFrame),
				# Then dividing the current degree by that number.  For instance, say there
				# is a key frame at frame 0, and frame 50.  Well, 50 - 0 == 50 so it comes out
				# to rotationDegree / 50.  This will give us the rotation needed for each frame.
				rotDegree = float(degree / (currentFrame - previousFrame))
	
				# Add the current rotation degree and vector for this frame
				((self.m_CurrentObject).vRotation[i]) = (vRotation[currentKey])									
				((self.m_CurrentObject).vRotDegree[i]) = (rotDegree)			
				# Check if we need to go to the next key frame 
				# (if the current frame i == the current key's frame number)
				if(vFrameNumber[currentKey] <= i) :
					currentKey = currentKey + 1;		
			
			# Otherwise, we are done with key frames, so no more interpolating
			else :
			
				# Set the rest of the rotations to 0 since we don't need to rotate it anymore
				# The rotation axis doesn't matter since the degree is 0.
				self.m_CurrentObject.vRotation.append(vRotation[currentKey - 1])
				self.m_CurrentObject.vRotDegree.append(0.0)
											
		
	#///////////////////////////////// READ KEYFRAME SCALE \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	#/////
	#/////	This function reads in the scale value of the current object for every key frame
	#/////
	#///////////////////////////////// READ KEYFRAME SCALES \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\*
	def ReadKeyFrameScales(self, pModel, pPreviousChunk):

		print( "--> READKEYFRAMESCALES")
		
		frameNumber = 0;
		self.m_CurrentObject.vScale = []
		
		# Like the translation key frame data, the scale ratio is stored for
		# every frame in the animation, not just for every key frame.  This makes
		# it so we don't have to interpolate between frames. 
		# The first 5 short's are ignored because we do not utilize
		# them in this tutorial.  they are flags, the node ID, tension, bias, strength
		# I believe.  Don't worry about them now, the next tutorial we will further explain it.

		# Read past the ignored data
		pPreviousChunk.bytesRead += self.skip(10)
		
		# Here we read in the amount of scale frames there are in the animation.
		# If there is 100 frames of animation and only 50 frames of scaling, we just
		# set the rest of the 50 frames to the last scale frame.
		value  = self.fread("h",2,1)
		pPreviousChunk.bytesRead += value[0] 
		self.m_CurrentObject.scaleFrames = value[1]
	
		# Read past ignored data
		pPreviousChunk.bytesRead += self.skip(2)	
	
		# Now we need to go through ALL of the frames of animation and set
		# the scale value of the object for every frame.  Even if we only have one
		# or 50 scale changes out of 100 frames, we will set the remaining to
		# the last position it scaled too.
		for i in xrange(int(pModel.numberOfFrames)+1):

			# If the current frame is less than the amount of scale frames, read scale data in
			if (i < self.m_CurrentObject.scaleFrames) :
			
				# Read in the current frame number (not used because there is no interpolation)
				value  = self.fread("h",2,1)
				pPreviousChunk.bytesRead += value[0] 	
				frameNumber = value[1]

				# Read past an unknown long
				pPreviousChunk.bytesRead += self.skip(4)	
			
				# Read in the (X, Y, Z) scale value for the current frame.  We will pass this
				# into glScalef() when animating in AnimateModel()			
				value  = self.fread("f",4,1)
				pPreviousChunk.bytesRead += value[0]  
				x = value[1] 
				value  = self.fread("f",4,1)
				pPreviousChunk.bytesRead += value[0]  
				y = value[1] 
				value  = self.fread("f",4,1)
				pPreviousChunk.bytesRead += value[0]  
				z = value[1] 
	
				# Here we add a new CVector3 to our list of scale values. 
				self.m_CurrentObject.vScale.append(CVector3(x,y,z))	
			
			# Otherwise we are done with the scale frames so set the rest to the last scale value
			else:
			
				#Set the current frame's scale value to the last scale value for the animation
				self.m_CurrentObject.vScale.append( self.m_CurrentObject.vScale[self.m_CurrentObject.scaleFrames - 1])
		
			
			
#/////////////////////////////////// CVECTOR3 ///////////////////////////////////*
#/////
#///// This  is the vector class
#/////
#/////////////////////////////////// CVECTOR ////////////////////////////////////*
class CVector3(object):

    def __init__(self,x,y,z):
      self.x = x
      self.y = y
      self.z = z
      
#/////////////////////////////////// CVECTOR2 ///////////////////////////////////*
#/////
#///// This  is the vector class
#/////
#/////////////////////////////////// CVECTOR2 ///////////////////////////////////*
class CVector2(object):

    def __init__(self,x,y):
      self.x = x
      self.y = y
				

	
EVENT_PATHCHANGE=		1
EVENT_IMPORT=			2
EVENT_IMPORT_MATS=		3
EVENT_QUIT=				4

bMaterials = False

#//////////////////////////////////// TOBLENDER /////////////////////////////////*
#/////
#/////	Import the info held by Model3d to blender
#/////
#//////////////////////////////////// TOBLENDER /////////////////////////////////*
def ToBlender(Model3d,FileName):

	FilePath = FileName[0:(len(FileName)-len(bpy.sys.basename(FileName)))] 
	#Get out the  current scene
	scene = Scene.getCurrent()
	
	#//////////////////////// LOAD ANY LIGHT \\\\\\\\\\\\\\\\\\\\\\\\

	for i in xrange(Model3d.numOfLights):
	
		lite = bpy.Lamp.New('Lamp')
		
		# I cant fogur out where light color is stored :(
		# lite.col( Model3d.pLights[i].color[0], 
		#		  		Model3d.pLights[i].color[1], 
		#		  		Model3d.pLights[i].color[2])
	
		lamp = bpy.Object.New('Lamp')
		lamp.setLocation( Model3d.pLights[i].position[0],
						  		Model3d.pLights[i].position[1],
						  		Model3d.pLights[i].position[2])
		# Make the lamp a real light object
		lamp.link(lite)
		# add the lamp to the scene
		scene.link(lamp)
		
	
	#//////////////////////// LOAD ANY CAMERA \\\\\\\\\\\\\\\\\\\\\\\\\

	for i in xrange(Model3d.numOfCameras):
	
		cam = bpy.Camera.New('ortho')
		cam.setClipEnd(Model3d.pCameras[i].far)
		cam.setClipStart(Model3d.pCameras[i].near)
		
		camera = bpy.Object.New('Camera')
		camera.setLocation(  Model3d.pCameras[i].Position[0],
									Model3d.pCameras[i].Position[1],
									Model3d.pCameras[i].Position[2])
		# make the camera a real camera object
		camera.link(cam)
		# add camera to the scene
		scene.link(camera)
	
	#///////////////// LOAD ANY TEXTURE AND MATERIAL \\\\\\\\\\\\\\\\\\\

	
	mats = []
	
	for i in xrange(Model3d.numOfMaterials):
	
		mat = Material.New(Model3d.pMaterials[i].strName)
		# Add color material
		mat.rgbCol = ( float((Model3d.pMaterials[i].color[0])/255.0),
							float((Model3d.pMaterials[i].color[1])/255.0),
					  		float((Model3d.pMaterials[i].color[2])/255.0) )				
			  		
		# Add the specular color
		mat.specCol =( float((Model3d.pMaterials[i].specular[0])/255.0),
					   	float((Model3d.pMaterials[i].specular[1])/255.0),
					   	float((Model3d.pMaterials[i].specular[2])/255.0) )
		# Add the ambient color (i'm not very sure about this)
		mat.mirCol = ( float((Model3d.pMaterials[i].ambient[0])/255.0),
					  		float((Model3d.pMaterials[i].ambient[1])/255.0),
					  		float((Model3d.pMaterials[i].ambient[2])/255.0) )						  			  
		# Add the alpha channel			  
		mat.setAlpha(1.0-(float((Model3d.pMaterials[i].alpha)/100.0)))						  
				
		# If the material has a texture load in the image
		if (len(Model3d.pMaterials[i].strFile) > 0):
			try:
				img = bpy.Image.Load(Model3d.pMaterials[i].strFile)
			except IOError:
				try:
					imgName = str(FilePath+Model3d.pMaterials[i].strFile)
					img = bpy.Image.Load(imgName)
				except IOError:
					print( "failed to load ->%s<- texture" % (imgName))
					img = bpy.Image.New(fname,1,1,24) #blank image							
			tex = bpy.Texture.New()
			tex.setType("Image")
			tex.image = img
			mat.setTexture(0, tex)							
		mats.append(mat)


	#/////////////////////// FOR EVERY OBJECT \\\\\\\\\\\\\\\\\\\\\\\\\
	
	for i in xrange(Model3d.numOfObjects):
	
		# Make sure we have valid objects just in case. (size() is in the vector class)
		if(len(Model3d.pObjects) <= 0):
			break
			
		# Get the current object that we are displaying
		pObject = C3DObject()
		pObject = Model3d.pObjects[i]  
		
		currMesh = bpy.NMesh.New()
		
		#////////////////////// ADD VERTICES \\\\\\\\\\\\\\\\\\\\\\\\\
		
		# Go through all of the vertices of the object and assign them
		# to the current mesh
		for j in xrange(pObject.numOfVerts):
			
			vert = NMesh.Vert(pObject.pVerts[j].x,pObject.pVerts[j].y,pObject.pVerts[j].z)
				
			currMesh.verts.append(vert)
		
		#////////////// ADD MATERIALS AND TEXTURES \\\\\\\\\\\\\\\\\

		# If Object has a texture Set the flag for the uv texture
		if pObject.bHasTexture == True:
			currMesh.hasFaceUV(1)
				
			# Add Vertex uvco coordinates
			for j in xrange(pObject.numTexVertex):
					
				currMesh.verts[j].uvco  = ( pObject.pTexVerts[j].x,pObject.pTexVerts[j].y )
			
		# Add the materials to the mesh
		for m in xrange(len(mats)):
			for ids in xrange(len(pObject.materialID)):
				if mats[m].name == (Model3d.pMaterials[pObject.materialID[ids]].strName):
					print( "Appling to mesh " + str(mats[m].name) + " material")
					currMesh.materials.append(mats[m])
						
		#/////////////////////// ADD FACES \\\\\\\\\\\\\\\\\\\\\\\\\
		
		# Loop again in faces to assign the face indeces
		for j in xrange(pObject.numOfFaces):
			
			face = NMesh.Face()
			face.v.append(currMesh.verts[pObject.pFaces[j].vertIndex.a])
			face.v.append(currMesh.verts[pObject.pFaces[j].vertIndex.b])
			face.v.append(currMesh.verts[pObject.pFaces[j].vertIndex.c])
			currMesh.faces.append(face)
			
		#////////////// FINALLY CREATE THE MESH \\\\\\\\\\\\\\\\\
			
		# Done, unpdate and draw
		#NMesh.PutRaw(currMesh,str(pObject.strName),1)			
		currObject = bpy.Object.New('Mesh',str(pObject.strName) )
		currObject.link(currMesh)
		scene.link(currObject)
		
		#/////////////////////// APPLY MATRIX \\\\\\\\\\\\\\\\\\\\\\\\\
		
		# If we have a valid matrix
		if len(pObject.objMatrix) > int(13):
			# transform our matrix in a squared 4x4 matrix
			row1 = pObject.objMatrix[:3]+[0] 
			row2 = pObject.objMatrix[3:6]+[0] 
			row3 = pObject.objMatrix[6:9]+[0] 
			row4 = pObject.objMatrix[9:]+[1] 		
			matrix = bpy.Mathutils.Matrix(row1,row2,row3,row4)
			currObject.setMatrix(matrix)						
		
		#///////////////////////// ADD IPOS \\\\\\\\\\\\\\\\\\\\\\\\\
			
		ipo = bpy.Ipo.New('Object',str(pObject.strName))
		currObject.setIpo(ipo)
		
		#/////// POSITIONS IPOS \\\\\\\\
		
		locx = ipo.addCurve('LocX')
		locy = ipo.addCurve('LocY')
		locz = ipo.addCurve('LocZ')
		
		locx.setInterpolation('Linear')
		locx.setExtrapolation('Cyclic')
		locy.setExtrapolation('Cyclic')		
		locz.setInterpolation('Linear')
		locz.setExtrapolation('Cyclic')
		
		#//////// SCALE IPOS \\\\\\\\\\
		
		sclx = ipo.addCurve('SizeX')
		scly = ipo.addCurve('SizeY')
		sclz = ipo.addCurve('SizeZ')

		sclx.setInterpolation('Linear')
		sclx.setExtrapolation('Cyclic')		
		scly.setInterpolation('Linear')
		scly.setExtrapolation('Cyclic')		
		sclz.setInterpolation('Linear')
		sclz.setExtrapolation('Cyclic')		
		
		#//////// SCALE IPOS \\\\\\\\\\
		
		rotx = ipo.addCurve('RotX')
		roty = ipo.addCurve('RotY')
		rotz = ipo.addCurve('RotZ')

		rotx.setInterpolation('Linear')
		rotx.setExtrapolation('Cyclic')		
		roty.setInterpolation('Linear')
		roty.setExtrapolation('Cyclic')		
		rotz.setInterpolation('Linear')
		rotz.setExtrapolation('Cyclic')				
					
		angle = 0.0;
	
		#loop thourght the frames		
		for i in xrange(int(Model3d.numberOfFrames)+1):
				
			# add position interpolation	
			locx.addBezier((i, pObject.vPosition[i].x))
			locy.addBezier((i, pObject.vPosition[i].y))						
			locz.addBezier((i, pObject.vPosition[i].z))			
			locx.update()	
			locy.update()
			locz.update()						
				
			# add scale interpolation	
			sclx.addBezier((i, pObject.vScale[i].x))
			scly.addBezier((i, pObject.vScale[i].y))						
			sclz.addBezier((i, pObject.vScale[i].z))				
			sclx.update()		
			scly.update()	
			sclz.update()		
		
			# add rotation interpolation
			if pObject.vRotation[i].x > 0.0 :
				angle += pObject.vRotDegree[i] 
				rotx.addBezier((i, angle))
				rotx.update()
			elif pObject.vRotation[i].x < 0.0 :
				angle -= pObject.vRotDegree[i] 
				rotx.addBezier((i, angle))
				rotx.update()										
			if pObject.vRotation[i].y > 0.0 :
				angle +=pObject.vRotDegree[i] 			
				roty.addBezier((i, angle))
				roty.update()
			elif pObject.vRotation[i].y< 0.0 :
				angle -=pObject.vRotDegree[i] 			
				roty.addBezier((i, angle))
				roty.update()											
			if pObject.vRotation[i].z > 0.0 :
				angle +=pObject.vRotDegree[i] 														
				rotz.addBezier((i, angle))					
				rotz.update()					
			elif pObject.vRotation[i].z < 0.0 :
				angle -=pObject.vRotDegree[i] 														
				rotz.addBezier((i, angle))					
				rotz.update()
							
	bpy.Redraw()
			
	
#//////////////////////////////////// IMPORT /////////////////////////////////*
#/////
#/////	Load the 3ds file, parse it and import everything in blender
#/////
#//////////////////////////////////// IMPORT /////////////////////////////////*
def Import(FileName):

	LOGDIR = FileName[0:(len(FileName)-len(bpy.sys.basename(FileName)))] 
	logfile = '3ds_blend_log.txt'
	try:
		st_f = open(LOGDIR + logfile, 'a+', 0) 
	except IOError:
		try:
			st_f = open(LOGDIR + logfile, 'w+', 0)
		except IOError:
			st_f = open(LOGDIR + logfile, 'w+', 0)
	sys.stderr=sys.stdout=st_f

	try:
		Loader = CLoad3ds()
		Model3d = C3DModel()
		Loader.Import3DS(Model3d,FileName)
		ToBlender(Model3d,FileName)
	except IOError:
		Draw()
		print( "error while loading/processing 3ds file make sure path is correct")


#////////////////////////////////////  MAIN SCRIPT /////////////////////////////////*
#/////
#/////	Start the script
#/////
#////////////////////////////////////  MAIN SCRIPT /////////////////////////////////*
bpy.Window.FileSelector(Import, "Import 3DS", '*.3ds')




