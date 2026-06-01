#......................................................................
#
# Program name : swt_main.R  
# Author       : Aurelie Uemura 
# Description  : 
# A progrm to save SWT data at wafer level in EDA_PUBLIC with one directory 
# by technology in order to get longer wafer archive than DBPROD 1year 
# 

# # Used R version 
# platform       x86_64-redhat-linux-gnu     
# version.string R version 3.6.1 (2019-07-05)
#......................................................................
#                       Change log 
# 2022-01-10 Aurelie Uemura 
# -  add warn.conflicts = FALSE for library loadinings 
#.................................................. ....................

# Clean envi, plots, console 
rm(list=ls())
if(!is.null(dev.list())) dev.off()
cat("\014") 

# Setup account 
str_home = "/home/auemura@xfab.ads"
str_project = paste0(str_home, "/scripts/swt/eda_csv")

# Load Credential 
source(paste0(str_home, "/scripts/autoexec.R"))

# Load libraries (package version) 
library(RODBC, warn.conflicts = FALSE)     #(1.3.16)
library(plyr, warn.conflicts = FALSE)      #(1.8.4)
library(dplyr, warn.conflicts = FALSE)     #(0.8.3)
library(stringr, warn.conflicts = FALSE)   #(1.4.0)
library(lubridate, warn.conflicts = FALSE) #(1.7.4)
library(haven, warn.conflicts = FALSE)     #(2.1.1)
library(data.table, warn.conflicts = FALSE)#1.12.2
library(log4r, warn.conflicts = FALSE)     #v.0.3.2
library(glue, warn.conflicts = FALSE)



# log file 
xFile = paste0(str_project,"/log/log.txt" ) 
root_address = paste0( str_home,"/share/EDASHARE/EDA_PUBLIC/CARAC/")

# Load functions 
source(paste0(str_project,"/swt_utilities.R")   )


# Create log file 
log_file <- xFile
logger <- logger("INFO", appenders = file_appender(log_file) )


log4r::info(logger, "START --- script: eda_csv/swt_manual_with_profile.R ----  "  )



#Set date for updates today , today - 7 days 
# xstr_date1 = paste0("'",as.character(today() - lubridate::days(330) ),"'")
# xstr_date2 = paste0("'",as.character(today()),"'") 
xstr_date1 = "'2025-04-01'" ; xstr_date2 = "'2025-04-30'";manual_npnpid = 9806
xstr_date1 = "'2025-01-01'" ; xstr_date2 = "'2025-02-28'" ; manual_npnpid = 9807
xstr_date1 = "'2025-01-01'" ; xstr_date2 = "'2025-02-30'" ; manual_npnpid = 9809
xstr_date1 = "'2025-01-01'" ; xstr_date2 = "'2025-03-30'" ; manual_npnpid = 9810

xstr_date1 = "'2025-01-01'" ; xstr_date2 = "'2025-03-30'" ; manual_npnpid = 9811

xstr_message =   paste("start date: ", xstr_date1, ", end date :", xstr_date2 ) 
log4r::info(logger, xstr_message ) 





# ========================================

df_profile <- get_swt_profiles( conid = conid )

df_profile <- df_profile  %>% 
  dplyr::filter( npnpid == manual_npnpid )  

 

str_param <- "" ; str_techno <- ""; str_npnpid <- "" ; str_version <- "" ; str_address <- "" ; str_pmax <- "" 

# Load setting for the profile 
i =1 

str_techno <- df_profile$techno[i]
str_npnpid <- df_profile$npnpid[i]
str_version <- df_profile$version[i]
str_address <- get_address(str_techno = str_techno , str_root = root_address)
str_pmax <- get_pmax(str_techno = str_techno)
# Print settings : techno,  npnpid and version  
log4r::info(logger, paste( i , ": start with " ,str_techno, ", npnpid =  ", str_npnpid, ",version : ", str_version ) ) 

# Get nparam string 
## Get predefine list 

str_nparam <- get_nparam(str_techno = str_techno) 


if (str_param == "none"  ){
  # Get all available nparam in dbprod 
  str_nparam <- f_param_list(fstr_npnpid = str_npnpid, fstr_version = str_version, conid=conid) }


# if nparam no empty 
if (str_nparam != "" ) {
  # Get and update lot data 
  f_update_data_lot( str_address, str_npnpid, str_version , str_nparam, str_pmax, xstr_date1 ,xstr_date2 ,xFile, conid=conid)
  
  # Get and update wafer data 
  f_update_data_wafer( str_address, str_npnpid, str_version , str_nparam, str_pmax, xstr_date1 ,xstr_date2 ,xFile, conid= conid)
  
  # Get and update allgoodwafers 
  if(str_techno == "T18SO"){
    f_update_allgood_wafer( str_address, str_npnpid)
  }
  
} else { log4r::info(logger, "NPARAM strings is empty " ) 
}







log4r::info(logger, "END script  ---->>>> " ) 

