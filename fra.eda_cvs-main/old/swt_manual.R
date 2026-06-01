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


log4r::info(logger, "START --- script: eda_csv/swt_manual.R ----  "  )



#Set date for updates today , today - 7 days 
# xstr_date1 = paste0("'",as.character(today() - lubridate::days(330) ),"'")
xstr_date1 = "'2022-05-20'"
xstr_date2 = paste0("'",as.character(today()),"'") 


xstr_message =   paste("start date: ", xstr_date1, ", end date :", xstr_date2 ) 


log4r::info(logger, xstr_message ) 


# List of arguments -------------------------------------------------------

list_product <- list(


  list(
    techno="XH018",
    source = " " , 
    test_name = "TDK_HVCG ", 
    address = paste0( root_address,"FWT_XH018"), 
    npnpid ="1890",
    version="1",
    pmax ="12000",
    nparam=paste0(
      "10691,10695,10696,10697,10698,10699,",
      "10000,", 
      "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,",
      "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,",
      "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,",
      "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,",
      "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050 "
    )
  )
  
)


# Loop with arguments  ----------------------------------------------------

i=1
  
  xstr_address = list_product[[i]]$address 
  xstr_npnpid = list_product[[i]]$npnpid
  xstr_version = list_product[[i]]$version
  xstr_pmax = list_product[[i]]$pmax
  
  if(list_product[[i]]$techno == "T18SO"){
    xstr_nparam = f_param_list(xstr_npnpid, xstr_version, conid= conid)
  } else{
    xstr_nparam =list_product[[i]]$nparam  
  }
  
  log4r::info(logger, paste("start with " ,list_product[[i]]$techno, list_product[[i]]$source ," npnpid =  ", xstr_npnpid, ",version : ", xstr_version ) ) 
  
  f_update_data_lot( xstr_address, xstr_npnpid, xstr_version , xstr_nparam, xstr_pmax, xstr_date1 ,xstr_date2 ,xFile, conid=conid)
  f_update_data_wafer( xstr_address, xstr_npnpid, xstr_version , xstr_nparam, xstr_pmax, xstr_date1 ,xstr_date2 ,xFile, conid= conid)
  
  if(list_product[[i]]$techno == "T18SO"){
    f_update_allgood_wafer( xstr_address, xstr_npnpid)
  }
  







log4r::info(logger, "END script  ---->>>> " ) 

