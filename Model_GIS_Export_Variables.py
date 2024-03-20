##AFTER UPDATE AND SAVE YOU MUST RESTART THE KERNEL IN JUPYTER NOTEBOOK TO UPDATE VARIABLES!

##Remember to insert r in front of all paths, e.g. r"J:\SEWER_AREA_MODELS\FSA\03_SIMULATION_WORK\Calibration_2022\MODEL"

#All setups, initialize lists to not throw error if undefined.
master_list = []
absolute_velocity_discharge = True

acronym_filter = ['BIN']

rawn_years = [2061,2071,2081,2091,2101]

output_folder = r'J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Temp_Output'
model_manhole_csv = r'J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\Manhole_GIS_Model_Match.csv'
model_pipe_csv = r'J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\Mains_GIS_Model_Match.csv'
rawn_csv = r"J:\SEWER_AREA_MODELS\FSA\04_ANALYSIS_WORK\Model_Result_To_GIS\Automation\RAWN_Files.csv"


#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
#&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

model_area = 'FSA'
db_type = 'sqlite'
model_folder = r"J:\SEWER_AREA_MODELS\FSA\03_SIMULATION_WORK\Always_Latest_GIS_Input_Simulations_FSA\Model"

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

master_list.append([model_area,db_type,model_folder,output_folder,res_list])

# # # #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
