#Permanent cell 1
import arcpy
import pandas as pd
import sqlite3
import math
import numpy as np

#Permanent cell 2
def sql_to_df(sql,model):
    con = sqlite3.connect(model)
    df = pd.read_sql(sql, con)
    con.close()
    return df

def execute_sql(sqls,model):
    con = sqlite3.connect(model)
    cur = con.cursor()
    if type(sqls) == list:
        for sql in sqls:
            cur.execute(sql)
    else:         
        cur.execute(sqls)
    cur.close()
    con.commit()
    con.close()

# User Input, to move to separate sheet so no permanent cell
#stop trace if more pipes than max_steps traced from catchment, must be an endless loop. 
max_steps = 1000 

update_field_in_model = True
update_field = 'Description'

output_folder = r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\Rawn_Tool\Output"
model_path = r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\NSSA_Base_2018pop.sqlite"
sewer_area = 'NSSA'
pop_book = r"\\prdsynfile01\LWS_Modelling\SEWER_AREA_MODELS\NSSA\02_MODEL_COMPONENTS\04_DATA\01. POPULATION\MPF4_Temp_Hold\NSSA_Master_Population_File_4_No_2237_ResArea.xlsx"
pop_sheet = 'MPF Update 4'
model = 'NSSA'

#Permanent cell 3

years = [2060,2070,2080,2090,2100]
categories = ['res','com','ind','inst','infl','infi']

mpf_col_dict = {}

area_col_dict = {}
area_col_dict['res'] = 'Area_Res'
area_col_dict['com'] = 'Area_Com'
area_col_dict['ind'] = 'Area_Ind'
area_col_dict['inst'] = 'Area_Inst'
area_col_dict['ini'] = 'Area_Total'

per_unit_dict = {}
per_unit_dict['res'] = 320
per_unit_dict['com'] = 33700 
per_unit_dict['ind'] = 56200
per_unit_dict['inst'] = 33700
per_unit_dict['infl'] = 5600
per_unit_dict['infi'] = 5600

header_dict = {}
# header_dict['gen'] = ['GENERAL INFO',['TYPE','MODELID','CATCHMENT','ID','YEAR','LOCATION']]
header_dict['gen'] = ['GENERAL INFO',['TYPE','CATCHMENT','YEAR','LOCATION']]
header_dict['res'] = ['RESIDENTIAL',['AREA (Ha)','POPULATION','AVG. FLOW (L/s)','PEAK FLOW (L/s)']]
header_dict['com'] = ['COMMERCIAL',['AREA (Ha)','AVG. FLOW (L/s)','PEAK FLOW (L/s)']]
header_dict['ind'] = ['INDUSTRIAL',['AREA (Ha)','AVG. FLOW (L/s)','PEAK FLOW (L/s)']]
header_dict['inst'] = ['INSTITUTIONAL',['AREA (Ha)','AVG. FLOW (L/s)','PEAK FLOW (L/s)']]
header_dict['ini'] = ['INFLOW / INFILTRATION',['AREA (Ha)','INFLOW (L/s)','INFILTRATION (L/s)']]
header_dict['flow'] = ['FLOWS',['AVG. SAN. FLOW (L/s)','ADWF (L/s)','PWWF (L/s)']]

avg_calc_dict = {}
avg_calc_dict['res'] = ['RESIDENTIAL','POPULATION','AVG. FLOW (L/s)']
avg_calc_dict['com'] = ['COMMERCIAL','AREA (Ha)','AVG. FLOW (L/s)']
avg_calc_dict['ind'] = ['INDUSTRIAL','AREA (Ha)','AVG. FLOW (L/s)']
avg_calc_dict['inst'] = ['INSTITUTIONAL','AREA (Ha)','AVG. FLOW (L/s)']
avg_calc_dict['infl'] = ['INFLOW / INFILTRATION','AREA (Ha)','INFLOW (L/s)']
avg_calc_dict['infi'] = ['INFLOW / INFILTRATION','AREA (Ha)','INFILTRATION (L/s)']

header_tuples = []
for header in header_dict:
    for sub_header in (header_dict[header][1]):
        header_tuples.append((header_dict[header][0],sub_header))
header_tuples

# columns_multiindex = pd.MultiIndex.from_tuples(header_tuples,names=['Category', 'Subcategory'])
columns_multiindex = pd.MultiIndex.from_tuples(header_tuples)
df_template = pd.DataFrame(columns=columns_multiindex)





#Permanent cell 4
pop_df = pd.read_excel(pop_book,sheet_name=pop_sheet,dtype={'Catchment': str})#[['Catchment','Year','Pop_Total']]
pop_df.rename(columns={"Pop_Total": "Population"},inplace=True)
pop_df = pop_df[['Catchment','Year','Pop_ResLD','Pop_ResHD','Pop_Mixed','Population','Area_ResLD','Area_ResHD','Area_Mixed','Area_Com','Area_Ind','Area_Inst']]
pop_df['Area_Res'] = pop_df.Area_ResLD + pop_df.Area_ResHD + pop_df.Area_Mixed
pop_df['Area_Total'] = pop_df.Area_ResLD + pop_df.Area_ResHD + pop_df.Area_Mixed + pop_df.Area_Com + pop_df.Area_Ind + pop_df.Area_Inst
pop_df['Population_Sum_Check'] = pop_df.Pop_ResLD + pop_df.Pop_ResHD + pop_df.Pop_Mixed
pop_sum_total_col = int(pop_df.Population.sum())
pop_sum_sub_cols = int(pop_df.Pop_ResLD.sum() + pop_df.Pop_ResHD.sum() + pop_df.Pop_Mixed.sum())
pop_df['Key'] = sewer_area + '@' + pop_df.Catchment + '@' + pop_df['Year'].astype(str)
pop_df.set_index('Key',inplace=True)

if pop_sum_total_col != pop_sum_sub_cols:
      raise ValueError("Error. The sum of 'Population' (" + str(pop_sum_total_col) + ") is different than the sum of 'Pop_ResLD' + 'Pop_ResHD' + 'Pop_Mixed' (" + str(pop_sum_sub_cols) + ")") 


#Permanent cell 5
#Active = 1 takes only elements from the activated scenario

node_types = {}
node_types[1] = 'Manhole'
node_types[2] = 'Basin'
node_types[3] = 'Outlet'
node_types[4] = 'Junction'
node_types[5] = 'Soakaway'
node_types[6] = 'River Junction'

sql = "SELECT catchid AS Catchment, nodeid AS Connected_Node FROM msm_Catchcon WHERE Active = 1"
catchments = sql_to_df(sql,model_path)

sql = "SELECT muid AS MUID, fromnodeid AS [From], tonodeid as [To], uplevel AS Outlet_Level FROM msm_Link WHERE Active = 1"
lines = sql_to_df(sql,model_path)

sql = "SELECT muid AS MUID, fromnodeid AS [From], tonodeid as [To], invertlevel AS Outlet_Level FROM msm_Orifice WHERE Active = 1"
orifices = sql_to_df(sql,model_path)
lines = pd.concat([lines,orifices])

sql = "SELECT muid AS MUID, fromnodeid AS [From], tonodeid as [To], invertlevel AS Outlet_Level FROM msm_Valve WHERE Active = 1"
valves = sql_to_df(sql,model_path)
lines = pd.concat([lines,valves])

sql = "SELECT muid AS MUID, fromnodeid AS [From], tonodeid as [To], crestlevel AS Outlet_Level FROM msm_Weir WHERE Active = 1"
weirs = sql_to_df(sql,model_path)
lines = pd.concat([lines,weirs])

sql = "SELECT muid AS MUID, fromnodeid AS [From], tonodeid as [To], startlevel AS Outlet_Level FROM msm_Pump WHERE Active = 1"
pumps = sql_to_df(sql,model_path)
lines = pd.concat([lines,pumps])

lines['Outlet_Level'].fillna(-9999, inplace=True)

sql = "SELECT muid, acronym, assetname FROM msm_Node WHERE active = 1"
node_id_df = sql_to_df(sql,model_path)
node_id_df = node_id_df[(node_id_df.assetname.str[:2]=='MH') & (node_id_df.assetname.str.len() > 2) & (node_id_df.acronym.notna())]
node_id_df.rename(columns={'muid':'Node'},inplace=True)
node_id_df['ID'] = node_id_df.acronym + '_' + node_id_df.assetname
node_id_df = node_id_df[['Node','ID']]
node_id_df

test = set()
test.add(2)
test.add(4)

test.pop()

test

node_catchment

#Plan for how to do multi path
#Multi path is reached.
#Save multipath in dict
#dict[node] = [Multi_index,]

#Go down first path
#Second multipath reached
#Save second multi path in list

#[Level1,Node,[pipe1,pipe2]]
#[Level2,Node,[pipe3,pipe4]]



#Permanent cell 6
accumulated_catchment_set = set()

for index, row in catchments.iterrows():
    catchment = row['Catchment']
    node = row['Connected_Node']
    start_node = row['Connected_Node']
    steps = 0
    
#     print (str((node,add_catchment)) + ' in set: ' + str((node,catchment) in accumulated_catchment_set))
#     print('added set for node ' + node + ' and catchment ' + catchment + ', path started from ' + start_node + '. Set length: ' + str(len(accumulated_catchment_set)))
    accumulated_catchment_set.add((node,catchment))
    
    while steps <= max_steps:
        steps += 1
        downstream_lines = lines[lines.From==node].sort_values(by=['Outlet_Level']).copy()
        if len(downstream_lines) > 0:
            line = downstream_lines.iloc[0].MUID
            node = downstream_lines.iloc[0].To
        else:
            row['Outlet'] = node

            sql = "SELECT typeno FROM msm_Node WHERE muid = '" + node + "'"
            type_no = sql_to_df(sql,model_path).iloc[0][0]
            row['Type'] = node_types[type_no]

            break
        if steps == max_steps:
            row['Error'] = "Maximum steps were reached, indicating a loop."
            row['Outlet'] = node
            sql = "SELECT typeno FROM msm_Node WHERE muid = '" + node + "'"
            type_no = sql_to_df(sql,model_path).iloc[0][0]
            row['Type'] = node_types[type_no]
            
#         print (str((node,add_catchment)) + ' in set: ' + str((node,catchment) in accumulated_catchment_set))
#         print('added set for node ' + node + ' and catchment ' + catchment + ', path started from ' + start_node + '. Set length: ' + str(len(accumulated_catchment_set)))
        accumulated_catchment_set.add((node,catchment))
        
accumulation_df = pd.DataFrame(accumulated_catchment_set,columns=['Node','Catchment'])
accumulation_df = pd.merge(accumulation_df,node_id_df,how='inner',on=['Node'])
data = {
    ('GENERAL INFO', 'CATCHMENT'): accumulation_df.Catchment,
    ('GENERAL INFO', 'NODE'): accumulation_df.Node,
    ('GENERAL INFO', 'ID'): accumulation_df.ID,
}

# Create a DataFrame with MultiIndex columns
accumulation_df = pd.DataFrame(data)
            
#         node_connection_df = catchments[catchments['Connected_Node']==node]
#         if len(node_connection_df) > 0:
#             for add_catchment in list(node_connection_df.Catchment.unique()):
                
#                 print (str((node,add_catchment)) + ' in set: ' + str((node,add_catchment) in accumulated_catchment_set))
#                 print('added set for node ' + node + ' and catchment ' + add_catchment + ', path started from ' + start_node + '. Set length: ' + str(len(accumulated_catchment_set)))
#                 accumulated_catchment_set.add((node,add_catchment))
            
# try:
#     catchments.to_excel(output_sheet, index=False)
# except:
#     #If the spreadsheet export gives an error, export to csv instead
#     catchments.to_csv(output_sheet[:-5] + '.csv', index=False)

#Permanent cell 7
catchments = list(pop_df.Catchment.unique())

catchment_df = df_template.copy()
for catchment in catchments:
    for year in years:
        key = model + '@' + catchment + '@' + str(year)
        catchment_df.loc[key,('GENERAL INFO','TYPE')] = 'UNKNOWN'
        catchment_df.loc[key,('GENERAL INFO','CATCHMENT')] = catchment
        catchment_df.loc[key,('GENERAL INFO','YEAR')] = year
        catchment_df.loc[key,('GENERAL INFO','LOCATION')] = model
        for area_col_dict_key in area_col_dict:
            catchment_df.loc[key,(header_dict[area_col_dict_key][0],'AREA (Ha)')] = pop_df.loc[key,area_col_dict[area_col_dict_key]]
        catchment_df.loc[key,('RESIDENTIAL','POPULATION')] = pop_df.loc[key,'Population']
        san_flow = 0
        adwf = 0
        for avg_calc_dict_key in avg_calc_dict:
            input1 = catchment_df.loc[key,(avg_calc_dict[avg_calc_dict_key][0],avg_calc_dict[avg_calc_dict_key][1])]
            input2 = per_unit_dict[avg_calc_dict_key]
            avg_flow = input1 * input2 / 86400
            adwf += avg_flow
            if avg_calc_dict_key not in ['infl','infi']:
                san_flow += avg_flow
            catchment_df.loc[key,(avg_calc_dict[avg_calc_dict_key][0],avg_calc_dict[avg_calc_dict_key][2])] = avg_flow
        catchment_df.loc[key,('FLOWS','AVG. SAN. FLOW (L/s)')] = san_flow
        catchment_df.loc[key,('FLOWS','ADWF (L/s)')] = adwf

        
catchment_node_df = accumulation_df.merge(catchment_df,on=[('GENERAL INFO','CATCHMENT')],how='inner')
node_df = catchment_node_df.copy()
node_df.drop(columns=[('GENERAL INFO','CATCHMENT')],inplace=True)
node_df = node_df.groupby([('GENERAL INFO','NODE'),('GENERAL INFO','TYPE'),('GENERAL INFO','YEAR'),('GENERAL INFO','LOCATION'),('GENERAL INFO','ID')]).sum()
node_df.reset_index(inplace=True)
node_df[('RESIDENTIAL','PEAK FLOW (L/s)')] = (1 + 14 / (4 + (node_df[('RESIDENTIAL','POPULATION')] / 1000) ** 0.5)) * node_df[('RESIDENTIAL','AVG. FLOW (L/s)')]
node_df[('COMMERCIAL','PEAK FLOW (L/s)')] = (1 + 14 / (4 + (per_unit_dict['com'] * node_df[('COMMERCIAL','AREA (Ha)')]/(per_unit_dict['res'] * 1000)) ** 0.5))*node_df[('COMMERCIAL','AVG. FLOW (L/s)')]*0.8
node_df[('INSTITUTIONAL','PEAK FLOW (L/s)')] = (1 + 14 / (4 + (per_unit_dict['inst'] * node_df[('INSTITUTIONAL','AREA (Ha)')] / (per_unit_dict['res'] * 1000)) ** 0.5)) * node_df[('INSTITUTIONAL','AVG. FLOW (L/s)')]

mask = node_df[('INDUSTRIAL', 'AREA (Ha)')] != 0 #Avoid error from log(0)
node_df.loc[mask, ('INDUSTRIAL', 'PEAK FLOW (L/s)')] = (
    0.8 * (1 + 14 / (4 + (node_df[('INDUSTRIAL', 'AREA (Ha)')][mask] * per_unit_dict['ind'] / (per_unit_dict['res'] * 1000)) ** 0.5)) *
    np.where(
        node_df[('INDUSTRIAL', 'AREA (Ha)')][mask] < 121,
        1.7,
        2.505 - 0.1673 * np.log(node_df[('INDUSTRIAL', 'AREA (Ha)')][mask])
    ) * node_df[('INDUSTRIAL', 'AVG. FLOW (L/s)')][mask]
)

node_df[('FLOWS','PWWF (L/s)')] = (
    node_df[('RESIDENTIAL','PEAK FLOW (L/s)')] +
    node_df[('COMMERCIAL','PEAK FLOW (L/s)')] +
    node_df[('INDUSTRIAL','PEAK FLOW (L/s)')] +
    node_df[('INSTITUTIONAL','PEAK FLOW (L/s)')] +
    node_df[('INFLOW / INFILTRATION','INFLOW (L/s)')] +
    node_df[('INFLOW / INFILTRATION','INFILTRATION (L/s)')]
)
node_df

for id in node_df[('GENERAL INFO','ID')].unique():
    node_single_df = node_df[node_df[('GENERAL INFO','ID')]==id]
    node_single_df.to_excel(output_folder + '\\' + id + '.xlsx')

list(accumulation_df[('GENERAL INFO','NODE')].unique())

gdb_name = 'test6.gdb'
# arcpy.CreatePersonalGDB_management(output_folder, 'test.mdb')

out_path = r'J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\Rawn_Tool\Output' + '\\' + gdb_name

gdb_name = 'test6.gdb'
# arcpy.CreatePersonalGDB_management(output_folder, 'test.mdb')
output_folder = r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\Rawn_Tool\Output"
model_path = r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\NSSA_Base_2018pop.sqlite"
arcpy.management.CreateFileGDB(output_folder, gdb_name)
out_path = r'J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\Rawn_Tool\Output' + '\\' + gdb_name
arcpy.env.workspace = out_path
sr = arcpy.SpatialReference(26910)
arcpy.conversion.FeatureClassToFeatureClass(model_path + '\\msm_Catchment', out_path, 'msm_catchment')
arcpy.DefineProjection_management('msm_catchment', sr)
arcpy.management.AddField('msm_catchment', "Drains_To", "TEXT")



arcpy.env.workspace = out_path

nodes = list(accumulation_df[('GENERAL INFO','NODE')].unique())
for i, node in enumerate(nodes):
    print('Dissolving for node ' + str(i) + ' of ' + str(len(nodes)) + ' at time ' + str(datetime.datetime.now()))
    catchment_df = accumulation_df[accumulation_df[('GENERAL INFO','NODE')]==node]
    catchments = list(catchment_df[('GENERAL INFO','CATCHMENT')].unique())
    arcpy.management.CalculateField('msm_Catchment', "Drains_To", "''", "PYTHON3")
    with arcpy.da.UpdateCursor('msm_catchment', ['muid', 'Drains_To']) as cursor:
        for row in cursor:
            if row[0] in catchments:
                row[1] = node
                cursor.updateRow(row)

    query = "Drains_To = 'Test'"
    arcpy.management.MakeFeatureLayer('msm_catchment', "temp_layer", "Drains_To = '" + node + "'")
    dissolve_output = out_path + '\\msm_Catchment_Dissolve_Single'
    arcpy.management.Dissolve("temp_layer", dissolve_output, "Drains_To", "", "MULTI_PART")
    arcpy.management.Delete("temp_layer")

    arcpy.conversion.FeatureClassToFeatureClass('msm_Catchment_Dissolve_Single', out_path, 'Node_Catchment_' + node)



nodes = list(accumulation_df[('GENERAL INFO','NODE')].unique())
for i, node in enumerate(nodes):    
    print('Appending for node ' + str(i) + ' of ' + str(len(nodes)) + ' at time ' + str(datetime.datetime.now()))
    if i == 0:
        arcpy.conversion.FeatureClassToFeatureClass('Node_Catchment_' + node, out_path, 'Node_Catchment')
    else:
        arcpy.management.Append('Node_Catchment_' + node, "Node_Catchment", "NO_TEST")

stophere = 0
#Test multi path
extra_lines = set()
#Permanent cell 99
accumulated_catchment_set = set()

for index1, row1 in catchments.iterrows():
    catchment = row1['Catchment']
    nodes = [row1['Connected_Node']]
    start_node = row1['Connected_Node']
    steps = 0
    
    accumulated_catchment_set.add((node,catchment))
        
    while steps <= max_steps:
        steps += 1
        downstream_df = lines[lines['From'].isin(nodes)]
#         print(len(downstream_df))
         
#         if '7134' in nodes:
#             break
        if len(downstream_df) > 0:
            nodes = list(downstream_df.To.unique())
#             if '7133' in list(downstream_df.From.unique()):
#                 break
#                 print(len(downstream_df))
            nodes = [node for node in nodes if len(node)>0]
            for node in nodes:
                accumulated_catchment_set.add((node,catchment)) 
#                 if '7134' in nodes:
#                     print('Added ' + str((node,catchment)))

        
        else:
            break
        if steps == max_steps:
            raise ValueError("Maximum steps were reached, indicating a loop. Start catchment is '" + catchment + "'")
           
        accumulated_catchment_set.add((node,catchment))
        
accumulation_df = pd.DataFrame(accumulated_catchment_set,columns=['Node','Catchment'])
# accumulation_df = pd.merge(accumulation_df,node_id_df,how='inner',on=['Node'])
data = {
    ('GENERAL INFO', 'CATCHMENT'): accumulation_df.Catchment,
    ('GENERAL INFO', 'NODE'): accumulation_df.Node,
#     ('GENERAL INFO', 'ID'): accumulation_df.ID,
}

# Create a DataFrame with MultiIndex columns
accumulation_df = pd.DataFrame(data)

# accumulation_df


accumulation_df

accumulated_catchment_set

accumulation_df[accumulation_df[('GENERAL INFO','NODE')]=='1_173']

downstream_df

nodes

for hh, ff in catchment_df.iterrows():
    print (ff[2])

# import pandas as pd

# # Sample DataFrame
# data = {
#     'Catchment': [1, 2, 3],
#     'Node': [4, 5, 6]

# }
# accumulation_df = pd.DataFrame(data)

# # Create a MultiIndex with the existing columns
# existing_columns_multiindex = pd.MultiIndex.from_tuples([
#     ('GENERAL INFO', 'Catchment'),  # Header with no subheaders
#     ('GENERAL INFO', 'Node'),  # Header with no subheaders
# ])

# # Create a MultiIndex with the upper level 'GENERAL INFO'
# upper_level = [('GENERAL INFO', '')] * len(existing_columns_multiindex)

# # Concatenate the upper level and the existing columns MultiIndex
# new_columns_multiindex = pd.MultiIndex.from_tuples(list(zip(upper_level, existing_columns_multiindex)))

# # Assign the new MultiIndex to the DataFrame columns
# accumulation_df.columns = new_columns_multiindex

# accumulation_df


# import pandas as pd

# # Sample data for the DataFrame
# data = {
#     ('GENERAL INFO', 'CATCHMENT'): accumulation_df.Catchment,
#     ('GENERAL INFO', 'NODE'): accumulation_df.Node,
# }

# # Create a DataFrame with MultiIndex columns
# df = pd.DataFrame(data)

# # Set names for the levels of the MultiIndex
# # df.columns.names = ['Header', 'Subheader']

# df
