#=====================================================================#  
#                                                                     #
# Program name : DBILTR_to_datamart_pcm_ref.R                         #
# Description  :                                                      #
#    Program to Load in datamart dmp new PCM reference                #
#                                                                     #
# Author       :  Corentin Bresselle & Aurelie Uemura                 #                                                                    
# Version      :  v3,                                                 #   
#                                                                     #
#                                                                     #  
#=====================================================================# 
#                      Content                                        #
# 0. Initialization                                                   # 
# 1. Settings                                                         # 
# 2. Add new references                                               #
#=====================================================================# 
#                      Log History                                     
# 2020-02-25 Aurelie Uemura : initial version 
# 2020-03-04 AU - change table name 
# 2020-05-05 v1.1 AU - change datamart from dmd to dmp 
# 2020-05-14 v2.1 AU  - check available npnpid 
# 2020-10-30 v2.2 AU 
#            - change user for datamart dmp from appdatamart to refpcmswt 
#            - remove object at k loop step to avoid writing in dmp with previous dataframes or scalar selection 
#            - anti date 1 year for date insertion 
#            - add manually ref_param_id 
# 2021-05-14 v2.3 AU 
#            - 1.1 change 'now() %m-% months(12)' to 'now() - days(365)'
#             xDateX = paste0("'",as.character(today() - days(7)),"'") -> todays - days(7)
#            - replace paste by glue for SQL queries 
# 2021-06-22 v3.0 CB
#            - Add update
#=====================================================================# 

# 0. Initialization  ==================================================
  # Clean envi, plots, console 
  rm(list=ls())
  if(!is.null(dev.list())) dev.off()
  cat("\014") 

  # Version 
  xstr_version = "v.3.0"

  # Set configuration and credentials  
  source("~/etl_ref_pcm/etc/config_file.R")


  # Load Library 
  library(RMariaDB)          #v1.0.7
  library(RODBC)             #v1.3.16
  library(dplyr)             #v1.0.5     
  library(data.table)        #v1.13.2
  library(lubridate)         #v1.7.4
  library(tidyr)             #v1.0.0
  library(stringr)           #v1.4.0
  library(log4r, warn.conflicts = FALSE,quietly = TRUE)    #v0.3.2
  library(utils)             #v3.6.1
  library(glue)              #v1.4.1
  library(DBI)               #v1.0.0

  source("~/scripts/autoexec.R")

  xstr_version = "v.3.0"
  
  res=TRUE

  # set Dates & logs
  xdatetime = now() - days(365)
  xstr_now= str_replace_all( now(),  c(" " = "_", "-" = "", ":"=""))
  xstr_Date0 = str_replace_all( as.character(today()),"-","")
  xDateX = today() - days(45)

  xFile=paste0(log_directory, "log_" ,xstr_now,".txt" ) 
  file.create(xFile)
  log_file <- xFile
  logger <- log4r::logger("INFO", appenders = file_appender(log_file) )

  info(logger, paste("DBILTR_to_datamart_pcm_ref.R - version",xstr_version   , "- new search of reference to load  ")) 


# 1 Extract master references ----
  # 1.1 Extract data from DBPROD.T_TLOTNPI ----

    query  <-glue::glue (" SELECT NLOCFAB, NPNPID, VERSION, CPROD, DDTEST 
                           FROM  DBPROD.T_TLOTPNPI
                           WHERE DDTEST >= '{date_start}'" ,
                        date_start= xDateX ) 

    con_DBPROD = RODBC::odbcConnect(dsn = "DBPROD", uid = userDBPROD, pwd = pwDBPROD)
    df_npnpid_prod_xd_lot <- RODBC::sqlQuery(con_DBPROD, query, stringsAsFactors=FALSE)
    RODBC::odbcCloseAll()

    df_npnpid_prod_xd = df_npnpid_prod_xd_lot %>%
    dplyr::mutate(npnp_id = as.integer(NPNPID),
                  version= as.integer(VERSION)) %>%
    dplyr::select(npnp_id ) %>%
    dplyr::distinct()
    
    if(res==TRUE)
    {
      if(nrow(df_npnpid_prod_xd)==0)
      {
        error=function(e){paste("ERROR FOUND ON DBPROD", e)}
        res=FALSE
      }
    }


  # 1.2 Extract data from t_pcm_ref_master ----

    dbquery  <-"select * from t_pcm_ref_master" 

    con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    dbsend  <- RMariaDB::dbSendQuery(con, dbquery )
    df_ref_master <- RMariaDB::dbFetch(dbsend )
    RMariaDB::dbClearResult(dbsend )
    RMariaDB::dbDisconnect(con)
    
    if(res==TRUE)
    {
      if(nrow(df_ref_master)==0)
      {
        error=function(e){paste("ERROR FOUND ON dmp", e)}
        res=FALSE
      }
    }

  # 1.3 Get new and update references ----
    # 1.3.1 Get new npnp_id ----
      df_npnpid_ref_xd = df_ref_master %>%
      dplyr::select(npnp_id ) %>%
      dplyr::distinct()

      df_new_npnpid <- dplyr::anti_join(df_npnpid_prod_xd,df_npnpid_ref_xd ,by=c("npnp_id"))

    #1.3.2 Build new and updated references fron npnp_id ----


      conISIS = RODBC::odbcConnect(dsn = dsnDBISIS, uid = userDBISIS, pwd = pwDBISIS)

      kxlist_npnp_id <- toString(sprintf("'%s'", df_npnpid_ref_xd[,'npnp_id']))

      get_pcm_ref_master_references <- function(npnp_id_list,reftable,programme_version,datetime,conISIS)
      {
        kdf_tpr <- data.frame(NULL)
  
  
        query <- glue::glue ("SELECT NPNPID as npnp_id, TECHNO as isis_techno, TPR as isis_tpr FROM DBILTR.T_TPR 
                              WHERE NPNPID IN ({npnpid}) " ,
                              npnpid = as.character(npnp_id_list)) 
  
        conISIS
        kdf_tpr = RODBC::sqlQuery(conISIS, query, stringsAsFactors=F)
        odbcCloseAll()
        
        
        if(res==TRUE)
        {
          if(nrow(kdf_tpr)==0)
          {
            error=function(e){paste("ERROR FOUND ON DBILTR NPNPID TECHNO", e)}
            res=FALSE
          }
        }
        
  
  
        colnames(kdf_tpr) <- tolower(colnames(kdf_tpr))
  
        kdf_tpr$load_file_name = "DBILTR_sql"
  
        kdf_tpr$comment=paste(kdf_tpr$isis_techno,kdf_tpr$isis_tpr, kdf_tpr$npnp_id,"- load with DBILTR_to_datamart_pcm_ref.R version ",programme_version) 
  
        kdf_tpr$pcm_ref_fra_datetime = datetime
  
        kdf_tpr <- kdf_tpr[c("npnp_id","pcm_ref_fra_datetime","load_file_name","comment","isis_techno","isis_tpr")]
  
  
        if(!is.null(reftable))
        {
          ref_pcm_ref_master <-  dplyr::anti_join(kdf_tpr,reftable,by=c("npnp_id","isis_techno","isis_tpr")) 
        }
  
        else
        {
          ref_pcm_ref_master <- kdf_tpr
        }
  
        return(ref_pcm_ref_master)
      }

      updated_reference_master_from_master <- get_pcm_ref_master_references(kxlist_npnp_id,df_ref_master,xstr_version,xdatetime,conISIS)
      df_ref_master <- subset(df_ref_master,select=c(pcm_ref_id,npnp_id))
      updated_reference_master_from_master <- merge(updated_reference_master_from_master,df_ref_master,by=c("npnp_id"))
      updated_reference_master_from_master <- updated_reference_master_from_master[c("pcm_ref_id","npnp_id","pcm_ref_fra_datetime","load_file_name","comment","isis_techno","isis_tpr")]

      kxlist_new_npnp_id <- toString(sprintf("'%s'", df_new_npnpid[,'npnp_id']))

      conISIS = RODBC::odbcConnect(dsn = dsnDBISIS, uid = userDBISIS, pwd = pwDBISIS)


      if(kxlist_new_npnp_id!="")
      {
        created_reference_master_from_master <- get_pcm_ref_master_references(kxlist_new_npnp_id ,NULL,xstr_version,xdatetime,conISIS)
      }else
      {
        created_reference_master_from_master <- data.frame(matrix(ncol=6,nrow=0))
        colnames(created_reference_master_from_master) <- c('npnp_id','pcm_ref_fra_datetime','load_file_name','comment','isis_techno','isis_tpr')
      }

      #View(updated_reference_master_from_master)
      #View(created_reference_master_from_master)

  #1.4 Load references ----
    # 1.4.1 Load new references to Datamart ----

      #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
      Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
      dbWriteTable(
      Mariacon,
      SQL('t_pcm_ref_master'),
      created_reference_master_from_master,
      field.types = NULL,
      row.names = FALSE,
      overwrite = FALSE,
      append = TRUE,
      temporary = FALSE
      )

      dbDisconnect(Mariacon)



    #1.4.2 Load updated references to Datamart ----

    #Define the number of reference to update

    df_max <- updated_reference_master_from_master %>% group_by() %>% summarise(var_max=n())
    var_max <- as.integer(df_max$var_max)

    if(var_max>0)
    {
      # # Define the loop to update each ret one by one
      i=1
      for (i in 1:var_max)
      {
        #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
        Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
        query_update_t_pcm_ref_master <- paste0("UPDATE `dmp`.`t_pcm_ref_master` 
                                                SET `pcm_ref_fra_datetime`='",updated_reference_master_from_master$pcm_ref_fra_datetime[i],"',
                                                `load_file_name`='",updated_reference_master_from_master$load_file_name[i],"',
                                                `comment`='",updated_reference_master_from_master$comment[i],"', 
                                                `isis_techno`='",updated_reference_master_from_master$isis_techno[i],"',
                                                `isis_tpr`='",updated_reference_master_from_master$isis_tpr[i],"'
                                                 WHERE `pcm_ref_id`=",updated_reference_master_from_master$pcm_ref_id[i]," 
                                                 AND `npnp_id`=",updated_reference_master_from_master$npnp_id[i],"
                                                 ") 
    
        df_t_pcm_ref_master_update <- dbSendQuery(Mariacon, query_update_t_pcm_ref_master)
        df_t_pcm_ref_master_update_to_datamart <- dbFetch(df_t_pcm_ref_master_update, n=-1)
        dbClearResult(df_t_pcm_ref_master_update)              
        dbDisconnect(Mariacon)
      }
    }


###################################################################################################################################################################################################################  

# 2 Extract parameter references ----
  #2.1 Extract data from t_pcm_ref_param ----

    query_param <- "SELECT a.pcm_ref_id,a.npnp_id,a.isis_techno,a.isis_tpr,b.ref_param_id,b.parameter_id,b.parameter_name,b.unit,b.pcm_group,b.merge_type,b.process_option,b.module,b.pcell,b.slm,b.npnp_id2,b.parameter_id2,b.parameter_name2,b.unit2,b.reptseq,b.report_variable 
                    FROM t_pcm_ref_master a left join t_pcm_ref_param b on a.pcm_ref_id=b.pcm_ref_id" 
    #con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    dbsend  <- RMariaDB::dbSendQuery(con, query_param)
    kdf_refparam <- RMariaDB::dbFetch(dbsend) 
    RMariaDB::dbClearResult(dbsend )
    RMariaDB::dbDisconnect(con)

    if(res==TRUE)
    {
      if(nrow(kdf_refparam)==0)
      {
        error=function(e){paste("ERROR FOUND ON DMP REF", e)}
        res=FALSE
      }
    }


    #Check if unique keys in DB
    df_test <- subset(kdf_refparam,select=c(npnp_id,pcm_ref_id,parameter_id))

    tot <- nrow(df_test)

    df_test2 <- unique(df_test)

    tot2 <- nrow(df_test2)

    tot
    tot2

    #Convert data to get a common formate between R and SQL result

    kdf_refparam <- kdf_refparam %>% dplyr::mutate(parameter_name=replace_na(parameter_name,""),
                                                  unit=replace_na(unit,""),
                                                  pcm_group=replace_na(pcm_group,""),
                                                  merge_type=replace_na(merge_type,""),
                                                  process_option=replace_na(process_option,""),
                                                   module=replace_na(module,""),
                                                  pcell=replace_na(pcell,""),
                                                  slm=replace_na(slm,""),
                                                  npnp_id2=replace_na(npnp_id2,""),
                                                  parameter_name2=replace_na(parameter_name2,""),
                                                  unit2=replace_na(unit2,""),
                                                  report_variable=replace_na(report_variable,"")
                                                  )



  #2.2 Get data from DBILTR


    #Prepare list of techno and tpr available in pcm_ref_master
    ref_master_1 <- subset(kdf_refparam ,select=c(pcm_ref_id,npnp_id,isis_techno,isis_tpr))
    ref_master_1 <- distinct(ref_master_1)

    kxchar_TECHNO <- toString(sprintf("'%s'", unique(ref_master_1[,'isis_techno'])))
    kxchar_TPR <- toString(sprintf("'%s'", unique(ref_master_1[,'isis_tpr'])))

    #Get data from DB
    query_param = glue::glue(
      "SELECT TECHNO as isis_techno,
       TPR as isis_tpr,
       NPARAM as parameter_id, 
       DESC_PARAM as parameter_name, 
       UNIT as unit, 
       GROUP as pcm_group,  
       MERGE_TYPE as merge_type, 
       REPORT as process_option,
       MODULE_LIST as module,
       PRIMITIVE_DEVICE as pcell,
       SLM as slm,
       STAT_HR as npnp_id2,
       STAT_ALARM as parameter_id2,
       F_DTS as parameter_name2,
       AFFICHAGE as unit2, 
       F_PARAM as reptseq,
       REPORT_VAR1 as report_variable 
       FROM  DBILTR.T_PARAM 
       WHERE TECHNO  IN ({techno}) 
       AND TPR IN ({tpr}) "
      , 
      techno = kxchar_TECHNO, 
      tpr = kxchar_TPR
      )

    conISIS = RODBC::odbcConnect(dsn = dsnDBISIS, uid = userDBISIS, pwd = pwDBISIS)
    kdf_param = RODBC::sqlQuery(conISIS, query_param, stringsAsFactors=F, as.is=T)
    RODBC::odbcCloseAll()
    
    if(res==TRUE)
    {
      if(nrow(kdf_param)==0)
      {
        error=function(e){paste("ERROR FOUND ON DBILTR REF", e)}
        res=FALSE
      }
    }


    # Convert variable names in lowcase 
    colnames(kdf_param) =tolower(colnames(kdf_param) )

    #Convert data to get a common formate between R and SQL result
    kdf_param <- kdf_param %>% dplyr::mutate(parameter_name=replace_na(parameter_name,""),
                                            unit=replace_na(unit,""),
                                            pcm_group=replace_na(pcm_group,""),
                                            merge_type=replace_na(merge_type,""),
                                            process_option=replace_na(process_option,""),
                                            module=replace_na(module,""),
                                            pcell=replace_na(pcell,""),
                                            slm=replace_na(slm,""),
                                            npnp_id2=replace_na(npnp_id2,""),
                                            parameter_id2=as.integer(parameter_id2),
                                            parameter_name2=replace_na(parameter_name2,""),
                                            unit2=replace_na(unit2,""),
                                            report_variable=replace_na(report_variable,"")
                                            )


  #2.3 Get new and updated references  ----

    #Get npnp_id from previous references thanks to t_pcm_ref_master
    kdf_param_npnpid <- merge(kdf_param,ref_master_1,by=c("isis_techno","isis_tpr"))
    kdf_param_npnp_id <- distinct(kdf_param_npnpid)

    #Define merge_type
    kdf_param_npnp_id <- kdf_param_npnp_id %>% 
    dplyr::mutate(merge_type = if_else( is.na(merge_type)==T, "GROUPE", merge_type),
                  parameter_id2 = if_else( stringr::str_detect(parameter_id2,"\\D")==T ,
                                         NA_integer_, as.integer(parameter_id2)))


    #Get new parameter_id not in dmp.t_pcm_ref_param
    kdf_new_param <- anti_join(kdf_param_npnp_id,kdf_refparam,by=c("npnp_id","isis_techno","isis_tpr","parameter_id"))
    kdf_new_param <- subset(kdf_new_param,select=-c(npnp_id,isis_techno,isis_tpr))

    kdf_new_param <- kdf_new_param[c("pcm_ref_id","parameter_id","parameter_name","unit","pcm_group","merge_type","process_option","module","pcell","slm","npnp_id2","parameter_id2","parameter_name2","unit2","reptseq","report_variable")]

    #Delete spaces in the two tables before merging
    kdf_param_npnp_id<-kdf_param_npnp_id %>% dplyr::mutate(parameter_name=trimws(parameter_name,"both"),
                                                          unit=trimws(unit,"both"),
                                                          pcm_group=trimws(pcm_group,"both"),
                                                          merge_type=trimws(merge_type,"both"),
                                                          process_option=trimws(process_option,"both"),
                                                          module=trimws(module,"both"),
                                                          pcell=trimws(pcell,"both"),
                                                          slm=trimws(slm,"both"),
                                                          npnp_id2=trimws(npnp_id2,"both"),
                                                          parameter_name2=trimws(parameter_name2,"both"),
                                                          unit2=trimws(unit2,"both"),
                                                          report_variable=trimws(report_variable,"both"))

    kdf_refparam <- kdf_refparam %>% dplyr::mutate(parameter_name=trimws(parameter_name,"both"),
                                                  unit=trimws(unit,"both"),
                                                  pcm_group=trimws(pcm_group,"both"),
                                                  merge_type=trimws(merge_type,"both"),
                                                  process_option=trimws(process_option,"both"),
                                                  module=trimws(module,"both"),
                                                  pcell=trimws(pcell,"both"),
                                                  slm=trimws(slm,"both"),
                                                  npnp_id2=trimws(npnp_id2,"both"),
                                                  parameter_name2=trimws(parameter_name2,"both"),
                                                  unit2=trimws(unit2,"both"),
                                                  report_variable=trimws(report_variable,"both"))



    #Compare result between DBILTR and dmp to get updated references
    kdf_updated_param <- anti_join(kdf_param_npnp_id,kdf_refparam,by=c("npnp_id","isis_techno","isis_tpr","parameter_id","parameter_name","unit","pcm_group","merge_type","process_option","module","pcell","slm","npnp_id2","parameter_id2","parameter_name2","unit2","reptseq","report_variable"))
    kdf_updated_param <- subset(kdf_updated_param,select=-c(npnp_id,isis_techno,isis_tpr))
    kdf_updated_param <- kdf_updated_param[c("pcm_ref_id","parameter_id","parameter_name","unit","pcm_group","merge_type","process_option","module","pcell","slm","npnp_id2","parameter_id2","parameter_name2","unit2","reptseq","report_variable")]


    #Remove new parameter from previous table to get only existing updated parameters
    kdf_updated_param <- anti_join(kdf_updated_param,kdf_new_param,by=c("pcm_ref_id","parameter_id","parameter_name","unit","pcm_group","merge_type","process_option","module","pcell","slm","npnp_id2","parameter_id2","parameter_name2","unit2","reptseq","report_variable"))

    kdf_refparam <- subset(kdf_refparam,select=c(ref_param_id,pcm_ref_id,parameter_id))


    #Check the number of updated param compare to references
    xint_ref_param <- nrow(kdf_refparam)
    xint_ref_updated_param <- nrow(kdf_updated_param)

    xint_ref_param
    xint_ref_updated_param


    #Get ref_param_id of already existing parameter (unique key of table)
    kdf_updated_param <- merge(kdf_updated_param,kdf_refparam,by=c("pcm_ref_id","parameter_id"))

    xint_ref_param
    xint_ref_updated_param


    #Prepare columns for loading
    kdf_updated_param <- kdf_updated_param[c("ref_param_id","pcm_ref_id","parameter_id","parameter_name","unit","pcm_group","merge_type","process_option","module","pcell","slm","npnp_id2","parameter_id2","parameter_name2","unit2","reptseq","report_variable")]



    #Prepare variables to be compatible with SQL Update request
    kdf_updated_param <- kdf_updated_param %>% dplyr::mutate(parameter_name=replace_na(parameter_name,""),
                                                            unit=replace_na(unit,""),
                                                            pcm_group=replace_na(pcm_group,""),
                                                            merge_type=replace_na(merge_type,""),
                                                            process_option=replace_na(process_option,""),
                                                            module=replace_na(module,""),
                                                            pcell=replace_na(pcell,""),
                                                            slm=replace_na(slm,""),
                                                            npnp_id2=replace_na(npnp_id2,""),
                                                            parameter_id2 = replace_na(parameter_id2,"NULL"),
                                                            parameter_name2=replace_na(parameter_name2,""),
                                                            unit2=replace_na(unit2,""),
                                                            reptseq=replace_na(reptseq,"NULL"),
                                                            report_variable=replace_na(report_variable,"")
                                                            )




    #View(kdf_new_param)
    #View(kdf_updated_param)

  #2.4 Load params ----
    # 2.4.1 Load new param to Datamart ----

     # Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    dbWriteTable(
                  Mariacon,
                  SQL('t_pcm_ref_param'),
                  kdf_new_param,
                  field.types = NULL,
                  row.names = FALSE,
                  overwrite = FALSE,
                  append = TRUE,
                  temporary = FALSE
                  )

      dbDisconnect(Mariacon)


      #2.4.2 Load updated param to Datamart ----
      
        # Define the number of reference to update
          df_max <- kdf_updated_param %>% group_by() %>% summarise(var_max=n())
          var_max <- as.integer(df_max$var_max)

          if(var_max>0)
          {
            # Define the loop to update each ret one by one
            i=1
            for (i in 1:var_max)
            {
              #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
              Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
              query_update_t_pcm_ref_param <- paste("UPDATE `dmp`.`t_pcm_ref_param`",
                                                    "SET `parameter_name`='",kdf_updated_param$parameter_name[i],"',",
                                                    "`unit`='",kdf_updated_param$unit[i],"',",
                                                    "`pcm_group`='",kdf_updated_param$pcm_group[i],"',",
                                                    "`merge_type`='",kdf_updated_param$merge_type[i],"',",
                                                    "`process_option`='",kdf_updated_param$process_option[i],"',",
                                                    "`module`='",kdf_updated_param$module[i],"',",
                                                    "`pcell`='",kdf_updated_param$pcell[i],"',",
                                                    "`slm`='",kdf_updated_param$slm[i],"',",
                                                    "`npnp_id2`='",kdf_updated_param$npnp_id2[i],"',",
                                                    "`parameter_id2`=",kdf_updated_param$parameter_id2[i],",",
                                                    "`parameter_name2`='",kdf_updated_param$parameter_name2[i],"',",
                                                    "`unit2`='",kdf_updated_param$unit2[i],"',",
                                                    "`reptseq`=",kdf_updated_param$reptseq[i],",",
                                                    "`report_variable`='",kdf_updated_param$report_variable[i],"'",
                                                     "WHERE `ref_param_id`=",kdf_updated_param$ref_param_id[i],"",
                                                    "AND `pcm_ref_id`=",kdf_updated_param$pcm_ref_id[i],"",
                                                    "AND `parameter_id`=",kdf_updated_param$parameter_id[i],"",
                                                    "")
    
              df_t_pcm_ref_param_update <- dbSendQuery(Mariacon, query_update_t_pcm_ref_param)
              df_t_pcm_ref_param_update_to_datamart <- dbFetch(df_t_pcm_ref_param_update, n=-1)
              dbClearResult(df_t_pcm_ref_param_update)
              dbDisconnect(Mariacon)
            }
          }




####################################################################################################################################################################################################################  

# 3 Extract parameter spec ----
  #3.1 Extract data from t_pcm_ref_spec ----

    query_spec <- "SELECT a.pcm_ref_id,a.npnp_id,a.isis_techno,a.isis_tpr,b.ref_param_id,b.parameter_id,c.ref_param_version_id,c.version,c.lsl,c.usl,c.low_control_limit,c.high_control_limit,c.low_cens_limit,c.high_cens_limit,c.lsl3,c.usl3,c.target,c.type,c.cr,c.cpk_flag
                  FROM (t_pcm_ref_master a left join t_pcm_ref_param b on a.pcm_ref_id=b.pcm_ref_id) left join t_pcm_ref_spec c on b.ref_param_id=c.ref_param_id"


    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmd', host='mariadb-d1lx',port=as.integer(3306))
    dbsend  <- RMariaDB::dbSendQuery(con, query_spec)
    kdf_ref_spec <- RMariaDB::dbFetch(dbsend) 
    RMariaDB::dbClearResult(dbsend )
    RMariaDB::dbDisconnect(con)

    kdf_ref_spec <- distinct(kdf_ref_spec)
    
    if(res==TRUE)
    {
      if(nrow(kdf_ref_spec)==0)
      {
        error=function(e){paste("ERROR FOUND ON DMP REF PEC", e)}
        res=FALSE
      }
    }


    #3.2 Extract data from dbiltr ----


    ref_param_1 <- subset(kdf_ref_spec ,select=c(ref_param_id,parameter_id,npnp_id,isis_techno,isis_tpr))
    ref_param_1 <- distinct(ref_param_1)

    kxchar_TECHNO <- toString(sprintf("'%s'", unique(ref_param_1[,'isis_techno'])))
    kxchar_TPR <- toString(sprintf("'%s'", unique(ref_param_1[,'isis_tpr'])))

    query = glue::glue(
      "SELECT lm.NPARAM as parameter_id , lm.VERSION as version,  
      lm.LSP1 as lsl, 
      lm.HSP1 as usl, 
      lm.LSP2 as low_control_limit, 
      lm.HSP2 as high_control_limit, 
      lm.LCS as low_cens_limit, 
      lm.HCS as high_cens_limit, 
      lm.LSP3 as lsl3, 
      lm.HSP3 as usl3, 
      lm.TARGET as target, 
      lm.TYPE as type, 
      lm.CR_CODE as cr, 
      pa.F_CPK as cpk_flag, 
      lm.TPR as isis_tpr,
      lm.TECHNO as isis_techno
      FROM (DBILTR.T_LIMITS lm 
         INNER JOIN DBILTR.T_PARAM pa on (lm.TPR= pa.TPR and lm.TECHNO=pa.TECHNO and lm.NPARAM = pa.NPARAM )  )   
      WHERE lm.TECHNO IN ({techno}) 
      AND lm.TPR IN ({tpr})", 
      techno = kxchar_TECHNO, 
      tpr = kxchar_TPR 
    ) 

    conISIS = RODBC::odbcConnect(dsn = dsnDBISIS, uid = userDBISIS, pwd = pwDBISIS)
    kdf_spec= RODBC::sqlQuery(conISIS, query, stringsAsFactors=F)
    RODBC::odbcCloseAll()
    
    if(res==TRUE)
    {
      if(nrow(kdf_spec)==0)
      {
        error=function(e){paste("ERROR FOUND ON DBILTR REF SPEC", e)}
        res=FALSE
      }
    }

    # conversion on variable names in lowcase 
    colnames(kdf_spec) =tolower(colnames(kdf_spec) )

    # Get nnp_id,isis_techno,isis_tpr list
    query_npnp_id <- "SELECT npnp_id,isis_techno,isis_tpr
   FROM t_pcm_ref_master"
    
    
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmd', host='mariadb-d1lx',port=as.integer(3306))
    dbsend  <- RMariaDB::dbSendQuery(con, query_npnp_id)
    kdf_ref_npnp_id <- RMariaDB::dbFetch(dbsend) 
    RMariaDB::dbClearResult(dbsend )
    RMariaDB::dbDisconnect(con)
    
    kdf_ref_npnp_id <- distinct(kdf_ref_npnp_id)
    
    if(res==TRUE)
    {
      if(nrow(kdf_ref_npnp_id)==0)
      {
        error=function(e){paste("ERROR FOUND ON NPNPID FOR REF SPEC", e)}
        res=FALSE
      }
    }
    
    #3.3 Get new and updated spec ----
    
    kdf_spec$parameter_id <- trimws(kdf_spec$parameter_id,"both")
    kdf_spec$isis_techno <- trimws(kdf_spec$isis_techno,"both")
    kdf_spec$isis_tpr<- trimws(kdf_spec$isis_tpr,"both")
    
    kdf_ref_spec$parameter_id <- trimws(kdf_ref_spec$parameter_id,"both")
    kdf_ref_spec$isis_techno <- trimws(kdf_ref_spec$isis_techno,"both")
    kdf_ref_spec$isis_tpr<- trimws(kdf_ref_spec$isis_tpr,"both")
    
    kdf_spec <- merge(kdf_spec,kdf_ref_npnp_id,by=c("isis_tpr","isis_techno"))

    #Compare data from dbiltr and dmp to get new ones on key parameters
    kdf_new_spec <- anti_join(kdf_spec,kdf_ref_spec,by=c("npnp_id","parameter_id","isis_techno","isis_tpr","version"))
    kdf_new_spec <- kdf_new_spec[c("npnp_id","isis_techno","isis_tpr","parameter_id","version","lsl","usl","low_control_limit","high_control_limit","low_cens_limit","high_cens_limit","lsl3","usl3","target","type","cr","cpk_flag")]

    kdf_new_spec <- distinct(kdf_new_spec)

    #Get parameters references from dmp
    query_param <- "SELECT a.isis_techno,a.isis_tpr,a.npnp_id,b.ref_param_id,b.parameter_id from t_pcm_ref_master a left join t_pcm_ref_param b on a.pcm_ref_id=b.pcm_ref_id"

    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmd', host='mariadb-d1lx',port=as.integer(3306))
    dbsend  <- RMariaDB::dbSendQuery(con, query_param)
    kdf_ref_param <- RMariaDB::dbFetch(dbsend) 
    RMariaDB::dbClearResult(dbsend )
    RMariaDB::dbDisconnect(con)

    kdf_ref_param <- distinct(kdf_ref_param)
    
    if(res==TRUE)
    {
      if(nrow(kdf_ref_param)==0)
      {
        error=function(e){paste("ERROR FOUND ON PARAM FOR REF SPEC", e)}
        res=FALSE
      }
    }

    #View(kdf_ref_param)

    #Prepare data for merging
    kdf_new_spec$parameter_id <- as.numeric(kdf_new_spec$parameter_id)

    #Merge new spec with parameters references from dmp
    kdf_new_spec <- merge(kdf_new_spec,kdf_ref_param,by=c("isis_techno","isis_tpr","npnp_id","parameter_id"),all.x=TRUE)


    #Prepare variables for merging
    kdf_spec$cpk_flag <- as.character(kdf_spec$cpk_flag)
    kdf_ref_spec$cpk_flag <- as.character(kdf_ref_spec$cpk_flag)

    kdf_ref_spec <- kdf_ref_spec %>% dplyr::mutate(lsl=replace_na(lsl,"NULL"),
                                                  usl=replace_na(usl,"NULL"),
                                                  low_control_limit=replace_na(low_control_limit,"NULL"),
                                                  high_control_limit=replace_na(high_control_limit,"NULL"),
                                                  low_cens_limit=replace_na(low_cens_limit,"NULL"),
                                                  high_cens_limit=replace_na(high_cens_limit,"NULL"),
                                                  lsl3=replace_na(lsl3,"NULL"),
                                                  usl3=replace_na(usl3,"NULL"),
                                                  target=replace_na(target,"NULL"),
                                                  type = replace_na(type,""),
                                                  cr=replace_na(cr,"NULL"),
                                                  cpk_flag=replace_na(cpk_flag,"")
                                                  )

    kdf_spec <- kdf_spec %>% dplyr::mutate(lsl=replace_na(lsl,"NULL"),
                                          usl=replace_na(usl,"NULL"),
                                          low_control_limit=replace_na(low_control_limit,"NULL"),
                                          high_control_limit=replace_na(high_control_limit,"NULL"),
                                          low_cens_limit=replace_na(low_cens_limit,"NULL"),
                                          high_cens_limit=replace_na(high_cens_limit,"NULL"),
                                          lsl3=replace_na(lsl3,"NULL"),
                                          usl3=replace_na(usl3,"NULL"),
                                          target=replace_na(target,"NULL"),
                                          type = replace_na(type,""),
                                          cr=replace_na(cr,"NULL"),
                                          cpk_flag=replace_na(cpk_flag,"")
                                          )

    #Get updated spec by comparing dbiltr and dmp to see if change
    kdf_updated_spec <- anti_join(kdf_spec,kdf_ref_spec,by=c("npnp_id","parameter_id","isis_techno","isis_tpr","version","lsl","usl","low_control_limit","high_control_limit","low_cens_limit","high_cens_limit","lsl3","usl3","target","type","cr","cpk_flag"))
    kdf_updated_spec <- kdf_updated_spec[c("npnp_id","isis_techno","isis_tpr","parameter_id","version","lsl","usl","low_control_limit","high_control_limit","low_cens_limit","high_cens_limit","lsl3","usl3","target","type","cr","cpk_flag")]

    #Prepare new spec for anti-join
    kdf_new_spec2 <- kdf_new_spec %>% dplyr::mutate(lsl=replace_na(lsl,"NULL"),
                                                    usl=replace_na(usl,"NULL"),
                                                    low_control_limit=replace_na(low_control_limit,"NULL"),
                                                    high_control_limit=replace_na(high_control_limit,"NULL"),
                                                    low_cens_limit=replace_na(low_cens_limit,"NULL"),
                                                    high_cens_limit=replace_na(high_cens_limit,"NULL"),
                                                    lsl3=replace_na(lsl3,"NULL"),
                                                    usl3=replace_na(usl3,"NULL"),
                                                    target=replace_na(target,"NULL"),
                                                    type = replace_na(type,""),
                                                    cr=replace_na(cr,"NULL"),
                                                    cpk_flag=replace_na(cpk_flag,"")
                                                    )


    #Takeout new spec from comparison to get only updated spec
    kdf_updated_spec <- anti_join(kdf_updated_spec,kdf_new_spec2,by=c("npnp_id","isis_techno","isis_tpr","version","lsl","usl","low_control_limit","high_control_limit","low_cens_limit","high_cens_limit","lsl3","usl3","target","type","cr","cpk_flag"))

    kdf_updated_spec <- distinct(kdf_updated_spec)

    #Get ref_param_version id for updated spec
    query_param2 <- "SELECT a.isis_techno,a.isis_tpr,a.npnp_id,b.ref_param_id,b.parameter_id,c.ref_param_version_id,c.version from (t_pcm_ref_master a left join t_pcm_ref_param b on a.pcm_ref_id=b.pcm_ref_id) left join t_pcm_ref_spec c on b.ref_param_id=c.ref_param_id"

    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmd', host='mariadb-d1lx',port=as.integer(3306))
    dbsend  <- RMariaDB::dbSendQuery(con, query_param2)
    kdf_ref_param2 <- RMariaDB::dbFetch(dbsend) 
    RMariaDB::dbClearResult(dbsend )
    RMariaDB::dbDisconnect(con)

    kdf_ref_param <- distinct(kdf_ref_param2)
    
    if(res==TRUE)
    {
      if(nrow(kdf_ref_param)==0)
      {
        error=function(e){paste("ERROR FOUND ON PARAM FOR REF SPEC", e)}
        res=FALSE
      }
    }

    #Merge updated spec with ref_param_version_id reference from dmp
    kdf_updated_spec <- merge(kdf_updated_spec,kdf_ref_param2,by=c("npnp_id","isis_techno","isis_tpr","parameter_id","version"),all.x=TRUE)

    #Prepare tables for loading
    kdf_updated_spec <- kdf_updated_spec[c("ref_param_version_id","ref_param_id","version","lsl","usl","low_control_limit","high_control_limit","low_cens_limit","high_cens_limit","lsl3","usl3","target","type","cr","cpk_flag")]
    kdf_new_spec <- kdf_new_spec[c("ref_param_id","version","lsl","usl","low_control_limit","high_control_limit","low_cens_limit","high_cens_limit","lsl3","usl3","target","type","cr","cpk_flag")]

    kdf_updated_spec <- unique(kdf_updated_spec)
    kdf_new_spec <- unique(kdf_new_spec)

    #Take out references from parameters not in the datamart
    kdf_new_spec <- kdf_new_spec %>% filter(!is.na(ref_param_id))

    #Prepare references for SQL Update request
    kdf_updated_spec <- kdf_updated_spec %>% dplyr::mutate(lsl=replace_na(lsl,"NULL"),
                                                          usl=replace_na(usl,"NULL"),
                                                          low_control_limit=replace_na(low_control_limit,"NULL"),
                                                          high_control_limit=replace_na(high_control_limit,"NULL"),
                                                          low_cens_limit=replace_na(low_cens_limit,"NULL"),
                                                          high_cens_limit=replace_na(high_cens_limit,"NULL"),
                                                          lsl3=replace_na(lsl3,"NULL"),
                                                          usl3=replace_na(usl3,"NULL"),
                                                          target=replace_na(target,"NULL"),
                                                          type = replace_na(type,""),
                                                          cr=replace_na(cr,"NULL"),
                                                          cpk_flag=replace_na(cpk_flag,"")
                                                          )
    kdf_new_spec <- unique(kdf_new_spec)
    
    #View(kdf_new_spec)
    #View(kdf_updated_spec)


  # 3.4 Load spec ----
    # 3.4.1 Load new spec to Datamart ----

     # Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
    Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
    dbWriteTable(
                  Mariacon,
                  SQL('t_pcm_ref_spec'),
                  kdf_new_spec,
                  field.types = NULL,
                  row.names = FALSE,
                  overwrite = FALSE,
                  append = TRUE,
                  temporary = FALSE
                  )

      dbDisconnect(Mariacon)


    #3.4.2 Load updated spec to Datamart : No update ----

      # Define the number of reference to update
      df_max <- kdf_updated_spec %>% group_by() %>% summarise(var_max=n())
      var_max <- as.integer(df_max$var_max)


      if(var_max>0)
      {
        # Define the loop to update each ret one by one
        i=1
        for (i in 1:var_max)
        {
          #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
          Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
          query_update_t_pcm_ref_spec <- paste0("UPDATE `dmp`.`t_pcm_ref_spec` 
                                                SET `lsl`=",kdf_updated_spec$lsl[i],", 
                                                `usl`=",kdf_updated_spec$usl[i],",
                                                `low_control_limit`=",kdf_updated_spec$low_control_limit[i],", 
                                                `high_control_limit`=",kdf_updated_spec$high_control_limit[i],",
                                                `low_cens_limit`=",kdf_updated_spec$low_cens_limit[i],", 
                                                `high_cens_limit`=",kdf_updated_spec$high_cens_limit[i],",
                                                `lsl3`=",kdf_updated_spec$lsl3[i],", 
                                                `usl3`=",kdf_updated_spec$usl3[i],",
                                                `target`=",kdf_updated_spec$target[i],", 
                                                `type`='",kdf_updated_spec$type[i],"',
                                                 `cr`=",kdf_updated_spec$cr[i],", 
                                                 `cpk_flag`='",kdf_updated_spec$cpk_flag[i],"'
                                                 WHERE `ref_param_version_id`=",kdf_updated_spec$ref_param_version_id[i]," 
                                                 AND `ref_param_id`=",kdf_updated_spec$ref_param_id[i],"
                                                 AND `version`=",kdf_updated_spec$version[i],"
                                                 ") 
    
          df_t_pcm_ref_spec_update <- dbSendQuery(Mariacon, query_update_t_pcm_ref_spec)
          df_t_pcm_ref_spec_update_to_datamart <- dbFetch( df_t_pcm_ref_spec_update, n=-1)
          dbClearResult(df_t_pcm_ref_spec_update)              
          dbDisconnect(Mariacon)
      }
    }

#####################################################################################################################################################
####4 Update vgroup----
      # 4.1 Prepare vgroup table variables ----
      
      query_spec <- "SELECT *
                  FROM t_pcm_ref_spec"
      
      
      #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
      con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
      #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmd', host='mariadb-d1lx',port=as.integer(3306))
      dbsend  <- RMariaDB::dbSendQuery(con, query_spec)
      kdf_ref_spec <- RMariaDB::dbFetch(dbsend) 
      RMariaDB::dbClearResult(dbsend )
      RMariaDB::dbDisconnect(con)
      
      kdf_spec <- distinct(kdf_ref_spec)
      
      if(res==TRUE)
      {
        if(nrow(kdf_ref_spec)==0)
        {
          error=function(e){paste("ERROR FOUND ON DMP SPEC FOR REF VGROUP", e)}
          res=FALSE
        }
      }
      
      #kdf_spec = kdf_spec %>% mutate(ref_param_id=as.integer(parameter_id))
      
      kdf_vgroup0 = kdf_spec %>% 
        dplyr::select(ref_param_id, version, lsl, usl, target) %>% 
        dplyr::mutate(s_target = as.character(target), 
                      s_lsl = as.character(lsl), 
                      s_usl = as.character(usl), 
                      s_ref_param_id= paste0("R",as.character(ref_param_id)))
      
      kdf_vgroup <- kdf_vgroup0 %>%
        dplyr::select(ref_param_id, version, s_target, s_lsl, s_usl )%>%
        dplyr::arrange(ref_param_id, version )
      
      
      #4.2 Get dmp.t_pcm_ref_vgroup----
      
      dbquery  <-"select * from t_pcm_ref_vgroup"   
      
      con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
      #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
      dbsend  <- RMariaDB::dbSendQuery(con, dbquery )
      df_ref_vgroup <- RMariaDB::dbFetch(dbsend )
      RMariaDB::dbClearResult(dbsend )
      RMariaDB::dbDisconnect(con)
      
      
      if(res==TRUE)
      {
        if(nrow(df_ref_vgroup)==0)
        {
          error=function(e){paste("ERROR FOUND ON DMP VGROUP FOR REF VGROUP", e)}
          res=FALSE
        }
      }
      
      
      #4.3 Compare dbiltr with datamart ----
      
      #4.3.1 New ref_param_id ----
      
      xint_vgroup <- nrow(kdf_vgroup)
      print("Number of param available:")
      xint_vgroup
      
      
      kdf_new_vgroup_ref_param_id <- anti_join(kdf_vgroup,df_ref_vgroup,by=c("ref_param_id"))
      
      xint_nrow_new_vgroup_ref_param_id <- nrow(kdf_new_vgroup_ref_param_id)
      xint_nrow_new_vgroup_ref_param_id
      
      df_ref_param_id <- subset(df_ref_vgroup,select=c("ref_param_id"))
      df_ref_param_id <- unique(df_ref_param_id)
      
      kdf_old_vgroup_ref_param_id <- inner_join(kdf_vgroup,df_ref_param_id,by=c("ref_param_id"))
      
      xint_nrow_new_vgroup_ref_param_id <- nrow(kdf_new_vgroup_ref_param_id)
      print("Number of new parameters:")
      xint_nrow_new_vgroup_ref_param_id
      
      xint_nrow_old_vgroup_ref_param_id <- nrow(kdf_old_vgroup_ref_param_id)
      print("Number of already known parameters:")
      xint_nrow_old_vgroup_ref_param_id
      
      delta <- xint_vgroup - xint_nrow_new_vgroup_ref_param_id - xint_nrow_old_vgroup_ref_param_id
      print("Delta (should be =0):")
      delta
      
      #4.3.2 New ref_param_id+version ----
      kdf_new_vgroup_ref_param_id_version <- anti_join(kdf_old_vgroup_ref_param_id,df_ref_vgroup,by=c("ref_param_id","version"))
      kdf_new_vgroup_ref_param_id_version <- anti_join(kdf_new_vgroup_ref_param_id_version,kdf_new_vgroup_ref_param_id,by=c("ref_param_id","version","s_target","s_lsl","s_usl"))
      
      df_ref_param_id_version <- subset(df_ref_vgroup,select=c("ref_param_id","version"))
      df_ref_param_id_version <- unique(df_ref_param_id_version)
      
      kdf_old_vgroup_ref_param_id_version <- inner_join(kdf_old_vgroup_ref_param_id,df_ref_param_id_version,by=c("ref_param_id","version"))
      
      xint_nrow_new_vgroup_ref_param_id_version <- nrow(kdf_new_vgroup_ref_param_id_version)
      print("Number of new parameters+version:")
      xint_nrow_new_vgroup_ref_param_id_version
      
      xint_nrow_old_vgroup_ref_param_id_version <- nrow(kdf_old_vgroup_ref_param_id_version)
      print("Number of already known parameters+version:")
      xint_nrow_old_vgroup_ref_param_id_version
      
      delta2 <- xint_nrow_old_vgroup_ref_param_id - xint_nrow_new_vgroup_ref_param_id_version - xint_nrow_old_vgroup_ref_param_id_version
      print("Delta (should be =0):")
      delta2
      
      #4.3.3 Update of s_lsl, s_usl or s_target----
      
      kdf_update_vgroup <- anti_join(kdf_old_vgroup_ref_param_id_version,df_ref_vgroup,by=c("ref_param_id","version","s_target","s_lsl","s_usl"))
      
      kdf_unchanged <- inner_join(kdf_old_vgroup_ref_param_id_version,df_ref_vgroup,by=c("ref_param_id","version","s_target","s_lsl","s_usl"))
      
      xint_nrow_updated <- nrow(kdf_update_vgroup)
      print("Number of updated references:")
      xint_nrow_updated
      
      xint_unchanged <- nrow(kdf_unchanged)
      print("Number of unchanged line:")
      xint_unchanged
      
      delta3 <- xint_nrow_old_vgroup_ref_param_id_version - xint_nrow_updated - xint_unchanged
      print("Delta (should be =0):")
      delta3
      
      #4.3.4 New triplet s_target,s_lsl,s_usl ----
      kdf_new_triplet <- anti_join(kdf_new_vgroup_ref_param_id_version,df_ref_vgroup,by=c("ref_param_id","s_target","s_lsl","s_usl"))
      
      df_ref_param_id_target <- subset(df_ref_vgroup,select=c("ref_param_id","s_target","s_lsl","s_usl"))
      df_ref_param_id_target <- unique(df_ref_param_id_target)
      
      kdf_old_triplet <- inner_join(kdf_new_vgroup_ref_param_id_version,df_ref_param_id_target,by=c("ref_param_id","s_target","s_lsl","s_usl"))
      
      xint_nrow_new_triplet <- nrow(kdf_new_triplet)
      print("Number of new triplets:")
      xint_nrow_new_triplet
      
      xint_nrow_old_triplet <- nrow(kdf_old_triplet)
      print("Number of new ref_param_id+version without new triplet:")
      xint_nrow_old_triplet
      
      delta4 <- xint_nrow_new_vgroup_ref_param_id_version - xint_nrow_new_triplet - xint_nrow_old_triplet
      print("Delta (should be =0):")
      delta4
      
      #4.4 Delete all vgroup for parameters in updated limits or new ref_param+version and new limits ----
      
      kdf_to_delete <- rbind(kdf_new_triplet,kdf_update_vgroup)
      
      kdf_ref_param_to_delete <- subset(kdf_to_delete,select=c(ref_param_id))
      kdf_ref_param_to_delete <- unique(kdf_ref_param_to_delete)
      
      xint_ref_param_to_delete <- nrow(kdf_ref_param_to_delete)
      
      # Get the list of deleted parameters
      
      #kdf_ref_vgroup_deleted <- as.data.frame(NULL)
      
       if(xint_ref_param_to_delete>0)
       {
      #   # # Define the loop to update each ret one by one
      #   i=1
      #   #for (i in 1:xint_ref_param_to_delete)
      #   for (i in 2:2)
      #   {
      
           kxchar_parameter <- toString(sprintf("'%s'",unique(kdf_ref_param_to_delete[,'ref_param_id'])))
      
           query_ref_vgroup <- paste0("SELECT ref_param_id FROM t_pcm_ref_vgroup where ref_param_id in (",kxchar_parameter,") ")
      
           #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
           con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
           #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmd', host='mariadb-d1lx',port=as.integer(3306))
           dbsend  <- RMariaDB::dbSendQuery(con, query_ref_vgroup)
           kdf_ref_vgroup_deleted <- RMariaDB::dbFetch(dbsend) 
           RMariaDB::dbClearResult(dbsend )
           RMariaDB::dbDisconnect(con)
 
           
      #      kdf_ref_vgroup_deleted <- rbind(kdf_ref_vgroup_deleted,kdf_ref_vgroup_deleted_i)
      #   
      #   }
       #}
      
      #kdf_ref_vgroup_deleted <- distinct(kdf_ref_vgroup_deleted)
      xint_delete <- nrow(kdf_ref_vgroup_deleted)
      print("References deleted")
      xint_delete
      
      xint_to_add <- xint_delete + xint_nrow_new_triplet
      print("References to add at the end")
      xint_to_add
      
      
      #4.5  Define all ref_param_id+version from dbiltr & datamart
      
      #Get deleted ref_param_id
      kdf_to_delete_ref_param_id <- subset(kdf_to_delete,select=c(ref_param_id))
      kdf_to_delete_ref_param_id <- unique(kdf_to_delete_ref_param_id)
      
      #Get all ref_param+version list
      kdf_to_delete_ref <- merge(kdf_to_delete_ref_param_id,df_ref_vgroup,by=c("ref_param_id"))
      kdf_to_delete_ref_no_vgroup_limits <- subset(kdf_to_delete_ref,select=-c(vgroup,s_target,s_lsl,s_usl))
      kdf_to_delete_no_vgroup_limits <- subset(kdf_to_delete,select=-c(s_target,s_lsl,s_usl))
      
      kdf_to_delete_all <- rbind(kdf_to_delete_ref_no_vgroup_limits,kdf_to_delete_no_vgroup_limits)
      kdf_to_delete_all <- unique(kdf_to_delete_all)
      
      #Get last limits for all ref_param+version in any case
      kdf_to_delete_ref_no_vgroup <- subset(kdf_to_delete_ref,select=-c(vgroup))
      kdf_to_delete_no_vgroup <- kdf_to_delete
      
      kdf_to_delete_all_dbiltr <- merge(kdf_to_delete_all,kdf_to_delete_no_vgroup,by=c("ref_param_id","version"))
      
      kdf_missing <- anti_join(kdf_to_delete_all,kdf_to_delete_no_vgroup,by=c("ref_param_id","version"))
      
      kdf_missing <- merge(kdf_missing,kdf_to_delete_ref_no_vgroup,by=c("ref_param_id","version"))
      
      kdf_to_delete_all <- rbind(kdf_to_delete_all_dbiltr,kdf_missing)
      
      #kdf_ref_vgroup_deleted <- distinct(kdf_ref_vgroup_deleted)
      xint_param_version_limit <- nrow(kdf_to_delete_all)
      print("Parameter to add")
      xint_param_version_limit
      
      #Get good vgroup
      kdf_to_delete_ref_vgroup <- subset(kdf_to_delete,select=c(ref_param_id,s_target,s_lsl,s_usl))
      kdf_ref_vgroup <- subset(kdf_to_delete_ref,select=c(ref_param_id,s_target,s_lsl,s_usl,vgroup))
      
      kdf_to_delete_ref_vgroup <- unique(kdf_to_delete_ref_vgroup)
      kdf_ref_vgroup <- unique(kdf_ref_vgroup)
      
      kdf_to_delete_all_dbiltr <- inner_join(kdf_to_delete_all,kdf_to_delete_ref_vgroup,by=c("ref_param_id","s_target","s_lsl","s_usl"))
      
      kdf_to_delete_all_datamart <- anti_join(kdf_to_delete_all,kdf_to_delete_ref_vgroup,by=c("ref_param_id","s_target","s_lsl","s_usl"))
      #kdf_to_delete_all_datamart <- inner_join(kdf_to_delete_all_datamart,kdf_ref_vgroup,by=c("ref_param_id","s_target","s_lsl","s_usl"))
      
      kdf_to_delete_all_final <- rbind(kdf_to_delete_all_dbiltr, kdf_to_delete_all_datamart)
      kdf_to_delete_all_final <- unique(kdf_to_delete_all_final)
      
      
      #Get vgroup
      kdf_to_delete_all_final = kdf_to_delete_all_final %>%
        dplyr::mutate(s_ref_param_id= paste0("R",as.character(ref_param_id)))
      
      
      kdf_vgroup_creation = kdf_to_delete_all_final %>%
        dplyr::mutate(s_ref_param_id= paste0("R",as.character(ref_param_id)))%>%
        dplyr::select(s_ref_param_id, s_target, s_lsl, s_usl ) %>%
        dplyr::distinct() %>%
        dplyr::arrange(s_ref_param_id,  s_lsl, s_usl , s_target)%>%
        dplyr::group_by(s_ref_param_id )%>%
        dplyr::mutate(vgroup = 1:n())
      
      kdf_to_delete_all_final = merge(kdf_to_delete_all_final, kdf_vgroup_creation, by=c("s_ref_param_id", "s_target", "s_lsl", "s_usl"))
      
      kdf_to_delete_all_final = kdf_to_delete_all_final %>%
        dplyr::select(ref_param_id, vgroup, version, s_target, s_lsl, s_usl )%>%
        dplyr::arrange(ref_param_id, vgroup, version )
      
      #View(kdf_to_delete_all_final)
      
      #kdf_ref_vgroup_deleted <- distinct(kdf_ref_vgroup_deleted)
      xint_delete_then_add <- nrow(kdf_to_delete_all_final)
      print("Parameter in delete and add parameter")
      xint_delete_then_add
      
      # Delete previous references
      
      var_max <- nrow(kdf_ref_param_to_delete)
      
      if(var_max>0)
      {
        # # Define the loop to update each ret one by one
        i=1
        for (i in 1:var_max)
        {
          #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
          Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
          querydelete <- paste0("delete from `dmp`.`t_pcm_ref_vgroup` WHERE `ref_param_id`=",kdf_ref_param_to_delete$ref_param_id[i]," ")
          # emap_id IS NULL and
          delete <- dbSendQuery(Mariacon, querydelete)
          delete2 <- dbFetch(delete, n=-1)
          dbClearResult(delete)              
          dbDisconnect(Mariacon)
        }
      }
      
      #4.7 Load deleted vgroup to Datamart----
      
      if(nrow(kdf_to_delete_all_final)>0)
      {
        kdf_to_delete_all_final <- kdf_to_delete_all_final[c("vgroup", "ref_param_id","version","s_target","s_lsl","s_usl")]
      
        #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
        Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
        dbWriteTable(
          Mariacon,
          SQL('t_pcm_ref_vgroup'),
          kdf_to_delete_all_final,
          field.types = NULL,
          row.names = FALSE,
          overwrite = FALSE,
          append = TRUE,
          temporary = FALSE
        )
      
        dbDisconnect(Mariacon)
      }
      
      }
      # 4.6 Load new vgroup to Datamart ----
      
      kdf_new_vgroup_ref_param_id = kdf_new_vgroup_ref_param_id %>%
        dplyr::mutate(s_ref_param_id= paste0("R",as.character(ref_param_id)))
      
      
      #Get vgroup
      if(nrow(kdf_new_vgroup_ref_param_id)>0)
      {
      kdf_vgroup_creation = kdf_new_vgroup_ref_param_id %>%
        dplyr::select(s_ref_param_id, s_target, s_lsl, s_usl ) %>%
        dplyr::distinct() %>%
        dplyr::arrange(s_ref_param_id,  s_lsl, s_usl , s_target)%>%
        dplyr::group_by(s_ref_param_id )%>%
        dplyr::mutate(vgroup = 1:n())
      
      kdf_new_vgroup_ref_param_id = merge(kdf_new_vgroup_ref_param_id, kdf_vgroup_creation, by=c("s_ref_param_id", "s_target", "s_lsl", "s_usl"))
      
      kdf_new_vgroup_ref_param_id = kdf_new_vgroup_ref_param_id %>%
        dplyr::select(ref_param_id, vgroup, version, s_target, s_lsl, s_usl )%>%
        dplyr::arrange(ref_param_id, vgroup, version )
      
      
      kdf_new_vgroup_ref_param_id <- kdf_new_vgroup_ref_param_id[c("vgroup", "ref_param_id","version","s_target","s_lsl","s_usl")]
      
      xint_new_add <- nrow(kdf_new_vgroup_ref_param_id)
      print("Parameter totally new")
      xint_new_add
      
      #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
      Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
      dbWriteTable(
        Mariacon,
        SQL('t_pcm_ref_vgroup'),
        kdf_new_vgroup_ref_param_id,
        field.types = NULL,
        row.names = FALSE,
        overwrite = FALSE,
        append = TRUE,
        temporary = FALSE
      )
      
      dbDisconnect(Mariacon)
      
      }
      
      #4.8 Load new ref_param_id+version with already known triplets----
      
      #Get last version of dmp.t_pcm_ref_vgroup to avoid previously deleted ref_param_id problem----
      
      dbquery  <-"select * from t_pcm_ref_vgroup"   
      
      con <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
      #con <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
      dbsend  <- RMariaDB::dbSendQuery(con, dbquery )
      df_ref_vgroup <- RMariaDB::dbFetch(dbsend )
      RMariaDB::dbClearResult(dbsend )
      RMariaDB::dbDisconnect(con)
      
      
      kdf_get_vgroup <- subset(df_ref_vgroup,select=c("vgroup","ref_param_id","s_target","s_lsl","s_usl"))
      kdf_get_vgroup <- unique(kdf_get_vgroup)
      
      kdf_old_triplet <- merge(kdf_old_triplet,kdf_get_vgroup,by=c("ref_param_id","s_target","s_lsl","s_usl"),all.x=TRUE)
      
      
      kdf_old_triplet <- kdf_old_triplet[c("vgroup", "ref_param_id","version","s_target","s_lsl","s_usl")]
      
      
      
      #Mariacon <- dbConnect(RMariaDB::MariaDB(), user='appdatamart', password='appdatamart1', dbname='dmq', host='mariadb-d1lx',port=as.integer(3306))
      Mariacon <- dbConnect(RMariaDB::MariaDB(), user=userDM, password=pwDM, dbname=dbDM, host=hostDM, port=4306)
      dbWriteTable(
        Mariacon,
        SQL('t_pcm_ref_vgroup'),
        kdf_old_triplet,
        field.types = NULL,
        row.names = FALSE,
        overwrite = FALSE,
        append = TRUE,
        temporary = FALSE
      )
      
      dbDisconnect(Mariacon)

status = 'E'
if ((isTRUE (res))){
    message("RETURNCODE=0")
    status = 'D'
}else{
    print(res)
    message("RETURNCODE=2")
    status = 'E'
}