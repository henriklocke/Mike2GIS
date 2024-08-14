##AFTER UPDATE AND SAVE YOU MUST RESTART THE KERNEL IN JUPYTER NOTEBOOK TO UPDATE VARIABLES!

##Remember to insert r in front of all paths, e.g. r"J:\SEWER_AREA_MODELS\FSA\03_SIMULATION_WORK\Calibration_2022\MODEL"

#All setups, initialize lists to not throw error if undefined.
master_list = []
absolute_velocity_discharge = True #If True then negative values are changed to positive values.

acronym_filter = []

rawn_years = [2060,2070,2080,2090,2100]

output_folder = r'\\gvrdfile01\gisdata\PROJECTS\CP18\07\KeyFlowsandHGL\Datafiles'
model_manhole_csv = r"J:\UAI_GENERAL\KEY FLOW & HGL_GIS\TOOLS EXECUTION\TOOL1\Manhole_GIS_Model_Match.csv"
model_pipe_csv = r"J:\UAI_GENERAL\KEY FLOW & HGL_GIS\TOOLS EXECUTION\TOOL1\Mains_GIS_Model_Match.csv"

rawn_input_from_model = True
open_save_close = False #Use if model RAWN sheets have not been opened and saved before (required to calculate the formulas in opepyxl sheets)

#Only used when rawn_input_from_model = False
rawn_csv = r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\RAWN_Files.csv"

#Only used when rawn_input_from_model = True
#rawn_inputfolders has the following items:
#[Model area nam,Rawn sheet folder]
rawn_inputfolders = []
rawn_inputfolders.append(['FSA',r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\RAWN_From_Model\Excel"])
rawn_inputfolders.append(['NSSA',r"J:\SEWER_AREA_MODELS\NSSA\04_ANALYSIS_WORK\RAWN_From_Model\Excel"])
rawn_inputfolders.append(['LISA',r"J:\SEWER_AREA_MODELS\LISA\04_ANALYSIS_WORK\RAWN_From_Model\Excel"])

#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

#res_list has the following items:
#([Description,Population Year,Result file name with extension])D

model_area = 'VSA'
model = 'VSA_BASE_MODEL_2030_Backup304_DWF_No_Tide.mdb' #Used to read version and extension, one model is enough.
model_folder = r"J:\SEWER_AREA_MODELS\VSA\03_SIMULATION_WORK\Key_Flow_HGL_GIS_Sim_VSA\Model"

res_list = []
res_list.append(['DWF',2025,'VSA_DWF_No_Tide_2025pop_Base.res1d'])
res_list.append(['DS-2yr-24hr',2025,'VSA_WWF_EX-2yr-24hr-SCS1A_2025pop_Base.res1d'])
res_list.append(['DS-5yr-24hr',2025,'VSA_WWF_EX-5yr-24hr-SCS1A_2025pop_Base.res1d'])
res_list.append(['DS-10yr-24hr',2025,'VSA_WWF_EX-10yr-24hr-SCS1A_2025pop_Base.res1d'])
res_list.append(['DS-25yr-24hr',2025,'VSA_WWF_EX-25yr-24hr-SCS1A_2025pop_Base.res1d'])

res_list.append(['DWF',2030,'VSA_DWF_No_Tide_2030pop_Base.res1d'])
res_list.append(['DS-2yr-24hr',2030,'VSA_WWF_EX-2yr-24hr-SCS1A_2030pop_Base.res1d'])
res_list.append(['DS-5yr-24hr',2030,'VSA_WWF_EX-5yr-24hr-SCS1A_2030pop_Base.res1d'])
res_list.append(['DS-10yr-24hr',2030,'VSA_WWF_EX-10yr-24hr-SCS1A_2030pop_Base.res1d'])
res_list.append(['DS-25yr-24hr',2030,'VSA_WWF_EX-25yr-24hr-SCS1A_2030pop_Base.res1d'])

master_list.append([model_area,model,model_folder,output_folder,res_list])

model_area = 'FSA'
model = 'FSA_2025pop_V157.sqlite' #Used to read version and extension, one model is enough.
model_folder = r"J:\SEWER_AREA_MODELS\FSA\03_SIMULATION_WORK\Key_Flow_HGL_GIS_Sim_FSA\Model"

res_list = []
res_list.append(['DWF',2025,'FSA_DWF_2021-07-22_4d_2025pop_BaseDefault_Network_HD.res1d'])
res_list.append(['DS-2yr-24hr',2025,'FSA_GA_EX-2y-24h-AES_2025p_Base-DSS1Default_Network_HD.res1d'])
res_list.append(['DS-5yr-24hr',2025,'FSA_GA_EX-5y-24h-AES_2025p_Base-DSS2Default_Network_HD.res1d'])
res_list.append(['DS-10yr-24hr',2025,'FSA_GA_EX-10y-24h-AES_2025p_Base-DSS3Default_Network_HD.res1d'])
res_list.append(['DS-25yr-24hr',2025,'FSA_GA_EX-25y-24h-AES_2025p_Base-DSS16Default_Network_HD.res1d'])

res_list.append(['DWF',2030,'FSA_DWF_2021-07-22_4d_2030pop_2030_NetworkDefault_Network_HD.res1d'])
res_list.append(['DS-2yr-24hr',2030,'FSA_GA_EX-2y-24h-AES_2030p_F_2030_Network-DSS4Default_Network_HD.res1d'])
res_list.append(['DS-5yr-24hr',2030,'FSA_GA_EX-5y-24h-AES_2030p_F_2030_Network-DSS5Default_Network_HD.res1d'])
res_list.append(['DS-10yr-24hr',2030,'FSA_GA_EX-10y-24h-AES_2030p_F_2030_Network-DSS6Default_Network_HD.res1d'])
res_list.append(['DS-25yr-24hr',2030,'FSA_GA_EX-25y-24h-AES_2030p_F_2030_Network-DSS17Default_Network_HD.res1d'])

master_list.append([model_area,model,model_folder,output_folder,res_list])

model_area = 'NSSA'
model = 'NSSA_2025pop_V88.sqlite' #Used to read version and extension, one model is enough.
model_folder = r"\\prdsynfile01\LWS_Modelling\SEWER_AREA_MODELS\NSSA\03_SIMULATION_WORK\Key_Flow_HGL_GIS_Sim_NSSA\Model"

res_list = []
res_list.append(['DWF',2025,'NSSA_DWF_2018-07-26_4d_2025pop_BaseDefault_Network_HD.res1d'])
res_list.append(['DS-2yr-24hr',2025,'NSSA_GA_EX-2y-24h-AES_2025p_Base-DSS1Default_Network_HD.res1d'])
res_list.append(['DS-5yr-24hr',2025,'NSSA_GA_EX-5y-24h-AES_2025p_Base-DSS2Default_Network_HD.res1d'])
res_list.append(['DS-10yr-24hr',2025,'NSSA_GA_EX-10y-24h-AES_2025p_Base-DSS3Default_Network_HD.res1d'])
res_list.append(['DS-25yr-24hr',2025,'NSSA_GA_EX-25y-24h-AES_2025p_Base-DSS10Default_Network_HD.res1d'])

res_list.append(['DWF',2030,'NSSA_DWF_2018-07-26_4d_2030pop_BaseDefault_Network_HD.res1d'])
res_list.append(['DS-2yr-24hr',2030,'NSSA_GA_EX-2y-24h-AES_2030p_Base-DSS1Default_Network_HD.res1d'])
res_list.append(['DS-5yr-24hr',2030,'NSSA_GA_EX-5y-24h-AES_2030p_Base-DSS2Default_Network_HD.res1d'])
res_list.append(['DS-10yr-24hr',2030,'NSSA_GA_EX-10y-24h-AES_2030p_Base-DSS3Default_Network_HD.res1d'])
res_list.append(['DS-25yr-24hr',2030,'NSSA_GA_EX-25y-24h-AES_2030p_Base-DSS10Default_Network_HD.res1d'])

master_list.append([model_area,model,model_folder,output_folder,res_list])

model_area = 'LISA'
model = 'LISA_2025pop_V21.sqlite' #Used to read version and extension, one model is enough.
model_folder = r"J:\SEWER_AREA_MODELS\LISA\03_SIMULATION_WORK\Key_Flow_HGL_GIS_Sim_LISA\Model"

res_list = []
res_list.append(['DWF',2025,'LISA_DWF_2025pop_2025Default_Network_HD.res1d'])
res_list.append(['DS-2yr-24hr',2025,'LISA_WWF_EX-2yr-24hr-SCS_2025pop_2025Default_Network_HD.res1d'])
res_list.append(['DS-5yr-24hr',2025,'LISA_WWF_EX-5yr-24hr-SCS_2025pop_2025Default_Network_HD.res1d'])
res_list.append(['DS-10yr-24hr',2025,'LISA_WWF_EX-10yr-24hr-SCS_2025pop_2025Default_Network_HD.res1d'])
res_list.append(['DS-25yr-24hr',2025,'LISA_WWF_EX-25yr-24hr-SCS_2025pop_2025Default_Network_HD.res1d'])

res_list.append(['DWF',2030,'LISA_DWF_2030pop_2030Default_Network_HD.res1d'])
res_list.append(['DS-2yr-24hr',2030,'LISA_WWF_EX-2yr-24hr-SCS_2030pop_2030Default_Network_HD.res1d'])
res_list.append(['DS-5yr-24hr',2030,'LISA_WWF_EX-5yr-24hr-SCS_2030pop_2030Default_Network_HD.res1d'])
res_list.append(['DS-10yr-24hr',2030,'LISA_WWF_EX-10yr-24hr-SCS_2030pop_2030Default_Network_HD.res1d'])
res_list.append(['DS-25yr-24hr',2030,'LISA_WWF_EX-25yr-24hr-SCS_2030pop_2030Default_Network_HD.res1d'])

master_list.append([model_area,model,model_folder,output_folder,res_list])


# # # #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
