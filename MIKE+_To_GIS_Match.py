#Version 1: MU classic only
#Version 2: Works with MIKE+

import pypyodbc #used to run Access queries

import arcpy
from arcpy import env #used to create mdb

import os # for file operations
import sqlite3
import ctypes
MessageBox = ctypes.windll.user32.MessageBoxA

def executeQuery(sqls, process_path):
    if ".mdb" in process_path:
        conn = pypyodbc.win_connect_mdb(process_path)
    elif ".sqlite" in process_path:
        conn = sqlite3.connect(process_path)
    cur = conn.cursor()
    if type(sqls) == list:
        for sql in sqls:
            print sql
            cur.execute(sql)
    else:
        sql = sqls
        print sql
        cur.execute(sql)
    cur.close()
    conn.commit()
    conn.close()

def readQuery(SQL, process_path):
    queryOutput = []
    if ".mdb" in process_path:
        conn = pypyodbc.win_connect_mdb(process_path)
    elif ".sqlite" in process_path:
        conn = sqlite3.connect(process_path)
    cur = conn.cursor()
    print SQL
    cur.execute(SQL)
    while True:
        row = cur.fetchone()
        if not row:
            break
        #queryOutput.append(row[0])
        queryOutput.append(row)
    cur.close()
    conn.commit()
    conn.close()
    return queryOutput

def changeFieldType(table,field,field_type,db_path):
    sqls = []
    sqls.append("ALTER TABLE " + table + " ADD COLUMN " + field + "_TRANSFER " + field_type)
    sqls.append("UPDATE " + table + " SET " + field + "_TRANSFER = " + field)
    sqls.append("ALTER TABLE " + table + " DROP COLUMN " + field )
    sqls.append("ALTER TABLE " + table + " ADD COLUMN " + field + " " + field_type)
    sqls.append("UPDATE " + table + " SET " + field + " = " + field + "_TRANSFER")
    sqls.append("ALTER TABLE " + table + " DROP COLUMN " + field + "_TRANSFER")
    executeQuery(sqls, db_path)


working_folder = os.getcwd()

accepted_distance = 10

muidCommaSeparated = "FSA_Base_2021pop.sqlite,VSA_BASE_MODEL_2024.sqlite,NSSA_Base_2018pop.sqlite,Lisa_Base.sqlite"
LayerCommaSeparated = "msm_Node,msm_Link"

gis_folder = r'G:\GISLayers\Sewer'
gis_layers = ['Sewer Mains.lyr','Sewer Manholes.lyr','Sewer Structures.lyr','Sewer Valves.lyr','Sewer Connection.lyr']

sewer_area_file = 'Sewer_Areas.shp'
sewer_area_field = 'Sewer_Area'

processDB = "Model_GIS_Processing.mdb"


modelList = [x.strip() for x in muidCommaSeparated.split(',')]

layerList = [x.strip() for x in LayerCommaSeparated.split(',')]

coord_dims = ['X','Y']
ends = [['Start','first','From'],['End','last','To']]

if '.mdb' in muidCommaSeparated and '.sqlite' in muidCommaSeparated:
    message = "Tool ends. You cannot have both .mdb and .sqlite in muidCommaSeparated\n\n"
    MessageBox = ctypes.windll.user32.MessageBoxA
    MessageBox(None, message, 'Info', 0)
    exit()
elif '.mdb' in muidCommaSeparated:
    ext = 'mdb'
else:
    ext = 'sqlite'

#Delete mdb if it exists and create a new
process_path = working_folder + "\\" + processDB
os.remove(process_path) if os.path.exists(process_path) else None
arcpy.CreatePersonalGDB_management(working_folder,processDB)
arcpy.env.workspace = process_path

#Import GIS

sewer_area_path = working_folder + '\\' + sewer_area_file
##sewer_area_layer = arcpy.MakeFeatureLayer_management(sewer_area_path, "Sewer_Area_Layer")
sewer_area_layer = arcpy.MakeFeatureLayer_management(sewer_area_path, "sewer_area_layer")
sewer_area_names = [row[0] for row in arcpy.da.SearchCursor(sewer_area_layer, sewer_area_field)]

for gis_layer in gis_layers:
    print "Importing " + gis_layer
    table_name = gis_layer[:-4].replace(' ','_')

##    arcpy.FeatureClassToFeatureClass_conversion (gis_folder + "\\" + gis_layer, process_path, table_name)

    arcpy.MakeFeatureLayer_management(gis_folder + "\\" + gis_layer, "temp_layer", "LifeCycleStatus <> 'Abandoned' AND LifeCycleStatus <> 'Removed'")

    arcpy.FeatureClassToFeatureClass_conversion("temp_layer", process_path, table_name)
    arcpy.Delete_management("temp_layer")

    arcpy.AddField_management(table_name, 'Sewer_Area', "String")

    arcpy.MakeFeatureLayer_management(table_name, "sewer_layer")

    changeFieldType(table_name,'FacilityID',"TEXT",process_path)

    for sewer_area_name in sewer_area_names:
        arcpy.SelectLayerByAttribute_management(sewer_area_layer, "NEW_SELECTION", sewer_area_field + " = '" + sewer_area_name + "'")
        arcpy.SelectLayerByLocation_management("sewer_layer", "INTERSECT", sewer_area_layer)
        arcpy.CalculateField_management("sewer_layer", 'Sewer_Area', "'" + sewer_area_name + "'", "PYTHON_9.3")
        arcpy.SelectLayerByAttribute_management(sewer_area_layer, "CLEAR_SELECTION")
        arcpy.SelectLayerByAttribute_management("sewer_layer", "CLEAR_SELECTION")
    arcpy.Delete_management("sewer_layer")

    for coord_dim in coord_dims:
        prefix = 'Mid_' if table_name == 'Sewer_Mains' else ''
        arcpy.AddField_management(table_name, prefix + coord_dim + "_GIS", "DOUBLE")
        arcpy.CalculateField_management(table_name, prefix + coord_dim + "_GIS", "!SHAPE!.centroid." + coord_dim, "PYTHON_9.3")
        if table_name == 'Sewer_Mains':
            for end in ends:
                for coord_dim in coord_dims:
                    field_name = end[0] + "_" + coord_dim + "_GIS"
                    arcpy.AddField_management(table_name, field_name, "DOUBLE")
                    arcpy.CalculateField_management(table_name, field_name, "!SHAPE!." + end[1] + "Point." + coord_dim, "PYTHON_9.3")

arcpy.Delete_management("sewer_area_layer")

for l in layerList:

    #Delete table in processDB if it exists
    try:
        firstModel = arcpy.Delete_management(process_path+ "\\" + l)
    except Exception:
        pass

for l in layerList:

    firstModel = True
    for m in modelList:

        print "Importing " + l + " from " + m

        MUPath = working_folder + "\\" + m

        if firstModel == True:

            arcpy.MakeFeatureLayer_management(MUPath+ "\\" + l, "temp_layer", "active = 1")
            arcpy.FeatureClassToFeatureClass_conversion("temp_layer", process_path, l)
            arcpy.Delete_management("temp_layer")
            #Add column Model
            sql = "ALTER TABLE " + l + " ADD COLUMN Model_Area String;"
            executeQuery(sql, process_path)
            sql = "UPDATE " + l + " SET Model_Area = '" + m.split('_')[0] + "';"
            executeQuery(sql, process_path)

        else:
            #Append element
            feature_class_path = MUPath + "\\" + l
            arcpy.MakeFeatureLayer_management(MUPath+ "\\" + l, "temp_layer", "active = 1")
            arcpy.Append_management("temp_layer", l, "NO_TEST","","")
            arcpy.Delete_management("temp_layer")
            sql = "UPDATE " + l + " SET Model_Area = '" + m.split('_')[0] + "' WHERE Model_Area IS NULL;"
            executeQuery(sql, process_path)

        firstModel = False

    changeFieldType(l,'muid',"TEXT",process_path)

    for coord_dim in coord_dims:
        prefix = 'Mid_' if l == 'msm_Link' else ''
        arcpy.AddField_management(l, prefix + coord_dim + "_Model", "DOUBLE")
        arcpy.CalculateField_management(l, prefix + coord_dim + "_Model", "!SHAPE!.centroid." + coord_dim, "PYTHON_9.3")


#Make master ID table
sqls = []
#Mains
sqls.append("SELECT Sewer_Area, FacilityID INTO Mains_GIS_Model_Match FROM Sewer_Mains WHERE Sewer_Area IS NOT NULL GROUP BY Sewer_Area, FacilityID")
sqls.append("ALTER TABLE Mains_GIS_Model_Match ADD COLUMN MUID TEXT, Match_Code INTEGER")

sql = "SELECT FacilityID, muid, Sewer_Area, Model_Area, Mid_X_GIS, Mid_Y_GIS, Mid_X_Model, Mid_Y_Model, "
sql += "((Mid_X_GIS - Mid_X_Model)^2 + (Mid_Y_GIS - Mid_Y_Model)^2)^0.5 AS Distance, 0 AS Acceptable "
sql += "INTO Mains_Match FROM Sewer_Mains INNER JOIN msm_Link ON Sewer_Mains.FacilityID = msm_Link.muid"
sqls.append(sql)

sqls.append("UPDATE Mains_Match SET Acceptable = 1 WHERE Distance <= " + str(accepted_distance) + " AND Sewer_Area = Model_Area")
sqls.append("UPDATE Mains_GIS_Model_Match SET Match_Code = 99")
sqls.append("UPDATE Mains_GIS_Model_Match INNER JOIN Mains_Match ON Mains_GIS_Model_Match.FacilityID = Mains_Match.FacilityID SET Mains_GIS_Model_Match.MUID = Mains_Match.muid, Mains_GIS_Model_Match.Match_Code = 1")

sqls.append("ALTER TABLE Sewer_Mains ADD COLUMN From_Node_GIS TEXT, To_Node_GIS TEXT, From_Table_GIS TEXT, To_Table_GIS TEXT")

for gis_layer in gis_layers[1:]:
    table = gis_layer[:-4].replace(' ','_')
    for end in ends:
        sql = "UPDATE " + table + " INNER JOIN Sewer_Mains ON (" + table + ".Y_GIS = Sewer_Mains.Start_Y_GIS) AND (" + table + ".X_GIS = Sewer_Mains.Start_X_GIS) "
        sql += "SET Sewer_Mains." + end[2] + "_Node_GIS = " + table + ".FacilityID, " + end[2] + "_Table_GIS = '" + table + "'"
        sqls.append(sql)

executeQuery(sqls, process_path)









