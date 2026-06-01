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


.