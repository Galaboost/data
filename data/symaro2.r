#======================================================================  
# Location :      ~/Symaro/
# Program Name :  Symaro_to_datamart.R 
#
# 2021-05-25 v1.0.0 CB 
#
# # Used R version 
# platform       x86_64-redhat-linux-gnu     
# version.string R version 3.6.1 (2019-07-05)
#====================================================================== 

rm(list=ls())
if(!is.null(dev.list())) dev.off()
cat("\014") 


library(DBI)
library(RMariaDB)
library(RMySQL)
library('RODBC')
library(data.table)
require(dplyr)
require(tidyr)
library(reshape2)
library(lubridate)
library(compare)
library(log4r)

source("/it/itadm/appli/rdatamart/etl_ref_route_cp/etc/config_file.R")

#Get instant time value
xstr_now <- as.character(lubridate::now())

#set-up algorithm version
xstr_version <- "1.0"

#Set-up logs
xFile=paste0(log_directory, "log_" ,xstr_now,".txt" ) 
file.create(xFile)
log_file <- xFile
logger <- log4r::logger("INFO", appenders = file_appender(log_file) )

info(logger, paste("space_to_datamart.R - version",xstr_version, "- Get last day references ")) 

info(logger, paste0("Loading data from date :",lubridate::today()))

### 1 Extract data

#1.1 Extract Operation from Symaro----

try <- tryCatch(               
  
  # Specifying expression
  expr = {  
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO, password = pwSYMARO, host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryOper <- paste0("SELECT OPE_ID,OPE_NAME,OPE_COMMENT,OPE_UPD_TIME
                         FROM T_OPERATION")
    dbOper  <- dbGetQuery(con,queryOper)
    dbDisconnect(con)
    
    df_oper <<- dplyr::distinct(dbOper)
    df_oper$OPE_UPD_TIME <- as_datetime(df_oper$OPE_UPD_TIME)
    
    df_oper2 <- df_oper %>% group_by(OPE_NAME) %>% summarise(last_oper=max(OPE_UPD_TIME))
    df_oper3 <- merge(df_oper,df_oper2,by.x=c("OPE_NAME","OPE_UPD_TIME"),by.y=c("OPE_NAME","last_oper"))
    df_oper3 <- distinct(df_oper3)
    
    #return(df_oper, df_oper3)
    
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.1 OK ",
                       ))
    print(paste0("Data acquisition 1.1 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.1 FAILED "))
    print(paste0("Data acquisition 1.1 FAILED "))
  },
  # Specifying warning message
  warning = function(w){  
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO, password = pwSYMARO, host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryOper <- paste0("SELECT OPE_ID,OPE_NAME,OPE_COMMENT,OPE_UPD_TIME
                         FROM T_OPERATION")
    dbOper  <- dbGetQuery(con,queryOper)
    dbDisconnect(con)
    
    df_oper <<- dplyr::distinct(dbOper)
    df_oper$OPE_UPD_TIME <- as_datetime(df_oper$OPE_UPD_TIME)
    
    df_oper2 <- df_oper %>% group_by(OPE_NAME) %>% summarise(last_oper=max(OPE_UPD_TIME))
    df_oper3 <- merge(df_oper,df_oper2,by.x=c("OPE_NAME","OPE_UPD_TIME"),by.y=c("OPE_NAME","last_oper"))
    df_oper3 <<- distinct(df_oper3)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.1 WITH WARNINGS "))
    print(paste0("Data acquisition 1.1 WITH WARNINGS "))
  }
  
)

#1.2 Extract Rattachement from Symaro ----

tryCatch(               
  
  # Specifying expression
  expr = {  
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO,password = pwSYMARO,host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryRattachement <- paste0("SELECT RAT_ID,RAT_OPE_ID,RAT_PRODUCT_CODE,RAT_CODETECHNO, RAT_ROUTE_ID,RAT_UPD_TIME
                         FROM T_RATTACHEMENT")
    dbRattachement  <- dbGetQuery(con,queryRattachement)
    dbDisconnect(con)
    
    df_rattachement <<- dplyr::distinct(dbRattachement)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.2 OK ",
    ))
    print(paste0("Data acquisition 1.2 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.2 FAILED "))
    print(paste0("Data acquisition 1.2 FAILED "))
  },
  # Specifying warning message
  warning = function(e){ 
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO,password = pwSYMARO,host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryRattachement <- paste0("SELECT RAT_ID,RAT_OPE_ID,RAT_PRODUCT_CODE,RAT_CODETECHNO, RAT_ROUTE_ID,RAT_UPD_TIME
                         FROM T_RATTACHEMENT")
    dbRattachement  <- dbGetQuery(con,queryRattachement)
    dbDisconnect(con)
    
    df_rattachement <<- dplyr::distinct(dbRattachement)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.2 WITH WARNINGS "))
    print(paste0("Data acquisition 1.2 WITH WARNINGS "))
    
  }
  
)


# 1.3 Extract Destination from Symaro ----

tryCatch(               
  
  # Specifying expression
  expr = {  
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO,password = pwSYMARO,host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryDestination <- paste0("SELECT DEST_ROUTE_ID, DEST_RAT_ID, DEST_ROUTE_DESCRIPTION
                            FROM T_DESTINATION")
    dbDestination  <- dbGetQuery(con,queryDestination)
    dbDisconnect(con)
    
    df_destination <<- dplyr::distinct(dbDestination)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.3 OK "))
    print(paste0("Data acquisition 1.3 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.3 FAILED "))
    print(paste0("Data acquisition 1.3 FAILED "))
  },
  # Specifying warning message
  warning = function(e){ 
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO,password = pwSYMARO,host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryDestination <- paste0("SELECT DEST_ROUTE_ID, DEST_RAT_ID, DEST_ROUTE_DESCRIPTION
                            FROM T_DESTINATION")
    dbDestination  <- dbGetQuery(con,queryDestination)
    dbDisconnect(con)
    
    df_destination <<- dplyr::distinct(dbDestination)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.3 WITH WARNINGS "))
    print(paste0("Data acquisition 1.3 WITH WARNINGS "))
  }
  
)


# 1.4 Extract Route from Symaro----

tryCatch(               
  
  # Specifying expression
  expr = {  
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO,password = pwSYMARO,host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryRoute <- paste0("SELECT RTE_ID, RTE_NAME,RTE_UPD_TIME
                           FROM T_ROUTE")
    dbRoute  <- dbGetQuery(con,queryRoute)
    dbDisconnect(con)
    
    df_route <<- dplyr::distinct(dbRoute)
    df_route$RTE_UPD_TIME <- as_datetime(df_route$RTE_UPD_TIME)
    
    df_route2 <- df_route %>% group_by(RTE_NAME) %>% summarise(last_route=max(RTE_UPD_TIME))
    df_route3 <- merge(df_route,df_route2,by.x=c("RTE_NAME","RTE_UPD_TIME"),by.y=c("RTE_NAME","last_route"))
    df_route3 <<- distinct(df_route3)
    
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.4 OK "))
    print(paste0("Data acquisition 1.4 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.4 FAILED "))
    print(paste0("Data acquisition 1.4 FAILED "))
  },
  # Specifying warning message
  warning = function(e){    
    
    con <-  dbConnect(RMySQL::MySQL(),username = userSYMARO,password = pwSYMARO,host = dsnSYMARO ,port = 3306,dbname = "symaro")
    
    queryRoute <- paste0("SELECT RTE_ID, RTE_NAME,RTE_UPD_TIME
                           FROM T_ROUTE")
    dbRoute  <- dbGetQuery(con,queryRoute)
    dbDisconnect(con)
    
    df_route <<- dplyr::distinct(dbRoute)
    df_route$RTE_UPD_TIME <- as_datetime(df_route$RTE_UPD_TIME)
    
    df_route2 <- df_route %>% group_by(RTE_NAME) %>% summarise(last_route=max(RTE_UPD_TIME))
    df_route3 <- merge(df_route,df_route2,by.x=c("RTE_NAME","RTE_UPD_TIME"),by.y=c("RTE_NAME","last_route"))
    df_route3 <<- distinct(df_route3)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.4 WITH WARNINGS "))
    print(paste0("Data acquisition 1.4 WITH WARNINGS "))
  }
  
)


# 1.5 Extract cp from datamart ----

tryCatch(               
  
  # Specifying expression
  expr = {  
    
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    querydevice <- "SELECT DISTINCT substr(l.mes_lot_id, 1, 2) as product_code, d.device_id FROM  t_lot l join t_device d on l.device_id = d.device_id"
    
    device <- dbSendQuery(Mariacon, querydevice)
    df_device_cp <<- dbFetch(device, n=-1)
    dbClearResult(device)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.5 OK "))
    print(paste0("Data acquisition 1.5 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.5 FAILED "))
    print(paste0("Data acquisition 1.5 FAILED "))
  },
  # Specifying warning message
  warning = function(e){ 
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    querydevice <- "SELECT DISTINCT substr(l.mes_lot_id, 1, 2) as product_code, d.device_id FROM  t_lot l join t_device d on l.device_id = d.device_id"
    
    device <- dbSendQuery(Mariacon, querydevice)
    df_device_cp <<- dbFetch(device, n=-1)
    dbClearResult(device)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.5 WITH WARNINGS "))
    print(paste0("Data acquisition 1.5 WITH WARNINGS "))
  }
  
)



# 1.6 Extract current cp ----


tryCatch(               
  
  # Specifying expression
  expr = {  
    
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    querycp <- "SELECT * FROM t_mes_ref_cp" 
    
    cp <- dbSendQuery(Mariacon, querycp)
    df_from_datamart_cp <<- dbFetch(cp, n=-1)
    dbClearResult(cp)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.6 OK "))
    print(paste0("Data acquisition 1.6 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.6 FAILED "))
    print(paste0("Data acquisition 1.6 FAILED "))
  },
  # Specifying warning message
  warning = function(e){
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    querycp <- "SELECT * FROM t_mes_ref_cp" 
    
    cp <- dbSendQuery(Mariacon, querycp)
    df_from_datamart_cp <<- dbFetch(cp, n=-1)
    dbClearResult(cp)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.6 WITH WARNINGS "))
    print(paste0("Data acquisition 1.6 WITH WARNINGS "))
  }
  
)


# 1.7 Extract current route ----

tryCatch(               
  
  # Specifying expression
  expr = {  
    
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    queryroute <- "SELECT * FROM t_mes_ref_route" 
    
    route <- dbSendQuery(Mariacon, queryroute)
    df_from_datamart_route <<- dbFetch(route, n=-1)
    dbClearResult(route)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.7 OK "))
    print(paste0("Data acquisition 1.7 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.7 FAILED "))
    print(paste0("Data acquisition 1.7 FAILED "))
  },
  # Specifying warning message
  warning = function(e){
    
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    queryroute <- "SELECT * FROM t_mes_ref_route" 
    
    route <- dbSendQuery(Mariacon, queryroute)
    df_from_datamart_route <<- dbFetch(route, n=-1)
    dbClearResult(route)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.7 WITH WARNINGS "))
    print(paste0("Data acquisition 1.7 WITH WARNINGS "))
  }
)


# 1.8 Get data from dmp.t_mes_ref_oper ----


tryCatch(               
  
  # Specifying expression
  expr = { 
    
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    queryemap <- "SELECT operation, route FROM t_mes_ref_oper" 
    
    emap <- dbSendQuery(Mariacon, queryemap)
    df_from_datamart <- dbFetch(emap, n=-1)
    dbClearResult(emap)              
    dbDisconnect(Mariacon)
    
    df_from_datamart <<- unique(df_from_datamart)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.8 OK "))
    print(paste0("Data acquisition 1.8 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.8 FAILED "))
    print(paste0("Data acquisition 1.8 FAILED "))
  },
  # Specifying warning message
  warning = function(e){   
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    queryemap <- "SELECT operation, route FROM t_mes_ref_oper" 
    
    emap <- dbSendQuery(Mariacon, queryemap)
    df_from_datamart <- dbFetch(emap, n=-1)
    dbClearResult(emap)              
    dbDisconnect(Mariacon)
    
    df_from_datamart <<- unique(df_from_datamart)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.8 WITH WARNINGS "))
    print(paste0("Data acquisition 1.8 WITH WARNINGS "))
  }
)


# 1.9 Get data from dmp.t_mes_ref_oper ----

tryCatch(               
  
  # Specifying expression
  expr = {  
    
     Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
     #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
     querydevice <- "SELECT device_id,local_process_family FROM t_device" 
     
     device <- dbSendQuery(Mariacon, querydevice)
     df_device <<- dbFetch(device, n=-1)
     dbClearResult(device)              
     dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 1.9 OK "))
    print(paste0("Data acquisition 1.9 OK"))
  },
  # Specifying error message
  error = function(e){      
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 1.19 FAILED",e))
    print(paste0("Data acquisition 1.9 FAILED",e))
  },
  # Specifying warning message
  warning = function(e){     
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    
    querydevice <- "SELECT device_id,local_process_family FROM t_device" 
    
    device <- dbSendQuery(Mariacon, querydevice)
    df_device <<- dbFetch(device, n=-1)
    dbClearResult(device)              
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 1.9 WITH WARNINGS "))
    print(paste0("Data acquisition 1.9 WITH WARNINGS "))
  }
)





### 2 merge ----

# 2.1 Merge operation from symaro to find alternative routes ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_or <- merge(df_oper,df_rattachement, by.x=c("OPE_ID"),by.y=c("RAT_OPE_ID"))
    
    df_ord <- merge(df_or,df_destination,by.x=c("RAT_ID"),by.y=c("DEST_RAT_ID"))
    
    df_ordr <- merge(df_ord,df_route3,by.x=c("DEST_ROUTE_ID"),by.y=c("RTE_ID"))
    
    df_ordrr <- merge(df_ordr,df_route3,by.x=c("RAT_ROUTE_ID"),by.y=c("RTE_ID"), all.x=TRUE)
    
    df_ordro <- merge(df_from_datamart,df_ordrr,by.x=c("operation"),by.y = c("OPE_NAME"))
    
    df_ordro  <<- df_ordro %>%
      dplyr::filter(RTE_NAME.y == route | is.na(RTE_NAME.y)==TRUE ) %>%
      dplyr::select(operation,route,RTE_NAME.x) %>%
      dplyr::distinct()
    
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.1 OK "))
    print(paste0("Data acquisition 2.1 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.1 FAILED "))
    print(paste0("Data acquisition 2.1 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    
    df_or <- merge(df_oper,df_rattachement, by.x=c("OPE_ID"),by.y=c("RAT_OPE_ID"))
    
    df_ord <- merge(df_or,df_destination,by.x=c("RAT_ID"),by.y=c("DEST_RAT_ID"))
    
    df_ordr <- merge(df_ord,df_route3,by.x=c("DEST_ROUTE_ID"),by.y=c("RTE_ID"))
    
    df_ordrr <- merge(df_ordr,df_route3,by.x=c("RAT_ROUTE_ID"),by.y=c("RTE_ID"), all.x=TRUE)
    
    df_ordro <- merge(df_from_datamart,df_ordrr,by.x=c("operation"),by.y = c("OPE_NAME"))
    
    df_ordro  <<- df_ordro %>%
      dplyr::filter(RTE_NAME.y == route | is.na(RTE_NAME.y)==TRUE ) %>%
      dplyr::select(operation,route,RTE_NAME.x) %>%
      dplyr::distinct()
  
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.1 WITH WARNINGS "))
    print(paste0("Data acquisition 2.1 WITH WARNINGS "))
    
  }
)

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_ordro$alt <- NA
    df_ordro$alt[1] <- 1
    
    length_array <- nrow(df_ordro)
    
    i=2
    while(i<=length_array)
    {
      df_ordro$alt[i] <-  ifelse((df_ordro$operation[i-1] == df_ordro$operation[i] & df_ordro$route[i-1]==df_ordro$route[i]),
                                 df_ordro$alt[i-1]+1,
                                 1)
      i=i+1
    }
    
    df_ordro$alt <- paste0("alt_",df_ordro$alt)
    
    
    df_ordro_l <<- df_ordro %>%
      tidyr::pivot_wider(names_from = alt,
                         values_from = RTE_NAME.x)
    
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.1 alternatives OK "))
    print(paste0("Data acquisition 2.1 alternatives OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.1 alternatives FAILED "))
    print(paste0("Data acquisition 2.1 alternatives FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    df_ordro$alt <- NA
    df_ordro$alt[1] <- 1
    
    length_array <- nrow(df_ordro)
    
    i=2
    while(i<=length_array)
    {
      df_ordro$alt[i] <-  ifelse((df_ordro$operation[i-1] == df_ordro$operation[i] & df_ordro$route[i-1]==df_ordro$route[i]),
                                 df_ordro$alt[i-1]+1,
                                 1)
      i=i+1
    }
    
    df_ordro$alt <- paste0("alt_",df_ordro$alt)
    
    
    df_ordro_l <<- df_ordro %>%
      tidyr::pivot_wider(names_from = alt,
                         values_from = RTE_NAME.x)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.1 alternatives WITH WARNINGS "))
    print(paste0("Data acquisition 2.1 alternatives WITH WARNINGS "))
    
  }
)




# 2.2 Get main routes from t_device ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_device <- df_device  %>% 
      separate(local_process_family, c('process_family', 'Route'))
    
    df_device <- df_device %>%
      mutate(route_1 = paste0(substr(Route,1,2),"00"),
             route_2 = paste0(substr(Route,3,4),"00"),
             route_3 = paste0(substr(Route,5,6),"00")
      )
    
    df_device_l <<- df_device %>%
      tidyr::pivot_longer(cols= starts_with("route_"),
                          names_to="temp",
                          names_prefix ="",
                          names_repair="minimal",
                          values_to = "Routes",
                          values_drop_na = TRUE)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.2 OK "))
    print(paste0("Data acquisition 2.2 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.2 FAILED "))
    print(paste0("Data acquisition 2.2 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    df_device <- df_device  %>% 
      separate(local_process_family, c('process_family', 'Route'))
    
    df_device <<- df_device %>%
      mutate(route_1 = paste0(substr(Route,1,2),"00"),
             route_2 = paste0(substr(Route,3,4),"00"),
             route_3 = paste0(substr(Route,5,6),"00")
      )
    
    df_device_l <- df_device %>%
      tidyr::pivot_longer(cols= starts_with("route_"),
                          names_to="temp",
                          names_prefix ="",
                          names_repair="minimal",
                          values_to = "Routes",
                          values_drop_na = TRUE)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.2 WITH WARNINGS "))
    print(paste0("Data acquisition 2.2 WITH WARNINGS "))
    
  }
)

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_ordro$alt <- NA
    df_ordro$alt[1] <- 1
    
    length_array <- nrow(df_ordro)
    
    i=2
    while(i<=length_array)
    {
      df_ordro$alt[i] <-  ifelse((df_ordro$operation[i-1] == df_ordro$operation[i] & df_ordro$route[i-1]==df_ordro$route[i]),
                                 df_ordro$alt[i-1]+1,
                                 1)
      i=i+1
    }
    
    df_ordro$alt <- paste0("alt_",df_ordro$alt)
    
    
    df_ordro_l <<- df_ordro %>%
      tidyr::pivot_wider(names_from = alt,
                         values_from = RTE_NAME.x)
    
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.1 alternatives OK "))
    print(paste0("Data acquisition 2.1 alternatives OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.1 alternatives FAILED "))
    print(paste0("Data acquisition 2.1 alternatives FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    df_ordro$alt <- NA
    df_ordro$alt[1] <- 1
    
    length_array <- nrow(df_ordro)
    
    i=2
    while(i<=length_array)
    {
      df_ordro$alt[i] <-  ifelse((df_ordro$operation[i-1] == df_ordro$operation[i] & df_ordro$route[i-1]==df_ordro$route[i]),
                                 df_ordro$alt[i-1]+1,
                                 1)
      i=i+1
    }
    
    df_ordro$alt <- paste0("alt_",df_ordro$alt)
    
    
    df_ordro_l <<- df_ordro %>%
      tidyr::pivot_wider(names_from = alt,
                         values_from = RTE_NAME.x)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.1 alternatives WITH WARNINGS "))
    print(paste0("Data acquisition 2.1 alternatives WITH WARNINGS "))
    
  }
)


# 2.3 Get all opers from main route ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_route_oper <<- merge(df_device_l,df_from_datamart,by.x=c("Routes"),by.y=c("route"),all.x=TRUE)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.3 OK "))
    print(paste0("Data acquisition 2.3 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.3 FAILED "))
    print(paste0("Data acquisition 2.3 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    df_route_oper <<- merge(df_device_l,df_from_datamart,by.x=c("Routes"),by.y=c("route"),all.x=TRUE)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.3 WITH WARNINGS "))
    print(paste0("Data acquisition 2.3 WITH WARNINGS "))
    
  }
)


# 2.4 Add alternative route operation ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_route_oper_alt <<- merge(df_route_oper,df_ordro_l,by.x=c("Routes","operation"),by.y=c("route","operation"),all.x=TRUE)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.4 OK "))
    print(paste0("Data acquisition 2.4 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.4 FAILED "))
    print(paste0("Data acquisition 2.4 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    df_route_oper_alt <<- merge(df_route_oper,df_ordro_l,by.x=c("Routes","operation"),by.y=c("route","operation"),all.x=TRUE)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.4 WITH WARNINGS "))
    print(paste0("Data acquisition 2.4 WITH WARNINGS "))
    
  }
)

# 2.5 Prepare merged table with main and alt ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    df_route_oper_alt_l <- df_route_oper_alt %>%
      tidyr::pivot_longer(cols= starts_with("alt_"),
                          names_to="tempo",
                          names_prefix ="",
                          names_repair="minimal",
                          values_to = "alt",
                          values_drop_na = TRUE)
    
    df_route_oper_alt_l <- df_route_oper_alt_l %>%
      dplyr::select(process_family, Routes, device_id, alt)
    
    df_principal <- df_route_oper_alt_l %>%
      select(process_family, Routes,device_id) %>%
      distinct %>%
      mutate(Type="Main") %>%
      transmute(process_family=process_family,
                route=Routes,
                device_id=device_id,
                type=Type)
    
    df_alternative <- df_route_oper_alt_l %>%
      select(process_family,alt, device_id) %>%
      distinct() %>%
      mutate(Type="Alternative") %>%
      transmute(process_family=process_family,
                device_id=device_id,
                route=alt,
                type=Type)
    
    df_final <- rbind(df_principal,df_alternative)
    
    df_final <<- df_final %>%
      dplyr::mutate(process_family= ifelse(is.na(process_family)==TRUE,"MISC",process_family))
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.5 OK "))
    print(paste0("Data acquisition 2.5 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.5 FAILED "))
    print(paste0("Data acquisition 2.5 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    df_route_oper_alt_l <- df_route_oper_alt %>%
      tidyr::pivot_longer(cols= starts_with("alt_"),
                          names_to="tempo",
                          names_prefix ="",
                          names_repair="minimal",
                          values_to = "alt",
                          values_drop_na = TRUE)
    
    df_route_oper_alt_l <- df_route_oper_alt_l %>%
      dplyr::select(process_family, Routes, device_id, alt)
    
    df_principal <- df_route_oper_alt_l %>%
      select(process_family, Routes,device_id) %>%
      distinct %>%
      mutate(Type="Main") %>%
      transmute(process_family=process_family,
                route=Routes,
                device_id=device_id,
                type=Type)
    
    df_alternative <- df_route_oper_alt_l %>%
      select(process_family,alt, device_id) %>%
      distinct() %>%
      mutate(Type="Alternative") %>%
      transmute(process_family=process_family,
                device_id=device_id,
                route=alt,
                type=Type)
    
    df_final <- rbind(df_principal,df_alternative)
    
    df_final <<- df_final %>%
      dplyr::mutate(process_family= ifelse(is.na(process_family)==TRUE,"MISC",process_family))
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.5 WITH WARNINGS "))
    print(paste0("Data acquisition 2.5 WITH WARNINGS "))
    
  }
)



# 2.6 Get new references ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    #Get new cp/device couple
    df_new_cp <<- dplyr::anti_join(df_device_cp,df_from_datamart_cp,by=c("product_code","device_id"))
    
    #Get new cp/device couple
    df_new_route <<- dplyr::anti_join(df_final,df_from_datamart_route,by=c("process_family","device_id","route","type"))
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 2.6 OK "))
    print(paste0("Data acquisition 2.6 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 2.6 FAILED "))
    print(paste0("Data acquisition 2.6 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    #Get new cp/device couple
    df_new_cp <<- dplyr::anti_join(df_device_cp,df_from_datamart_cp,by=c("product_code","device_id"))
    
    #Get new cp/device couple
    df_new_route <<- dplyr::anti_join(df_final,df_from_datamart_route,by=c("process_family","device_id","route","type"))
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 2.6 WITH WARNINGS "))
    print(paste0("Data acquisition 2.6 WITH WARNINGS "))
    
  }
)


### 3 Load datamart ----
# 3.1 Load t_mes_ref_route ----

tryCatch(
  
  # Specifying expression
  expr = {
    
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    dbWriteTable(
      Mariacon,
      SQL('t_mes_ref_route'),
      df_new_route,
      field.types = NULL,
      row.names = FALSE,
      overwrite = FALSE,
      append = TRUE,
      temporary = FALSE
    )
    
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 3.1 OK "))
    print(paste0("Data acquisition 3.1 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 3.1 FAILED "))
    print(paste0("Data acquisition 3.1 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){ 
    
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    dbWriteTable(
      Mariacon,
      SQL('t_mes_ref_route'),
      df_new_route,
      field.types = NULL,
      row.names = FALSE,
      overwrite = FALSE,
      append = TRUE,
      temporary = FALSE
    )
    
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 3.1 WITH WARNINGS "))
    print(paste0("Data acquisition 3.1 WITH WARNINGS "))
    
  }
)


# 3.2 Load t_mes_ref_cp----

tryCatch(
  
  # Specifying expression
  expr = {
    
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    dbWriteTable(
      Mariacon,
      SQL('t_mes_ref_cp'),
      df_new_cp,
      field.types = NULL,
      row.names = FALSE,
      overwrite = FALSE,
      append = TRUE,
      temporary = FALSE
    )
    
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=0")
    print("RETURNCODE=0")
    info(logger,paste0("Data acquisition 3.2 OK "))
    print(paste0("Data acquisition 3.2 OK"))
  },
  # Specifying error message
  error = function(e){
    info(logger,"RETURNCODE=2")
    print("RETURNCODE=2")
    info(logger,paste0("Data acquisition 3.2 FAILED "))
    print(paste0("Data acquisition 3.2 FAILED "))
  },
  
  # Specifying warning message
  warning = function(e){     
    #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmp', host='maxscale',port=as.integer(4306))
    dbWriteTable(
      Mariacon,
      SQL('t_mes_ref_cp'),
      df_new_cp,
      field.types = NULL,
      row.names = FALSE,
      overwrite = FALSE,
      append = TRUE,
      temporary = FALSE
    )
    
    dbDisconnect(Mariacon)
    
    info(logger,"RETURNCODE=1")
    print("RETURNCODE=1")
    info(logger,paste0("Data acquisition 3.2 WITH WARNINGS "))
    print(paste0("Data acquisition 3.2 WITH WARNINGS "))
    
  }
)

lapply(dbListConnections( dbDriver( drv = "MySQL")), dbDisconnect)