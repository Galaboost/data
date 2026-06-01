# Clean envi, plots, console 
rm(list=ls())
if(!is.null(dev.list())) dev.off()
cat("\014") 

# Setup account 
str_home = "/home/auemura@xfab.ads"
root_address = paste0( str_home,"/share/EDASHARE/EDA_PUBLIC/CARAC/")


# Setup account 
str_home = "/home/auemura@xfab.ads"
str_project = paste0(str_home, "/scripts/swt/eda_csv")

# Load Credential 
source(paste0(str_home, "/scripts/autoexec.R"))

# Load libraries (package version) 
# library(RODBC, warn.conflicts = FALSE)     #(1.3.16)
# library(RMariaDB, warn.conflicts = FALSE)
# library(plyr, warn.conflicts = FALSE)      #(1.8.4)
# library(dplyr, warn.conflicts = FALSE)     #(0.8.3)
# library(stringr, warn.conflicts = FALSE)   #(1.4.0)
# library(lubridate, warn.conflicts = FALSE) #(1.7.4)
# library(haven, warn.conflicts = FALSE)     #(2.1.1)
# library(data.table, warn.conflicts = FALSE)#1.12.2
# library(log4r, warn.conflicts = FALSE)     #v.0.3.2
# library(glue, warn.conflicts = FALSE)



# log file 
xFile = paste0(str_project,"/log/log.txt" ) 
root_address = paste0( str_home,"/share/EDASHARE/EDA_PUBLIC/CARAC/")

# Load functions 
source(paste0(str_project,"/swt_utilities.R")   )


# debug -------------------------------------------------------------------





str_npnpid = "1800"
str_techno="XH018"

correct_dates <- function(str_npnpid, str_techno, ftype ){
  str_address <- get_address (str_techno=str_techno, str_root= root_address)
  
  str_file = paste0(str_address,"/db",str_npnpid, ftype,".csv" ) 
  dt <- data.table::fread(str_file)
  
  
  dtf  <- dt %>% 
    dplyr::mutate ( 
      DDTEST = if_else(
        substr(DDTEST,3,3) =="/" ,
        paste0(substr(DDTEST ,7,10),"-",substr(DDTEST ,4,5),'-',substr(DDTEST ,1,2)), 
        DDTEST )
    ) 
  
  data.table::fwrite(dtf,file=str_file)
}

correct_dates(str_npnpid = "1800",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1800",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1801",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1801",str_techno="XH018", ftype="w")


correct_dates(str_npnpid = "1802",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1802",str_techno="XH018", ftype="w")


correct_dates(str_npnpid = "1805",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1805",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1806",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1806",str_techno="XH018", ftype="w")


correct_dates(str_npnpid = "1810",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1810",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1811",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1811",str_techno="XH018", ftype="w")


correct_dates(str_npnpid = "1812",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1812",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1815",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1815",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1817",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1817",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1820",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1820",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1821",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1821",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1822",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1822",str_techno="XH018", ftype="w")

correct_dates(str_npnpid = "1890",str_techno="XH018", ftype="l")
correct_dates(str_npnpid = "1890",str_techno="XH018", ftype="w")
