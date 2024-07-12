#Tool date: July 5 2024

#Start of user input  --------------------------------------------------------------------------------------------------------------------------------

#For all runs except debugging, the following must be True
preprocessing = True
make_maps_mains = True
make_maps_manholes = True
make_review_csvs = True
make_mus = True

map_template_pipe = 'Template_Pipe_Review_Map.mxd'
map_template_node = 'Template_Manhole_Review_Map.mxd'
processDB = "Model_GIS_Processing.mdb"
map_subfolder = 'Review_Maps'
accepted_distance_pipe = 10
accepted_distance_node = 10

accepted_buffer_fraction = 0.99
buffer_size = 0.1 #On each side
expanded_extend_m = 100000

#Do not include Base, must be list of subscenarios, even if only 1
subscenario_dict = {}
subscenario_dict['FSA'] = ['2030_Network']

modelCommaSeparated = "FSA_Base_2021pop.sqlite,VSA_BASE_MODEL_2024.sqlite,NSSA_Base_2018pop.sqlite,Lisa_Base.sqlite"
LayerCommaSeparated = "msm_Node,msm_Link,msm_Orifice,msm_Pump,msm_Valve,msm_Weir"

gis_folder = r'G:\GISLayers\Sewer'
gis_layers = ['Sewer Mains.lyr','Sewer Manholes.lyr','Sewer Chambers.lyr','Sewer Structures.lyr','Sewer Connection.lyr','Sewer Air Vent.lyr','Sewer Fitting.lyr','Sewer Gates.lyr','Sewer Hatch.lyr','Sewer Valves.lyr','Sewer Pumps.lyr','Sewer Cathodic Protection.lyr','Sewer Flow Meters.lyr','Sewer Pump Stations.lyr','Sewer Rectifiers.lyr','Treatment Plants.lyr']
gis_extra = []
gis_layers += gis_extra

sewer_area_file = 'Sewer_Areas.shp'
sewer_area_field = 'Sewer_Area'



#End of user input  ----------------------------------------------------------------------------------------------------------------------------------

import pypyodbc #used to run Access queries
import arcpy
from arcpy import env
import pandas as pd
import datetime
from datetime import timedelta
import os
import shutil
import sqlite3
import ctypes
import re
MessageBox = ctypes.windll.user32.MessageBoxA

def sql_to_df(sql, full_path):
    print sql
    queryOutput = []
    conn = pypyodbc.win_connect_mdb(full_path)
    cur = conn.cursor()
    df = pd.read_sql(sql, conn)
    cur.close()
    conn.close()
    return df

def dataframe_to_mdb(df, mdb_path, table_name):
    # Connect to the .mdb file (create if it doesn't exist)
    conn = pypyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + mdb_path)
    cursor = conn.cursor()

    # Create a dictionary to map pandas dtypes to Access data types
    dtype_mapping = {
        'int64': 'INTEGER',
        'float64': 'DOUBLE',
        'object': 'TEXT'
    }

    # Generate the SQL for the CREATE TABLE statement
    columns = []
    col_types = []
    for col_name, dtype in df.dtypes.iteritems():
        col_type = dtype_mapping.get(str(dtype), 'TEXT')  # Default to TEXT if dtype is not in mapping
        columns.append("[{}] {}".format(col_name, col_type))
        col_types.append(col_type)
    create_table_sql = "CREATE TABLE {} ({})".format(table_name, ', '.join(columns))

    # Drop the table if it already exists
    try:
        cursor.execute("DROP TABLE {}".format(table_name))
        conn.commit()
    except pypyodbc.DatabaseError:
        pass  # Ignore error if table doesn't exist

    # Execute the CREATE TABLE statement
    cursor.execute(create_table_sql)
    conn.commit()

    # Insert data into the table
    for index,row in df.iterrows():
        vals = []
        for i, col in enumerate(df.columns):
            val = "'" + row[col] + "'" if type(row[col])==str else str(row[col])
            print(val)
            vals.append(val)
            values = ','.join(vals)
        print columns
        insert_sql = "INSERT INTO {} VALUES ({})".format(table_name, values)
        print insert_sql
        cursor.execute(insert_sql)

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()

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

def writeMusFile(layerName,elementList,musPath):
    os.remove(musPath) if os.path.exists(musPath) else None
    file = open(musPath, "w")
    file.write(layerName + "\n")
    for c in elementList:
        file.write(str(c) + "\n")
    file.close()

start_timer = datetime.datetime.now()
working_folder = os.getcwd()



match_code_dict = {}
match_code_dict[0] = 'Match by ID, acronym; and start or end location' #Auto accepted
match_code_dict[1] = 'Match by ID; and start and end location' #Auto accepted
match_code_dict[2] = 'Match by ID; and start or end location'
match_code_dict[3] = 'Match by ID and acronym'
match_code_dict[4] = 'Match by ID and buffer'#Auto accepted
match_code_dict[5] = 'Match by buffer'
match_code_dict[6] = 'Match by ID; and upstream and downstream node ID'
match_code_dict[7] = 'Match by ID and upstream node ID'
match_code_dict[8] = 'Match by ID and downstream node ID'
match_code_dict[9] = 'Match by ID only'
match_code_dict[10] = 'Match by ID, MH Name and location' #Auto accepted
match_code_dict[11] = 'Match by ID and location'
match_code_dict[12] = 'Match by ID and MH Name'
match_code_dict[14] = 'Match by manual assignment'
match_code_dict[15] = 'Manually approved'
match_code_dict[99] = 'No match'



modelList = [x.strip() for x in modelCommaSeparated.split(',')]

layerList = [x.strip() for x in LayerCommaSeparated.split(',')]

model_areas = [x.split('_')[0].upper() for x in modelCommaSeparated.split(',')]

coord_dims = ['X','Y']
ends = [['Start','first','From'],['End','last','To']]

if '.mdb' in modelCommaSeparated:
    message = "Tool ends. You cannot have extension mdb in modelCommaSeparated, only sqlite since only MIKE+ files are accepted.\n\n"
    MessageBox = ctypes.windll.user32.MessageBoxA
    MessageBox(None, message, 'Info', 0)
    exit()


process_path = working_folder + "\\" + processDB

if preprocessing:

    #Do review ##################################################################################################################
    #Find the latest review folder
    review_majors = ['Mains','Manholes']
    not_founds = []

    folders = []
    map_folder = working_folder + '\\' + map_subfolder
    for item in os.listdir(map_folder):
    	if os.path.isdir(os.path.join(map_folder, item)):
    		if re.match(r'^\d{8}_\d{4}$',item):
    			folders.append(item)
    if len(folders) > 0:

        review_folder = map_folder + '\\' + max(folders) #Max based on folder name which will be the one with the highest date
        previous_review_csv = review_folder + '\\Previous_Reviews_Accumulated.csv'
        if os.path.exists(previous_review_csv):
            review_df = pd.read_csv(previous_review_csv, dtype={'FacilityID':str,'MUID':str})
        else:
            messageText = "WARNING: Previous Review CSV not found. All previous reviews (MAJOR WORK) will be lost!\n\n" + previous_review_csv
            messageText += "\n\nContinue?"
            MessageBox = ctypes.windll.user32.MessageBoxA
            if MessageBox(None, messageText, 'Info', 4) == 7:
                MessageBox(None, "Please restore a previously backed up version to:\n\n" + previous_review_csv, 'Info', 0)
                exit()

        for review_major in review_majors:

            for model_area in model_areas:
                review_folder_model = review_folder + '\\' + model_area
                review_csv = review_folder_model + '\\' + model_area + '_Review_' + review_major + '.csv'

                print(review_csv)
                if os.path.exists(review_csv):
                    review_df_single = pd.read_csv(review_csv, dtype={'FacilityID':str,'MUID':str})
                    review_df_single['Major'] = review_major
                    review_df_single['Reviewed_Date'] = max(folders)
                    review_df_single['Facility_Key'] = review_df_single['Sewer_Area'] + '@' + review_df_single['FacilityID']
                    review_df['Strong_Key'] = review_df.Major + '@' + review_df.Facility_Key
                    review_df_single = review_df_single[review_df_single['Accepted'] != 0]
                    review_df = review_df_single.copy() if not 'review_df' in locals() else pd.concat([review_df,review_df_single])
                else:
                    not_founds.append(model_area + '_Review_' + review_major + '.csv')


        if len(not_founds) > 0:
            messageText = "The following review files were not found: \n\n"
            for f in not_founds:
                messageText += f + "\n"
            messageText += "\nContinue?"
            MessageBox = ctypes.windll.user32.MessageBoxA
            if MessageBox(None, messageText, 'Info', 4) == 7:
                MessageBox(None, "Please look inside the folders and ask around if the review was done.", 'Info', 0)
                exit()
    else:
        MessageBox = ctypes.windll.user32.MessageBoxA
        if MessageBox(None, "No past review folder was found under\n\n" + review_folder + '\n\nContinue?', 'Info', 4) == 7:
            MessageBox(None, "Please check the folder setup.", 'Info', 0)
            exit()


    #Create database ############################################################################################################################
    #Delete mdb if it exists and create a new
    os.remove(process_path) if os.path.exists(process_path) else None
    arcpy.CreatePersonalGDB_management(working_folder,processDB)
    arcpy.env.workspace = process_path

    if 'review_df' in locals():
        for review_major in review_majors:
            review_df_major = review_df[review_df.Major==review_major]
            table_name = 'Review_' + review_major
            dataframe_to_mdb(review_df_major, process_path, table_name)


    sqls = []
    sqls.append("CREATE TABLE Match_Codes (Match_Code INTEGER, Match_Code_Text TEXT)")

    for match_code in match_code_dict:
        sqls.append("INSERT INTO Match_Codes (Match_Code, Match_Code_Text) SELECT " + str(match_code) + ", '" + match_code_dict[match_code] + "'")
    executeQuery(sqls, process_path)

    #Import GIS
    sewer_area_path = working_folder + '\\' + sewer_area_file
    ##sewer_area_layer = arcpy.MakeFeatureLayer_management(sewer_area_path, "Sewer_Area_Layer")
    sewer_area_layer = arcpy.MakeFeatureLayer_management(sewer_area_path, "sewer_area_layer")
    sewer_area_names = [row[0] for row in arcpy.da.SearchCursor(sewer_area_layer, sewer_area_field)]

    for gis_layer in gis_layers:
        print "Importing " + gis_layer
        table_name = gis_layer[:-4].replace(' ','_')

    ##    arcpy.FeatureClassToFeatureClass_conversion (gis_folder + "\\" + gis_layer, process_path, table_name)

        try:
            arcpy.MakeFeatureLayer_management(gis_folder + "\\" + gis_layer, "temp_layer", "LifeCycleStatus <> 'Abandoned' AND LifeCycleStatus <> 'Removed'")

            arcpy.FeatureClassToFeatureClass_conversion("temp_layer", process_path, table_name)
            arcpy.Delete_management("temp_layer")
        except:
            print(gis_layer + ' could only be imported without lifecycle check.')
            try:
                arcpy.FeatureClassToFeatureClass_conversion(gis_layer, process_path, table_name)
            except:
                print(gis_layer + ' could not be imported.')

        try:
            arcpy.AddField_management(table_name, 'Sewer_Area', "String")

            arcpy.MakeFeatureLayer_management(table_name, "sewer_layer")
            try:
                changeFieldType(table_name,'FacilityID',"TEXT",process_path)
            except:
                print(gis_layer + ' has no FacilityID.')

            for sewer_area_name in sewer_area_names:
                arcpy.SelectLayerByAttribute_management(sewer_area_layer, "NEW_SELECTION", sewer_area_field + " = '" + sewer_area_name + "'")
                arcpy.SelectLayerByLocation_management("sewer_layer", "INTERSECT", sewer_area_layer)
                arcpy.CalculateField_management("sewer_layer", 'Sewer_Area', "'" + sewer_area_name + "'", "PYTHON_9.3")
                arcpy.SelectLayerByAttribute_management(sewer_area_layer, "CLEAR_SELECTION")
                arcpy.SelectLayerByAttribute_management("sewer_layer", "CLEAR_SELECTION")
            arcpy.Delete_management("sewer_layer")
        except:
            pass

        try:
            for coord_dim in coord_dims:
                if table_name == 'Sewer_Mains':
                    for end in ends:
                        field_name = end[0] + "_" + coord_dim + "_GIS"
                        arcpy.AddField_management(table_name, field_name, "DOUBLE")
                        arcpy.CalculateField_management(table_name, field_name, "!SHAPE!." + end[1] + "Point." + coord_dim, "PYTHON_9.3")
                else:
                    arcpy.AddField_management(table_name, coord_dim + "_GIS", "DOUBLE")
                    arcpy.CalculateField_management(table_name, coord_dim + "_GIS", "!SHAPE!.centroid." + coord_dim, "PYTHON_9.3")
        except:
            print('Could not add coordinates for ' + gis_layer)

    arcpy.Delete_management("sewer_area_layer")

    desc = arcpy.Describe("sewer_mains")
    extent = desc.extent

    expanded_extent = arcpy.Extent(extent.XMin - expanded_extend_m,
                    extent.YMin - expanded_extend_m,
                    extent.XMax + expanded_extend_m,
                    extent.YMax + expanded_extend_m)
    arcpy.env.XYDomain = expanded_extent

    for l in layerList:

        #Delete table in processDB if it exists
        try:
            firstModel = arcpy.Delete_management(process_path+ "\\" + l)
        except Exception:
            pass

    sql = "CREATE TABLE Duplicates_All (Model_Area TEXT, MUID TEXT, MUID_Key TEXT, Layer TEXT)"
    executeQuery(sql,process_path)

    for l in layerList:

        firstModel = True
        for m in modelList:

            model_area = m.split('_')[0].upper()

            print "Importing " + l + " from " + m

            MUPath = working_folder + "\\" + m

            if firstModel == True:

                arcpy.MakeFeatureLayer_management(MUPath+ "\\" + l, "temp_layer", "active = 1")
                arcpy.FeatureClassToFeatureClass_conversion("temp_layer", process_path, l)
                arcpy.Delete_management("temp_layer")
                #Add column Model
                sql = "ALTER TABLE " + l + " ADD COLUMN Model_Area STRING, MUID_Key STRING, Scenario STRING, Remove_Duplicate INTEGER;"
                executeQuery(sql, process_path)
                sql = "UPDATE " + l + " SET Scenario = 'Base', Model_Area = '" + model_area + "';"
                executeQuery(sql, process_path)
            else:
                #Append element
                feature_class_path = MUPath + "\\" + l
                arcpy.MakeFeatureLayer_management(MUPath+ "\\" + l, "temp_layer", "active = 1")
                arcpy.Append_management("temp_layer", l, "NO_TEST","","")
                arcpy.Delete_management("temp_layer")
                sql = "UPDATE " + l + " SET Scenario = 'Base', Model_Area = '" + model_area + "' WHERE Model_Area IS NULL;"
                executeQuery(sql, process_path)

            #Add sub scenarios
            if model_area in [model for model in subscenario_dict]:
                print model_area
                for subscenario in subscenario_dict[model_area]:
                    sql = "SELECT altid FROM m_ScenarioManagementAlternative WHERE muid = '" + subscenario + "' AND groupid = 'CS_Network'"
                    altid_record = readQuery(sql,MUPath)
                    if len(altid_record) == 0:
                        message = "Tool ends. Sub scenario " + subscenario + " not found in " + model_area + "\n\n"
                        MessageBox = ctypes.windll.user32.MessageBoxA
                        MessageBox(None, message, 'Info', 0)
                        exit()
                    else:
                        altid = altid_record[0][0]
                        #Append element
                        feature_class_path = MUPath + "\\" + l
                        arcpy.MakeFeatureLayer_management(MUPath+ "\\" + l, "temp_layer", "altid = " + str(altid))
                        arcpy.Append_management("temp_layer", l, "NO_TEST","","")
                        arcpy.Delete_management("temp_layer")
                        sql = "UPDATE " + l + " SET Scenario = '" + subscenario + "', Model_Area = '" + model_area + "' WHERE Model_Area IS NULL;"
                        executeQuery(sql, process_path)

            firstModel = False

        if l == 'msm_Link' or l == 'msm_Node':
            changeFieldType(l,'muid',"TEXT",process_path)
            changeFieldType(l,'acronym',"TEXT",process_path)
            changeFieldType(l,'assetname',"TEXT",process_path)
        if l == 'msm_Link':
            changeFieldType(l,'fromnodeid',"TEXT",process_path)
            changeFieldType(l,'tonodeid',"TEXT",process_path)

        for coord_dim in coord_dims:
            if l == 'msm_Link':
                for end in ends:
                    field_name = end[0] + "_" + coord_dim + "_Model"
                    arcpy.AddField_management(l, field_name, "DOUBLE")
                    arcpy.CalculateField_management(l, field_name, "!SHAPE!." + end[1] + "Point." + coord_dim, "PYTHON_9.3")
            else:
                arcpy.AddField_management(l, coord_dim + "_Model", "DOUBLE")
                arcpy.CalculateField_management(l, coord_dim + "_Model", "!SHAPE!.centroid." + coord_dim, "PYTHON_9.3")

        #remove sub scenario duplicates, only elements unique to this sub scenario will be kept. Also set MUID_Key.

        sql = "UPDATE " + l + " SET MUID_Key = Model_Area & '@' & MUID"
        executeQuery(sql,process_path)
        sqls = []
        sqls.append("SELECT Model_Area, muid, MUID_Key, '" + l + "' AS Layer INTO Duplicates FROM " + l + " GROUP BY Model_Area, muid, MUID_Key HAVING Count(muid)>1")
        sqls.append("UPDATE " + l + " SET Remove_Duplicate = 0")
        sqls.append("UPDATE " + l + " INNER JOIN Duplicates ON (" + l + ".MUID_Key = Duplicates.MUID_Key) SET " + l + ".Remove_Duplicate = 1 WHERE " + l + ".Scenario <> 'Base'")
        sqls.append("INSERT INTO Duplicates_All SELECT * FROM Duplicates")
        sqls.append("DROP TABLE Duplicates")

        executeQuery(sqls,process_path)

        sql = "SELECT COUNT(muid) FROM " + l + " WHERE Remove_Duplicate = 1"
        remove_count = readQuery(sql,process_path)[0][0]
        if remove_count > 1:
            arcpy.MakeFeatureLayer_management(l, "temp_layer", "Remove_Duplicate=1")
            arcpy.DeleteFeatures_management("temp_layer")
            arcpy.Delete_management("temp_layer")


    #Make master ID table

    #Mains
##    sqls.append("SELECT Sewer_Area, FacilityID, Acronym INTO Mains_GIS_Model_Match FROM Sewer_Mains WHERE Sewer_Area IS NOT NULL GROUP BY Sewer_Area, FacilityID, Acronym")
##    sql = "ALTER TABLE Mains_GIS_Model_Match ADD COLUMN MUID TEXT, Match_Code INTEGER, "
##    sql += "ID_Match INTEGER, Acronym_Match INTEGER, Accept_Distance INTEGER, Upstream_ID_Match INTEGER, Downstream_ID_Match INTEGER, Buffer_Match INTEGER, Map_Match INTEGER, Reviewed INTEGER, Pending_Review INTEGER"
##    sqls.append(sql)
    sql = "ALTER TABLE Sewer_Mains ADD COLUMN Facility_KEY TEXT, GIS_Pipe_Length DOUBLE, From_Node_GIS TEXT, To_Node_GIS TEXT, From_Table_GIS TEXT, To_Table_GIS TEXT"
    executeQuery(sql,process_path)

    sql = "UPDATE Sewer_Mains SET Facility_KEY = Sewer_Area & '@' & FacilityID"
    executeQuery(sql,process_path)

    sql = "SELECT FacilityID, muid, Facility_KEY, MUID_Key, Sewer_Area, Model_Area, Sewer_Mains.Acronym AS Acronym, msm_Link.Acronym AS Acronym_Model, Start_X_GIS, Start_Y_GIS, End_X_GIS, End_Y_GIS, Start_X_Model, Start_Y_Model, End_X_Model, End_Y_Model, "
    sql += "((Start_X_GIS - Start_X_Model)^2 + (Start_Y_GIS - Start_Y_Model)^2)^0.5 AS Start_Distance, ((End_X_GIS - End_X_Model)^2 + (End_Y_GIS - End_Y_Model)^2)^0.5 AS End_Distance, "
    sql += "0 AS Accept_Dist, 0 AS Accept_Both_Dist, 1 AS ID_Match, 0 AS Acronym_Match, 0 AS Upstream_ID_Match, 0 AS Downstream_ID_Match, 0 AS Buffer_Match, 0 AS Map_Match, 0 AS Reviewed, "
    sql += "0 AS Pending_Review, 0 AS Approved_For_GIS, 99 AS Match_Code, 99 AS Match_Code_Unreviewed "
    sql += "INTO Mains_GIS_Model_Match FROM Sewer_Mains LEFT JOIN msm_Link ON Sewer_Mains.Facility_Key = msm_Link.MUID_Key "
    sql += "WHERE Sewer_Mains.Sewer_Area IS NOT NULL AND Sewer_Mains.FacilityID IS NOT NULL"
    executeQuery(sql,process_path)

    sqls = []

    #Matchcode 1: Match by ID, acronym and one end point
    #Matchcode 1: Match by ID and both end points
    #Matchcode 2: Match by ID and one end point
    #Matchcode 3: Match by ID and acronym

    sqls.append("UPDATE Mains_GIS_Model_Match SET Accept_Dist = 1 WHERE (Start_Distance <= " + str(accepted_distance_pipe) + " OR End_Distance <= " + str(accepted_distance_pipe) + ") AND Sewer_Area = Model_Area")
    sqls.append("UPDATE Mains_GIS_Model_Match SET Accept_Both_Dist = 1 WHERE (Start_Distance <= " + str(accepted_distance_pipe) + " AND End_Distance <= " + str(accepted_distance_pipe) + ") AND Sewer_Area = Model_Area")
    sqls.append("UPDATE Mains_GIS_Model_Match SET Acronym_Match = 1 WHERE Acronym = Acronym_Model AND Sewer_Area = Model_Area")
    sqls.append("UPDATE Mains_GIS_Model_Match SET Match_Code = IIF(Acronym_Match = 1 AND Accept_Dist = 1, 0, IIF(Accept_Both_Dist = 1, 1, IIF(Accept_Dist = 1, 2, IIF(Acronym_Match = 1, 3, 99))))")


    sqls.append("UPDATE Sewer_Mains SET GIS_Pipe_Length = SHAPE_Length")

    for gis_layer in gis_layers[1:]:
        table = gis_layer[:-4].replace(' ','_')
        for end in ends:
            sql = "UPDATE " + table + " INNER JOIN Sewer_Mains ON (" + table + ".Y_GIS = Sewer_Mains." + end[0] + "_Y_GIS) AND (" + table + ".X_GIS = Sewer_Mains." + end[0] + "_X_GIS) "
            sql += "SET Sewer_Mains." + end[2] + "_Node_GIS = " + table + ".FacilityID, " + end[2] + "_Table_GIS = '" + table + "' WHERE " + end[2] + "_Table_GIS IS NULL"
            sqls.append(sql)

    executeQuery(sqls, process_path)

    #Create buffer around modelpipes
    arcpy.Buffer_analysis("msm_Link", "msm_Link_Buffer", str(buffer_size))
    arcpy.Intersect_analysis (['Sewer_Mains','msm_Link_Buffer'], "Sewer_Main_Buffer_Intersect ")

    #Matchcode 4: Match by ID and buffer
    #Matchcode 5: Match by buffer

    sqls = []
    sqls.append("ALTER TABLE Sewer_Main_Buffer_Intersect ADD COLUMN Int_Fraction DOUBLE")
    sqls.append("UPDATE Sewer_Main_Buffer_Intersect SET Int_Fraction = SHAPE_Length / GIS_Pipe_Length")

    sql = "UPDATE Mains_GIS_Model_Match INNER JOIN Sewer_Main_Buffer_Intersect ON Mains_GIS_Model_Match.Facility_Key = Sewer_Main_Buffer_Intersect.Facility_Key "
    sql += "SET Mains_GIS_Model_Match.Match_Code = 5, Mains_GIS_Model_Match.MUID_Key = Sewer_Main_Buffer_Intersect.MUID_Key, Mains_GIS_Model_Match.MUID = Sewer_Main_Buffer_Intersect.muid, Mains_GIS_Model_Match.Buffer_Match = 1 "
    sql += "WHERE Mains_GIS_Model_Match.Match_Code = 99 AND Sewer_Main_Buffer_Intersect.Int_Fraction >= " + str(accepted_buffer_fraction)
    sqls.append(sql)
    sqls.append("UPDATE Mains_GIS_Model_Match SET Match_Code = 4 WHERE Match_Code = 5 AND FacilityID = MUID")

    #Matchcode 6: Match by ID; and upstream and downstream node ID
    sqls.append("SELECT Sewer_Mains.Sewer_Area, Sewer_Mains.FacilityID, Sewer_Mains.Facility_Key, msm_Link.muid, msm_Link.MUID_Key, From_Node_GIS, To_Node_GIS, fromnodeid AS From_Node_Model, \
        tonodeid AS To_Node_Model INTO Upstream_Downstream_Match FROM Sewer_Mains INNER JOIN msm_Link ON \
        (Sewer_Mains.To_Node_GIS = msm_Link.tonodeid) AND (Sewer_Mains.From_Node_GIS = msm_Link.fromnodeid) AND (Sewer_Mains.Facility_Key = msm_Link.MUID_Key)")
##    sqls.append("UPDATE Upstream_Downstream_Match SET ID_Match = 1 WHERE FacilityID = MUID")
    sql = "UPDATE Mains_GIS_Model_Match INNER JOIN Upstream_Downstream_Match ON Mains_GIS_Model_Match.Facility_Key = Upstream_Downstream_Match.Facility_Key "
    sql += "SET Mains_GIS_Model_Match.MUID = Upstream_Downstream_Match.muid, Mains_GIS_Model_Match.MUID_Key = Upstream_Downstream_Match.MUID_Key, Mains_GIS_Model_Match.Match_Code = 6, Upstream_ID_Match = 1, Downstream_ID_Match = 1 WHERE Mains_GIS_Model_Match.Match_Code=99"
    sqls.append(sql)

    #Matchcode 7: Match by ID and upstream node ID
    sqls.append("SELECT Sewer_Mains.FacilityID, Sewer_Mains.Facility_Key, msm_Link.muid, msm_Link.MUID_Key, From_Node_GIS, To_Node_GIS, fromnodeid AS From_Node_Model, tonodeid AS To_Node_Model INTO Upstream_Match \
        FROM Sewer_Mains INNER JOIN msm_Link ON (Sewer_Mains.Facility_Key = msm_Link.MUID_Key) AND (Sewer_Mains.From_Node_GIS = msm_Link.fromnodeid)")
    sql = "UPDATE Mains_GIS_Model_Match INNER JOIN Upstream_Match ON Mains_GIS_Model_Match.Facility_Key = Upstream_Match.Facility_Key "
    sql += "SET Mains_GIS_Model_Match.MUID = Upstream_Match.muid, Mains_GIS_Model_Match.MUID_Key = Upstream_Match.MUID_Key, Mains_GIS_Model_Match.Match_Code = 7, Upstream_ID_Match = 1 WHERE Mains_GIS_Model_Match.Match_Code=99"
    sqls.append(sql)

    #Matchcode 8: Match by ID and downstream node ID
    sqls.append("SELECT Sewer_Mains.FacilityID, Sewer_Mains.Facility_Key, msm_Link.muid, msm_Link.MUID_Key, From_Node_GIS, To_Node_GIS, fromnodeid AS From_Node_Model, tonodeid AS To_Node_Model  INTO Downstream_Match \
        FROM Sewer_Mains INNER JOIN msm_Link ON (Sewer_Mains.Facility_Key = msm_Link.MUID_Key) AND (Sewer_Mains.To_Node_GIS = msm_Link.tonodeid)")
    sql = "UPDATE Mains_GIS_Model_Match INNER JOIN Downstream_Match ON Mains_GIS_Model_Match.Facility_Key = Downstream_Match.Facility_Key "
    sql += "SET Mains_GIS_Model_Match.MUID = Downstream_Match.muid, Mains_GIS_Model_Match.MUID_Key = Downstream_Match.MUID_Key, Mains_GIS_Model_Match.Match_Code = 8, Downstream_ID_Match = 1 WHERE Mains_GIS_Model_Match.Match_Code=99"
    sqls.append(sql)

    #Matchcode 9: Match by ID only
    sqls.append("UPDATE Mains_GIS_Model_Match SET Match_Code = 9 WHERE FacilityID = MUID AND Match_Code = 99")

    sqls.append("UPDATE Mains_GIS_Model_Match SET ID_Match = 1 WHERE FacilityID = MUID")


    sqls.append("UPDATE Mains_GIS_Model_Match SET Reviewed = 0")

    #Matchcode 14: Match by manual assignment
    df = pd.read_csv(working_folder + '\\Mains_Manual_Assignment.csv', dtype={'FacilityID':str,'MUID':str})
    for index, row in df.iterrows():
        sqls.append("UPDATE Mains_GIS_Model_Match SET MUID = '" + row['MUID'] + "', MUID_Key = Sewer_Area & '@" + row['MUID'] + "', Match_Code = 14 WHERE Sewer_area = '" + row['Sewer_Area'] + "' AND FacilityID = '" + row['FacilityID'] + "'")

    #Copy Match_Code field to store match keys prior to giving code 15 (reviewed) because this value is later used to compare before/after match codes.
    sqls.append("UPDATE Mains_GIS_Model_Match SET Match_Code_Unreviewed = Match_Code")

    #Matchcode 15: Match by manual review
    if 'review_df' in locals():
        sqls.append("UPDATE Mains_GIS_Model_Match INNER JOIN Review_Mains ON Review_Mains.Facility_Key = Mains_GIS_Model_Match.Facility_Key SET \
            Mains_GIS_Model_Match.MUID = Review_Mains.MUID, Mains_GIS_Model_Match.MUID_Key = Mains_GIS_Model_Match.Sewer_Area & '@' & Review_Mains.MUID, Mains_GIS_Model_Match.Match_Code = 15 \
            WHERE Mains_GIS_Model_Match.Match_Code = Review_Mains.Match_Code")


    sqls.append("ALTER TABLE Sewer_Mains ADD COLUMN Match_Code INTEGER, MUID TEXT, Map_Display TEXT, Map_Name TEXT, Approved_For_GIS INTEGER, Pending_Review INTEGER")

    executeQuery(sqls, process_path)

    sqls = []

    #Register approval for GIS

    sql = "UPDATE Mains_GIS_Model_Match SET Approved_For_GIS = 1 WHERE Match_Code = 0 OR Match_Code = 1 OR Match_Code = 4 OR Match_Code = 14 OR Match_Code = 15"
    sqls.append(sql)

    #Register for upcoming manual approval
    sql = "UPDATE Mains_GIS_Model_Match SET Pending_Review = 1 WHERE Match_Code = 2 OR Match_Code = 3 OR Match_Code = 6 OR Match_Code = 5 OR Match_Code = 7 OR Match_Code = 8 OR Match_Code = 9"
    sqls.append(sql)


    sql = "UPDATE Sewer_Mains INNER JOIN Mains_GIS_Model_Match ON Sewer_Mains.Facility_Key = Mains_GIS_Model_Match.Facility_Key SET Sewer_Mains.Match_Code = Mains_GIS_Model_Match.Match_Code, "
    sql += "Sewer_Mains.MUID = Mains_GIS_Model_Match.MUID, Sewer_Mains.Pending_Review = Mains_GIS_Model_Match.Pending_Review, Sewer_Mains.Approved_For_GIS = Mains_GIS_Model_Match.Approved_For_GIS"

    sqls.append(sql)

    sqls.append("SELECT Match_Code, Count(FacilityID) AS Match_Code_Count INTO Mains_GIS_Model_Match_Count FROM Mains_GIS_Model_Match GROUP BY Mains_GIS_Model_Match.Match_Code")

    sqls.append("ALTER TABLE msm_Link ADD COLUMN FacilityID TEXT, Facility_Key TEXT, Match_Code INTEGER")


    sql = "UPDATE Sewer_Mains INNER JOIN Match_Codes ON Sewer_Mains.Match_Code = Match_Codes.Match_Code "
    sql += "SET Sewer_Mains.Map_Display = 'GIS Facility ID ' & Sewer_Mains.FacilityID & ', Model MUID ' & Sewer_Mains.MUID & ' ' & IIF(Sewer_Mains.MUID=Sewer_Mains.FacilityID,'(Same)','(Different)') & '\nMatch Code ' & Sewer_Mains.Match_Code & ': ' & Match_Codes.Match_Code_Text"

    sqls.append(sql)
    sqls.append("UPDATE Sewer_Mains SET Map_Name = Sewer_Area & '_Mains_GIS_Model_Matchcode_' & Match_Code & '_FacilityID_' & FacilityID WHERE Pending_Review = 1")
    executeQuery(sqls, process_path)

    arcpy.Buffer_analysis("Sewer_Mains", "Sewer_Mains_Page_Buffer", str(1))


    sqls = []

    sqls.append("SELECT Sewer_Area, FacilityID, Acronym, MUID, Match_Code, Approved_For_GIS INTO Mains_GIS_Model_Match_Final FROM Mains_GIS_Model_Match")
    sqls.append("UPDATE Mains_GIS_Model_Match_Final SET MUID = '' WHERE Approved_For_GIS = 0")

    executeQuery(sqls, process_path)

    sql = "SELECT * FROM Mains_GIS_Model_Match_Final"
    df = sql_to_df(sql, process_path)
    df.to_csv(working_folder + '\\Mains_GIS_Model_Match.csv', index=False)

    #Nodes *******************************************************************************************************************************************************************************************************************
    sqls = []
    sqls.append("ALTER TABLE Sewer_Manholes ADD COLUMN Facility_KEY TEXT, Match_Code INTEGER, MUID TEXT, Map_Display TEXT, Map_Name TEXT, Pending_Review INTEGER")
    sqls.append("UPDATE Sewer_Manholes SET Facility_KEY = Sewer_Area & '@' & FacilityID")
    executeQuery(sqls,process_path)

    sqls = []
##    sqls.append("SELECT Sewer_Area, FacilityID, Acronym, MHName INTO Manholes_GIS_Model_Match FROM Sewer_Manholes WHERE Sewer_Area IS NOT NULL AND FacilityID IS NOT Null GROUP BY Sewer_Area, FacilityID, Acronym, MHName")

##    #Initialize Manholes_GIS_Model_Match table
##    sqls.append("ALTER TABLE Manholes_GIS_Model_Match ADD COLUMN MUID TEXT, Match_Code INTEGER, Map_Match INTEGER, Approved_For_GIS INTEGER, Reviewed INTEGER, New_Review INTEGER")
##    sqls.append("UPDATE Manholes_GIS_Model_Match SET Match_Code = 99")

    #Initialize Manholes_GIS_Model_Match table
    sql = "SELECT Sewer_Manholes.Sewer_Area, msm_Node.Model_Area, Sewer_Manholes.FacilityID, msm_Node.muid, Sewer_Manholes.Facility_Key, msm_Node.MUID_Key, Sewer_Manholes.MHName, msm_Node.assetname, "
    sql += "Sewer_Manholes.Acronym AS Acronym, msm_Node.acronym AS Model_Acronym, Sewer_Manholes.X_GIS, Sewer_Manholes.Y_GIS, msm_Node.X_Model, msm_Node.Y_Model, "
    sql += "((X_GIS - X_Model)^2 + (Y_GIS - Y_Model)^2)^0.5 AS Distance, 99 AS Match_Code, 99 AS Match_Code_Unreviewed, 0 AS ID_Match, 0 AS Accept_Dist, 0 AS Acronym_Match, 0 AS MHName_Match, "
    sql += "0 AS Map_Match, 0 AS Approved_For_GIS, 0 AS Reviewed, 0 AS Pending_Review "
    sql += "INTO Manholes_GIS_Model_Match FROM Sewer_Manholes INNER JOIN msm_Node ON Sewer_Manholes.FacilityID = msm_Node.muid "
    sql += "WHERE Sewer_Manholes.Sewer_Area Is Not Null AND msm_Node.Model_Area=Sewer_Manholes.Sewer_Area"
    sqls.append(sql)

    #Register initial matches
    executeQuery(sqls, process_path)

    sqls = []
    sqls.append("UPDATE Manholes_GIS_Model_Match SET ID_Match = 1 WHERE muid = FacilityID")
    sqls.append("UPDATE Manholes_GIS_Model_Match SET Acronym_Match = 1 WHERE Model_Acronym = Acronym")
    sqls.append("UPDATE Manholes_GIS_Model_Match SET MHName_Match = 1 WHERE assetname = MHName")
    sqls.append("UPDATE Manholes_GIS_Model_Match SET Accept_Dist = 1 WHERE Distance <= " + str(accepted_distance_node))

    sql = "UPDATE Manholes_GIS_Model_Match SET Match_Code = 10 WHERE MHName_Match = 1 AND Accept_Dist = 1"
    sqls.append(sql)

    sql = "UPDATE Manholes_GIS_Model_Match SET Match_Code = 11 WHERE MHName_Match = 0 AND Accept_Dist = 1"
    sqls.append(sql)

    sql = "UPDATE Manholes_GIS_Model_Match SET Match_Code = 12 WHERE MHName_Match = 1 AND Accept_Dist = 0"
    sqls.append(sql)

    #Matchcode 9: Match by ID only
    sqls.append("UPDATE Manholes_GIS_Model_Match SET Match_Code = 9 WHERE FacilityID = MUID AND Match_Code = 99")

    #Match code 14: Read manual assignment
    df = pd.read_csv(working_folder + '\\Manholes_Manual_Assignment.csv', dtype={'FacilityID':str,'MUID':str})
    for index, row in df.iterrows():
        sqls.append("UPDATE Manholes_GIS_Model_Match SET MUID = '" + row['MUID'] + "', MUID_Key = Sewer_Area & '@" + row['MUID'] + "', Match_Code = 14 WHERE Sewer_area = '" + row['Sewer_Area'] + "' AND FacilityID = '" + row['FacilityID'] + "'")

    #Copy Match_Code field to store match keys prior to giving code 15 (reviewed) because this value is later used to compare before/after match codes.
    sqls.append("UPDATE Manholes_GIS_Model_Match SET Match_Code_Unreviewed = Match_Code")

    #Matchcode 15: Match by manual review
    if 'review_df' in locals():
        sqls.append("UPDATE Manholes_GIS_Model_Match INNER JOIN Review_Manholes ON Review_Manholes.Facility_Key = Manholes_GIS_Model_Match.Facility_Key SET \
            Manholes_GIS_Model_Match.MUID = Review_Manholes.MUID, Manholes_GIS_Model_Match.MUID_Key = Manholes_GIS_Model_Match.Sewer_Area & '@' & Review_Manholes.MUID, Manholes_GIS_Model_Match.Match_Code = 15 \
            WHERE Manholes_GIS_Model_Match.Match_Code = Review_Manholes.Match_Code")

    #Register approval for GIS
    sql = "UPDATE Manholes_GIS_Model_Match SET Approved_For_GIS = 1 WHERE Match_Code = 10 OR Match_Code = 14 OR Match_Code = 15"
    sqls.append(sql)

    #Register for upcoming manual approval
    sql = "UPDATE Manholes_GIS_Model_Match SET Pending_Review = 1 WHERE Match_Code = 9 OR Match_Code = 11 OR Match_Code = 12 OR Match_Code = 13"
    sqls.append(sql)

    #Transfer the MUID and match code from Manholes_GIS_Model_Match to Sewer_Manholes so they can be mapped.

    sqls.append("UPDATE Sewer_Manholes INNER JOIN Manholes_GIS_Model_Match ON Sewer_Manholes.FacilityID = Manholes_GIS_Model_Match.FacilityID SET \
        Sewer_Manholes.Match_Code = Manholes_GIS_Model_Match.Match_Code, Sewer_Manholes.MUID = Manholes_GIS_Model_Match.MUID, Sewer_Manholes.Pending_Review = Manholes_GIS_Model_Match.Pending_Review")

    #Create the map text.
    sql = "UPDATE Sewer_Manholes INNER JOIN Match_Codes ON Sewer_Manholes.Match_Code = Match_Codes.Match_Code "
    sql += "SET Sewer_Manholes.Map_Display = 'GIS Facility ID ' & Sewer_Manholes.FacilityID & ', Model MUID ' & Sewer_Manholes.MUID & ' ' & "
    sql += "IIF(Sewer_Manholes.MUID=Sewer_Manholes.FacilityID,'(Same)','(Different)') & '\nMatch Code ' & Sewer_Manholes.Match_Code & ': ' & Match_Codes.Match_Code_Text"
    sqls.append(sql)
    sqls.append("UPDATE Sewer_Manholes SET Map_Name = Sewer_Area & '_Manholes_Matchcode_' & Match_Code & '_FacilityID_' & FacilityID WHERE Pending_Review = 1")

    sqls.append("UPDATE Manholes_GIS_Model_Match SET Reviewed = 0")

    sqls.append("SELECT Sewer_Area, FacilityID, Acronym, MHName, MUID, Match_Code, Approved_For_GIS INTO Manholes_GIS_Model_Match_Final FROM Manholes_GIS_Model_Match")
    sqls.append("UPDATE Manholes_GIS_Model_Match_Final SET MUID = '' WHERE Approved_For_GIS = 0")

    executeQuery(sqls, process_path)

    sql = "SELECT * FROM Manholes_GIS_Model_Match_Final"
    df = sql_to_df(sql, process_path)
    df.to_csv(working_folder + '\\Manhole_GIS_Model_Match.csv', index=False)


    ##################################################################################################################################################################################


    #Create copy of msm_Link
    sqls = []
    sqls.append("UPDATE Mains_GIS_Model_Match SET Map_Match = 0")
    sqls.append("UPDATE msm_Link INNER JOIN Mains_GIS_Model_Match ON msm_Link.MUID_Key = Mains_GIS_Model_Match.MUID_Key SET msm_Link.FacilityID = Mains_GIS_Model_Match.FacilityID, msm_Link.Match_Code = Mains_GIS_Model_Match.Match_Code")
    sqls.append("UPDATE msm_Link INNER JOIN Mains_GIS_Model_Match ON msm_Link.FacilityID = Mains_GIS_Model_Match.FacilityID SET Map_Match = 1 WHERE msm_Link.FacilityID IS NOT NULL")
    executeQuery(sqls, process_path)

    arcpy.FeatureClassToFeatureClass_conversion('msm_Link', process_path, 'msm_Link_Map')

    #Create layer with model pipes matched to GIS, duplicated where matched with more than one.
    iter_count = 0
    remaining_count = 999
    while iter_count < 1000 and remaining_count > 0:
        sql = "SELECT COUNT(FacilityID) FROM Mains_GIS_Model_Match WHERE Map_Match = 0 and Match_Code <> 99"
        remaining_count = readQuery(sql,process_path)[0][0]
        iter_count += 1 #To escape endless loop while debugging
        if remaining_count > 0:
            print str(remaining_count) + " records added to msm_Link.map"
            sqls = []
            sqls.append("UPDATE msm_Link SET FacilityID = '', Facility_Key = '', Match_Code = 0")
            sqls.append("UPDATE msm_Link INNER JOIN Mains_GIS_Model_Match ON msm_Link.MUID_Key = Mains_GIS_Model_Match.MUID_Key SET msm_Link.FacilityID = Mains_GIS_Model_Match.FacilityID, \
                msm_Link.Facility_Key = Mains_GIS_Model_Match.Facility_Key, msm_Link.Match_Code = Mains_GIS_Model_Match.Match_Code WHERE Mains_GIS_Model_Match.Map_Match = 0 and Mains_GIS_Model_Match.Match_Code <> 99")
            sqls.append("UPDATE msm_Link INNER JOIN Mains_GIS_Model_Match ON msm_Link.Facility_Key = Mains_GIS_Model_Match.Facility_Key SET Map_Match = 1 WHERE msm_Link.FacilityID IS NOT NULL")
            executeQuery(sqls, process_path)

            arcpy.MakeFeatureLayer_management('msm_Link', "temp_layer", "Match_Code IS NOT NULL")
            arcpy.Append_management(inputs='temp_layer', target='msm_Link_Map', schema_type="NO_TEST", field_mapping="", subtype="")
            arcpy.Delete_management("temp_layer")

    sqls = []
    sqls.append("UPDATE Manholes_GIS_Model_Match SET Map_Match = 0")
    sqls.append("ALTER TABLE msm_Node ADD COLUMN FacilityID TEXT, Facility_Key TEXT, Match_Code INTEGER")
    sqls.append("UPDATE msm_Node INNER JOIN Manholes_GIS_Model_Match ON msm_Node.MUID_Key = Manholes_GIS_Model_Match.MUID_Key SET msm_Node.FacilityID = Manholes_GIS_Model_Match.FacilityID, \
        msm_Node.Facility_Key = Manholes_GIS_Model_Match.Facility_Key, msm_Node.Match_Code = Manholes_GIS_Model_Match.Match_Code")
    sqls.append("UPDATE msm_Node INNER JOIN Manholes_GIS_Model_Match ON msm_Node.Facility_Key = Manholes_GIS_Model_Match.Facility_Key SET Map_Match = 1 WHERE msm_Node.FacilityID IS NOT NULL")
    executeQuery(sqls, process_path)


    arcpy.FeatureClassToFeatureClass_conversion('msm_Node', process_path, 'msm_Node_Map')
    while iter_count < 1000 and remaining_count > 0:
        sql = "SELECT COUNT(FacilityID) FROM Manholes_GIS_Model_Match WHERE Map_Match = 0 and Match_Code <> 99"
        remaining_count = readQuery(sql,process_path)[0][0]
        iter_count += 1 #To escape endless loop while debugging
        if remaining_count > 0:
            print str(remaining_count) + " records added to msm_Node.map"
            sqls = []
            sqls.append("UPDATE msm_Node SET FacilityID = '', FacilityKey = '',  Match_Code = 0")
            sqls.append("UPDATE msm_Node INNER JOIN Manholes_GIS_Model_Match ON msm_Node.MUID_Key = Manholes_GIS_Model_Match.MUID_Key SET msm_Node.FacilityID = Manholes_GIS_Model_Match.FacilityID, \
                msm_Node.Facility_Key = Manholes_GIS_Model_Match.Facility_Key, msm_Node.Match_Code = Manholes_GIS_Model_Match.Match_Code WHERE Manholes_GIS_Model_Match.Map_Match = 0 and Manholes_GIS_Model_Match.Match_Code <> 99")
            sqls.append("UPDATE msm_Node INNER JOIN Manholes_GIS_Model_Match ON msm_Node.Facility_Key = Manholes_GIS_Model_Match.Facility_Key SET Map_Match = 1 WHERE msm_Node.FacilityID IS NOT NULL")
            executeQuery(sqls, process_path)

            arcpy.MakeFeatureLayer_management('msm_Node', "temp_layer", "Match_Code IS NOT NULL")
            arcpy.Append_management(inputs='temp_layer', target='msm_Node_Map', schema_type="NO_TEST", field_mapping="", subtype="")
            arcpy.Delete_management("temp_layer")

if make_maps_manholes or make_maps_mains or make_review_csvs or make_mus:
    #Mains Maps
    dated_subfolder = str(datetime.datetime.now())[:16].replace('-','').replace(':','').replace(' ','_')
    map_folder = working_folder + '\\' + map_subfolder + '\\' + dated_subfolder
    if not os.path.isdir(map_folder): os.makedirs(map_folder)

    #Make backups of key files
    shutil.copy(working_folder  + '\\' + map_template_pipe,map_folder  + '\\' + map_template_pipe)
    shutil.copy(working_folder  + '\\' + map_template_node,map_folder  + '\\' + map_template_node)
    shutil.copy(working_folder  + '\\' + processDB,map_folder  + '\\' + processDB)
    shutil.copy(working_folder  + '\\Mains_Manual_Assignment.csv',map_folder  + '\\Mains_Manual_Assignment.csv')
    shutil.copy(working_folder  + '\\Manholes_Manual_Assignment.csv',map_folder  + '\\Manholes_Manual_Assignment.csv')
    shutil.copy(working_folder  + '\\Mains_GIS_Model_Match.csv',map_folder  + '\\Mains_GIS_Model_Match.csv')
    shutil.copy(working_folder  + '\\Manhole_GIS_Model_Match.csv',map_folder  + '\\Manhole_GIS_Model_Match.csv')

    sql = "SELECT Sewer_Area FROM Sewer_Mains GROUP BY Sewer_Area HAVING Sewer_Area <> ''"
    sewer_areas = readQuery(sql,process_path)
    for sewer_area in sewer_areas:
        sewer_area = sewer_area[0]
        map_subfolder = map_folder + '\\' + sewer_area
        if not os.path.isdir(map_subfolder): os.makedirs(map_subfolder)

    #Create mus files
    if make_mus:
        for m in modelList:

            model_area = m.split('_')[0].upper()

            mus_folder = map_folder + '\\' + model_area + '\\MUS_Selection_Files'
            if not os.path.isdir(mus_folder): os.makedirs(mus_folder)
            for major in review_majors:
                muid_ticked = []
                sql = "SELECT Match_Code FROM " + major + "_GIS_Model_Match WHERE Sewer_Area = '" + model_area + "' GROUP BY Match_Code"
                df = sql_to_df(sql, process_path)
                match_codes = list(df.match_code.unique())
                for match_code in match_codes:
                    sql = "SELECT muid FROM " + major + "_GIS_Model_Match WHERE Match_Code = " + str(match_code) + " AND Sewer_Area = '" + model_area + "'"
                    df = sql_to_df(sql, process_path)
                    muids = list(df.muid.unique())
                    muid_ticked +=muids
                    layer_name = 'msm_Link' if major == 'Mains' else 'msm_Node'
                    writeMusFile(layer_name,muids,mus_folder + '\\' + model_area + "_" + major + "_Match_Code_" + str(match_code) + ".mus")
                muid_ticked = set(muid_ticked)
                sql = "SELECT MUID from " + layer_name + " WHERE Model_Area = '" + model_area + "' GROUP BY MUID"
                df = sql_to_df(sql, process_path)
                muid_unticked = set(df.muid.unique())
                for muid in muid_ticked:
                    muid_unticked.discard(muid)
                writeMusFile(layer_name,muid_unticked,mus_folder + '\\' + model_area + "_" + major + "_Remaining_Unmatched.mus")
                muid_ticked = set(muid_ticked)


    if 'review_df' in locals():

        for major in review_majors:
            skip_keys = []
            sql = "SELECT '" + major + "@' & " + major + "_GIS_Model_Match.Facility_Key AS Strong_Key, " + major + "_GIS_Model_Match.Facility_Key, Review_" + major + ".Match_Code AS Reviewed_Match_Code, " + major + "_GIS_Model_Match.Match_Code_Unreviewed AS New_Match_Code "
            sql += "FROM " + major + "_GIS_Model_Match INNER JOIN Review_" + major + " ON Review_" + major + ".Facility_Key = " + major + "_GIS_Model_Match.Facility_Key  "
            sql += "WHERE " + major + "_GIS_Model_Match.Match_Code_Unreviewed <> Review_" + major + ".Match_Code"
            for row in readQuery(sql,process_path):
                skip_key = str(row[0])
                skip_keys.append(skip_key)
                review_df = review_df[review_df.Strong_Key!=skip_key]
            skip_df = sql_to_df(sql,process_path) if not 'skip_df' in locals() else pd.concat([skip_df,sql_to_df(sql,process_path)])
        skip_df['Explanation'] = "This reviewed element is skipped because the match code at time of review was different than the current match code."
        skip_df.to_csv(map_folder  + '\\Skipped_Review_Elements.csv',index=False)


        review_df.to_csv(map_folder + '\\Previous_Reviews_Accumulated.csv',index=False)
    for m in modelList:
        shutil.copy(working_folder  + '\\' + m,map_folder  + '\\' + m)


    if make_review_csvs:
        #Make review sheets

        sql = "SELECT Sewer_Area, FacilityID, MUID, Acronym, Match_Code FROM Manholes_GIS_Model_Match WHERE Pending_Review = 1 ORDER BY  Sewer_Area, Match_Code, FacilityID"
        df_review = sql_to_df(sql,process_path)
        df_review.columns = ['Sewer_Area','FacilityID','MUID','Acronym','Match_Code']
        df_review['Accepted'] = 0

        for sewer_area in sewer_areas:
            sewer_area = sewer_area[0]
            df_review_local =  df_review[df_review.Sewer_Area==sewer_area]
            df_review_local.to_csv(map_folder + '\\' + sewer_area + '\\' + sewer_area + '_Review_Manholes-ONCE_REVIEWED_REMOVE_HYPHEN_AND_ALLCAPS_LETTERS_IN_THIS_FILENAME.csv',index=False)

        sql = "SELECT Sewer_Area, FacilityID, MUID, Acronym, Match_Code FROM Mains_GIS_Model_Match WHERE Pending_Review = 1 ORDER BY  Sewer_Area, Match_Code, FacilityID"
        df_review = sql_to_df(sql,process_path)
        df_review.columns = ['Sewer_Area','FacilityID','MUID','Acronym','Match_Code']
        df_review['Accepted'] = 0
        for sewer_area in sewer_areas:
            sewer_area = sewer_area[0]
            df_review_local =  df_review[df_review.Sewer_Area==sewer_area]
            df_review_local.to_csv(map_folder + '\\' + sewer_area + '\\' + sewer_area + '_Review_Mains-ONCE_REVIEWED_REMOVE_HYPHEN_AND_ALLCAPS_LETTERS_IN_THIS_FILENAME.csv',index=False)

    #Mains maps
    if make_maps_mains:
        mxd = arcpy.mapping.MapDocument(working_folder + '\\' + map_template_pipe)
        page_count = mxd.dataDrivenPages.pageCount
        for i in range(1, page_count + 1):
            print 'Making pipe jpg ' + str(i) + ' of ' + str(page_count)
            mxd.dataDrivenPages.currentPageID = i
            row = mxd.dataDrivenPages.pageRow
            arcpy.mapping.ExportToJPEG(mxd, map_folder + "\\" + row.getValue('Sewer_Area') + '\\' + row.getValue('Map_Name') + ".jpg")

    #Manhole Maps
    if make_maps_manholes:
        mxd = arcpy.mapping.MapDocument(working_folder + '\\' + map_template_node)
        page_count = mxd.dataDrivenPages.pageCount
        for i in range(1, page_count + 1):
            print 'Making node jpg ' + str(i) + ' of ' + str(page_count)
            mxd.dataDrivenPages.currentPageID = i
            row = mxd.dataDrivenPages.pageRow
            arcpy.mapping.ExportToJPEG(mxd, map_folder + "\\" + row.getValue('Sewer_Area') + '\\' + row.getValue('Map_Name') + ".jpg")

end_timer = datetime.datetime.now()
duration = end_timer - start_timer
duration_seconds = duration.seconds

message = "Finished in " + str(duration_seconds) + " seconds"
print message

MessageBox = ctypes.windll.user32.MessageBoxA
MessageBox(None, message, 'Info', 0)







