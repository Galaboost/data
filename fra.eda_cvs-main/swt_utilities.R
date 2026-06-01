
#======================================================================#  
#
# Program name : swt_utilities.R 
# Author       : Aurelie Uemura 
# Description  : 
# /home/auemura@xfab.ads/scripts/swt/eda_csv
#......................................................................
# Used R version v 
# platform       x86_64-redhat-linux-gnu     
# version.string R version 3.6.1 (2019-07-05)
#......................................................................
#                         Log for Changes 
# 2021-11-26 v1.6 
#......................................................................
# # Clean envi, plots, console 
# rm(list=ls())
# if(!is.null(dev.list())) dev.off()
# cat("\014") 



# 0 Generic ---------------------------------------------------------

#' sql_dbprod
#' A function to send SQL query in DBPROD 
#' 
#' @param str_query 
#' @param conid credentials list 
#'
#' @import RODBC 
#' 
#' @return
#' @export
#'
sql_dbprod <- function( str_query ,conid){
  con <- RODBC::odbcConnect(dsn = conid$dbprod$dsn, uid = conid$dbprod$user, pwd = conid$dbprod$pw)
  df<- RODBC::sqlQuery(con, str_query, stringsAsFactors=F)
  RODBC::odbcCloseAll() 
  return(df)
}




#' sql_dmp
#' A function to send SQL query in dmp DataMart 
#' 
#' @param str_query 
#' @param conid credentials list
#'
#' @import RMariaDB
#' 
#' @return
#' @export
#'
sql_dmp <- function( str_query ,conid){
  con <- RMariaDB::dbConnect(RMariaDB::MariaDB(), host=conid$dmp$host, dbname =conid$dmp$db,
                             user=conid$dmp$user, password=conid$dmp$pw, port = conid$dmp$port )
  dbsend  <- RMariaDB::dbSendQuery(con, str_query, stringsAsFactors=F)
  df <- RMariaDB::dbFetch(dbsend )
  RMariaDB::dbClearResult(dbsend )
  RMariaDB::dbDisconnect(con)
  
  return(df)
}



#1 get data ---- 

#' get_swt_profiles
#' A fucntion to get profiles npnpid, version, from dmp maps swt profiles 
#' 
#' @param conid credentials 
#'
#' @return
#' @export
#'
#' @import dplyr 
#' @import stringr 
#' 
#' 
#' dependencies 
#' sql_dmp 
#' 
get_swt_profiles <- function(conid){
  str_sql <- "SELECT profile_name,selected_npnpid,selected_version
  FROM  t_profile_maps_master " 
  df <- df <- sql_dmp(str_query = str_sql , conid = conid)
  
  # Add techno as First Word in profile_names 
  #   and remove duplicates rows 
  df <- df %>% 
    dplyr::mutate(techno =  stringr::str_extract(profile_name, "[:alnum:]*" ) ) %>% 
    dplyr::rename(npnpid  = selected_npnpid, 
                  version = selected_version ) %>% 
    dplyr::select(techno, npnpid, version ) %>% 
    dplyr::distinct() %>% 
    dplyr::arrange(techno, npnpid,version)
  
  # Return
  return(df)
}


#' get_address
#' get adresses in EDA_PUBLIC by techno 
#' 
#' @param str_techno string techno 
#' @param str_root
#'
#' @import dplyr 
#' 
#' @return
#' @export
#'
#' 
get_address <- function(str_techno, str_root= root_address){
  
  vec_setup <-  c("AH018", "C10N",  "C11N",  
      "T18AL", "T18B",  "T18RF", "T18SO",
      "XH018", "XP018", "XR013", "XT011","XT018"
    ) 
  
  dtr <- dplyr::tribble(
    ~techno  , ~file , 
    #--------, ------, 
    "AH018"  , "FWT_AH18" , 
    "C10N"   , "FWT_C10",
    "C11N"   , "FWT_C11",
    "T18AL"  , "FWT_SOI", 
    "T18B"   , "FWT_T18B",    
    "T18RF"  , "FWT_T18RF",
    "T18SO"  , "FWT_SOI", 
    "XH018"  , "FWT_XH018", 
    "XP018"  , "FWT_XP018",
    "XR013"  , "FWT_XR013",
    "XT011"  , "FWT_XT011", 
    "XT018"  , "FWT_XT018"
  )
  
  
  # Test if the techno in vec_setup 
  if ( str_techno %in% vec_setup){
    
    str_file <- dtr %>% 
      dplyr::filter(techno == str_techno )%>% 
      dplyr::select(file) %>% 
      pull()
    
    str_address = paste0(str_root,str_file)
    return(str_address)

  } else{
      return(paste("Error - Techno repository not defined :", str_techno ) ) 
    }
  
  
}




#' get_pmax
#' Function to define max nparam for SQL in DBPROD for swt data 
#' By default, the function returns  "12000" , 
#' For T18SO, it returns "10000" 
#' @param str_techno  a string for technology 
#'
#' @return
#' @export
#'
get_pmax <- function(str_techno ){
 
  if (str_techno %in% c("T18SO")){
    return("10000")
  }else{
    return("12000")
  }
  
}


#' get_nparam
#' A function to return a string of  NPARAM by techno 
#'  eg "10001,10002,10003,10004,10005" 
#' It is used for T18RF, XH018, XT018, XP018 
#' not generic nparam for T18SO (cf f_param_list)
#' 
#' @param str_techno a string for the techno 
#'
#' @return
#' @export
#'
get_nparam <- function(str_techno) {
  nparam ="none"
  
  if (str_techno =="T18RF") {
    nparam=paste0(
      "10691,10692,10693,10595,10596,10597,10598,10599,10000,",
      "10001,10002,10003,10004,10005,10006,10007,10008,10009,10015,10017,",
      "10026,10027,10028,10029,10030,10037,10063,10064,10072,10074,10080,10327"  )  
  } else if (str_techno %in% c("XH018","XT018")) { 
    nparam=paste0(
      "10691,10695,10696,10697,10698,10699,",
      "10000,", 
      "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,",
      "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,",
      "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,",
      "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,",
      "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050 ", 
      "10051,10052,10053,10054,10055,10056,10057,10058,10059,10060 " 
    )
  } else if (str_techno == "AH018") {
    nparam=paste0(
      "10691,10695,10696,10697,10698,10699,",
      "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,",
      "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,",
      "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,",
      "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,",
      "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050 ", 
      "10051,10052,10053,10054,10055,10056,10057,10058,10059,10060 ",
      "10061,10062,10063,10064,10065,10066,10067,10068,10069,10070 ",
      "10099"
    )
  }  else if(str_techno =="XP018"){
    nparam=paste0(
      "10691,10695,10696,10697,10698,10699,",
      "10001,10002,10003,10004,10005,10006,10007,10008,10009,",
      "10010,10011,10012,10013,10015,10016,10017,10018,10019,10021,",
      "10022,10025,10026,10028,10029,10032,10033,10035,10036,10057,10058,",
      "10060,10062,10063,10064,10099"
    )
  }   else if(str_techno =="XR013"){
  nparam=paste0(
    "10691,10695,10696,10697,10698,10699,",
    "10001,10002,10003,10004,10005,10006,10007,10008,10009,",
    "10010,10032, 10035"
  )
} else{ 
    nparam=paste0(
      "10691,10695,10696,10697,10698,10699,",
      "10000,", 
      "10001,10002,10003,10004,10005,10006,10007,10008,10009,10010,",
      "10011,10012,10013,10014,10015,10016,10017,10018,10019,10020,",
      "10021,10022,10023,10024,10025,10026,10027,10028,10029,10030,",
      "10031,10032,10033,10034,10035,10036,10037,10038,10039,10040,",
      "10041,10042,10043,10044,10045,10046,10047,10048,10049,10050 ") 
    
  }
  
  # Return
  return(nparam)
}


#' f_param_list
#' A function to get nparam available in DBPROD for a SWT couple of npnpid-version 
#' It is used to get all available NPARAM for T18SO 
#' 
#' @param fstr_npnpid a string for npnpid eg. "7740" 
#' @param fstr_version a string for version eg. "1" 
#' @param conid a list with credentials 
#' 
#' @importFrom glue glue
#' @import RODBC
#'
#' @return a string of nparam eg."10001,10002" 
#' @export
f_param_list <- function(fstr_npnpid, fstr_version , conid) {
  
  # SQL 
  dbquery_param <- glue::glue( 
    "SELECT nparam 
    FROM DBPROD.T_TPARAMF  
    WHERE  npnpid = '{npnpid}' 
    AND version = '{version}' " , 
    npnpid = fstr_npnpid,
    version = fstr_version
  ) 
  
  con_PROD <- RODBC::odbcConnect(dsn = "DBPROD", uid = conid$dbprod$user , pwd = conid$dbprod$pw )
  df_param <- RODBC::sqlQuery(con_PROD, dbquery_param, stringsAsFactors=F, as.is=T)
  RODBC::odbcCloseAll() 
  
  str_nparam <- paste0( df_param$NPARAM, collapse="," ) 
  
  return(str_nparam)
}

# 2 Get lot and wafer data -----

#' f_update_data_lot 
#' a function to get SWT lot data from DBPROD on list of nparam 
#' and for a specific time period
#'
#' @param fstr_address the fileshare address to drop the csv file 
#' @param fstr_npnpid a string with npnpid for the SQL query eg. "7740"
#' @param fstr_version a string with the version for the SQL query eq."1" 
#' @param fstr_nparam a string with the nparameter for the SQL query eg. "10000,10010" 
#' @param fstr_pmax a string for pmax 
#' @param fstr_date1 a string for starting date eg. "'2021-10-01'"
#' @param fstr_date2 a string for ending date eg. "'2021-11-01'"
#' @param fstr_logfile the address for the log file 
#' @param conid a list with credential for DB access 
#' 
#' @import RODBC 
#' @import log4r 
#' @importFrom stringr str_replace_all
#' @importFrom glue glue 
#' @import RODBC 
#' @importFrom plyr rbind.fill
#' @import dplyr 
#' @importFrom tidyr pivot_wider
#' @importFrom data.table fread fwrite
#' @importFrom stringr str_trim str_remove_all
#' 
#' @return
#' @export
f_update_data_lot <- function(fstr_address, fstr_npnpid, fstr_version ,  
                             fstr_nparam,  fstr_pmax,  
                             fstr_date1, fstr_date2, fstr_logfile, conid ){
  
  logger <- log4r::logger("INFO", appenders = file_appender(fstr_logfile) )

  # # manual test 
  # fstr_address = str_address ;  fstr_npnpid= str_npnpid ; fstr_version = str_version 
  # fstr_nparam  =   str_nparam ; fstr_pmax =  str_pmax 
  # fstr_date1=xstr_date1 ;fstr_date2=xstr_date2 ;fstr_logfile= xFile  
  # conid=conid
  
  # 1 Create variable for SQL WHERE  ----
  str_nparam_char <- stringr::str_replace_all(fstr_nparam,",","','") 
  str_nparam_char <- paste0 ("'",str_nparam_char,"'")


  # 2 SQL from DBPROD with generic account   ----
  # Define SQL Query on DBPROD.T_TLOTPARF 
  dbquery_p <- glue::glue(
    "SELECT a.nlocfab,a.ddtest,a.npnpid,a.version,a.nparam,a.qvl50pc as value,
    substr(t.tparam,1,35)  as tparam 
    FROM (DBPROD.T_TLOTPARF  as a 
    INNER JOIN  DBPROD.T_TPARAMF AS t ON
      (a.npnpid=t.npnpid and a.version=t.version  and a.nparam =t.nparam)  )
    WHERE a.npnpid = '{npnpid}'
    AND a.version =  '{version}'
    AND a.nparam in ({nparam})
    AND (a.NLOCFAB ) in (SELECT NLOCFAB FROM  DBPROD.T_TLOTPNPF  
      WHERE  npnpid = '{npnpid}' AND version = '{version}' 
      AND ddtest >= {date1} AND ddtest <= {date2} ) ", 
    npnpid = fstr_npnpid ,
    version = fstr_version, 
    nparam = str_nparam_char,
    date1 = fstr_date1 , 
    date2 = fstr_date2
  ) 
  
  # Define SQL Query on DBPROD.T_TLOTYLDF - yield parameters 
  dbquery_y <- glue::glue(
    "SELECT  a.nlocfab,a.ddtest,a.npnpid,a.version,a.nparam,a.qyield as value,
    substr(t.tparam,1,35)  as tparam 
    FROM (DBPROD.T_TLOTYLDF AS a 
    INNER JOIN  DBPROD.T_TPARAMF AS t ON
      (a.npnpid=t.npnpid and a.version=t.version  and a.nparam =t.nparam)  )
    WHERE a.npnpid = '{npnpid}'
    AND a.version = '{version}'
    AND a.nparam in ({nparam})
    AND (a.NLOCFAB ) in (SELECT NLOCFAB FROM  DBPROD.T_TLOTPNPF  
      WHERE  npnpid = '{npnpid}' AND version = '{version}' 
      AND ddtest >= {date1} AND ddtest <= {date2} ) ", 
    npnpid = fstr_npnpid ,
    version = fstr_version, 
    nparam = str_nparam_char,
    date1 = fstr_date1 , 
    date2 = fstr_date2
  ) 

  # Query SQL 
  con_PROD <- RODBC::odbcConnect(dsn = "DBPROD", uid = conid$dbprod$user, pwd = conid$dbprod$pw)
    df_p <- RODBC::sqlQuery(con_PROD, dbquery_p, stringsAsFactors=FALSE, as.is=TRUE)
    df_y <- RODBC::sqlQuery(con_PROD, dbquery_y, stringsAsFactors=FALSE, as.is=TRUE)
  RODBC::odbcCloseAll() 
  
  
  # 3 Transform ----
  # Bind row for yield and parametric dataframes  
  if (nrow(df_p) >0 & nrow(df_y)>0 ){
    df <- plyr::rbind.fill(df_p, df_y )
  } else if (nrow(df_p) >0 & nrow(df_y)==0  ) {
    df <- df_p
  } else if (nrow(df_p) == 0 & nrow(df_y)>0  ) {
    df <- df_y
  } else {
    df <-data.frame()
  }
  
  if (nrow(df) >0){
  # Mutate tparam and transpose 
  df <- df %>% 
    dplyr::mutate( 
      TPARAM = dplyr::if_else( 
        NPARAM < fstr_pmax,
        paste0("t",stringr::str_trim(NPARAM),"_", stringr::str_remove_all(TPARAM, " ")), 
        stringr::str_trim(TPARAM)) ,
      NLOCFAB = stringr::str_trim(NLOCFAB), 
      NPNPID = stringr::str_trim(NPNPID), 
      VERSION = stringr::str_trim(VERSION))

  # Transpose 
  df_tr <- df  %>%  
    dplyr::arrange(TPARAM) %>% 
    tidyr::pivot_wider( id_cols = -c(NPARAM) , names_from = TPARAM, values_from = VALUE)
  
  # Modify DDTEST 
  df_tr  <- df_tr %>% 
    dplyr::mutate(DDTEST = as.character(DDTEST)) %>% 
    dplyr::mutate( 
      DDTEST = ifelse(grepl("^[0-9]$", substr(DDTEST,3,3) ) ==F ,
                      paste0(substr(DDTEST,7,10), "-", substr(DDTEST,4,5) , "-", substr(DDTEST,1,2) )  , 
                      DDTEST ))
  
  # create liste of lots 
  x_lot = unique(df$NLOCFAB)
  
  
  
  #4. Get archive data 
  str_archive_file = paste0(fstr_address,"/db",fstr_npnpid,"l.csv")
  #test is csv file already exist 
  boo_exist = file.exists(str_archive_file)
  
  if (boo_exist) { # if archive csv file exists 
    #4.1.2 load archive 
    df_archive <- data.table::fread(str_archive_file, sep = ",", header= TRUE )
    
    
    #4.1.1 convert ddtest in str and verify formation yyyy-mm-dd 
    df_archive <- df_archive %>% 
      dplyr::mutate(DDTEST = as.character(DDTEST)) %>% 
      dplyr::mutate( 
        DDTEST = ifelse(grepl("^[0-9]$", substr(DDTEST,3,3) ) ==F ,
        paste0(substr(DDTEST,7,10), "-", substr(DDTEST,4,5) , "-", substr(DDTEST,1,2) )  , 
        DDTEST ))
    
    #4.1.3 Compare lotids 
    x_lotarchive <- unique(df_archive$NLOCFAB)
    x_lotdiff <- setdiff(x_lot, x_lotarchive)
    log4r::info(logger, paste("Number of  new lots : " , length(x_lotdiff))  ) 
    
    #4.1.4  row bind 
      df_all <- rbind.fill(df_archive, df_tr) 
      
 
      
      
      
      # Distinct to remove duplications 
      df_all <- df_all %>% 
        dplyr::distinct() %>% 
        dplyr::arrange(DDTEST, NLOCFAB) %>% 
        dplyr::group_by(NLOCFAB ) %>% 
        dplyr::filter(DDTEST == max(DDTEST)) %>% 
        dplyr::ungroup()
    
      # Export  in csv 
      str_new_file = paste0(fstr_address,"/db",fstr_npnpid,"l.csv")
      
      data.table::fwrite(df_all,file=str_new_file)
      
      # Write in log 
      log4r::info(logger,"write update csv with new data -->> END of f_update_data_lot  " )

    
  }  else {   #else if  archive csv do not exist - case of new npnpid  
    df_all <- df_tr %>% 
      dplyr::distinct() %>% 
      dplyr::arrange(DDTEST, NLOCFAB)
    
    x_lotdiff <- nrow(df_all$NLOCFAB %>% unique() ) 
    
    # Write in log the number of new lots 
    log4r::info(logger, paste("Number of  new lots : " , length(x_lotdiff))  ) 
    
    # Export  in csv 
    str_new_file <- paste0(fstr_address,"/db",fstr_npnpid,"l.csv")
    data.table::fwrite(df_all,file=str_new_file)
    
    # Write in log 
    log4r::info(logger,"write update csv with new data -->> END of f_update_data_lot  " )
  }

  }
}
# # variables for test 
# fstr_address = xstr_address
# fstr_npnpid = xstr_npnpid
# fstr_version = xstr_version
# fstr_nparam = xstr_nparam
# fstr_pmax = xstr_pmax
# fstr_date1 = xstr_date1
# fstr_date2 = xstr_date2
# fstr_logfile = xFile




#' f_update_data_wafer
#' a function to get SWT wafer data from DBPROD on list of nparam 
#' and for a specific time period
#' 
#' @param fstr_address the fileshare address to drop the csv file 
#' @param fstr_npnpid a string with npnpid for the SQL query eg. "7740"
#' @param fstr_version a string with the version for the SQL query eq."1" 
#' @param fstr_nparam a string with the nparameter for the SQL query eg. "10000,10010" 
#' @param fstr_pmax a string for pmax 
#' @param fstr_date1 a string for starting date eg. "'2021-10-01'"
#' @param fstr_date2 a string for ending date eg. "'2021-11-01'"
#' @param fstr_logfile the address for the log file 
#' @param conid a list with credential for DB access 
#' 
#' @import RODBC 
#' @import log4r 
#' @importFrom stringr str_replace_all
#' @importFrom glue glue 
#' @import RODBC 
#' @importFrom plyr rbind.fill
#' @import dplyr 
#' @importFrom tidyr pivot_wider
#' @importFrom data.table fread fwrite
#' @importFrom stringr str_trim str_remove_all
#' 
#'
#' @return
#' @export
#'
f_update_data_wafer <- function(fstr_address, fstr_npnpid, fstr_version ,
                               fstr_nparam,  fstr_pmax,  fstr_date1, fstr_date2, 
                               fstr_logfile, conid  ){

  logger <- log4r::logger("INFO", appenders = file_appender(fstr_logfile) )
  
  #1 Create variable for SQL WHERE  ----
  str_nparam_char <-stringr::str_replace_all(fstr_nparam,",","','") 
  str_nparam_char <- paste0 ("'",str_nparam_char,"'")
  
  
  #2 SQL from DBPROD with generic account   ----
  dbquery_p <- glue::glue(  
  "SELECT a.nlocfab,a.ntranch, a.ddtest,a.npnpid,a.version,a.nparam,a.qvl50pc as value,
    substr(t.tparam,1,35)  as tparam 
    FROM (DBPROD.T_TTRCPARF  AS a 
    INNER JOIN  DBPROD.T_TPARAMF AS t ON
      (a.npnpid=t.npnpid and a.version=t.version  and a.nparam =t.nparam)  )
    WHERE a.npnpid = '{npnpid}'
    AND a.version =  '{version}'
    AND a.nparam in ({nparam})
    AND (a.NLOCFAB ) in (SELECT NLOCFAB FROM  DBPROD.T_TLOTPNPF  
      WHERE  npnpid = '{npnpid}' AND version = '{version}' 
      AND ddtest >= {date1} AND ddtest <= {date2} ) ", 
  npnpid = fstr_npnpid ,
  version = fstr_version, 
  nparam = str_nparam_char,
  date1 = fstr_date1 , 
  date2 = fstr_date2
  )
  
  dbquery_y <- glue::glue(  
    "SELECT  a.nlocfab,a.ntranch, a.ddtest,a.npnpid,a.version,a.nparam,a.qyield as value,
    substr(t.tparam,1,35)  as tparam 
    FROM (DBPROD.T_TTRCYLDF AS a 
    INNER JOIN  DBPROD.T_TPARAMF AS t ON
      (a.npnpid=t.npnpid and a.version=t.version  and a.nparam =t.nparam)  )
    WHERE a.npnpid = '{npnpid}'
    AND a.version =  '{version}'
    AND a.nparam in ({nparam})
    AND (a.NLOCFAB ) in (SELECT NLOCFAB FROM  DBPROD.T_TLOTPNPF  
      WHERE  npnpid = '{npnpid}' AND version = '{version}' 
      AND ddtest >= {date1} AND ddtest <= {date2} ) ", 
    npnpid = fstr_npnpid ,
    version = fstr_version, 
    nparam = str_nparam_char,
    date1 = fstr_date1 , 
    date2 = fstr_date2
  )

  # Load credential 
  con_PROD <- RODBC::odbcConnect(dsn = "DBPROD", uid = conid$dbprod$user , pwd = conid$dbprod$pw)
    df_p <- RODBC::sqlQuery(con_PROD, dbquery_p, stringsAsFactors=F, as.is=T)
    df_y <- RODBC::sqlQuery(con_PROD, dbquery_y, stringsAsFactors=F, as.is=T)
  RODBC::odbcCloseAll() 
  
  #3 Transform ----
  #3.1 bind row for yield and parametric dataframes 
  
  if (nrow(df_p) >0 & nrow(df_y)>0 ){
    df <- plyr::rbind.fill(df_p, df_y )
  } else if (nrow(df_p) >0 & nrow(df_y)==0  ) {
    df <- df_p
  } else if (nrow(df_p) == 0 & nrow(df_y)>0  ) {
    df <- df_y
  } else {
    df <-data.frame()
  }
  
  if (nrow(df)>0){
  #3.2 mutate tparam and transpose 
  df <- df %>% 
    dplyr::mutate( 
      TPARAM = dplyr::if_else( 
        NPARAM < fstr_pmax,
        paste0("t",stringr::str_trim(NPARAM),"_", stringr::str_remove_all(TPARAM, " ")), 
        stringr::str_trim(TPARAM)),
      NLOCFAB = stringr::str_trim(NLOCFAB), 
      NTRANCH = stringr::str_trim(NTRANCH), 
      NPNPID = stringr::str_trim(NPNPID), 
      VERSION = stringr::str_trim(VERSION))
  
 
  
  x_lot <- unique(df$NLOCFAB)
  log4r::info(logger, paste("nb of lots ",  length(x_lot) )) 
  
  #3.3 transpose 
  df_tr <- df  %>%  
    dplyr::arrange(TPARAM) %>% 
    tidyr::pivot_wider( id_cols = -c(NPARAM) , names_from = TPARAM, values_from = VALUE)

  # Modify DDTEST formation 
  df_tr  <- df_tr %>% 
    dplyr::mutate(DDTEST = as.character(DDTEST)) %>% 
    dplyr::mutate( 
      DDTEST = ifelse(grepl("^[0-9]$", substr(DDTEST,3,3) ) ==F ,
                      paste0(substr(DDTEST,7,10), "-", substr(DDTEST,4,5) , "-", substr(DDTEST,1,2) )  , 
                      DDTEST ))
  
  
  
  
  #4. Get archive data 
  str_archive_file = paste0(fstr_address,"/db",fstr_npnpid,"w.csv")
  
  #test is csv file already exist 
  boo_exist = file.exists(str_archive_file)
  
  
  if (boo_exist) { # if there is archive csv file 
    # Load archive 
    df_archive <- data.table::fread(str_archive_file, sep = ",", header= TRUE )
    
    # Convert ddtest in str and verify format  yyyy-mm-dd 
    df_archive <- df_archive %>% 
      dplyr::mutate(DDTEST = as.character(DDTEST)) %>% 
      dplyr::mutate( 
        DDTEST = ifelse(grepl("^[0-9]$", substr(DDTEST,3,3) ) ==F ,
                        paste0(substr(DDTEST,7,10), "-", substr(DDTEST,4,5) , "-", substr(DDTEST,1,2) )  , 
                        DDTEST ))
    
    # Compare lotids 
    x_lotarchive <- unique(df_archive$NLOCFAB)
    x_lotdiff <- setdiff(x_lot, x_lotarchive)
    log4r::info(logger, paste("Number of new lots detected : " , length(x_lotdiff))  ) 

    # Row bind 
    df_all <- plyr::rbind.fill(df_archive, df_tr)
  
    # Distinct to remove duplications 
    df_all <- df_all %>% 
      dplyr::distinct() %>% 
      dplyr::group_by(NLOCFAB, NTRANCH) %>% 
      dplyr::filter(DDTEST == max(DDTEST)) %>% 
      dplyr::arrange(DDTEST, NLOCFAB,NTRANCH) %>% 
      dplyr::ungroup()
      
    # Export  in csv 
    str_new_file = paste0(fstr_address,"/db",fstr_npnpid,"w.csv")
    data.table::fwrite(df_all,file=str_new_file)
    
    log4r::info(logger,"end write csv update -->> END of f_update_data_wafer  " )

  } else{
    #else if there is not archive - new pnpid case 
    df_all <-  df_tr %>% 
      dplyr::distinct() %>% 
      dplyr::arrange(DDTEST, NLOCFAB)
    
    x_lotdiff <- nrow(df_all$NLOCFAB %>% unique() )  
    
    # Write in log numboer of new lots 
    log4r::info(logger, paste("Number of  new lots  : " , length(x_lotdiff))  ) 
    
    # Export  in csv 
    str_new_file = paste0(fstr_address,"/db",fstr_npnpid,"w.csv")
    
    # info(logger, paste("start write csv in  ",str_new_file ))
    data.table::fwrite(df_all,file=str_new_file)
    
    log4r::info(logger,"write update csv with new data -->> END of f_update_data_lot  " )
  }
  }
}



#' f_update_allgood_wafer 
#'
#' A function de make a subset of waf csv with only all good data 
#' and save it in EDA_PUBLIC fileshare 
#'
#' @param fstr_address 
#' @param fstr_npnpid 
#'
#' @import dplyr 
#' @importFrom data.table fwrite fread 
#'
#' @return
#' @export
#'
f_update_allgood_wafer <- function(fstr_address, fstr_npnpid){ 
  # Load wafer csv 
  # Keep only NPNPID	DDTEST	NLOCFAB	NTRANCH	AllGood
  str_waf_csv <- paste0(fstr_address,"/db",fstr_npnpid,"w.csv")
  
  df <- data.table::fread(file=str_waf_csv , stringsAsFactors = FALSE)  %>% 
    dplyr::select(NPNPID,	DDTEST,	NLOCFAB,	NTRANCH,	AllGood) 
  
  # Write in EDA 
  str_new_file = paste0(fstr_address,"/db",fstr_npnpid,"wb.csv")
  
  # info(logger, paste("start write csv in  ",str_new_file ))
  data.table::fwrite(df ,file=str_new_file)

  }


# ( str_address, str_npnpid)



#3 ----
#' f_convert_sas_to_csv
#'
#' @param fstr_address a string with directory address 
#' @param fstr_filename a sas file 
#'
#' @import haven 
#' @import dplyr 
#' @importFrom  data.table fwrite 
#' @return
#' @export
#'
f_convert_sas_to_csv <- function(fstr_address, fstr_filename){
  
  # Get archive data 
  str_file <- paste0(fstr_address,"/",fstr_filename,".sas7bdat")
  df <- haven::read_sas(str_file )
  
  # Remove label and format.sas  
  attr(df,"label") <- NULL 
  attr(df$NLOCFAB,"label") <- NULL 
  attr(df$DDTEST,"label") <- NULL 
  attr(df$NPNPID,"label") <- NULL 
  attr(df$VERSION,"label") <- NULL 
  
  attr(df$NLOCFAB,"format.sas") <- NULL
  attr(df$DDTEST,"format.sas") <- NULL
  attr(df$NPNPID,"format.sas") <- NULL
  attr(df$VERSION,"format.sas") <- NULL
  
  df <- df %>% 
    dplyr::mutate(DDTEST = as.character(DDTEST))

  # Export  in csv "
  str_new_file <- paste0(fstr_address,"/",fstr_filename,".csv")
  data.table::fwrite(df,file=str_new_file)

}




